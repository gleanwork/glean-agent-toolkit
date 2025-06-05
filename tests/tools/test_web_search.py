import pytest

from glean.agent_toolkit.tools.web_search import web_search
from glean.api_client import models


def test_web_search_success(vcr_cassette):
    """Test successful Web Search tool execution with VCR recording/replay."""
    query_text = "Python programming best practices"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = web_search(parameters=tool_params)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_web_search_api_error(vcr_cassette):
    """Test Web Search tool with API error response."""
    query_text = "invalid query that causes error"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = web_search(parameters=tool_params)

    assert result is not None


@pytest.mark.parametrize("query", [
    "JavaScript frameworks comparison",
    "Docker container deployment",
    "API design patterns",
    "database optimization techniques",
    "mobile app development",
])
def test_web_search_various_queries(vcr_cassette, query: str):
    """Test Web Search tool with various technical queries."""
    tool_params = {"query": models.ToolsCallParameter(name="query", value=query)}
    result = web_search(parameters=tool_params)

    assert result is not None
    assert "result" in result


def test_web_search_specific_domain(vcr_cassette):
    """Test Web Search tool with domain-specific search."""
    query_text = "site:stackoverflow.com Python async programming"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = web_search(parameters=tool_params)

    assert result is not None


def test_web_search_news_query(vcr_cassette):
    """Test Web Search tool with news-related query."""
    query_text = "latest technology news 2025"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = web_search(parameters=tool_params)

    assert result is not None


def test_web_search_no_results(vcr_cassette):
    """Test Web Search tool when no relevant results are found."""
    query_text = "extremely specific nonexistent query xyz123abc"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = web_search(parameters=tool_params)

    assert result is not None
