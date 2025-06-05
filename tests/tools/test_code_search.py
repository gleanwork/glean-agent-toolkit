"""Tests for the Code Search tool."""

import pytest

from glean.agent_toolkit.tools.code_search import code_search
from glean.api_client import models


@pytest.mark.skip(reason="Skipping test_code_search_success")
def test_code_search_success(vcr_cassette):
    """Test successful Code Search tool execution with VCR recording/replay."""
    query_text = "function authenticate user"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = code_search(parameters=tool_params)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_code_search_api_error(vcr_cassette):
    """Test Code Search tool with API error response."""
    query_text = "invalid query that causes error"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = code_search(parameters=tool_params)

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
    tool_params = {"query": models.ToolsCallParameter(name="query", value=query)}
    result = code_search(parameters=tool_params)

    assert result is not None
    assert "result" in result


def test_code_search_empty_query(vcr_cassette):
    """Test Code Search tool with empty query."""
    query_text = ""

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = code_search(parameters=tool_params)

    assert result is not None


def test_code_search_complex_query(vcr_cassette):
    """Test Code Search tool with complex search query."""
    query_text = "class:UserService method:authenticate lang:python"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = code_search(parameters=tool_params)

    assert result is not None
    assert "result" in result
