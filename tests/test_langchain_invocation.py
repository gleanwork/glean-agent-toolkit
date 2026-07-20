"""Regression tests: converted LangChain tools must be invocable.

The adapter previously built the legacy single-input
``langchain_core.tools.Tool``, which rejects multi-key dict inputs
("Too many arguments to single-input tool") and calls its func
positionally (breaking the kwargs-only wrappers). These tests exercise
LangChain's own ``invoke``/``ainvoke`` path end-to-end against the real
langchain-core package, mocking the network at the Glean client layer.
"""

from __future__ import annotations

import importlib
import json
from typing import Any

import pytest
from langchain_core.tools import StructuredTool

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, make_ok
from glean.agent_toolkit.tools.search import search

CANNED_PAYLOAD = "CANNED_LANGCHAIN_PAYLOAD"


@pytest.fixture
def patched_run_tool(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace the Glean network call with a canned ToolResult.

    ``search`` binds ``execute_tool`` into its module namespace at import
    time, so patch it there. The native async path flows through the
    transport seam's ``execute_tool_async``, so patch that too. Env vars
    are set so the (unused) client construction inside the tool does not
    fail.
    """
    monkeypatch.setenv("GLEAN_API_TOKEN", "test-token")
    monkeypatch.setenv("GLEAN_INSTANCE", "test-instance")

    captured: dict[str, Any] = {}

    def fake_execute_tool(
        tool_name: str,
        arguments: dict[str, Any],
        *,
        client: Any = None,
        ctx: Any = None,
    ) -> ToolResult:
        captured["tool_name"] = tool_name
        captured["arguments"] = dict(arguments)
        return make_ok({"marker": CANNED_PAYLOAD})

    async def fake_execute_tool_async(
        tool_name: str,
        arguments: dict[str, Any],
        *,
        client: Any = None,
        ctx: Any = None,
    ) -> ToolResult:
        return fake_execute_tool(tool_name, arguments, client=client)

    # The tools package re-exports the `search` function under the same
    # name as its module, so resolve the module object explicitly.
    search_module = importlib.import_module("glean.agent_toolkit.tools.search")
    monkeypatch.setattr(search_module, "execute_tool", fake_execute_tool)

    transport_module = importlib.import_module("glean.agent_toolkit.tools._transport")
    monkeypatch.setattr(transport_module, "execute_tool_async", fake_execute_tool_async)
    return captured


def test_as_langchain_tool_returns_structured_tool() -> None:
    tool = search.as_langchain_tool()

    assert isinstance(tool, StructuredTool)
    assert tool.name == "glean_search"
    assert tool.args_schema is not None


def test_invoke_multi_arg_through_langchain(patched_run_tool: dict[str, Any]) -> None:
    tool = search.as_langchain_tool()

    result = tool.invoke({"query": "test", "page_size": 5})

    assert isinstance(result, str)
    # The adapter unwraps the ToolResult envelope: raw payload only.
    assert json.loads(result) == {"marker": CANNED_PAYLOAD}
    assert patched_run_tool["tool_name"] == "glean_search"
    assert patched_run_tool["arguments"]["query"] == "test"
    assert patched_run_tool["arguments"]["page_size"] == 5


async def test_ainvoke_multi_arg_through_langchain(patched_run_tool: dict[str, Any]) -> None:
    tool = search.as_langchain_tool()

    result = await tool.ainvoke({"query": "async test", "page_size": 5})

    assert isinstance(result, str)
    assert json.loads(result) == {"marker": CANNED_PAYLOAD}
    assert patched_run_tool["arguments"]["query"] == "async test"
    assert patched_run_tool["arguments"]["page_size"] == 5


def test_custom_multi_arg_tool_invocable() -> None:
    @tool_spec(name="test_lc_add", description="Add two integers.")
    def add(a: int, b: int) -> int:
        """Add two integers.

        Args:
            a: First addend.
            b: Second addend.
        """
        return a + b

    tool = add.as_langchain_tool()

    assert isinstance(tool, StructuredTool)
    assert tool.invoke({"a": 3, "b": 5}) == "8"
