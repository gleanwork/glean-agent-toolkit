"""Tests for the Code Search tool."""

from unittest.mock import MagicMock

import pytest

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.code_search import code_search


def _make_ctx(return_value: object = None) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.return_value = (
        return_value if return_value is not None else {"data": "mock"}
    )
    return GleanContext(client=mock_client)


def test_code_search_success():
    """Test successful Code Search tool execution using injected context."""
    mock_result = {"data": "mock"}
    ctx = _make_ctx(mock_result)

    result = code_search(ctx, query="function authenticate user")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] == mock_result


def test_code_search_api_error():
    """Test Code Search tool returns error dict when API raises."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.side_effect = Exception("API Error")
    ctx = GleanContext(client=mock_client)

    result = code_search(ctx, query="invalid query that causes error")

    assert result is not None
    assert "error" in result
    assert result["result"] is None


@pytest.mark.parametrize(
    "query",
    [
        "class UserManager",
        "function login validation",
        "API endpoint security",
        "database connection pool",
        "error handling middleware",
    ],
)
def test_code_search_various_queries(query: str):
    """Test Code Search tool with various code-related queries."""
    ctx = _make_ctx()

    result = code_search(ctx, query=query)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None


def test_code_search_empty_query():
    """Test Code Search tool with empty query."""
    ctx = _make_ctx()

    result = code_search(ctx, query="")

    assert result is not None


def test_code_search_complex_query():
    """Test Code Search tool with complex search query."""
    ctx = _make_ctx()

    result = code_search(ctx, query="class:UserService method:authenticate lang:python")

    assert result is not None
    assert "result" in result
