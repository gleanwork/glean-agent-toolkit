"""Regression tests for CrewAI tool invocation using the real crewai package.

These tests guard against the bug where ``GleanCrewAITool`` called
``super().__init__`` without ``args_schema``. CrewAI generates the LLM-facing
tool description during ``__init__``, so assigning ``args_schema`` afterwards
left the description built from ``_run(self, **kwargs)`` — agents saw a bogus
``kwargs`` parameter (with a ``ForwardRef('Any')`` type) instead of the tool's
real parameters.
"""

from __future__ import annotations

import importlib
import json
from typing import Any

import pytest

try:
    from glean.agent_toolkit.adapters.crewai import HAS_CREWAI
except ImportError:  # pragma: no cover
    HAS_CREWAI = False

pytestmark = pytest.mark.skipif(not HAS_CREWAI, reason="CrewAI not installed")


@pytest.fixture(autouse=True)
def _glean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide dummy Glean credentials so client construction never fails."""
    monkeypatch.setenv("GLEAN_INSTANCE", "test-instance")
    monkeypatch.setenv("GLEAN_API_TOKEN", "test-token")


def test_crewai_glean_search_description_names_real_parameters() -> None:
    """The CrewAI-generated description must expose the real parameter names.

    Before the fix, CrewAI derived the schema from ``_run(self, **kwargs)``,
    producing ``Tool Arguments: {'kwargs': {... ForwardRef('Any')}}``.
    """
    from glean.agent_toolkit.tools import search

    tool = search.as_crewai_tool()

    # The generated description must name the actual parameters.
    assert "query" in tool.description
    assert "page_size" in tool.description

    # And must not fall back to the catch-all ``_run`` signature.
    assert "kwargs" not in tool.description
    assert "ForwardRef" not in tool.description

    # The args_schema itself must carry the real parameter names, with the
    # required ``query`` parameter typed as ``str``. (Optional parameter
    # types are intentionally not asserted here — see get_field_type in
    # adapters/base.py.)
    assert tool.args_schema is not None
    schema = tool.args_schema.model_json_schema()
    assert set(schema["properties"]) == {"query", "datasources", "filters", "page_size"}
    assert schema["properties"]["query"]["type"] == "string"
    assert "query" in schema.get("required", [])
    assert "kwargs" not in schema["properties"]


def test_crewai_glean_search_run_with_mocked_glean_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``tool.run(query=...)`` (the public CrewAI path) reaches the Glean layer."""
    search_mod = importlib.import_module("glean.agent_toolkit.tools.search")

    canned = {
        "status": "ok",
        "result": {"results": ["doc1"]},
        "error": None,
        "error_type": None,
        "suggested_action": None,
    }
    calls: list[dict[str, Any]] = []

    def fake_execute_tool(tool_name: str, arguments: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append({"name": tool_name, "arguments": dict(arguments)})
        return canned

    monkeypatch.setattr(search_mod, "execute_tool", fake_execute_tool)

    tool = search_mod.search.as_crewai_tool()
    output = tool.run(query="test")

    assert len(calls) == 1
    assert calls[0]["name"] == "glean_search"
    assert calls[0]["arguments"]["query"] == "test"

    # The adapter unwraps the ToolResult envelope: raw payload only.
    assert json.loads(output) == {"results": ["doc1"]}


def test_crewai_custom_tool_run_returns_result() -> None:
    """A custom decorated tool executes through the public ``run`` path."""
    from glean.agent_toolkit.decorators import tool_spec

    @tool_spec(name="add", description="Add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    tool = add.as_crewai_tool()

    # Description should name the real parameters, not ``kwargs``.
    assert "'a'" in tool.description or '"a"' in tool.description
    assert "kwargs" not in tool.description

    result = tool.run(a=3, b=5)
    assert result == "8"
