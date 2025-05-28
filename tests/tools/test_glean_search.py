import re

import pytest
from pytest_httpx import HTTPXMock
from tests.conftest import JSON, TOOLS_RUN_ENDPOINT_REGEX

from glean import models
from glean.toolkit.tools.glean_search import glean_search


@pytest.mark.load_json("glean_search_success")
def test_glean_search_success(httpx_mock: HTTPXMock, json_fixture_data: JSON) -> None:
    """Test successful Glean Search tool execution with a mocked API response."""
    query_text = "what are the holidays in 2025"
    expected_api_result = json_fixture_data

    httpx_mock.add_response(
        url=re.compile(TOOLS_RUN_ENDPOINT_REGEX),
        method="POST",
        json=expected_api_result,  # This is what the httpx client will return
        match_json={"name": "Glean Search", "parameters": {"query": query_text}},
    )

    tool_params = models.ToolParameters(query=query_text, other_params=models.ToolParameterValues())

    actual_result = glean_search(parameters=tool_params)

    assert actual_result["error"] is None
    assert actual_result["result"] == expected_api_result


def test_glean_search_api_error(httpx_mock: HTTPXMock) -> None:
    """Test Glean Search tool when the API returns an error."""
    query_text = "search that causes an error"

    httpx_mock.add_response(
        url=re.compile(TOOLS_RUN_ENDPOINT_REGEX),
        method="POST",
        status_code=500,
        json={"error": {"message": "Internal Server Error"}},
        match_json={"name": "Glean Search", "parameters": {"query": query_text}},
    )

    tool_params = models.ToolParameters(query=query_text, other_params=models.ToolParameterValues())
    actual_result = glean_search(parameters=tool_params)

    assert actual_result["result"] is None
    assert actual_result["error"] is not None
    assert "500" in actual_result["error"]
