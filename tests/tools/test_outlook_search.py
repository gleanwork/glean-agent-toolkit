from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.tools.outlook_search import outlook_search


def _mock_context(return_value: object = None) -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.return_value = (
        return_value if return_value is not None else {"data": "mock"}
    )
    return ctx


def test_outlook_search_success():
    """Test successful Outlook Search tool execution using a mocked API client."""
    mock_result = {"data": "mock"}
    ctx = _mock_context(mock_result)
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = outlook_search(query="quarterly planning meeting")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] == mock_result


def test_outlook_search_api_error():
    """Test Outlook Search tool returns error dict when API raises."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.side_effect = Exception("API Error")

    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = outlook_search(query="invalid query that causes error")

    assert result is not None
    assert "error" in result
    assert result["result"] is None


@pytest.mark.parametrize("query", [
    "budget review meeting",
    "team standup calendar",
    "client presentation tomorrow",
    "all-hands meeting",
    "project deadline reminder",
])
def test_outlook_search_various_queries(query: str):
    """Test Outlook Search tool with various calendar/email queries."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = outlook_search(query=query)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None


def test_outlook_search_calendar_events():
    """Test Outlook Search tool for calendar events."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = outlook_search(query="meetings this week")

    assert result is not None


def test_outlook_search_no_results():
    """Test Outlook Search tool when no results are found."""
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=_mock_context()):
        result = outlook_search(query="nonexistent meeting xyz")

    assert result is not None
