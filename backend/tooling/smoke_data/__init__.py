"""TE-1 smoke-test data harness.

This package is testing/tooling code only. It is never imported by
``app.main`` or any HTTP route, and it exposes no public API endpoint.
It seeds and cleans up demo/regression data by calling the same
service-layer functions the real API routes use, so validations and
lifecycle guards run exactly as they do in production traffic.
"""
