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


=====
About
=====
This software is brought to you by Byte, a webhosting provider based in Amsterdam, The Netherlands. We specialize in
fast and secure Magento hosting and scalable cluster hosting.

Check out our `Github page <https://github.com/ByteInternet>`_ for more open source software or `our site <https://www.byte.nl>`_
to learn about our products and technologies. Look interesting? Reach out about joining `the team <https://www.byte.nl/vacatures>`_.
Or just drop by for a cup of excellent coffee if you're in town!

[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/ByteInternet/python-events/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/ByteInternet/python-events/?branch=master)
