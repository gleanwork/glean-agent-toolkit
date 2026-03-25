from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.tools.gmail_search import gmail_search


def _mock_context(return_value: object = None) -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.return_value = return_value if return_value is not None else {"data": "mock"}
    return ctx


def test_gmail_search_success():
    """Test successful Gmail Search tool execution using a mocked API client."""
    mock_result = {"data": "mock"}
    ctx = _mock_context(mock_result)
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = gmail_search(query="project updates from last week")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] == mock_result


def test_gmail_search_api_error():
    """Test Gmail Search tool returns error dict when API raises."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.side_effect = Exception("API Error")

    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = gmail_search(query="invalid query that causes error")

    assert result is not None
    assert "error" in result
    assert result["result"] is None


@pytest.mark.parametrize("query", [
    "urgent emails from manager",
    "meeting invitations",
    "invoice from vendor",
    "password reset emails",
    "security alerts",
])
def test_gmail_search_various_queries(query: str):
    """Test Gmail Search tool with various email types."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = gmail_search(query=query)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None


def test_gmail_search_no_emails_found():
    """Test Gmail Search tool when no emails are found."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = gmail_search(query="nonexistent subject xyz123")

    assert result is not None


@pytest.mark.parametrize("search_filter", [
    "from:boss@company.com",
    "subject:urgent",
    "has:attachment",
    "before:2025/01/01",
    "label:important",
])
def test_gmail_search_with_filters(search_filter: str):
    """Test Gmail Search tool with Gmail-specific search filters."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = gmail_search(query=search_filter)

    assert result is not None
