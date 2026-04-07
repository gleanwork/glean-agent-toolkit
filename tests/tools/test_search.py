"""Tests for the Search tool."""

from glean.agent_toolkit.tools.search import search


def test_search_success(vcr_cassette):
    """Test successful Search tool execution with VCR recording/replay."""
    query_text = "company holidays 2025"

    result = search(query=query_text)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_search_api_error(vcr_cassette):
    """Test Search tool with API error response."""
    query_text = "invalid query that causes error"

    result = search(query=query_text)

    assert result is not None


def test_search_with_datasource(vcr_cassette):
    """Test Search tool with datasource filter."""
    result = search(query="support tickets", datasource="zendesk")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
