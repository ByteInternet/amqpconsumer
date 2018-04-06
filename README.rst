=============
amqpconsumer
=============

A Python module to facilitate listening for and acting on AMQP events.

Usage
-----

See `example_listener.py <https://github.com/ByteInternet/amqpconsumer/blob/master/example_listener.py>`_ for a code snippet.

Development
-----------

We recommend setting up a virtual environment for the project. All the following commands assume you've activated the virtual environment.

Make sure both module and development dependencies are installed:

.. code-block:: bash

    pip install -e . -r requirements-dev.txt

Run tests:

.. code-block:: bash

    pytest

If you want to generate code coverage statistics:

.. code-block:: bash

    pytest --cov amqpconsumer --cov-report html

Then open `htmlcov/index.html` in your favorite web browser.

Run linting and static analysis:

.. code-block:: bash

    prospector

=====
About
=====
This software is brought to you by Byte, a webhosting provider based in Amsterdam, The Netherlands. We specialize in
fast and secure Magento hosting and scalable cluster hosting.

Check out our `Github page <https://github.com/ByteInternet>`_ for more open source software or `our site <https://www.byte.nl>`_
to learn about our products and technologies. Look interesting? Reach out about joining `the team <https://www.byte.nl/vacatures>`_.
Or just drop by for a cup of excellent coffee if you're in town!

[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/ByteInternet/python-events/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/ByteInternet/python-events/?branch=master)
