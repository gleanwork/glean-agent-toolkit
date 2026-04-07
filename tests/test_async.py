"""Tests for async support."""

import asyncio
from unittest.mock import MagicMock

import pytest

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.spec import ToolSpec
from glean.agent_toolkit.tools._common import arun_tool
from glean.agent_toolkit.tools.search import search


def _mock_client(return_value: object = None) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.client.tools.run.return_value = return_value or {"data": "mock"}
    return mock


def test_tool_spec_has_async_function() -> None:
    spec = search.tool_spec
    assert spec.async_function is not None
    assert asyncio.iscoroutinefunction(spec.async_function)


async def test_async_function_returns_same_as_sync() -> None:
    ctx = GleanContext(client=_mock_client({"result": "async_test"}))
    sync_result = search(ctx, query="test")

    ctx2 = GleanContext(client=_mock_client({"result": "async_test"}))
    async_result = await search.tool_spec.async_function(ctx2, query="test")

    assert sync_result["status"] == "ok"
    assert async_result["status"] == "ok"
    assert sync_result["result"] == async_result["result"]


async def test_arun_tool() -> None:
    mock = _mock_client({"data": "arun"})
    from glean.api_client import models

    params = {"query": models.ToolsCallParameter(name="query", value="test")}
    result = await arun_tool("Glean Search", params, client=mock)

    assert result["status"] == "ok"
    assert result["result"] == {"data": "arun"}


async def test_arun_tool_error() -> None:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.client.tools.run.side_effect = Exception("async error")

    from glean.api_client import models

    params = {"query": models.ToolsCallParameter(name="query", value="test")}
    result = await arun_tool("Glean Search", params, client=mock)

    assert result["status"] == "error"
    assert result["error"] == "async error"


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
    from glean.agent_toolkit.registry import get_registry

    import glean.agent_toolkit.tools  # noqa: F401

    for spec in get_registry().list():
        assert spec.async_function is not None, f"{spec.name} missing async_function"
        assert asyncio.iscoroutinefunction(spec.async_function), (
            f"{spec.name} async_function is not a coroutine"
        )
