import logging
import pika
import json

logger = logging.getLogger(__name__)


class EventConsumer(object):
    """Basic consumer with event loop for RabbitMQ events.

    It takes an event handler that will be given all events from the provided
    queue. If the handler raises an exception, the run()-method that runs the
    event loop wil stop with that exception. To then gracefully shutdown the
    connection to RabbitMQ, call stop().

    Messages that are not valid JSON will be ignored.

    Based on the async consumer example from the pika docs:
    https://pika.readthedocs.org/en/latest/examples/asynchronous_consumer_example.html

    Usage:
    >>> def handler(event):
    >>>     print event

    >>> c = EventConsumer('amqp://rabbitmq.example.cm:6782/vhost', 'myqueue', handler)

    >>> try:
    >>>     c.run()  # Will run the event loop, passing each event into handler()
    >>> except KeyboardInterrupt:
    >>>     c.stop()  # Gracefully disconnect from RabbitMQ
    """

    # This class will string together all the async callbacks that are needed
    # before consuming. The flow is this:
    #
    # connect -> on_connection_open ->
    # open_channel -> on_channel_open ->
    # setup_exchange -> on_exchange_declareok -> (these 2 are skipped if no exchange is provided)
    # setup_queue -> on_queue_declareok ->
    # on_bindok (skipped if no exchange is provided) ->
    # start_consuming

    def __init__(self, amqp_url, queue, handler, exchange=None, exchange_type=None, routing_key=None):
        """Create a new instance of the consumer class, passing in the URL
        of RabbitMQ, the queue to listen to, and a callable handler that
        handles the events.

        The queue will be declared before consuming. If exchange, exchange_type,
        and routing_key are provided, it will also declare the exchange and bind
        the queue to it. Queue and exchange will be declared durable.

        :param str amqp_url: The AMQP url to connect with
        :param str queue: The queue to listen to
        :param function handler: The event handler that handles events
        :param str exchange: Optional name of exchange to declare
        :param str exchange_type: Optional type of exchange to declare
        :param str routing_key: Optional routing key of binding to create between exchange and queue
        """
        self._connection = None
        """:type: pika.SelectConnection"""

        self._channel = None
        self._consumer_tag = None
        self._closing = False
        self._handler = handler
        self._queue = queue
        self._url = amqp_url

        if ((exchange or exchange_type or routing_key)
                and not (exchange and exchange_type and routing_key)):
            raise RuntimeError("Either provide all of exchange, exchange_type, and routing_key, "
                               "or provide none of them to not declare and bind an exchange")

        self._exchange = exchange
        self._exchange_type = exchange_type
        self._routing_key = routing_key

    def connect(self):
        """Connect to RabbitMQ, returning the connection handle.

        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection
        """
        logger.debug('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     self.on_connection_open)

    def on_connection_open(self, _):
        """Called by pika once the connection to RabbitMQ has been established.

        It passes the handle to the connection object in case we need it,
        but in this case, we'll just mark it unused.

        :type _: pika.SelectConnection
        """
        logger.debug('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        """Add an on close callback that will be invoked by pika when
        RabbitMQ closes the connection to the consumer unexpectedly.
        """
        logger.debug('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, _, reply_code, reply_text):
        """Called by pika when the connection to RabbitMQ is closed
        unexpectedly.

        Since it is unexpected, we will reconnect to RabbitMQ if it disconnects.

        :param pika.connection.Connection _: The closed connection object
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given
        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            logger.warning('Connection closed, reopening in 5 seconds: (%s) %s', reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is closed.

        See the on_connection_closed method.
        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self._closing:
            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def on_channel_open(self, channel):
        """Called by pika when the channel has been opened.

        The channel object is passed in so we can make use of it. Since the
        channel is now open, we'll start consuming.

        :param pika.channel.Channel channel: The channel object
        """
        logger.debug('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_qos()

    def setup_qos(self):
        """Configure QoS to limit number of messages to prefetch """
        self._channel.basic_qos(prefetch_count=1, callback=self.on_qos_set)

    def on_qos_set(self, _):
        """Will be invoked when the QoS is configured"""
        if self._exchange:
            self.setup_exchange()
        else:
            self.setup_queue()

    def setup_exchange(self):
        """Declare the exchange

        When completed, the on_exchange_declareok method will be invoked by pika.
        """
        logger.debug('Declaring exchange %s', self._exchange)
        self._channel.exchange_declare(self.on_exchange_declareok,
                                       self._exchange,
                                       self._exchange_type,
                                       durable=True)

    def on_exchange_declareok(self, _):
        """Invoked by pika when the exchange is declared.

        :param pika.frame.Method _: Exchange.DeclareOk response frame
        """
        logger.debug("Exchange declared")
        self.setup_queue()

    def setup_queue(self):
        """Declare the queue

        When completed, the on_queue_declareok method will be invoked by pika.
        """
        logger.debug("Declaring queue %s" % self._queue)
        self._channel.queue_declare(self.on_queue_declareok, self._queue, durable=True)

    def on_queue_declareok(self, _):
        """Invoked by pika when queue is declared

        This method will start consuming or first bind the queue to the exchange
        if an exchange is provided.

        After binding, the on_bindok method will be invoked by pika.

        :param pika.frame.Method _: The Queue.DeclareOk frame
        """
        logger.debug("Binding %s to %s with %s", self._exchange, self._queue, self._routing_key)
        if self._exchange:
            self._channel.queue_bind(self.on_bindok, self._queue, self._exchange, self._routing_key)
        else:
            self.start_consuming()

    def on_bindok(self, _):
        """Invoked by pika after the queue is bound

        Starts consuming.

        :param pika.frame.Method _: The Queue.BindOk frame
        """
        logger.debug("Queue bound")
        self.start_consuming()

    def add_on_channel_close_callback(self):
        """Tells pika to call the on_channel_closed method if RabbitMQ
        unexpectedly closes the channel.
        """
        logger.debug('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Called by pika when RabbitMQ unexpectedly closes the channel.

        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection to
        shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed
        """
        logger.warning('Channel %d was closed: (%s) %s', channel, reply_code, reply_text)
        self._connection.close()

    def start_consuming(self):
        """Sets up the consumer.

        We do this by first calling add_on_cancel_callback so that the
        object is notified if RabbitMQ cancels the consumer. Then we issue
        a Basic.Consume command which returns the consumer tag that is used
        to uniquely identify the consumer with RabbitMQ. We keep the value
        to use it when we want to cancel consuming.

        The on_message method is passed in as a callback pika will invoke
        when a message is fully received.
        """
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                         self._queue)
        logger.info('Listening')

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the
        consumer for some reason.

        If RabbitMQ does cancel the consumer, on_consumer_cancelled will be
        invoked by pika.
        """
        logger.debug('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        logger.debug('Consumer was cancelled remotely, shutting down: %r', method_frame)
        if self._channel:
            self._channel.close()

    def on_message(self, _, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ.

        The channel is passed for your convenience. The basic_deliver object
        that is passed in carries the exchange, routing key, delivery tag
        and a redelivered flag for the message. The properties passed in is
        an instance of BasicProperties with the message properties and the
        body is the message that was sent.

        We'll json-decode the message body, and if that succeeds, call the
        handler that was given to us. Messages that contain invalid json
        will be discarded.

        :type _: pika.channel.Channel
        :type basic_deliver: pika.Spec.Basic.Deliver
        :type properties: pika.Spec.BasicProperties
        :type body: str|unicode
        """
        logger.debug('Received message # %s from %s: %s', basic_deliver.delivery_tag, properties.app_id, body)
        try:
            decoded = json.loads(body.decode('-utf-8'))
        except ValueError:
            logger.warning('Discarding message containing invalid json: %s', body)
        else:
            self._handler(decoded)

        self.acknowledge_message(basic_deliver.delivery_tag)

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ.

        :param int delivery_tag: The delivery tag from the Basic.Deliver frame
        """
        logger.debug('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def open_channel(self):
        """Open a new channel with RabbitMQ.

        When RabbitMQ responds that the channel is open, the on_channel_open
        callback will be invoked by pika.
        """
        logger.debug('Creating new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def run(self):
        """Start the consumer by connecting to RabbitMQ and then starting the
        IOLoop to block and allow the SelectConnection to operate.
        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the
        consumer with RabbitMQ.

        When RabbitMQ confirms the cancellation, on_cancelok will be invoked
        by pika, which will then closing the channel and connection.

        The IOLoop is started again, becuase this method is invoked when
        an exception is raised. This exception stops the IOLoop which needs
        to be running for pika to communicate with RabbitMQ. All of the
        commands issued prior to starting the IOLoop will be buffered but
        not processed.
        """
        logger.debug('Stopping')
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        logger.debug('Stopped')

    def stop_consuming(self):
        """Tell RabbitMQ that we would like to stop consuming."""
        if self._channel:
            logger.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def on_cancelok(self, _):
        """Called by pika when RabbitMQ acknowledges the cancellation of a
        consumer.

        At this point we will close the channel. This will invoke the
        on_channel_closed method once the channel has been closed, which
        will in-turn close the connection.

        :param pika.frame.Method _: The Basic.CancelOk frame
        """
        logger.debug('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly."""
        logger.debug('Closing the channel')
        self._channel.close()
