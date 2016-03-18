=============
amqpconsumer
=============

AMQP event listener

**Example:**

.. code-block:: python

    import logging

    from amqpconsumer.events import EventConsumer


    def handler(event):
        print "Got event:", event


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
