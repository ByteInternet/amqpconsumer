import json
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

from amqpconsumer.events import EventConsumer

TRACE_ID = 'abcdefabcdefabcdefabcdefabcdef12'
SPAN_ID = 'abcdefabcdef1234'


class OnMessageTestCase(TestCase):
    def setUp(self):
        self.handler = Mock()
        self.consumer = EventConsumer('amqp://user:pass@host:5672/%2f', 'some_queue', self.handler)
        self.consumer._channel = Mock()
        self.basic_deliver = Mock(delivery_tag=999, routing_key='some_key', exchange='some_exchange')
        self.properties = Mock(headers=None, app_id='some_app')
        self.event = {'type': 'some_event', 'data': [1, 2, 3]}
        self.body = json.dumps(self.event).encode('utf-8')

    def on_message(self):
        self.consumer.on_message(Mock(), self.basic_deliver, self.properties, self.body)


class TestOnMessage(OnMessageTestCase):
    def test_calls_handler_with_decoded_event(self):
        self.on_message()

        self.handler.assert_called_once_with(self.event)

    def test_acknowledges_message_after_handling(self):
        self.on_message()

        self.consumer._channel.basic_ack.assert_called_once_with(delivery_tag=999)

    def test_discards_invalid_json_without_calling_handler_but_still_acknowledges(self):
        self.body = b'not json'

        self.on_message()

        self.handler.assert_not_called()
        self.consumer._channel.basic_ack.assert_called_once_with(delivery_tag=999)

    def test_handler_exception_propagates_and_message_is_not_acknowledged(self):
        self.handler.side_effect = ValueError('boom')

        with self.assertRaises(ValueError):
            self.on_message()

        self.consumer._channel.basic_ack.assert_not_called()

    def test_calls_handler_with_non_dict_json(self):
        self.body = json.dumps([1, 2, 3]).encode('utf-8')

        self.on_message()

        self.handler.assert_called_once_with([1, 2, 3])


class TestOnMessageTracing(OnMessageTestCase):
    def setUp(self):
        super().setUp()
        self.exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        patcher = patch('amqpconsumer.events.tracer', provider.get_tracer('test'))
        self.addCleanup(patcher.stop)
        patcher.start()

    def get_span(self):
        return self.exporter.get_finished_spans()[0]

    def test_creates_consumer_span_with_messaging_attributes(self):
        self.on_message()

        span = self.get_span()
        self.assertEqual(span.name, 'process some_event')
        self.assertEqual(span.kind, SpanKind.CONSUMER)
        self.assertEqual(span.attributes['messaging.system'], 'rabbitmq')
        self.assertEqual(span.attributes['messaging.operation.name'], 'process')
        self.assertEqual(span.attributes['messaging.operation.type'], 'process')
        self.assertEqual(span.attributes['messaging.destination.name'], 'some_queue')
        self.assertEqual(span.attributes['messaging.rabbitmq.destination.routing_key'], 'some_key')
        self.assertEqual(span.attributes['event.type'], 'some_event')

    def test_continues_trace_from_message_headers(self):
        self.properties.headers = {'traceparent': '00-{}-{}-01'.format(TRACE_ID, SPAN_ID)}

        self.on_message()

        span = self.get_span()
        self.assertEqual(span.context.trace_id, int(TRACE_ID, 16))
        self.assertEqual(span.parent.span_id, int(SPAN_ID, 16))

    def test_starts_new_trace_when_message_has_no_headers(self):
        self.on_message()

        span = self.get_span()
        self.assertIsNone(span.parent)

    def test_does_not_create_span_for_invalid_json(self):
        self.body = b'not json'

        self.on_message()

        self.assertEqual(self.exporter.get_finished_spans(), ())

    def test_handler_exception_is_recorded_on_span_and_reraised(self):
        self.handler.side_effect = ValueError('boom')

        with self.assertRaises(ValueError):
            self.on_message()

        span = self.get_span()
        self.assertEqual(span.status.status_code, StatusCode.ERROR)

    def test_uses_queue_name_as_span_name_when_event_has_no_type(self):
        self.body = json.dumps({'data': 'no type key'}).encode('utf-8')

        self.on_message()

        self.assertEqual(self.get_span().name, 'process some_queue')
