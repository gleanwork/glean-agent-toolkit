"""Gating, marker registration, and fixtures for the live e2e suite.

These tests hit a REAL Glean instance. They never run unless the caller
explicitly opts in:

- ``GLEAN_API_TOKEN`` must be set, AND
- ``GLEAN_SERVER_URL`` or ``GLEAN_INSTANCE`` must be set, AND
- ``GLEAN_E2E=1`` must be set (explicit opt-in so a developer with real
  credentials in their shell cannot hit a live instance by accident when
  running the normal suite).

When the gate is closed every test in this directory is skipped with a
one-line reason explaining what is missing.

The ``e2e`` marker is registered here (not in pyproject.toml) via
``pytest_configure`` so it satisfies ``--strict-markers``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_E2E_DIR = Path(__file__).parent.resolve()


def _gate_skip_reason() -> str | None:
    """Return a one-line skip reason when the live-e2e gate is closed, else None."""
    missing: list[str] = []
    if not os.environ.get("GLEAN_API_TOKEN"):
        missing.append("GLEAN_API_TOKEN")
    if not (os.environ.get("GLEAN_SERVER_URL") or os.environ.get("GLEAN_INSTANCE")):
        missing.append("GLEAN_SERVER_URL (or GLEAN_INSTANCE)")

    if missing:
        return f"e2e: missing live credentials: {', '.join(missing)}; also requires GLEAN_E2E=1"

    if os.environ.get("GLEAN_E2E") != "1":
        return (
            "e2e: credentials present but GLEAN_E2E=1 not set "
            "(explicit opt-in required before hitting a live Glean instance)"
        )

    return None


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``e2e`` marker (pyproject registration is intentionally avoided)."""
    config.addinivalue_line(
        "markers",
        "e2e: live end-to-end test against a real Glean instance "
        "(requires GLEAN_E2E=1 plus GLEAN_API_TOKEN and GLEAN_SERVER_URL/GLEAN_INSTANCE)",
    )


def _is_e2e_item(item: pytest.Item) -> bool:
    path = getattr(item, "path", None)
    if path is None:  # pragma: no cover - pytest<7 fallback
        path = Path(str(item.fspath))
    try:
        return _E2E_DIR in Path(path).resolve().parents
    except (OSError, ValueError):  # pragma: no cover - defensive
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark every test under tests/e2e as ``e2e`` and enforce the opt-in gate."""
    reason = _gate_skip_reason()
    skip_marker = pytest.mark.skip(reason=reason) if reason else None

    for item in items:
        if not _is_e2e_item(item):
            continue
        item.add_marker(pytest.mark.e2e)
        if skip_marker is not None:
            item.add_marker(skip_marker)


@pytest.fixture(autouse=True)
def mock_glean_env_vars() -> None:
    """Override the repo-wide autouse fixture that fakes Glean credentials.

    tests/conftest.py patches ``GLEAN_API_TOKEN``/``GLEAN_SERVER_URL`` to fake
    values for the mocked unit suite. Live e2e tests must see the real
    environment, so this no-op override shadows it for this directory.
    """
    return None


# The shared QA test instance (salessavvy-test) runs release-qualification
# sweeps after every deploy, so 429s and latency spikes are expected in
# contention windows. Lean on the toolkit's built-in RetryConfig
# (GLEAN_RETRY_* envs, seconds) with generous defaults instead of adding a
# custom retry layer. Explicit values in the caller's environment win.
_DEFAULT_RETRY_ENVS = {
    "GLEAN_RETRY_INITIAL": "1",
    "GLEAN_RETRY_MAX": "30",
    "GLEAN_RETRY_MAX_ELAPSED": "120",
}


@pytest.fixture(autouse=True)
def _generous_retry_envs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default to generous GLEAN_RETRY_* settings for live calls (e2e dir only)."""
    for name, value in _DEFAULT_RETRY_ENVS.items():
        if not os.environ.get(name):
            monkeypatch.setenv(name, value)
