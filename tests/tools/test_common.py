"""Tests for _common.py helpers."""

from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, Field

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools._common import (
    ToolResult,
    _classify_error,
    make_error,
    make_ok,
    run_tool,
    serialize_tool_result,
)
from glean.api_client import errors as sdk_errors


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
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.return_value = _Item(camelCaseField="value")

    result = run_tool("Glean Search", {}, client=mock_client)

    assert result["status"] == "ok"
    assert result["error"] is None
    assert result["result"] == {"camelCaseField": "value"}


def test_run_tool_error_with_injected_client() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.side_effect = Exception("boom")

    result = run_tool("Glean Search", {}, client=mock_client)

    assert result["status"] == "error"
    assert result["error"] == "boom"
    assert result["result"] is None


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


def test_classify_error_connection_is_config() -> None:
    error_type, action = _classify_error(ConnectionError("DNS failure"))
    assert error_type == "config"
    assert action == "check_configuration"


def test_classify_error_httpx_connect_error_is_config() -> None:
    error_type, action = _classify_error(
        httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known")
    )
    assert error_type == "config"
    assert action == "check_configuration"


def test_classify_error_dns_gaierror_is_config() -> None:
    import socket

    error_type, action = _classify_error(
        socket.gaierror(8, "nodename nor servname provided, or not known")
    )
    assert error_type == "config"
    assert action == "check_configuration"


def test_classify_error_credentials_is_auth() -> None:
    from glean.agent_toolkit.context import GleanCredentialsError

    error_type, action = _classify_error(GleanCredentialsError("no token"))
    assert error_type == "auth"
    assert action == "check_credentials"


def test_classify_error_configuration_is_config() -> None:
    from glean.agent_toolkit.context import GleanConfigurationError

    error_type, action = _classify_error(GleanConfigurationError("bad server_url"))
    assert error_type == "config"
    assert action == "check_configuration"


def test_error_result_from_exception_appends_connection_hint() -> None:
    from glean.agent_toolkit.tools._common import (
        CONNECTION_ERROR_HINT,
        error_result_from_exception,
    )

    result = error_result_from_exception(httpx.ConnectError("Failed to resolve host"))

    assert result["status"] == "error"
    assert result["error_type"] == "config"
    assert result["suggested_action"] == "check_configuration"
    assert result["error"] is not None and result["error"].endswith(CONNECTION_ERROR_HINT)


def test_error_result_from_exception_no_hint_for_non_connection_config() -> None:
    from glean.agent_toolkit.context import GleanConfigurationError
    from glean.agent_toolkit.tools._common import error_result_from_exception

    result = error_result_from_exception(GleanConfigurationError("Invalid server_url"))

    assert result["error"] == "Invalid server_url"
    assert result["error_type"] == "config"


def test_classify_error_read_error_stays_api() -> None:
    """Mid-request network blips are transient: still api/retry."""
    error_type, action = _classify_error(httpx.ReadError("read failed"))
    assert error_type == "api"
    assert action == "retry"


def test_classify_error_generic() -> None:
    error_type, action = _classify_error(RuntimeError("unknown"))
    assert error_type == "api"
    assert action == "retry"


def _sdk_error(status_code: int) -> sdk_errors.GleanError:
    """Build a real SDK error instance carrying *status_code*."""
    response = httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://test-instance-be.glean.com/rest/api/v1/search"),
        text="upstream failure",
    )
    return sdk_errors.GleanError("API error occurred", response, "upstream failure")


@pytest.mark.parametrize(
    ("status_code", "expected_type", "expected_action"),
    [
        (400, "validation", "rephrase_query"),
        (401, "auth", "check_credentials"),
        (403, "auth", "check_credentials"),
        (404, "not_found", "rephrase_query"),
        (408, "timeout", "retry"),
        (418, "api", "retry"),  # unmapped 4xx falls back to api/retry
        (422, "validation", "rephrase_query"),
        (429, "rate_limit", "retry"),
        (500, "api", "retry"),
        (502, "api", "retry"),
        (503, "api", "retry"),
    ],
)
def test_classify_error_sdk_status_codes(
    status_code: int, expected_type: str, expected_action: str
) -> None:
    """Real SDK error instances are classified by their status code."""
    error_type, action = _classify_error(_sdk_error(status_code))
    assert error_type == expected_type
    assert action == expected_action


def test_classify_error_sdk_status_beats_message_heuristics() -> None:
    """The status code wins even when the body mentions other keywords."""
    response = httpx.Response(
        status_code=403,
        request=httpx.Request("POST", "https://example.com"),
        text="deadline timed out while checking rate limit",
    )
    error = sdk_errors.GleanError("API error occurred", response)

    error_type, action = _classify_error(error)

    assert error_type == "auth"
    assert action == "check_credentials"


def test_classify_error_glean_data_error_uses_status_code() -> None:
    """Subclasses of the SDK base error are classified the same way."""
    response = httpx.Response(
        status_code=422,
        request=httpx.Request("POST", "https://example.com"),
        text="{}",
    )
    data = sdk_errors.GleanDataErrorData()
    error = sdk_errors.GleanDataError(data, response)

    error_type, action = _classify_error(error)

    assert error_type == "validation"
    assert action == "rephrase_query"


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectTimeout("connect exceeded deadline"),
        httpx.ReadTimeout("read exceeded deadline"),
        httpx.PoolTimeout("pool exceeded deadline"),
    ],
)
def test_classify_error_httpx_timeout_classes(exc: Exception) -> None:
    error_type, action = _classify_error(exc)
    assert error_type == "timeout"
    assert action == "retry"
