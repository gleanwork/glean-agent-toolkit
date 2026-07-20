"""Regression tests for OpenAI Agents SDK strict-schema handling.

These tests exercise the real ``openai-agents`` package (no stubbing of the
SDK) to guarantee that:

1. ``get_tools("openai")`` returns every built-in tool even though some tool
   schemas (e.g. ``glean_search``'s free-form ``filters: list[dict]``) cannot
   be expressed under OpenAI strict-mode rules.
2. Tools whose schemas violate strict mode fall back cleanly to
   ``strict_json_schema=False`` instead of raising ``UserError`` at
   construction time.
3. Tool invocation through the framework path (``on_invoke_tool``) works.
"""

from __future__ import annotations

import copy
import json
from typing import Any
from unittest.mock import MagicMock

import pytest

pytest.importorskip("agents")

from agents.exceptions import UserError  # noqa: E402
from agents.strict_schema import ensure_strict_json_schema  # noqa: E402
from agents.tool import FunctionTool  # noqa: E402

from glean.agent_toolkit import get_tools  # noqa: E402
from glean.agent_toolkit.tools._common import make_ok  # noqa: E402

EXPECTED_TOOL_NAMES = {
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


def _mock_client() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _is_strict_valid(schema: dict[str, Any]) -> bool:
    """Whether *schema* already satisfies OpenAI strict-mode rules."""
    try:
        ensure_strict_json_schema(copy.deepcopy(schema))
    except UserError:
        return False
    return True


def test_get_tools_openai_returns_all_builtin_tools() -> None:
    """Regression: one strict-incompatible schema must not sink the whole list."""
    tools = get_tools("openai", client=_mock_client())

    names = {t.name for t in tools}
    # Other test modules may register extra tools in the global registry, so
    # assert the built-ins are a subset rather than an exact match.
    assert EXPECTED_TOOL_NAMES <= names
    for t in tools:
        assert isinstance(t, FunctionTool)


def test_search_as_openai_tool_constructs() -> None:
    """Regression: glean_search previously raised UserError at construction."""
    from glean.agent_toolkit.tools.search import search

    tool = search.as_openai_tool()

    assert isinstance(tool, FunctionTool)
    assert tool.name == "glean_search"
    if tool.strict_json_schema:
        # If the tool claims strict mode, its schema must actually be
        # strict-valid.
        assert _is_strict_valid(tool.params_json_schema)
    else:
        # Clean fallback: the original (non-strict) schema is preserved,
        # including the free-form filters dict.
        filters_items = tool.params_json_schema["properties"]["filters"]["anyOf"][0]["items"]
        assert filters_items == {"additionalProperties": True, "type": "object"}


async def test_on_invoke_tool_framework_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive a tool through the Agents SDK invocation path with Glean mocked."""
    canned = make_ok({"documents": [{"title": "canned-doc"}]})
    captured: dict[str, Any] = {}

    async def fake_execute_tool_async(tool_name: str, arguments: Any, *, client: Any = None) -> Any:
        captured["tool_name"] = tool_name
        captured["arguments"] = dict(arguments)
        return canned

    import importlib

    # on_invoke_tool awaits the tool's native async path, which flows
    # through the transport seam's execute_tool_async.
    transport_module = importlib.import_module("glean.agent_toolkit.tools._transport")
    monkeypatch.setattr(transport_module, "execute_tool_async", fake_execute_tool_async)

    tools = get_tools("openai", include=["glean_search"], client=_mock_client())
    assert len(tools) == 1
    tool = tools[0]

    ctx_stub = MagicMock()  # the adapter ignores the SDK run context
    result_str = await tool.on_invoke_tool(ctx_stub, '{"query": "test"}')

    result = json.loads(result_str)
    assert result["status"] == "ok"
    assert result["result"] == {"documents": [{"title": "canned-doc"}]}
    assert captured["tool_name"] == "glean_search"


def test_read_document_optional_params_schema_valid() -> None:
    """Optional-params tool constructs and stays valid under strict mode."""
    tools = get_tools("openai", include=["glean_read_document"], client=_mock_client())
    assert len(tools) == 1
    tool = tools[0]

    assert isinstance(tool, FunctionTool)
    schema = tool.params_json_schema
    assert schema["type"] == "object"
    if tool.strict_json_schema:
        assert _is_strict_valid(schema)
        # Strict mode forces optional params into `required`, but they must
        # remain nullable so callers can still omit meaningful values.
        assert set(schema["required"]) == {"document_id", "url"}
        for prop in ("document_id", "url"):
            any_of = schema["properties"][prop]["anyOf"]
            assert {"type": "null"} in any_of


def test_get_tools_warns_and_skips_on_conversion_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tool that fails conversion entirely is skipped with a warning."""
    from glean.agent_toolkit.adapters.openai import OpenAIAdapter

    original_to_tool = OpenAIAdapter.to_tool

    def flaky_to_tool(self: OpenAIAdapter) -> Any:
        if self.tool_spec.name == "glean_chat":
            raise RuntimeError("boom")
        return original_to_tool(self)

    monkeypatch.setattr(OpenAIAdapter, "to_tool", flaky_to_tool)

    with pytest.warns(RuntimeWarning, match="glean_chat"):
        tools = get_tools("openai", client=_mock_client())

    names = {t.name for t in tools}
    assert EXPECTED_TOOL_NAMES - {"glean_chat"} <= names
    assert "glean_chat" not in names
