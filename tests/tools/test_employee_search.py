"""Tests for the Employee Search tool."""

import pytest

from glean.agent_toolkit.tools.employee_search import employee_search


def test_employee_search_success(vcr_cassette):
    """Test successful Employee Search tool execution with VCR recording/replay."""
    query_text = "John Smith engineering manager"

    result = employee_search(query=query_text)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    if result["result"] and hasattr(result["result"], "result"):
        response_data = result["result"].result
        assert response_data is not None


def test_employee_search_api_error(vcr_cassette):
    """Test Employee Search tool with API error response."""
    query_text = "invalid query that causes error"

    result = employee_search(query=query_text)

    assert result is not None


@pytest.mark.parametrize(
    "query",
    [
        "Sarah Johnson product manager",
        "data scientist machine learning",
        "frontend developer React",
        "security engineer DevOps",
        "UX designer mobile apps",
    ],
)
def test_employee_search_various_queries(vcr_cassette, query: str):
    """Test Employee Search tool with various employee search queries."""
    result = employee_search(query=query)

    assert result is not None
    assert "result" in result


def test_employee_search_by_department(vcr_cassette):
    """Test Employee Search tool searching by department."""
    query_text = "engineering department"

    result = employee_search(query=query_text)

    assert result is not None


def test_employee_search_by_role(vcr_cassette):
    """Test Employee Search tool searching by role type."""
    query_text = "product manager marketing team"

    result = employee_search(query=query_text)

    assert result is not None


def test_employee_search_no_results(vcr_cassette):
    """Test Employee Search tool when no employees are found."""
    query_text = "nonexistent person xyz123"

    result = employee_search(query=query_text)

    assert result is not None
