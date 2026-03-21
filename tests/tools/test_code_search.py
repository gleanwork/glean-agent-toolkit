"""Tests for the Code Search tool."""

import pytest
from unittest.mock import MagicMock, patch

from glean.agent_toolkit.tools.code_search import code_search


def test_code_search_success():
    """Test successful Code Search tool execution using a mocked API client."""
    mock_result = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_context)
    mock_context.__exit__ = MagicMock(return_value=False)
    mock_context.client.tools.run.return_value = mock_result

    with patch("glean.agent_toolkit.tools._common.api_client", return_value=mock_context):
        result = code_search(query="function authenticate user")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] is mock_result


def test_code_search_api_error(vcr_cassette):
    """Test Code Search tool with API error response."""
    query_text = "invalid query that causes error"

    result = code_search(query=query_text)

    assert result is not None


@pytest.mark.parametrize("query", [
    "class UserManager",
    "function login validation",
    "API endpoint security",
    "database connection pool",
    "error handling middleware",
])
def test_code_search_various_queries(vcr_cassette, query: str):
    """Test Code Search tool with various code-related queries."""
    result = code_search(query=query)

    assert result is not None
    assert "result" in result


def test_code_search_empty_query(vcr_cassette):
    """Test Code Search tool with empty query."""
    query_text = ""

    result = code_search(query=query_text)

    assert result is not None


def test_code_search_complex_query(vcr_cassette):
    """Test Code Search tool with complex search query."""
    query_text = "class:UserService method:authenticate lang:python"

    result = code_search(query=query_text)

    assert result is not None
    assert "result" in result
