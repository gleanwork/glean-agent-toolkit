"""Tests for the private transport seam (_transport.py)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ConfigDict, Field

from glean.agent_toolkit.tools import _transport
from glean.agent_toolkit.tools._transport import (
    DEFAULT_MAX_RESULT_CHARS,
    MAX_RESULT_CHARS_ENV,
    TRUNCATION_MARKER,
    ToolsCallBackend,
    TypedBackend,
    execute_tool,
    get_backend,
    register_backend,
    truncate_payload,
)


class _AliasModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    camel_case_field: str = Field(alias="camelCaseField")


def _mock_client(tools_run_return: object = None) -> MagicMock:
    client = MagicMock()
    client.client.tools.run.return_value = (
        tools_run_return if tools_run_return is not None else {"data": "mock"}
    )
    return client


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


def test_truncate_payload_under_limit_passthrough() -> None:
    payload = {"small": "payload"}
    assert truncate_payload(payload) is payload


def test_truncate_payload_over_default_limit() -> None:
    payload = {"blob": "x" * (DEFAULT_MAX_RESULT_CHARS + 1000)}

    truncated = truncate_payload(payload)

    assert truncated["truncated"] is True
    assert truncated["max_chars"] == DEFAULT_MAX_RESULT_CHARS
    assert MAX_RESULT_CHARS_ENV in truncated["note"]
    assert truncated["content"].endswith(TRUNCATION_MARKER)
    # content is the capped serialization plus the marker
    assert len(truncated["content"]) == DEFAULT_MAX_RESULT_CHARS + len(TRUNCATION_MARKER)


def test_truncate_payload_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MAX_RESULT_CHARS_ENV, "100")

    payload = {"blob": "y" * 500}
    truncated = truncate_payload(payload)

    assert truncated["truncated"] is True
    assert truncated["max_chars"] == 100
    assert truncated["content"] == json.dumps(payload)[:100] + TRUNCATION_MARKER


def test_truncate_payload_env_invalid_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MAX_RESULT_CHARS_ENV, "not-a-number")

    payload = {"small": "payload"}
    assert truncate_payload(payload) is payload
    assert _transport._max_result_chars() == DEFAULT_MAX_RESULT_CHARS


def test_truncate_payload_env_zero_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MAX_RESULT_CHARS_ENV, "0")

    payload = {"blob": "z" * (DEFAULT_MAX_RESULT_CHARS * 2)}
    assert truncate_payload(payload) is payload


def test_truncate_payload_unserializable_uses_str(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MAX_RESULT_CHARS_ENV, "10")

    circular: dict[str, Any] = {}
    circular["self"] = circular  # json.dumps raises ValueError

    truncated = truncate_payload(circular)

    assert truncated["truncated"] is True
    assert truncated["content"] == str(circular)[:10] + TRUNCATION_MARKER


# ---------------------------------------------------------------------------
# ToolsCallBackend
# ---------------------------------------------------------------------------


def test_tools_call_backend_maps_and_coerces_arguments() -> None:
    client = _mock_client({"raw": "ok"})
    backend = ToolsCallBackend("Glean Search")

    result = backend.execute(
        client,
        {
            "query": "hello",
            "page_size": 5,
            "datasources": ["jira"],
            "flag": True,
            "skipped": None,
        },
    )

    assert result == {"raw": "ok"}
    kwargs = client.client.tools.run.call_args.kwargs
    assert kwargs["name"] == "Glean Search"
    params = kwargs["parameters"]
    assert set(params) == {"query", "page_size", "datasources", "flag"}
    assert params["query"].value == "hello"
    assert params["page_size"].value == "5"
    assert json.loads(params["datasources"].value) == ["jira"]
    assert json.loads(params["flag"].value) is True


def test_tools_call_backend_serializes_sdk_models() -> None:
    client = _mock_client(_AliasModel(camelCaseField="value"))
    backend = ToolsCallBackend("Code Search")

    result = backend.execute(client, {"query": "x"})

    assert result == {"camelCaseField": "value"}


def test_tools_call_backend_truncates_large_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MAX_RESULT_CHARS_ENV, "50")
    client = _mock_client({"blob": "x" * 200})
    backend = ToolsCallBackend("Code Search")

    result = backend.execute(client, {"query": "x"})

    assert result["truncated"] is True
    assert result["content"].endswith(TRUNCATION_MARKER)


# ---------------------------------------------------------------------------
# TypedBackend
# ---------------------------------------------------------------------------


def test_typed_backend_calls_fn_with_client_and_kwargs() -> None:
    client = MagicMock()
    seen: dict[str, Any] = {}

    def fn(passed_client: Any, *, query: str, page_size: int = 10) -> dict[str, Any]:
        seen["client"] = passed_client
        seen["query"] = query
        seen["page_size"] = page_size
        return {"ok": True}

    backend = TypedBackend(fn)

    result = backend.execute(client, {"query": "hello", "page_size": 3})

    assert result == {"ok": True}
    assert seen == {"client": client, "query": "hello", "page_size": 3}


def test_typed_backend_default_shaper_serializes_models() -> None:
    backend = TypedBackend(lambda client: _AliasModel(camelCaseField="v"))

    assert backend.execute(MagicMock(), {}) == {"camelCaseField": "v"}


def test_typed_backend_custom_shaper_applied() -> None:
    backend = TypedBackend(
        lambda client: {"answer": 42},
        shaper=lambda response: {"shaped": response["answer"]},
    )

    assert backend.execute(MagicMock(), {}) == {"shaped": 42}


# ---------------------------------------------------------------------------
# Registry and execute_tool dispatch
# ---------------------------------------------------------------------------


@pytest.fixture
def scratch_registry(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Isolate registry mutations from the real tool registrations."""
    scratch: dict[str, Any] = dict(_transport._BACKENDS)
    monkeypatch.setattr(_transport, "_BACKENDS", scratch)
    return scratch


def test_register_and_get_backend(scratch_registry: dict[str, Any]) -> None:
    backend = ToolsCallBackend("Scratch Tool")

    returned = register_backend("scratch_tool", backend)

    assert returned is backend
    assert get_backend("scratch_tool") is backend


def test_builtin_tools_all_registered() -> None:
    expected = {
        "glean_search",
        "glean_web_search",
        "glean_calendar_search",
        "glean_employee_search",
        "glean_code_search",
        "glean_gmail_search",
        "glean_outlook_search",
        "glean_chat",
        "glean_read_document",
    }
    import glean.agent_toolkit.tools  # noqa: F401  (registers all backends)

    for name in expected:
        assert get_backend(name) is not None, name


def test_execute_tool_unknown_tool(scratch_registry: dict[str, Any]) -> None:
    result = execute_tool("not_a_tool", {}, client=MagicMock())

    assert result["status"] == "error"
    assert result["error_type"] == "validation"
    assert result["suggested_action"] == "rephrase_query"
    assert result["error"] is not None
    assert "not_a_tool" in result["error"]


def test_execute_tool_dispatches_to_backend(scratch_registry: dict[str, Any]) -> None:
    client = MagicMock()
    seen: dict[str, Any] = {}

    class FakeBackend:
        def execute(self, client: Any, arguments: Any) -> Any:
            seen["client"] = client
            seen["arguments"] = dict(arguments)
            return {"payload": 1}

        async def execute_async(self, client: Any, arguments: Any) -> Any:
            return self.execute(client, arguments)

    register_backend("fake_tool", FakeBackend())

    result = execute_tool("fake_tool", {"a": 1}, client=client)

    assert result == {
        "status": "ok",
        "result": {"payload": 1},
        "error": None,
        "error_type": None,
        "suggested_action": None,
    }
    assert seen == {"client": client, "arguments": {"a": 1}}


def test_execute_tool_creates_default_client(scratch_registry: dict[str, Any]) -> None:
    seen: dict[str, Any] = {}

    class FakeBackend:
        def execute(self, client: Any, arguments: Any) -> Any:
            seen["client"] = client
            return "ok"

        async def execute_async(self, client: Any, arguments: Any) -> Any:
            return self.execute(client, arguments)

    register_backend("fake_tool", FakeBackend())

    result = execute_tool("fake_tool", {})

    assert result["status"] == "ok"
    assert seen["client"] is not None


def test_execute_tool_classifies_backend_errors(scratch_registry: dict[str, Any]) -> None:
    class FailingBackend:
        def execute(self, client: Any, arguments: Any) -> Any:
            raise ValueError("bad input")

        async def execute_async(self, client: Any, arguments: Any) -> Any:
            return self.execute(client, arguments)

    register_backend("failing_tool", FailingBackend())

    result = execute_tool("failing_tool", {}, client=MagicMock())

    assert result["status"] == "error"
    assert result["error"] == "bad input"
    assert result["error_type"] == "validation"
    assert result["suggested_action"] == "rephrase_query"
