from distutils.core import setup

setup(
    name='python-events',
    version='20140325.2',
    packages=['byte_events'],
    url='https://github.com/ByteInternet/python-events',
    license='3-clause BSD',
    author='Maarten van Schaik',
    author_email='maarten@byte.nl',
    description='RabbitMQ event listener',
    install_requires=['pika>=0.9.8']
)
