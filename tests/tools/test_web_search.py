"""Tests for the Web Search tool."""

from unittest.mock import MagicMock

import pytest

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.web_search import web_search


def _make_ctx(return_value: object = None) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.return_value = (
        return_value if return_value is not None else {"data": "mock"}
    )
    return GleanContext(client=mock_client)


def test_web_search_success() -> None:
    mock_result = {"data": "mock"}
    ctx = _make_ctx(mock_result)

    result = web_search(ctx, query="Python programming best practices")

    assert result["status"] == "ok"
    assert result["result"] == mock_result
    assert result["error"] is None


def test_web_search_api_error() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.side_effect = Exception("API Error")
    ctx = GleanContext(client=mock_client)

    result = web_search(ctx, query="invalid query that causes error")

    assert result["status"] == "error"
    assert result["result"] is None


@pytest.mark.parametrize(
    "query",
    [
        "JavaScript frameworks comparison",
        "Docker container deployment",
        "API design patterns",
        "database optimization techniques",
        "mobile app development",
    ],
)
def test_web_search_various_queries(query: str) -> None:
    ctx = _make_ctx()

    result = web_search(ctx, query=query)

    assert result["status"] == "ok"
    assert result["error"] is None
