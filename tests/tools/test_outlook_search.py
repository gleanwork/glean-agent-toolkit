from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.tools.outlook_search import outlook_search
from glean.api_client import models


def test_outlook_search_success():
    """Test successful Outlook Search tool execution using a mocked API client."""
    mock_result = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_context)
    mock_context.__exit__ = MagicMock(return_value=False)
    mock_context.client.tools.run.return_value = mock_result

    with patch("glean.agent_toolkit.tools._common.api_client", return_value=mock_context):
        result = outlook_search(query="quarterly planning meeting")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] is mock_result


def test_outlook_search_api_error(vcr_cassette):
    """Test Outlook Search tool with API error response."""
    query_text = "invalid query that causes error"

    result = outlook_search(query=query_text)

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
    result = outlook_search(query=query)

    assert result is not None
    assert "result" in result


def test_outlook_search_calendar_events(vcr_cassette):
    """Test Outlook Search tool for calendar events."""
    query_text = "meetings this week"

    result = outlook_search(query=query_text)

    assert result is not None


def test_outlook_search_no_results(vcr_cassette):
    """Test Outlook Search tool when no results are found."""
    query_text = "nonexistent meeting xyz"

    result = outlook_search(query=query_text)

    assert result is not None
