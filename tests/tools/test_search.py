"""Tests for the Search tool."""

import json
from unittest.mock import MagicMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.search import _build_search_params, search


def _make_ctx(return_value: object = None) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.return_value = (
        return_value if return_value is not None else {"data": "mock"}
    )
    return GleanContext(client=mock_client)


def test_search_success() -> None:
    mock_result = {"data": "mock"}
    ctx = _make_ctx(mock_result)

    result = search(ctx, query="company holidays 2025")

    assert result is not None
    assert result["status"] == "ok"
    assert result["result"] == mock_result
    assert result["error"] is None


def test_search_api_error() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.side_effect = Exception("API Error")
    ctx = GleanContext(client=mock_client)

    result = search(ctx, query="invalid query that causes error")

    assert result is not None
    assert result["status"] == "error"
    assert result["error"] == "API Error"
    assert result["result"] is None


def test_search_with_datasources() -> None:
    ctx = _make_ctx()
    result = search(ctx, query="onboarding", datasources=["confluence", "gdrive"])

    assert result["status"] == "ok"
    mock_client = ctx.get_client()
    call_params = mock_client.client.tools.run.call_args.kwargs["parameters"]
    assert "datasources" in call_params
    assert json.loads(call_params["datasources"].value) == ["confluence", "gdrive"]


def test_search_with_filters() -> None:
    ctx = _make_ctx()
    filters = [{"field": "app", "values": ["jira"], "exclude": False}]
    result = search(ctx, query="sprint tasks", filters=filters)

    assert result["status"] == "ok"
    mock_client = ctx.get_client()
    call_params = mock_client.client.tools.run.call_args.kwargs["parameters"]
    assert "filters" in call_params
    assert json.loads(call_params["filters"].value) == filters


def test_search_with_page_size() -> None:
    ctx = _make_ctx()
    result = search(ctx, query="docs", page_size=25)

    assert result["status"] == "ok"
    mock_client = ctx.get_client()
    call_params = mock_client.client.tools.run.call_args.kwargs["parameters"]
    assert call_params["pageSize"].value == "25"


def test_search_default_page_size() -> None:
    ctx = _make_ctx()
    result = search(ctx, query="docs")

    assert result["status"] == "ok"
    mock_client = ctx.get_client()
    call_params = mock_client.client.tools.run.call_args.kwargs["parameters"]
    assert call_params["pageSize"].value == "10"


def test_build_search_params_minimal() -> None:
    params = _build_search_params("hello")
    assert params == {"query": "hello", "pageSize": "10"}


def test_build_search_params_full() -> None:
    params = _build_search_params(
        "hello",
        datasources=["slack"],
        filters=[{"field": "owner", "values": ["alice"]}],
        page_size=5,
    )
    assert params["query"] == "hello"
    assert params["pageSize"] == "5"
    assert json.loads(params["datasources"]) == ["slack"]
    assert json.loads(params["filters"]) == [{"field": "owner", "values": ["alice"]}]
