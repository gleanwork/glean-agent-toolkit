"""Live framework-path e2e tests: glean_search through each real framework layer.

Drives the converted glean_search tool through every supported framework's
native invocation path against the live Glean API and asserts the adapter
result contract: the RAW result payload on success (the ToolResult envelope
is unwrapped at the adapter layer), or a compact
{"error", "error_type", "suggested_action"} dict on failure. No LLM API keys
are required -- these invoke the tool layer directly through framework
plumbing:

- LangChain: ``tool.invoke`` and ``tool.ainvoke``
- OpenAI Agents SDK: ``tool.on_invoke_tool``
- CrewAI: ``tool.run``
- Google ADK: ``tool.run_async``
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from glean.agent_toolkit import get_tools
from tests.e2e._live import unwrap_adapter_payload_or_skip

try:
    from glean.agent_toolkit.adapters.langchain import HAS_LANGCHAIN
except ImportError:  # pragma: no cover
    HAS_LANGCHAIN = False

try:
    from glean.agent_toolkit.adapters.openai import HAS_OPENAI
except ImportError:  # pragma: no cover
    HAS_OPENAI = False

try:
    from glean.agent_toolkit.adapters.crewai import HAS_CREWAI
except ImportError:  # pragma: no cover
    HAS_CREWAI = False

try:
    from glean.agent_toolkit.adapters.adk import HAS_ADK
except ImportError:  # pragma: no cover
    HAS_ADK = False

pytestmark = pytest.mark.e2e

SEARCH_ARGS: dict[str, Any] = {"query": "glean", "page_size": 3}
SEARCH_PAYLOAD_KEYS = {"results", "result_count", "has_more_results"}


def _get_search_tool(framework: str) -> Any:
    tools = get_tools(framework, include=["glean_search"])
    assert len(tools) == 1, f"glean_search missing from get_tools({framework!r})"
    return tools[0]


def _assert_live_search_result(raw_payload: Any, framework_path: str) -> None:
    """Assert the NEW adapter contract: the raw result payload, no envelope."""
    payload = unwrap_adapter_payload_or_skip(raw_payload, f"glean_search via {framework_path}")
    assert isinstance(payload, dict)
    assert set(payload) == SEARCH_PAYLOAD_KEYS
    assert isinstance(payload["results"], list)
    assert payload["result_count"] == len(payload["results"])


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
def test_langchain_invoke_live() -> None:
    tool = _get_search_tool("langchain")
    output = tool.invoke(dict(SEARCH_ARGS))
    assert isinstance(output, str)
    _assert_live_search_result(json.loads(output), "langchain invoke")


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
async def test_langchain_ainvoke_live() -> None:
    tool = _get_search_tool("langchain")
    output = await tool.ainvoke(dict(SEARCH_ARGS))
    assert isinstance(output, str)
    _assert_live_search_result(json.loads(output), "langchain ainvoke")


@pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI Agents SDK not installed")
async def test_openai_on_invoke_tool_live() -> None:
    tool = _get_search_tool("openai")
    # The adapter ignores the SDK run context, so a stub suffices.
    output = await tool.on_invoke_tool(SimpleNamespace(), json.dumps(SEARCH_ARGS))
    assert isinstance(output, str)
    _assert_live_search_result(json.loads(output), "openai on_invoke_tool")


@pytest.mark.skipif(not HAS_CREWAI, reason="CrewAI not installed")
def test_crewai_run_live() -> None:
    tool = _get_search_tool("crewai")
    output = tool.run(**SEARCH_ARGS)
    assert isinstance(output, str)
    _assert_live_search_result(json.loads(output), "crewai run")


@pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed")
async def test_adk_run_async_live() -> None:
    tool = _get_search_tool("adk")
    result = await tool.run_async(args=dict(SEARCH_ARGS), tool_context=None)
    assert isinstance(result, dict)
    _assert_live_search_result(result, "adk run_async")
