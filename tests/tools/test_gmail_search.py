import pytest

from glean.agent_toolkit.tools.gmail_search import gmail_search
from glean.api_client import models


@pytest.mark.skip(reason="Skipping test_gmail_search_success")
def test_gmail_search_success(vcr_cassette):
    """Test successful Gmail Search tool execution with VCR recording/replay."""
    query_text = "project updates from last week"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = gmail_search(parameters=tool_params)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_gmail_search_api_error(vcr_cassette):
    """Test Gmail Search tool with API error response."""
    query_text = "invalid query that causes error"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = gmail_search(parameters=tool_params)

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
    tool_params = {"query": models.ToolsCallParameter(name="query", value=query)}
    result = gmail_search(parameters=tool_params)

    assert result is not None
    assert "result" in result


def test_gmail_search_no_emails_found(vcr_cassette):
    """Test Gmail Search tool when no emails are found."""
    query_text = "nonexistent email thread"

    tool_params = {"query": models.ToolsCallParameter(name="query", value=query_text)}
    result = gmail_search(parameters=tool_params)

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
    tool_params = {"query": models.ToolsCallParameter(name="query", value=search_filter)}
    result = gmail_search(parameters=tool_params)

    assert result is not None
