"""Unit tests for retry-config env parsing and seconds-to-milliseconds conversion.

The ``GLEAN_RETRY_*`` environment variables are documented in seconds, but the
Speakeasy-generated ``BackoffStrategy`` consumes integer milliseconds (its
retry loop sleeps ``initial_interval / 1000`` seconds and compares elapsed
wall-clock milliseconds to ``max_elapsed_time``). Regression: values used to
be passed through ``round(seconds)`` as if they were already milliseconds,
turning a 1s backoff into 1ms.
"""

from __future__ import annotations

import pytest

from glean.agent_toolkit.context import _build_retry_config, _parse_retry_env_float


def test_defaults_convert_seconds_to_milliseconds(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "GLEAN_RETRY_INITIAL",
        "GLEAN_RETRY_MAX",
        "GLEAN_RETRY_MULTIPLIER",
        "GLEAN_RETRY_MAX_ELAPSED",
    ):
        monkeypatch.delenv(var, raising=False)

    config = _build_retry_config()

    assert config.backoff.initial_interval == 1000  # 1.0 s
    assert config.backoff.max_interval == 50000  # 50.0 s
    assert config.backoff.max_elapsed_time == 60000  # 60.0 s
    assert config.backoff.exponent == pytest.approx(1.1)
    assert config.strategy == "backoff"
    assert config.retry_connection_errors is True


def test_sub_second_values_survive_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    """0.5 s must become 500 ms, not round(0.5) == 0."""
    monkeypatch.setenv("GLEAN_RETRY_INITIAL", "0.5")
    monkeypatch.setenv("GLEAN_RETRY_MAX", "2.5")
    monkeypatch.setenv("GLEAN_RETRY_MAX_ELAPSED", "0.25")

    config = _build_retry_config()

    assert config.backoff.initial_interval == 500
    assert config.backoff.max_interval == 2500
    assert config.backoff.max_elapsed_time == 250


def test_intervals_are_integers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GLEAN_RETRY_INITIAL", "0.0015")

    config = _build_retry_config()

    assert isinstance(config.backoff.initial_interval, int)
    assert isinstance(config.backoff.max_interval, int)
    assert isinstance(config.backoff.max_elapsed_time, int)


def test_multiplier_stays_a_float_and_unscaled(monkeypatch: pytest.MonkeyPatch) -> None:
    """The exponent is a unitless multiplier and must not be ms-scaled."""
    monkeypatch.setenv("GLEAN_RETRY_MULTIPLIER", "2.0")

    config = _build_retry_config()

    assert config.backoff.exponent == pytest.approx(2.0)


def test_invalid_env_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GLEAN_RETRY_INITIAL", "not-a-number")

    config = _build_retry_config()

    assert config.backoff.initial_interval == 1000


def test_parse_retry_env_float(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GLEAN_RETRY_INITIAL", raising=False)
    assert _parse_retry_env_float("GLEAN_RETRY_INITIAL", 3.0) == 3.0

    monkeypatch.setenv("GLEAN_RETRY_INITIAL", "0.75")
    assert _parse_retry_env_float("GLEAN_RETRY_INITIAL", 3.0) == 0.75

    monkeypatch.setenv("GLEAN_RETRY_INITIAL", "")
    assert _parse_retry_env_float("GLEAN_RETRY_INITIAL", 3.0) == 3.0
