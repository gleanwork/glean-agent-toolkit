"""Tests for the Code Search tool."""

from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.tools.code_search import code_search


def _mock_context(return_value: object = None) -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.return_value = return_value if return_value is not None else {"data": "mock"}
    return ctx


def test_code_search_success():
    """Test successful Code Search tool execution using a mocked API client."""
    mock_result = {"data": "mock"}
    ctx = _mock_context(mock_result)
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = code_search(query="function authenticate user")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] == mock_result


def test_code_search_api_error():
    """Test Code Search tool returns error dict when API raises."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.side_effect = Exception("API Error")

    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = code_search(query="invalid query that causes error")

    assert result is not None
    assert "error" in result
    assert result["result"] is None


@pytest.mark.parametrize("query", [
    "class UserManager",
    "function login validation",
    "API endpoint security",
    "database connection pool",
    "error handling middleware",
])
def test_code_search_various_queries(query: str):
    """Test Code Search tool with various code-related queries."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = code_search(query=query)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None


def test_code_search_empty_query():
    """Test Code Search tool with empty query."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = code_search(query="")

    assert result is not None


def test_code_search_complex_query():
    """Test Code Search tool with complex search query."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = code_search(query="class:UserService method:authenticate lang:python")

    assert result is not None
    assert "result" in result
