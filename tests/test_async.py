"""Tests for native async support.

Covers the async transport seam (``execute_tool_async``, backend
``execute_async``), the decorator's async semantics (thread offload for
sync functions, native pass-through for ``async def`` functions, the
``native_async`` override hook), the legacy ``arun_tool`` shim, and the
"no hidden thread hop" guarantee for built-in tools.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_httpx import HTTPXMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.registry import get_registry
from glean.agent_toolkit.spec import ToolSpec
from glean.agent_toolkit.tools._common import arun_tool
from glean.agent_toolkit.tools._transport import (
    ToolsCallBackend,
    TypedBackend,
    execute_tool_async,
    register_backend,
)
from glean.agent_toolkit.tools.search import search

try:
    from glean.agent_toolkit.adapters.langchain import HAS_LANGCHAIN
except ImportError:  # pragma: no cover
    HAS_LANGCHAIN = False

BASE_URL = "https://test-instance-be.glean.com"
SEARCH_URL = f"{BASE_URL}/rest/api/v1/search"
TOOLS_CALL_URL = f"{BASE_URL}/rest/api/v1/tools/call"

BUILTIN_TOOL_NAMES = {
    "glean_search",
    "glean_web_search",
    "glean_calendar_search",
    "glean_employee_search",
    "glean_code_search",
    "glean_gmail_search",
    "glean_outlook_search",
    "glean_read_document",
    "glean_chat",
}


def _mock_client(*, run_async_return: object = None) -> MagicMock:
    """Build a mock Glean client with native async endpoint stubs."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.client.tools.run.return_value = run_async_return or {"data": "mock"}
    mock.client.tools.run_async = AsyncMock(return_value=run_async_return or {"data": "mock"})
    # MagicMock children are not awaitable; typed async endpoints need
    # explicit AsyncMocks (their default return is a plain MagicMock,
    # matching what the sync endpoints return).
    mock.client.search.query_async = AsyncMock()
    mock.client.chat.create_async = AsyncMock()
    mock.client.documents.retrieve_async = AsyncMock()
    return mock


@pytest.fixture
def unregister_tools() -> Any:
    """Track tool names registered by a test and remove them afterwards."""
    names: list[str] = []
    yield names
    registry = get_registry()
    for name in names:
        registry._tools.pop(name, None)


# ---------------------------------------------------------------------------
# ToolSpec / registry invariants
# ---------------------------------------------------------------------------


def test_tool_spec_has_async_function() -> None:
    spec = search.tool_spec
    assert spec.async_function is not None
    assert asyncio.iscoroutinefunction(spec.async_function)


def test_spec_async_function_field() -> None:
    def dummy() -> str:
        return "hello"

    spec = ToolSpec(
        name="test",
        description="test",
        function=dummy,
        input_schema={},
        output_schema={},
    )
    assert spec.async_function is None

    async def async_dummy() -> str:
        return "hello"

    spec2 = ToolSpec(
        name="test",
        description="test",
        function=dummy,
        input_schema={},
        output_schema={},
        async_function=async_dummy,
    )
    assert spec2.async_function is not None
    assert asyncio.iscoroutinefunction(spec2.async_function)


def test_all_registered_tools_have_async() -> None:
    import glean.agent_toolkit.tools  # noqa: F401
    from glean.agent_toolkit.registry import get_registry

    for spec in get_registry().list():
        assert spec.async_function is not None, f"{spec.name} missing async_function"
        assert asyncio.iscoroutinefunction(spec.async_function), (
            f"{spec.name} async_function is not a coroutine"
        )


def test_builtin_tools_have_native_async_twins() -> None:
    """Every built-in tool's async_function is the seam twin, not a thread wrapper."""
    import glean.agent_toolkit.tools  # noqa: F401

    for name in BUILTIN_TOOL_NAMES:
        spec = get_registry().get(name)
        assert spec is not None, name
        assert spec.async_function is not None, name
        # The auto-generated thread wrapper is named `_async_wrapper`; the
        # native twins are either `<tool>_async` (seam factory) or the
        # explicit `_read_document_async`.
        assert spec.async_function.__name__ != "_async_wrapper", (
            f"{name} still uses the thread-offload async wrapper"
        )


# ---------------------------------------------------------------------------
# execute_tool_async: ok / error / truncation / no backend
# ---------------------------------------------------------------------------


async def test_execute_tool_async_ok(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"results": [], "hasMoreResults": False},
    )

    result = await execute_tool_async("glean_search", {"query": "hello"})

    assert result["status"] == "ok"
    assert result["result"] == {"results": [], "result_count": 0, "has_more_results": False}
    assert result["error"] is None

    request = httpx_mock.get_requests()[0]
    assert json.loads(request.content)["query"] == "hello"


async def test_execute_tool_async_http_401_maps_to_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        status_code=401,
        json={"error": "Invalid token"},
    )

    result = await execute_tool_async("glean_search", {"query": "anything"})

    assert result["status"] == "error"
    assert result["result"] is None
    assert result["error_type"] == "auth"
    assert result["suggested_action"] == "check_credentials"


async def test_execute_tool_async_no_backend_is_validation_error() -> None:
    result = await execute_tool_async("not_a_registered_tool", {})

    assert result["status"] == "error"
    assert result["error_type"] == "validation"
    assert "No backend registered" in (result["error"] or "")


async def test_execute_tool_async_truncates_oversized_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GLEAN_TOOL_MAX_RESULT_CHARS", "100")
    register_backend("async_trunc_test_tool", ToolsCallBackend("Trunc Tool"))

    client = _mock_client(run_async_return={"blob": "x" * 10_000})
    result = await execute_tool_async("async_trunc_test_tool", {"query": "big"}, client=client)

    assert result["status"] == "ok"
    payload = result["result"]
    assert payload is not None
    assert payload["truncated"] is True
    assert payload["max_chars"] == 100
    assert payload["content"].endswith("[truncated]")


# ---------------------------------------------------------------------------
# Backend.execute_async
# ---------------------------------------------------------------------------


async def test_tools_call_backend_uses_native_run_async() -> None:
    """execute_async must call the SDK's run_async, never the sync run."""
    client = _mock_client(run_async_return={"data": "native"})
    backend = ToolsCallBackend("Some Tool")

    payload = await backend.execute_async(client, {"query": "q", "skipped": None})

    assert payload == {"data": "native"}
    client.client.tools.run_async.assert_awaited_once()
    client.client.tools.run.assert_not_called()
    parameters = client.client.tools.run_async.await_args.kwargs["parameters"]
    assert set(parameters) == {"query"}  # None arguments are dropped


async def test_typed_backend_prefers_native_async_fn(no_thread_roundtrip: None) -> None:
    calls: list[str] = []

    def sync_fn(client: Any, *, value: str) -> dict[str, str]:
        calls.append("sync")
        return {"path": "sync", "value": value}

    async def async_fn(client: Any, *, value: str) -> dict[str, str]:
        calls.append("async")
        return {"path": "async", "value": value}

    backend = TypedBackend(sync_fn, async_fn=async_fn)
    payload = await backend.execute_async(MagicMock(), {"value": "v"})

    assert payload == {"path": "async", "value": "v"}
    assert calls == ["async"]


async def test_typed_backend_falls_back_to_thread_without_async_fn() -> None:
    import threading

    calling_threads: list[str] = []

    def sync_fn(client: Any, *, value: str) -> dict[str, str]:
        calling_threads.append(threading.current_thread().name)
        return {"path": "sync", "value": value}

    backend = TypedBackend(sync_fn)
    payload = await backend.execute_async(MagicMock(), {"value": "v"})

    assert payload == {"path": "sync", "value": "v"}
    # The sync fn must have been offloaded, not run on the event-loop thread.
    assert calling_threads != [threading.main_thread().name]


async def test_typed_backend_execute_async_applies_shaper() -> None:
    async def async_fn(client: Any) -> dict[str, int]:
        return {"raw": 1}

    backend = TypedBackend(lambda client: {"raw": 1}, lambda r: {"shaped": r["raw"]}, async_fn)
    assert await backend.execute_async(MagicMock(), {}) == {"shaped": 1}


# ---------------------------------------------------------------------------
# Built-in tools: native async end-to-end, no thread hop
# ---------------------------------------------------------------------------


async def test_builtin_async_function_hits_wire_without_threads(
    httpx_mock: HTTPXMock, no_thread_roundtrip: None
) -> None:
    """The seam twin must reach the HTTP layer natively async."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"results": [], "hasMoreResults": False},
    )

    assert search.tool_spec.async_function is not None
    result = await search.tool_spec.async_function(query="native")

    assert result["status"] == "ok"
    assert json.loads(httpx_mock.get_requests()[0].content)["query"] == "native"


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
async def test_langchain_ainvoke_builtin_never_touches_to_thread(
    httpx_mock: HTTPXMock, no_thread_roundtrip: None
) -> None:
    """FAILS if the built-in async path secretly round-trips through a thread."""
    httpx_mock.add_response(
        method="POST",
        url=TOOLS_CALL_URL,
        json={"rawResponse": {"results": [{"title": "hit"}]}},
    )

    from glean.agent_toolkit.tools.web_search import web_search

    tool = web_search.as_langchain_tool()
    output = await tool.ainvoke({"query": "async native"})

    # The adapter unwraps the ToolResult envelope: raw payload only.
    result = json.loads(output)
    assert result["rawResponse"] == {"results": [{"title": "hit"}]}


async def test_read_document_async_validates_arguments() -> None:
    """The native async twin keeps the exactly-one-locator validation."""
    spec = get_registry().get("glean_read_document")
    assert spec is not None and spec.async_function is not None

    result = await spec.async_function(None)

    assert result["status"] == "error"
    assert result["error_type"] == "validation"
    assert "exactly one" in (result["error"] or "")


# ---------------------------------------------------------------------------
# Sync/async parity through a mocked client
# ---------------------------------------------------------------------------


async def test_async_function_returns_same_as_sync() -> None:
    ctx = GleanContext(client=_mock_client(run_async_return={"result": "async_test"}))
    sync_result = search(ctx, query="test")

    ctx2 = GleanContext(client=_mock_client(run_async_return={"result": "async_test"}))
    assert search.tool_spec.async_function is not None
    async_result = await search.tool_spec.async_function(ctx2, query="test")

    assert sync_result["status"] == "ok"
    assert async_result["status"] == "ok"
    assert sync_result["result"] == async_result["result"]


# ---------------------------------------------------------------------------
# arun_tool legacy shim
# ---------------------------------------------------------------------------


async def test_arun_tool_uses_native_async() -> None:
    mock = _mock_client(run_async_return={"data": "arun"})
    from glean.api_client import models

    params = {"query": models.ToolsCallParameter(name="query", value="test")}
    result = await arun_tool("Glean Search", params, client=mock)

    assert result["status"] == "ok"
    assert result["result"] == {"data": "arun"}
    mock.client.tools.run_async.assert_awaited_once()
    mock.client.tools.run.assert_not_called()


async def test_arun_tool_error() -> None:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.client.tools.run_async = AsyncMock(side_effect=Exception("async error"))

    from glean.api_client import models

    params = {"query": models.ToolsCallParameter(name="query", value="test")}
    result = await arun_tool("Glean Search", params, client=mock)

    assert result["status"] == "error"
    assert result["error"] == "async error"


# ---------------------------------------------------------------------------
# Custom tools: sync functions get a per-call thread offload
# ---------------------------------------------------------------------------


async def test_sync_custom_tool_async_wrapper_offloads_to_thread(
    unregister_tools: list[str],
) -> None:
    import threading

    unregister_tools.append("async_test_sync_tool")
    calling_threads: list[str] = []

    @tool_spec(name="async_test_sync_tool", description="Sync tool")
    def sync_tool(value: str) -> str:
        calling_threads.append(threading.current_thread().name)
        return value.upper()

    assert sync_tool.tool_spec.async_function is not None
    result = await sync_tool.tool_spec.async_function(value="abc")

    assert result == "ABC"
    assert calling_threads != [threading.main_thread().name]


def test_no_module_global_executors() -> None:
    """The fork-unsafe module-global thread pools must stay deleted."""
    import glean.agent_toolkit.decorators as decorators
    import glean.agent_toolkit.tools._common as common

    assert not hasattr(decorators, "_EXECUTOR")
    assert not hasattr(common, "_EXECUTOR")


# ---------------------------------------------------------------------------
# Custom tools: async def functions are used natively
# ---------------------------------------------------------------------------


async def test_async_def_custom_tool_used_natively(
    unregister_tools: list[str], no_thread_roundtrip: None
) -> None:
    unregister_tools.append("async_test_native_tool")

    @tool_spec(name="async_test_native_tool", description="Native async tool")
    async def native_tool(value: str) -> str:
        await asyncio.sleep(0)
        return value[::-1]

    spec = native_tool.tool_spec
    assert spec.async_function is not None
    # The original async def is used natively as the async_function.
    assert spec.async_function is getattr(native_tool, "__wrapped__")

    # The decorated function itself stays awaitable.
    assert asyncio.iscoroutinefunction(native_tool)
    assert await native_tool(value="abc") == "cba"
    assert await spec.async_function(value="abc") == "cba"


def test_async_def_custom_tool_sync_bridge_outside_loop(
    unregister_tools: list[str],
) -> None:
    """Sync callers outside an event loop get the result via asyncio.run."""
    unregister_tools.append("async_test_bridge_tool")

    @tool_spec(name="async_test_bridge_tool", description="Native async tool")
    async def bridge_tool(value: str) -> str:
        await asyncio.sleep(0)
        return value * 2

    result = bridge_tool.tool_spec.function(value="ab")
    assert result == "abab"


async def test_async_def_custom_tool_sync_call_in_loop_raises(
    unregister_tools: list[str],
) -> None:
    """Sync-calling an async tool inside a running loop is a clear error."""
    unregister_tools.append("async_test_loop_error_tool")

    @tool_spec(name="async_test_loop_error_tool", description="Native async tool")
    async def loop_tool(value: str) -> str:
        return value

    with pytest.raises(RuntimeError, match="async function.*running event loop"):
        loop_tool.tool_spec.function(value="x")


# ---------------------------------------------------------------------------
# native_async override hook
# ---------------------------------------------------------------------------


async def test_native_async_hook_overrides_generated_wrapper(
    unregister_tools: list[str], no_thread_roundtrip: None
) -> None:
    unregister_tools.append("async_test_override_tool")

    @tool_spec(name="async_test_override_tool", description="Overridable tool")
    def override_tool(value: str) -> str:
        return "sync"

    @override_tool.native_async
    async def _override_tool_async(value: str) -> str:
        return "native"

    spec = override_tool.tool_spec
    assert spec.async_function is _override_tool_async
    assert spec.async_function is not None
    assert await spec.async_function(value="x") == "native"
    # The sync contract is unchanged.
    assert override_tool(value="x") == "sync"
