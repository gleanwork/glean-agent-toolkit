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

    ``search`` binds ``run_tool`` into its module namespace at import
    time, so patch it there. Env vars are set so the (unused) client
    construction inside the tool does not fail.
    """
    monkeypatch.setenv("GLEAN_API_TOKEN", "test-token")
    monkeypatch.setenv("GLEAN_INSTANCE", "test-instance")

    captured: dict[str, Any] = {}

    def fake_run_tool(
        tool_display_name: str,
        parameters: dict[str, Any],
        *,
        client: Any = None,
    ) -> ToolResult:
        captured["tool_display_name"] = tool_display_name
        captured["parameters"] = {name: param.value for name, param in parameters.items()}
        return make_ok({"marker": CANNED_PAYLOAD})

    # The tools package re-exports the `search` function under the same
    # name as its module, so resolve the module object explicitly.
    search_module = importlib.import_module("glean.agent_toolkit.tools.search")
    monkeypatch.setattr(search_module, "run_tool", fake_run_tool)
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
    assert CANNED_PAYLOAD in result
    assert patched_run_tool["tool_display_name"] == "Glean Search"
    assert patched_run_tool["parameters"]["query"] == "test"
    assert patched_run_tool["parameters"]["pageSize"] == "5"


async def test_ainvoke_multi_arg_through_langchain(patched_run_tool: dict[str, Any]) -> None:
    tool = search.as_langchain_tool()

    result = await tool.ainvoke({"query": "async test", "page_size": 5})

    assert isinstance(result, str)
    assert CANNED_PAYLOAD in result
    assert patched_run_tool["parameters"]["query"] == "async test"
    assert patched_run_tool["parameters"]["pageSize"] == "5"


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
