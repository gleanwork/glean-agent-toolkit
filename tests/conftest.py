"""Global fixtures for tests."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def mock_glean_env_vars() -> Generator[None, None, None]:
    """Mock Glean environment variables for all tests.

    This ensures the API client can be created properly while the HTTP
    layer is mocked (e.g. via pytest-httpx) in transport-level tests.
    """
    with patch.dict(os.environ, {
        "GLEAN_API_TOKEN": "fake_token_for_testing",
        "GLEAN_SERVER_URL": "https://test-instance-be.glean.com",
    }):
        yield


@pytest.fixture
def no_thread_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if an async invocation round-trips through a thread.

    Poisons ``asyncio.to_thread`` (the toolkit's only thread-offload
    mechanism) and the sync ``httpx.Client.send`` (which any hidden
    sync-client round-trip would have to use), so a truly native async
    chain is the only way for the invocation to succeed.

    The Glean SDK's own async path legitimately offloads request
    *serialization* via its ``run_sync_in_thread`` helper while keeping
    HTTP I/O native async; that helper is inlined here so the
    ``asyncio.to_thread`` poison only trips on toolkit-level thread hops.
    """
    import glean.api_client.basesdk as basesdk

    async def _inline_run_sync(func: Any, *args: Any) -> Any:
        return func(*args)

    monkeypatch.setattr(basesdk, "run_sync_in_thread", _inline_run_sync)

    async def _no_to_thread(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "async invocation must not round-trip through asyncio.to_thread"
        )

    monkeypatch.setattr(asyncio, "to_thread", _no_to_thread)

    def _no_sync_send(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("async invocation must not use the sync HTTP client")

    monkeypatch.setattr(httpx.Client, "send", _no_sync_send)
