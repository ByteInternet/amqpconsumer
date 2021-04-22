<h1>Changelog</h1>
<h2>1.7.1</h2>
Remove the `stop_ioloop_on_close` argument since this is no longer in `pika>=1.0.0`.
Since removing this argument will change behaviour on version still using `pika<1.0.0`
make sure we require at least `pika>1.0.0` in setup.py so people installing this new
version will not have changed behaviour.
