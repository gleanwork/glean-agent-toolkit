import pytest

from glean.agent_toolkit.tools.outlook_search import outlook_search
from glean.api_client import models


@pytest.mark.skip(reason="Skipping test_outlook_search_success")
def test_outlook_search_success(vcr_cassette):
    """Test successful Outlook Search tool execution with VCR recording/replay."""
    query_text = "quarterly planning meeting"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = outlook_search(parameters=tool_params)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_outlook_search_api_error(vcr_cassette):
    """Test Outlook Search tool with API error response."""
    query_text = "invalid query that causes error"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = outlook_search(parameters=tool_params)

    assert result is not None


@pytest.mark.parametrize("query", [
    "budget review meeting",
    "team standup calendar",
    "client presentation tomorrow",
    "all-hands meeting",
    "project deadline reminder",
])
def test_outlook_search_various_queries(vcr_cassette, query: str):
    """Test Outlook Search tool with various calendar/email queries."""
    tool_params = {"query": models.ToolsCallParameter(name="query", value=query)}
    result = outlook_search(parameters=tool_params)

    assert result is not None
    assert "result" in result


def test_outlook_search_calendar_events(vcr_cassette):
    """Test Outlook Search tool for calendar events."""
    query_text = "meetings this week"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = outlook_search(parameters=tool_params)

    assert result is not None


def test_outlook_search_no_results(vcr_cassette):
    """Test Outlook Search tool when no results are found."""
    query_text = "nonexistent meeting xyz"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = outlook_search(parameters=tool_params)

    assert result is not None
