from unittest.mock import MagicMock, patch

from pydantic import BaseModel, ConfigDict, Field

from glean.agent_toolkit.tools._common import (
    ToolResult,
    _classify_error,
    make_error,
    make_ok,
    run_tool,
    serialize_tool_result,
)


class _Item(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    camel_case_field: str = Field(alias="camelCaseField")


class _Response(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    items: list[_Item]


def test_serialize_tool_result_uses_aliases() -> None:
    model = _Response(items=[_Item(camelCaseField="a"), _Item(camelCaseField="b")])

    result = serialize_tool_result(model)

    assert result == {"items": [{"camelCaseField": "a"}, {"camelCaseField": "b"}]}


def test_serialize_tool_result_passthrough() -> None:
    assert serialize_tool_result({"plain": "dict"}) == {"plain": "dict"}
    assert serialize_tool_result("string") == "string"
    assert serialize_tool_result(None) is None


def test_run_tool_serializes_sdk_response() -> None:
    with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
        mock_client = MagicMock()
        mock_client.client.tools.run.return_value = _Item(camelCaseField="value")
        mock_api_client.return_value.__enter__.return_value = mock_client

        result = run_tool("Glean Search", {})

        assert result["status"] == "ok"
        assert result["error"] is None
        assert result["result"] == {"camelCaseField": "value"}


def test_make_ok() -> None:
    result = make_ok({"data": 42})
    assert result["status"] == "ok"
    assert result["result"] == {"data": 42}
    assert result["error"] is None
    assert result["error_type"] is None
    assert result["suggested_action"] is None


def test_make_error() -> None:
    result = make_error("something broke", "api", "retry")
    assert result["status"] == "error"
    assert result["result"] is None
    assert result["error"] == "something broke"
    assert result["error_type"] == "api"
    assert result["suggested_action"] == "retry"


def test_classify_error_timeout() -> None:
    error_type, action = _classify_error(TimeoutError("request timed out"))
    assert error_type == "timeout"
    assert action == "retry"


def test_classify_error_timeout_message() -> None:
    error_type, action = _classify_error(Exception("Connection timed out"))
    assert error_type == "timeout"
    assert action == "retry"


def test_classify_error_auth_401() -> None:
    error_type, action = _classify_error(Exception("HTTP 401 Unauthorized"))
    assert error_type == "auth"
    assert action == "check_credentials"


def test_classify_error_auth_403() -> None:
    error_type, action = _classify_error(Exception("HTTP 403 Forbidden"))
    assert error_type == "auth"
    assert action == "check_credentials"


def test_classify_error_not_found() -> None:
    error_type, action = _classify_error(Exception("Resource not found"))
    assert error_type == "not_found"
    assert action == "rephrase_query"


def test_classify_error_validation() -> None:
    error_type, action = _classify_error(ValueError("invalid parameter"))
    assert error_type == "validation"
    assert action == "rephrase_query"


def test_classify_error_connection() -> None:
    error_type, action = _classify_error(ConnectionError("DNS failure"))
    assert error_type == "api"
    assert action == "retry"


def test_classify_error_generic() -> None:
    error_type, action = _classify_error(RuntimeError("unknown"))
    assert error_type == "api"
    assert action == "retry"
