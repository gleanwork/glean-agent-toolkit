"""Tests for the Glean Search tool."""

import pytest

from glean.agent_toolkit.tools.glean_search import glean_search
from glean.api_client import models


def test_glean_search_success(vcr_cassette):
    """Test successful Glean Search tool execution with VCR recording/replay."""
    query_text = "company holidays 2025"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = glean_search(parameters=tool_params)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_glean_search_api_error(vcr_cassette):
    """Test Glean Search tool with API error response."""
    query_text = "invalid query that causes error"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = glean_search(parameters=tool_params)

    # With VCR, we can test actual error scenarios by recording them
    assert result is not None
