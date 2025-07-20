"""Tests for the Glean Search tool."""

import pytest

from glean.agent_toolkit.tools.glean_search import glean_search


def test_glean_search_success(vcr_cassette):
    """Test successful Glean Search tool execution with VCR recording/replay."""
    query_text = "company holidays 2025"

    result = glean_search(query=query_text)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_glean_search_api_error(vcr_cassette):
    """Test Glean Search tool with API error response."""
    query_text = "invalid query that causes error"

    result = glean_search(query=query_text)

    assert result is not None
