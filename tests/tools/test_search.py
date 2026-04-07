"""Tests for the Search tool."""

import json
from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.tools.search import search


def _mock_context(return_value: object = None) -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.return_value = (
        return_value if return_value is not None else {"data": "mock"}
    )
    return ctx


def test_search_success():
    """Test successful search with query only."""
    mock_result = {"data": "mock"}
    ctx = _mock_context(mock_result)
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = search(query="company holidays 2025")

    assert result is not None
    assert "result" in result
    assert result.get("error") is None
    assert result["result"] == mock_result


def test_search_api_error():
    """Test search returns error dict when API raises."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.tools.run.side_effect = Exception("API Error")

    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = search(query="invalid query that causes error")

    assert result is not None
    assert "error" in result
    assert result["result"] is None


def test_search_with_datasources():
    """Test search with datasources filter."""
    ctx = _mock_context()
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = search(query="onboarding docs", datasources=["confluence", "jira"])

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    call_kwargs = ctx.client.tools.run.call_args
    params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
    assert "datasources" in params
    assert json.loads(params["datasources"].value) == ["confluence", "jira"]


def test_search_with_filters():
    """Test search with structured filters."""
    ctx = _mock_context()
    filters = [
        {"field": "type", "values": ["document", "spreadsheet"]},
        {"field": "owner", "values": ["jane"], "exclude": False},
    ]
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = search(query="quarterly report", filters=filters)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    call_kwargs = ctx.client.tools.run.call_args
    params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
    assert "filters" in params
    assert json.loads(params["filters"].value) == filters


def test_search_with_page_size():
    """Test search with custom page_size."""
    ctx = _mock_context()
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = search(query="security policy", page_size=25)

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    call_kwargs = ctx.client.tools.run.call_args
    params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
    assert "pageSize" in params
    assert params["pageSize"].value == "25"


def test_search_default_page_size_omitted():
    """Test that default page_size=10 is NOT sent as a parameter."""
    ctx = _mock_context()
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        search(query="test query")

    call_kwargs = ctx.client.tools.run.call_args
    params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
    assert "pageSize" not in params


def test_search_all_params():
    """Test search with all parameters combined."""
    ctx = _mock_context()
    filters = [{"field": "status", "values": ["open"], "exclude": True}]
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        result = search(
            query="bug reports",
            datasources=["jira"],
            filters=filters,
            page_size=50,
        )

    assert result is not None
    assert "result" in result
    assert result.get("error") is None

    call_kwargs = ctx.client.tools.run.call_args
    params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
    assert params["query"].value == "bug reports"
    assert json.loads(params["datasources"].value) == ["jira"]
    assert json.loads(params["filters"].value) == filters
    assert params["pageSize"].value == "50"


def test_search_none_datasources_omitted():
    """Test that datasources=None is NOT sent as a parameter."""
    ctx = _mock_context()
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        search(query="test query", datasources=None)

    call_kwargs = ctx.client.tools.run.call_args
    params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
    assert "datasources" not in params


def test_search_none_filters_omitted():
    """Test that filters=None is NOT sent as a parameter."""
    ctx = _mock_context()
    with patch("glean.agent_toolkit.tools._common.api_client", return_value=ctx):
        search(query="test query", filters=None)

    call_kwargs = ctx.client.tools.run.call_args
    params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
    assert "filters" not in params
