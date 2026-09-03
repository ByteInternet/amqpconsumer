# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.1] - 2026-09-03

### Added
- PyPI publishing on release

## [1.8.0] - 2026-07-30

### Added
- OpenTelemetry tracing support: `on_message` extracts trace context from the AMQP message headers and wraps the handler call in a consumer span, so handling continues the publisher's trace (see the eventsender 1.3.0 counterpart). Messages without trace headers start a trace of their own
- `opentelemetry-api` dependency. Without a configured OpenTelemetry backend all tracing calls are no-ops and behaviour is unchanged
- First test suite, run with `uv run pytest tests`
- `pyproject.toml` with uv support, replacing the legacy packaging files
- Tracing and test-running sections to the README

### Changed
- pika constraint from `>=1.0.0` to `>=1.3.2,<1.4`
- Minimum Python version is now 3.9, enforced via `requires-python` so installs on older interpreters keep resolving 1.7.4
- README usage example to Python 3 syntax

### Removed
- `setup.py`, `setup.cfg` and `MANIFEST.in`, replaced by `pyproject.toml`
- Obsolete Python 2 Debian packaging (nothing builds or consumes it anymore)

## [1.7.1] - 2021-04-22

### Removed
- The `stop_ioloop_on_close` argument since this is no longer in `pika>=1.0.0`

### Changed
- Require at least `pika>=1.0.0` in setup.py, since removing the `stop_ioloop_on_close` argument would change behaviour on versions still using `pika<1.0.0`
