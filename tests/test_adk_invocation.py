"""Regression tests for ADK tool declarations and invocation.

These tests exercise the real ``google-adk`` package. They cover a
regression where the ADK adapter wrapped tool functions in
``functools.partial`` (breaking ``_get_declaration`` with an
``AttributeError``) and exposed a bare ``(*args, **kwargs)`` signature
(so declarations contained zero typed parameters and ``run_async``
dropped all arguments).
"""

from __future__ import annotations

import importlib
from collections.abc import Generator
from typing import Any
from unittest import mock

import pytest

from glean.agent_toolkit.registry import get_registry

try:
    from glean.agent_toolkit.adapters.adk import HAS_ADK
except ImportError:  # pragma: no cover
    HAS_ADK = False

pytestmark = pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed")


def _mock_client() -> mock.MagicMock:
    client = mock.MagicMock()
    client.__enter__ = mock.MagicMock(return_value=client)
    client.__exit__ = mock.MagicMock(return_value=False)
    return client


def _declaration_properties(tool: Any) -> dict[str, Any]:
    """Return the declared parameter properties for an ADK tool."""
    declaration = tool._get_declaration()
    assert declaration is not None
    assert declaration.parameters is not None
    return declaration.parameters.properties or {}


@pytest.fixture
def unregister_tools() -> Generator[list[str], None, None]:
    """Track tool names registered by a test and remove them afterwards."""
    names: list[str] = []
    yield names
    registry = get_registry()
    for name in names:
        registry._tools.pop(name, None)


def test_get_tools_adk_declarations_expose_parameters() -> None:
    """get_tools("adk") tools must expose typed declarations (ctx is bound)."""
    from glean.agent_toolkit import get_tools

    tools = get_tools("adk", client=_mock_client())
    assert tools

    by_name = {tool.name: tool for tool in tools}
    assert "glean_search" in by_name

    # Previously raised AttributeError: 'functools.partial' object has no
    # attribute '__name__'.
    properties = _declaration_properties(by_name["glean_search"])
    assert "query" in properties
    assert "page_size" in properties

    declaration = by_name["glean_search"]._get_declaration()
    assert declaration.parameters.required == ["query"]

    # Every adapted tool must declare its schema parameters, not zero params.
    for name, tool in by_name.items():
        spec = get_registry().get(name)
        assert spec is not None
        expected = set((spec.input_schema.get("properties") or {}).keys())
        assert set(_declaration_properties(tool).keys()) == expected


async def test_run_async_delivers_arguments_to_search() -> None:
    """run_async must forward LLM-provided args to the underlying function."""
    from glean.agent_toolkit import get_tools

    search_mod = importlib.import_module("glean.agent_toolkit.tools.search")

    captured: dict[str, Any] = {}

    def fake_execute_tool(
        tool_name: str,
        arguments: dict[str, Any],
        *,
        client: Any = None,
    ) -> dict[str, Any]:
        captured["tool_name"] = tool_name
        captured["arguments"] = dict(arguments)
        return {"status": "success", "result": "canned-result"}

    with mock.patch.object(search_mod, "execute_tool", fake_execute_tool):
        (tool,) = get_tools("adk", include=["glean_search"], client=_mock_client())
        result = await tool.run_async(
            args={"query": "test", "page_size": 5},
            tool_context=None,
        )

    assert result == {"status": "success", "result": "canned-result"}
    assert captured["tool_name"] == "glean_search"
    # Previously the (*args, **kwargs) wrapper signature made ADK drop every
    # argument, so the query never reached the tool implementation.
    assert captured["arguments"]["query"] == "test"
    assert captured["arguments"]["page_size"] == 5


async def test_custom_multi_arg_tool_via_adk(unregister_tools: list[str]) -> None:
    """A custom multi-argument tool must declare and receive its arguments."""
    from glean.agent_toolkit import tool_spec

    @tool_spec(name="adk_invocation_test_add", description="Add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    unregister_tools.append("adk_invocation_test_add")

    tool = add.as_adk_tool()

    properties = _declaration_properties(tool)
    assert set(properties.keys()) == {"a", "b"}
    assert set(tool._get_declaration().parameters.required) == {"a", "b"}

    result = await tool.run_async(args={"a": 3, "b": 5}, tool_context=None)
    assert result == 8


async def test_custom_tool_via_get_tools_with_bound_context(
    unregister_tools: list[str],
) -> None:
    """Binding a GleanContext must not leak into tools that do not accept one."""
    from glean.agent_toolkit import get_tools, tool_spec

    @tool_spec(name="adk_invocation_test_add_ctx", description="Add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    unregister_tools.append("adk_invocation_test_add_ctx")

    (tool,) = get_tools(
        "adk",
        include=["adk_invocation_test_add_ctx"],
        client=_mock_client(),
    )
    result = await tool.run_async(args={"a": 3, "b": 5}, tool_context=None)
    assert result == 8
