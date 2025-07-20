import pytest

from glean.agent_toolkit.tools.gmail_search import gmail_search


@pytest.mark.skip(reason="Skipping test_gmail_search_success")
def test_gmail_search_success(vcr_cassette):
    """Test successful Gmail Search tool execution with VCR recording/replay."""
    query_text = "project updates from last week"

    result = gmail_search(query=query_text)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


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
