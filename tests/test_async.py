"""Tests for async support across tools, adapters, and ToolSpec."""

import asyncio
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.spec import ToolSpec
from glean.agent_toolkit.tools._common import arun_tool, run_tool
from glean.api_client import models


class TestArunTool:
    """Test the arun_tool async wrapper."""

    async def test_arun_tool_delegates_to_run_tool(self):
        """arun_tool should produce the same result as run_tool."""
        mock_result = {"documents": [{"title": "Test"}]}
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test"),
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = MagicMock()
            mock_client.client.tools.run.return_value = mock_result
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = await arun_tool("Test Tool", parameters)

            assert result == {"result": mock_result}
            mock_client.client.tools.run.assert_called_once_with(
                name="Test Tool",
                parameters=parameters,
            )

    async def test_arun_tool_propagates_errors(self):
        """arun_tool should return error dict on failure, same as run_tool."""
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test"),
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = MagicMock()
            mock_client.client.tools.run.side_effect = Exception("API Error")
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = await arun_tool("Test Tool", parameters)

            assert result == {"error": "API Error", "result": None}


class TestToolSpecAsyncFunction:
    """Test that ToolSpec has async_function support."""

    def test_toolspec_has_async_function_field(self):
        """ToolSpec should accept an async_function parameter."""

        async def async_add(a: int, b: int) -> int:
            return a + b

        def sync_add(a: int, b: int) -> int:
            return a + b

        spec = ToolSpec(
            name="add",
            description="Add two numbers",
            function=sync_add,
            async_function=async_add,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "integer"},
        )

        assert spec.async_function is async_add
        assert spec.function is sync_add

    def test_toolspec_async_function_defaults_to_none(self):
        """ToolSpec should default async_function to None."""

        def sync_add(a: int, b: int) -> int:
            return a + b

        spec = ToolSpec(
            name="add",
            description="Add two numbers",
            function=sync_add,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "integer"},
        )

        assert spec.async_function is None


class TestDecoratorAsyncGeneration:
    """Test that the @tool_spec decorator auto-generates async wrappers."""

    def test_decorated_function_has_acall(self):
        """Decorated functions should have an acall method."""
        from glean.agent_toolkit.tools.search import search

        assert hasattr(search, "acall")
        assert asyncio.iscoroutinefunction(search.acall)

    def test_decorated_function_has_async_on_toolspec(self):
        """The tool_spec attached to a decorated function should have async_function set."""
        from glean.agent_toolkit.tools.search import search

        assert search.tool_spec.async_function is not None
        assert asyncio.iscoroutinefunction(search.tool_spec.async_function)

    async def test_acall_produces_same_result_as_sync(self):
        """acall should produce the same result as the sync call."""
        from glean.agent_toolkit.decorators import tool_spec

        @tool_spec(name="test_add", description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        sync_result = add(3, 5)
        async_result = await add.acall(3, 5)

        assert sync_result == async_result == 8

    def test_sync_call_unchanged(self):
        """The sync __call__ should still work as before."""
        from glean.agent_toolkit.tools.search import search

        # Just verify it's callable (actual API call would need mocking)
        assert callable(search)


class TestAllToolsHaveAsync:
    """Verify all registered tools have async support."""

    def test_all_tools_have_async_function(self):
        """Every registered tool should have an async_function on its ToolSpec."""
        from glean.agent_toolkit.registry import get_registry

        registry = get_registry()
        tools = registry.list()

        assert len(tools) > 0, "No tools registered"

        for tool in tools:
            assert tool.async_function is not None, (
                f"Tool '{tool.name}' is missing async_function"
            )
            assert asyncio.iscoroutinefunction(tool.async_function), (
                f"Tool '{tool.name}' async_function is not a coroutine function"
            )

    def test_all_tools_have_acall(self):
        """Every tool module function should expose acall."""
        from glean.agent_toolkit.tools import (
            calendar_search,
            code_search,
            employee_search,
            gmail_search,
            outlook_search,
            read_document,
            search,
            web_search,
        )

        for tool_fn in [
            search,
            web_search,
            calendar_search,
            employee_search,
            code_search,
            gmail_search,
            outlook_search,
            read_document,
        ]:
            assert hasattr(tool_fn, "acall"), (
                f"{tool_fn.__name__} is missing acall"
            )


try:
    from glean.agent_toolkit.adapters.openai import HAS_OPENAI
except ImportError:
    HAS_OPENAI = False

try:
    from glean.agent_toolkit.adapters.langchain import HAS_LANGCHAIN
except ImportError:
    HAS_LANGCHAIN = False

try:
    from glean.agent_toolkit.adapters.adk import HAS_ADK
except ImportError:
    HAS_ADK = False


@pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI not installed")
class TestOpenAIAdapterAsync:
    """Test OpenAI adapter uses async function."""

    async def test_openai_agents_tool_uses_async(self):
        """The OpenAI Agents SDK on_invoke_tool should use the async function."""
        from glean.agent_toolkit.adapters.openai import OpenAIAdapter

        call_log = []

        async def mock_async_fn(a: int, b: int) -> int:
            call_log.append("async")
            return a + b

        def mock_sync_fn(a: int, b: int) -> int:
            call_log.append("sync")
            return a + b

        spec = ToolSpec(
            name="add",
            description="Add two numbers",
            function=mock_sync_fn,
            async_function=mock_async_fn,
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
            output_schema={"type": "integer"},
        )

        adapter = OpenAIAdapter(spec)
        tool = adapter.to_agents_tool()

        result = await tool.on_invoke_tool(None, '{"a": 3, "b": 5}')
        assert result == 8
        assert call_log == ["async"]


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
class TestLangChainAdapterAsync:
    """Test LangChain adapter exposes coroutine."""

    def test_langchain_tool_has_coroutine(self):
        """LangChain Tool should have coroutine set for async support."""
        from glean.agent_toolkit.adapters.langchain import LangChainAdapter

        async def mock_async_fn(a: int, b: int) -> int:
            return a + b

        def mock_sync_fn(a: int, b: int) -> int:
            return a + b

        spec = ToolSpec(
            name="add",
            description="Add two numbers",
            function=mock_sync_fn,
            async_function=mock_async_fn,
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
            output_schema={"type": "integer"},
        )

        adapter = LangChainAdapter(spec)
        tool = adapter.to_tool()

        assert tool.coroutine is mock_async_fn


@pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed")
class TestADKAdapterAsync:
    """Test ADK adapter uses async function."""

    def test_adk_tool_uses_async_function(self):
        """ADK FunctionTool should be initialized with the async function."""
        from glean.agent_toolkit.adapters.adk import ADKAdapter

        async def mock_async_fn(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        def mock_sync_fn(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        spec = ToolSpec(
            name="add",
            description="Add two numbers",
            function=mock_sync_fn,
            async_function=mock_async_fn,
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
            output_schema={"type": "integer"},
        )

        adapter = ADKAdapter(spec)
        tool = adapter.to_tool()

        assert tool.func is mock_async_fn
