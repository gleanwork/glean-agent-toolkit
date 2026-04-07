"""Tests for the Search tool (renamed from glean_search)."""

from unittest.mock import patch

import pytest

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


def test_search_without_datasource_passes_only_query():
    """Test that calling search without datasource only passes query to the API."""
    with patch("glean.agent_toolkit.tools._common.run_tool") as mock_run:
        mock_run.return_value = {"result": {}}
        search(query="test query")

        mock_run.assert_called_once()
        _, params = mock_run.call_args.args
        assert "query" in params
        assert "datasource" not in params


def test_search_with_datasource_passes_both_params():
    """Test that calling search with datasource passes both query and datasource."""
    with patch("glean.agent_toolkit.tools._common.run_tool") as mock_run:
        mock_run.return_value = {"result": {}}
        search(query="test query", datasource="confluence")

        mock_run.assert_called_once()
        _, params = mock_run.call_args.args
        assert "query" in params
        assert "datasource" in params
        assert params["datasource"].name == "datasource"
        assert params["datasource"].value == "confluence"
