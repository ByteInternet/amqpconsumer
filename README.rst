=============
amqpconsumer
=============

A Python module to facilitate listening for and acting on AMQP events.

Usage
-----

Example:

.. code-block:: python

    import logging

    from amqpconsumer.events import EventConsumer


    def handler(event):
        print("Got event:", event)


    def main():
        logging.basicConfig(level=logging.INFO)
        consumer = EventConsumer('amqp://guest:guest@localhost:5672/%2f',
                                 'testqueue',
                                 handler)
        try:
            consumer.run()
        except KeyboardInterrupt:
            consumer.stop()


    if __name__ == '__main__':
        main()


Tracing
-------
For every consumed message the consumer extracts OpenTelemetry trace context from the
AMQP message headers and wraps the handler call in a consumer span, continuing the
publisher's trace when the message carries one (messages without trace headers simply
start a trace of their own). This only depends on ``opentelemetry-api``, for applications
without a configured OpenTelemetry backend all tracing calls are no-ops and the behaviour
is unchanged. To get the spans into your tracing backend, configure an OpenTelemetry SDK
in your application (for example by enabling the Sentry SDK's OpenTelemetry support).


Running tests
-------------
Install `uv <https://docs.astral.sh/uv/>`_ and run ``uv run pytest tests``.


=====
About
=====
This software is brought to you by Byte, a webhosting provider based in Amsterdam, The Netherlands. We specialize in
fast and secure Magento hosting and scalable cluster hosting.

Check out our `Github page <https://github.com/ByteInternet>`_ for more open source software or `our site <https://www.byte.nl>`_
to learn about our products and technologies. Look interesting? Reach out about joining `the team <https://www.byte.nl/vacatures>`_.
Or just drop by for a cup of excellent coffee if you're in town!
