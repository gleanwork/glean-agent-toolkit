"""Unit tests for the shared adapter call path and input-model construction."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from glean.agent_toolkit import GleanContext, get_registry, tool_spec
from glean.agent_toolkit.adapters.base import (
    ainvoke_tool,
    invoke_tool,
    is_error_payload,
    payload_to_text,
    resolve_context_param,
)
from glean.agent_toolkit.decorators import (
    _build_input_model,
    _create_pydantic_input_schema,
)
from glean.agent_toolkit.spec import ToolSpec


def _hand_built(func: Any, properties: dict[str, Any], **kwargs: Any) -> ToolSpec:
    return ToolSpec(
        name=func.__name__,
        description="hand built",
        function=func,
        input_schema={"type": "object", "properties": properties, "required": []},
        output_schema={"type": "object"},
        **kwargs,
    )


@pytest.fixture
def ctx() -> GleanContext:
    return GleanContext(client=object())  # type: ignore[arg-type]


class TestResolveContextParam:
    """Where the context is injected, for decorated and hand-built specs."""

    def test_decorated_spec_records_context_param(self) -> None:
        @tool_spec(name="cp_decorated", description="d")
        def tool(query: str, glean: GleanContext | None = None) -> str:
            return query

        try:
            assert tool.tool_spec.context_param == "glean"
            assert resolve_context_param(tool.tool_spec) == "glean"
        finally:
            get_registry()._tools.pop("cp_decorated", None)

    def test_decorated_spec_without_context(self) -> None:
        @tool_spec(name="cp_none", description="d")
        def tool(query: str) -> str:
            return query

        try:
            assert tool.tool_spec.context_param is None
            assert resolve_context_param(tool.tool_spec) is None
        finally:
            get_registry()._tools.pop("cp_none", None)

    def test_hand_built_spec_with_annotated_context(self) -> None:
        def tool(query: str, ctx: GleanContext | None = None) -> str:
            return query

        spec = _hand_built(tool, {"query": {"type": "string"}, "ctx": {}})
        assert resolve_context_param(spec) == "ctx"

    def test_hand_built_spec_with_unannotated_context(self) -> None:
        def tool(ctx, query: str) -> str:  # type: ignore[no-untyped-def]  # noqa: ANN001
            return query

        spec = _hand_built(tool, {"query": {"type": "string"}})
        assert resolve_context_param(spec) == "ctx"

    def test_hand_built_spec_without_context(self) -> None:
        def tool(query: str, *args: Any, **kwargs: Any) -> str:
            return query

        spec = _hand_built(tool, {"query": {"type": "string"}})
        assert resolve_context_param(spec) is None


class TestInvokeTool:
    """The single sync/async call path every adapter uses."""

    def test_binds_context_by_name_for_hand_built_spec(self, ctx: GleanContext) -> None:
        def tool(query: str, ctx: GleanContext | None = None) -> dict[str, Any]:
            return {"query": query, "has_ctx": ctx is not None}

        spec = _hand_built(tool, {"query": {"type": "string"}})
        assert invoke_tool(spec, ctx, {"query": "q"}) == {"query": "q", "has_ctx": True}
        assert invoke_tool(spec, None, {"query": "q"}) == {"query": "q", "has_ctx": False}

    async def test_async_falls_back_to_sync_function(self, ctx: GleanContext) -> None:
        def tool(query: str) -> str:
            return query.upper()

        spec = _hand_built(tool, {"query": {"type": "string"}})
        assert spec.async_function is None
        assert await ainvoke_tool(spec, ctx, {"query": "q"}) == "Q"

    async def test_async_exception_becomes_compact_error(self) -> None:
        async def failing(query: str) -> str:
            raise TimeoutError("took too long")

        spec = _hand_built(failing, {"query": {"type": "string"}}, async_function=failing)
        payload = await ainvoke_tool(spec, None, {"query": "q"})
        assert is_error_payload(payload)
        assert payload["error_type"] == "timeout"
        assert payload["suggested_action"] == "retry"

    def test_tool_result_envelope_is_unwrapped(self) -> None:
        def tool() -> dict[str, Any]:
            return {
                "status": "ok",
                "result": {"answer": 42},
                "error": None,
                "error_type": None,
                "suggested_action": None,
            }

        assert invoke_tool(_hand_built(tool, {}), None, {}) == {"answer": 42}

    def test_payload_to_text(self) -> None:
        assert payload_to_text("plain") == "plain"
        assert payload_to_text({"a": 1}) == '{"a": 1}'


class TestInputModel:
    """Input-model construction in the decorator."""

    def test_var_args_and_kwargs_are_not_exposed(self) -> None:
        def tool(query: str, *args: Any, **kwargs: Any) -> str:
            return query

        model, context_param = _build_input_model("t", inspect.signature(tool), tool)
        assert model is not None
        assert list(model.model_fields) == ["query"]
        assert context_param is None

    def test_unannotated_parameters_are_strings(self) -> None:
        def tool(query, limit=3):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN201
            return query

        schema = _create_pydantic_input_schema(inspect.signature(tool), tool)
        assert schema["properties"]["query"]["type"] == "string"
        assert schema["properties"]["limit"]["default"] == 3
        assert schema["required"] == ["query"]

    def test_unbuildable_annotation_falls_back_per_parameter(self) -> None:
        def tool(query: str, weird: NotARealType) -> str:  # type: ignore[name-defined]  # noqa: F821
            return query

        model, _ = _build_input_model("t", inspect.signature(tool), tool)
        assert model is None
        schema = _create_pydantic_input_schema(inspect.signature(tool), tool)
        assert schema["properties"]["query"]["type"] == "string"
        assert schema["properties"]["weird"] == {"type": "string"}
        assert schema["required"] == ["query", "weird"]

    def test_decorating_unbuildable_annotation_does_not_raise(self) -> None:
        def tool(query: str, weird: NotARealType) -> str:  # type: ignore[name-defined]  # noqa: F821
            return query

        try:
            decorated = tool_spec(name="cp_unbuildable", description="d")(tool)
            assert decorated.tool_spec.input_model is None
            assert decorated.tool_spec.input_schema["properties"]["weird"] == {"type": "string"}
        finally:
            get_registry()._tools.pop("cp_unbuildable", None)


class TestDefaultTimeouts:
    """Operations get a sane read timeout unless the client configured one.

    Without a timeout, glean-api-client falls back to httpx's 5 s default,
    which a typical chat answer exceeds.
    """

    @staticmethod
    def _client(timeout_ms: int | None) -> Any:
        return SimpleNamespace(
            sdk_configuration=SimpleNamespace(timeout_ms=timeout_ms), client=MagicMock()
        )

    @staticmethod
    def _calls(client: Any) -> dict[str, Any]:
        from glean.agent_toolkit.tools._chat import _create_chat
        from glean.agent_toolkit.tools._transport import ToolsCallBackend
        from glean.agent_toolkit.tools.read_document import _retrieve_documents
        from glean.agent_toolkit.tools.search import _query_search

        _query_search(client, query="q")
        _create_chat(client, message="m")
        _retrieve_documents(client, document_id="d")
        ToolsCallBackend("Glean Search").call_raw(client, {})
        api = client.client
        return {
            "search": api.search.query.call_args.kwargs.get("timeout_ms"),
            "chat": api.chat.create.call_args.kwargs.get("timeout_ms"),
            "documents": api.documents.retrieve.call_args.kwargs.get("timeout_ms"),
            "tools": api.tools.run.call_args.kwargs.get("timeout_ms"),
        }

    def test_defaults_apply_when_client_has_no_timeout(self) -> None:
        assert self._calls(self._client(None)) == {
            "search": 30_000,
            "chat": 120_000,
            "documents": 30_000,
            "tools": 60_000,
        }

    def test_explicit_client_timeout_is_respected(self) -> None:
        assert self._calls(self._client(5_000)) == {
            "search": None,
            "chat": None,
            "documents": None,
            "tools": None,
        }

    async def test_async_chat_gets_the_default_too(self) -> None:
        from glean.agent_toolkit.tools._chat import _create_chat_async

        client = self._client(None)
        client.client.chat.create_async = AsyncMock()
        await _create_chat_async(client, message="m")
        assert client.client.chat.create_async.call_args.kwargs["timeout_ms"] == 120_000
