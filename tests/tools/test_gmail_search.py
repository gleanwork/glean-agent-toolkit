"""Tests for the Gmail Search tool."""

from unittest.mock import MagicMock

import pytest

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.gmail_search import gmail_search


def _make_ctx(return_value: object = None) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.return_value = (
        return_value if return_value is not None else {"data": "mock"}
    )
    return GleanContext(client=mock_client)


def test_gmail_search_success():
    """Test successful Gmail Search tool execution using injected context."""
    mock_result = {"data": "mock"}
    ctx = _make_ctx(mock_result)

    result = gmail_search(ctx, query="project updates from last week")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] == mock_result


def test_gmail_search_api_error():
    """Test Gmail Search tool returns error dict when API raises."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.side_effect = Exception("API Error")
    ctx = GleanContext(client=mock_client)

    result = gmail_search(ctx, query="invalid query that causes error")

    assert result is not None
    assert "error" in result
    assert result["result"] is None


@pytest.mark.parametrize(
    "query",
    [
        "urgent emails from manager",
        "meeting invitations",
        "invoice from vendor",
        "password reset emails",
        "security alerts",
    ],
)
def test_gmail_search_various_queries(query: str):
    """Test Gmail Search tool with various email types."""
    ctx = _make_ctx()

    result = gmail_search(ctx, query=query)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None


def test_gmail_search_no_emails_found():
    """Test Gmail Search tool when no emails are found."""
    ctx = _make_ctx()

    result = gmail_search(ctx, query="nonexistent subject xyz123")

    assert result is not None


@pytest.mark.parametrize(
    "search_filter",
    [
        "from:boss@company.com",
        "subject:urgent",
        "has:attachment",
        "before:2025/01/01",
        "label:important",
    ],
)
def test_gmail_search_with_filters(search_filter: str):
    """Test Gmail Search tool with Gmail-specific search filters."""
    ctx = _make_ctx()

    result = gmail_search(ctx, query=search_filter)

    assert result is not None
