import mock
from amqpconsumer.events import EventConsumer


def get_consumer(
    amqp_url='amqps://fake-url',
    queue='fake-queue',
    handler=None,
    exchange=None,
    exchange_type=None,
    routing_key=None,
):
    consumer = EventConsumer(
        amqp_url=amqp_url,
        queue=queue,
        handler=handler,
        exchange=exchange,
        exchange_type=exchange_type,
        routing_key=routing_key,
    )
    consumer._connection = mock.MagicMock()
    consumer._channel = mock.Mock()
    return consumer


def get_consumer_with_exchange():
    mock_exchange = mock.Mock()
    consumer = get_consumer(exchange=mock_exchange, exchange_type='fake-type',
                            routing_key='fake-key')
    return consumer


def test_connect_calls_pika_selectconnection():
    consumer = get_consumer()
    with mock.patch('pika.SelectConnection') as mock_select:
        consumer.connect()

    mock_select.assert_called_once()


def test_on_connection_open():
    consumer = get_consumer()
    consumer.on_connection_open('??')

    consumer._connection.add_on_close_callback.assert_called_once_with(consumer.on_connection_closed)
    consumer._connection.channel.assert_called_once_with(on_open_callback=consumer.on_channel_open)


def test_on_connection_closed_reconnects():
    consumer = get_consumer()
    consumer.on_connection_closed('??', 'fake-code', 'fake-text')

    consumer._connection.add_timeout.assert_called_once_with(5, consumer.reconnect)


def test_on_connection_closed_stops_when_closing():
    consumer = get_consumer()
    consumer._closing = True
    consumer.on_connection_closed('??', 'fake-code', 'fake-text')

    consumer._connection.ioloop.stop.assert_called_once_with()


def test_open_channel_calls_connection_channel():
    consumer = get_consumer()
    consumer.open_channel()

    consumer._connection.channel.assert_called_once_with(on_open_callback=consumer.on_channel_open)


def test_on_channel_open():
    channel = mock.Mock()
    consumer = get_consumer()
    consumer.on_channel_open(channel)

    channel.add_on_close_callback.assert_called_once_with(consumer.on_channel_closed)
    channel.basic_qos.assert_called_once_with(prefetch_count=1, callback=consumer.on_qos_set)


def test_on_qos_set_when_exchange_is_none():
    consumer = get_consumer(exchange=None)
    consumer.on_qos_set('??')

    consumer._channel.queue_declare.assert_called_once_with(
        consumer.on_queue_declareok, consumer._queue, durable=True
    )


def test_on_exchange_declareok():
    consumer = get_consumer_with_exchange()
    consumer.on_exchange_declareok('??')

    consumer._channel.queue_declare.assert_called_once_with(
        consumer.on_queue_declareok, consumer._queue, durable=True
    )


def test_on_qos_set_when_exchange_is_something():
    consumer = get_consumer_with_exchange()
    consumer.on_qos_set('??')

    consumer._channel.exchange_declare.assert_called_once_with(
        consumer.on_exchange_declareok,
        consumer._exchange,
        consumer._exchange_type,
        durable=True,
    )


def test_on_queue_declareok_when_exchange_is_something():
    consumer = get_consumer_with_exchange()
    consumer.on_queue_declareok('??')

    consumer._channel.queue_bind(
        consumer.on_bindok, consumer._queue, consumer._exchange, consumer._routing_key
    )


def test_on_queue_declareok_when_exchange_is_none():
    consumer = get_consumer()
    consumer._channel.basic_consume.return_value = 'fake-tag'
    consumer.on_queue_declareok('??')

    consumer._channel.add_on_cancel_callback.assert_called_once_with(consumer.on_consumer_cancelled)
    consumer._channel.basic_consume.assert_called_once_with(consumer.on_message, consumer._queue)
    assert consumer._consumer_tag == 'fake-tag'


def test_on_bindok():
    consumer = get_consumer()
    consumer._channel.basic_consume.return_value = 'fake-tag'
    consumer.on_bindok('??')

    consumer._channel.add_on_cancel_callback.assert_called_once_with(consumer.on_consumer_cancelled)
    consumer._channel.basic_consume.assert_called_once_with(consumer.on_message, consumer._queue)
    assert consumer._consumer_tag == 'fake-tag'


def test_on_channel_closed():
    consumer = get_consumer()
    consumer.on_channel_closed('fake-channel', 'fake-code', 'fake-text')

    consumer._connection.close.assert_called_once()


def test_on_consumer_cancelled():
    consumer = get_consumer()
    consumer.on_consumer_cancelled('fake-frame')

    consumer._channel.close.assert_called_once()


def test_on_message():
    mock_handler = mock.Mock()
    consumer = get_consumer(handler=mock_handler)
    body = b'{"foo":"bar"}'
    mock_deliver = mock.Mock()
    mock_properties = mock.Mock()
    consumer.on_message('??', mock_deliver, mock_properties, body)

    mock_handler.assert_called_once_with({'foo': 'bar'})
    consumer._channel.basic_ack.assert_called_once_with(mock_deliver.delivery_tag)


def test_run():
    consumer = get_consumer()
    with mock.patch('pika.SelectConnection') as mock_select:
        consumer.run()

    mock_select.assert_called_once()
    consumer._connection.ioloop.start.assert_called_once()


def test_stop():
    consumer = get_consumer()
    consumer.stop()

    assert consumer._closing
    consumer._channel.basic_cancel.assert_called_once_with(
        consumer.on_cancelok, consumer._consumer_tag
    )
    consumer._connection.ioloop.start.assert_called_once()


def test_on_cancelok():
    consumer = get_consumer()
    consumer.on_cancelok('??')

    consumer._channel.close.assert_called_once_with()
