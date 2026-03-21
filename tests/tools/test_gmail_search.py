import pytest
from unittest.mock import MagicMock, patch

from glean.agent_toolkit.tools.gmail_search import gmail_search


def test_gmail_search_success():
    """Test successful Gmail Search tool execution using a mocked API client."""
    mock_result = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_context)
    mock_context.__exit__ = MagicMock(return_value=False)
    mock_context.client.tools.run.return_value = mock_result

    with patch("glean.agent_toolkit.tools._common.api_client", return_value=mock_context):
        result = gmail_search(query="project updates from last week")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] is mock_result


def test_gmail_search_api_error(vcr_cassette):
    """Test Gmail Search tool with API error response."""
    query_text = "invalid query that causes error"

    result = gmail_search(query=query_text)

    assert result is not None


@pytest.mark.parametrize("query", [
    "urgent emails from manager",
    "meeting invitations",
    "invoice from vendor",
    "password reset emails",
    "security alerts",
])
def test_gmail_search_various_queries(vcr_cassette, query: str):
    """Test Gmail Search tool with various email types."""
    result = gmail_search(query=query)

    assert result is not None
    assert "result" in result


def test_gmail_search_no_emails_found(vcr_cassette):
    """Test Gmail Search tool when no emails are found."""
    query_text = "nonexistent subject xyz123"

    result = gmail_search(query=query_text)

    assert result is not None


@pytest.mark.parametrize("search_filter", [
    "from:boss@company.com",
    "subject:urgent",
    "has:attachment",
    "before:2025/01/01",
    "label:important",
])
def test_gmail_search_with_filters(vcr_cassette, search_filter: str):
    """Test Gmail Search tool with Gmail-specific search filters."""
    result = gmail_search(query=search_filter)

    assert result is not None
