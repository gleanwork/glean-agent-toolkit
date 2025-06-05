import pytest

from glean.agent_toolkit.tools.ai_web_search import ai_web_search
from glean.api_client import models


def test_ai_web_search_success(vcr_cassette):
    """Test successful AI Web Search tool execution with VCR recording/replay."""
    query_text = "latest developments in artificial intelligence"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = ai_web_search(parameters=tool_params)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_ai_web_search_api_error(vcr_cassette):
    """Test AI Web Search tool with API error response."""
    query_text = "invalid query that causes error"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = ai_web_search(parameters=tool_params)

    assert result is not None


@pytest.mark.parametrize("query", [
    "machine learning frameworks 2025",
    "cloud computing trends",
    "cybersecurity best practices",
    "sustainable technology solutions",
    "blockchain applications",
])
def test_ai_web_search_various_queries(vcr_cassette, query: str):
    """Test AI Web Search tool with various technology topics."""
    tool_params = {"query": models.ToolsCallParameter(name="query", value=query)}
    result = ai_web_search(parameters=tool_params)

    assert result is not None
    assert "result" in result


def test_ai_web_search_complex_query(vcr_cassette):
    """Test AI Web Search tool with complex multi-part query."""
    query_text = "comparative analysis of LLM models GPT vs Claude performance benchmarks"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = ai_web_search(parameters=tool_params)

    assert result is not None


def test_ai_web_search_no_results(vcr_cassette):
    """Test AI Web Search tool when no relevant results are found."""
    query_text = "nonexistent technology xyz123"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = ai_web_search(parameters=tool_params)

    assert result is not None
