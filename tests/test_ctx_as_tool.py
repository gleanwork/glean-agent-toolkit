"""Regression tests: ``as_*_tool(ctx)`` must bind the context into invocations.

Previously the per-function ``as_openai_tool``/``as_adk_tool``/
``as_langchain_tool``/``as_crewai_tool`` helpers constructed adapters with no
context, so conversion silently fell back to env-only configuration even when
the caller had an explicit :class:`GleanContext`.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast
from unittest.mock import MagicMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.decorators import ToolSpecFunction, tool_spec


def _make_ctx(marker: str) -> GleanContext:
    """A context wrapping a mock client tagged with *marker*."""
    client = MagicMock()
    client.marker = marker
    return GleanContext(client=client)


def _make_probe(name: str) -> ToolSpecFunction:
    @tool_spec(name=name, description="Echoes the ctx client marker")
    def probe(ctx: GleanContext, text: str) -> str:
        client: Any = ctx.get_client()
        return f"{client.marker}:{text}"

    return cast(ToolSpecFunction, probe)


def test_as_openai_tool_binds_ctx() -> None:
    probe = _make_probe("ctx_probe_openai")
    ctx = _make_ctx("injected")

    tool = cast(Any, probe.as_openai_tool(ctx))
    result = asyncio.run(tool.on_invoke_tool(None, json.dumps({"text": "hi"})))

    assert result == "injected:hi"


def test_as_langchain_tool_binds_ctx() -> None:
    probe = _make_probe("ctx_probe_langchain")
    ctx = _make_ctx("lc")

    tool = probe.as_langchain_tool(ctx)
    assert tool.invoke({"text": "x"}) == "lc:x"


def test_as_adk_tool_binds_ctx() -> None:
    probe = _make_probe("ctx_probe_adk")
    ctx = _make_ctx("adk")

    tool = probe.as_adk_tool(ctx)
    # ADK FunctionTool wraps the (ctx-bound) callable as a coroutine function.
    assert asyncio.run(tool.func(text="y")) == "adk:y"


def test_as_crewai_tool_binds_ctx() -> None:
    probe = _make_probe("ctx_probe_crewai")
    ctx = _make_ctx("crew")

    tool = probe.as_crewai_tool(ctx)
    assert tool.run(text="z") == "crew:z"


def test_ctx_adapter_not_cached_across_contexts() -> None:
    """A ctx-bound conversion must not poison the cache for other calls."""
    probe = _make_probe("ctx_probe_cache")
    ctx_a = _make_ctx("a")
    ctx_b = _make_ctx("b")

    tool_a = probe.as_langchain_tool(ctx_a)
    tool_b = probe.as_langchain_tool(ctx_b)

    assert tool_a.invoke({"text": "1"}) == "a:1"
    assert tool_b.invoke({"text": "2"}) == "b:2"

    # ctx-bound conversions must not populate the ctx-less adapter cache.
    cached = probe.tool_spec.get_adapter("langchain")
    assert cached is None or cached.ctx is None


def test_ctxless_cache_not_reused_for_ctx_call() -> None:
    """Converting without ctx first must not make later ctx calls env-only."""
    probe = _make_probe("ctx_probe_order")

    probe.as_langchain_tool()  # populates the ctx-less cache
    cached = probe.tool_spec.get_adapter("langchain")
    assert cached is not None and cached.ctx is None

    ctx = _make_ctx("late")
    tool = probe.as_langchain_tool(ctx)
    assert tool.invoke({"text": "q"}) == "late:q"
