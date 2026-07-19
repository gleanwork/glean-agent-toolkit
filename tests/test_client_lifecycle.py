"""Regression tests for Glean client lifecycle management.

These tests use the REAL ``glean.api_client.Glean`` client (with HTTP
mocked at the transport layer via pytest-httpx) rather than MagicMock.
MagicMock has a no-op ``__exit__``, which hid a bug where every tool
call ran inside ``with client:`` and the SDK's ``__exit__`` closed the
shared httpx client, breaking all subsequent calls on the same context.
"""

from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.search import search

SERVER_URL = "https://example.glean.com"
TOOLS_CALL_URL = f"{SERVER_URL}/rest/api/v1/tools/call"


@pytest.fixture
def ctx() -> GleanContext:
    """A context pointing at a fake server with a fake token."""
    return GleanContext(api_token="fake-token", server_url=SERVER_URL)


def _mock_tools_call(httpx_mock: HTTPXMock, count: int = 1) -> None:
    for _ in range(count):
        httpx_mock.add_response(
            method="POST",
            url=TOOLS_CALL_URL,
            json={"rawResponse": {"results": []}},
        )


def test_second_tool_call_with_same_context_succeeds(
    ctx: GleanContext, httpx_mock: HTTPXMock
) -> None:
    """Two sequential tool calls on ONE context must both succeed.

    Regression: the first call used to close the shared client via
    ``with client:``, making the second call raise
    ``ValueError("client is required")`` from the SDK.
    """
    _mock_tools_call(httpx_mock, count=2)

    first = search(ctx, query="a")
    assert first["status"] == "ok", f"first call failed: {first['error']}"

    second = search(ctx, query="a")
    assert second["status"] == "ok", f"second call failed: {second['error']}"


def test_client_still_usable_after_tool_call(ctx: GleanContext, httpx_mock: HTTPXMock) -> None:
    """A tool call must not close or null the context's cached client."""
    _mock_tools_call(httpx_mock, count=1)

    client = ctx.get_client()
    result = search(ctx, query="a")
    assert result["status"] == "ok"

    # Same cached client instance, with a live underlying httpx client.
    assert ctx.get_client() is client
    httpx_client = client.sdk_configuration.client
    assert isinstance(httpx_client, httpx.Client)
    assert not httpx_client.is_closed


def test_close_closes_underlying_client(ctx: GleanContext) -> None:
    """GleanContext.close() closes the underlying httpx client."""
    client = ctx.get_client()
    httpx_client = client.sdk_configuration.client
    assert isinstance(httpx_client, httpx.Client)

    ctx.close()

    assert httpx_client.is_closed
    # Idempotent.
    ctx.close()


def test_context_manager_closes_client() -> None:
    """Using GleanContext as a context manager closes the client on exit."""
    with GleanContext(api_token="fake-token", server_url=SERVER_URL) as ctx:
        client = ctx.get_client()
        httpx_client = client.sdk_configuration.client
        assert isinstance(httpx_client, httpx.Client)
        assert not httpx_client.is_closed

    assert httpx_client.is_closed
