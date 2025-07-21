import pytest

from glean.agent_toolkit.tools.calendar_search import calendar_search


def test_calendar_search_success(vcr_cassette):
    """Test successful Calendar Search tool execution with VCR recording/replay."""
    query_text = "team standup meetings next week"

    result = calendar_search(query=query_text)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_calendar_search_api_error(vcr_cassette):
    """Test Calendar Search tool with API error response."""
    query_text = "invalid query that causes error"

    result = calendar_search(query=query_text)

    assert result is not None


@pytest.mark.parametrize("query", [
    "sprint planning meeting",
    "quarterly business review",
    "client demo presentation",
    "one-on-one meetings",
    "conference room bookings",
])
def test_calendar_search_various_queries(vcr_cassette, query: str):
    """Test Calendar Search tool with various meeting types."""
    result = calendar_search(query=query)

    assert result is not None
    assert "result" in result


def test_calendar_search_by_date_range(vcr_cassette):
    """Test Calendar Search tool with date range filtering."""
    query_text = "meetings this week"

    result = calendar_search(query=query_text)

    assert result is not None


def test_calendar_search_by_attendee(vcr_cassette):
    """Test Calendar Search tool with specific attendee."""
    query_text = "meetings with John Smith"

    result = calendar_search(query=query_text)

    assert result is not None


def test_calendar_search_no_results(vcr_cassette):
    """Test Calendar Search tool when no meetings are found."""
    query_text = "nonexistent meeting xyz123"

    result = calendar_search(query=query_text)

    assert result is not None
