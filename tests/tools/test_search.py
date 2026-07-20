"""Tests for the Search tool (typed Search API backend)."""

from typing import Any
from unittest.mock import MagicMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.search import (
    _SNIPPET_MAX_CHARS,
    _shape_search_response,
    _to_facet_filters,
    search,
)
from glean.api_client import models


def _make_ctx(response: object = None) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.search.query.return_value = (
        response if response is not None else models.SearchResponse(results=[])
    )
    return GleanContext(client=mock_client)


def _query_kwargs(ctx: GleanContext) -> dict[str, Any]:
    mock_client = ctx.get_client()
    return mock_client.client.search.query.call_args.kwargs  # type: ignore[union-attr]


def _sdk_response() -> models.SearchResponse:
    return models.SearchResponse(
        results=[
            models.SearchResult(
                title="Q3 Financial Results",
                url="https://drive.example.com/doc/abc123",
                document=models.Document(id="doc-1", datasource="gdrive"),
                snippets=[
                    models.SearchResultSnippet(text="Revenue grew 18% quarter over quarter."),
                ],
            ),
            models.SearchResult(
                title="Q3 Board Deck",
                url="https://docs.example.com/deck/def456",
                document=models.Document(id="doc-2", datasource="gdrive"),
                snippets=[models.SearchResultSnippet(text="Q3 highlights and FY outlook.")],
            ),
        ],
        has_more_results=True,
    )


def test_search_success_returns_shaped_results() -> None:
    ctx = _make_ctx(_sdk_response())

    result = search(ctx, query="quarterly financial results")

    assert result["status"] == "ok"
    assert result["error"] is None

    payload = result["result"]
    assert payload["result_count"] == 2
    assert payload["has_more_results"] is True
    first = payload["results"][0]
    assert first == {
        "title": "Q3 Financial Results",
        "url": "https://drive.example.com/doc/abc123",
        "snippets": ["Revenue grew 18% quarter over quarter."],
        "datasource": "gdrive",
        "document_id": "doc-1",
    }


def test_search_sends_query_and_page_size() -> None:
    ctx = _make_ctx()

    result = search(ctx, query="company holidays 2025", page_size=25)

    assert result["status"] == "ok"
    kwargs = _query_kwargs(ctx)
    assert kwargs["query"] == "company holidays 2025"
    assert kwargs["page_size"] == 25
    assert kwargs["request_options"] is None


def test_search_default_page_size() -> None:
    ctx = _make_ctx()

    search(ctx, query="docs")

    assert _query_kwargs(ctx)["page_size"] == 10


def test_search_with_datasources() -> None:
    ctx = _make_ctx()

    result = search(ctx, query="onboarding", datasources=["confluence", "gdrive"])

    assert result["status"] == "ok"
    request_options = _query_kwargs(ctx)["request_options"]
    assert isinstance(request_options, models.SearchRequestOptions)
    assert request_options.datasources_filter == ["confluence", "gdrive"]
    assert request_options.facet_filters is None


def test_search_with_filters_maps_to_facet_filters() -> None:
    ctx = _make_ctx()
    filters = [{"field": "type", "values": ["Presentation", "Spreadsheet"]}]

    result = search(ctx, query="sprint tasks", filters=filters)

    assert result["status"] == "ok"
    request_options = _query_kwargs(ctx)["request_options"]
    facet_filters = request_options.facet_filters
    assert len(facet_filters) == 1
    assert facet_filters[0].field_name == "type"
    assert [v.value for v in facet_filters[0].values] == ["Presentation", "Spreadsheet"]
    assert all(v.relation_type == models.RelationType.EQUALS for v in facet_filters[0].values)


def test_search_exclude_filter_maps_to_not_equals() -> None:
    ctx = _make_ctx()
    filters = [{"field": "from", "values": ["bot"], "exclude": True}]

    search(ctx, query="deploy failures", filters=filters)

    facet_filters = _query_kwargs(ctx)["request_options"].facet_filters
    assert facet_filters[0].values[0].relation_type == models.RelationType.NOT_EQUALS


def test_search_invalid_filter_is_validation_error() -> None:
    ctx = _make_ctx()

    result = search(ctx, query="docs", filters=[{"values": ["x"]}])

    assert result["status"] == "error"
    assert result["error_type"] == "validation"
    assert result["suggested_action"] == "rephrase_query"


def test_search_api_error() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.search.query.side_effect = Exception("API Error")
    ctx = GleanContext(client=mock_client)

    result = search(ctx, query="invalid query that causes error")

    assert result["status"] == "error"
    assert result["error"] == "API Error"
    assert result["result"] is None


def test_to_facet_filters_requires_field_and_values() -> None:
    import pytest

    with pytest.raises(ValueError):
        _to_facet_filters([{"field": "app", "values": []}])
    with pytest.raises(ValueError):
        _to_facet_filters([{"values": ["jira"]}])


def test_to_facet_filters_empty_input() -> None:
    assert _to_facet_filters(None) == []
    assert _to_facet_filters([]) == []


def test_shape_search_response_truncates_long_snippets() -> None:
    long_text = "x" * (_SNIPPET_MAX_CHARS + 100)
    response = models.SearchResponse(
        results=[
            models.SearchResult(
                title="Doc",
                url="https://example.com/doc",
                snippets=[models.SearchResultSnippet(text=long_text)],
            )
        ]
    )

    shaped = _shape_search_response(response)

    snippet = shaped["results"][0]["snippets"][0]
    assert snippet == "x" * _SNIPPET_MAX_CHARS + "..."


def test_shape_search_response_falls_back_to_deprecated_snippet_field() -> None:
    response = models.SearchResponse(
        results=[
            models.SearchResult(
                title="Doc",
                url="https://example.com/doc",
                snippets=[models.SearchResultSnippet(snippet="legacy snippet text")],
            )
        ]
    )

    shaped = _shape_search_response(response)

    assert shaped["results"][0]["snippets"] == ["legacy snippet text"]


def test_shape_search_response_handles_empty_response() -> None:
    shaped = _shape_search_response(models.SearchResponse())

    assert shaped == {"results": [], "result_count": 0, "has_more_results": False}


def test_search_missing_credentials_returns_tool_result_not_raise() -> None:
    """A2: credential errors surface as a structured ToolResult, never raise."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {}, clear=True):
        result = search(query="anything")

    assert result["status"] == "error"
    assert result["error_type"] == "auth"
    assert result["suggested_action"] == "check_credentials"
    assert result["error"] is not None
    assert "GLEAN_API_TOKEN" in result["error"]
    assert "configure()" in result["error"]


def test_search_invalid_server_url_returns_config_error() -> None:
    """A1: a scheme-less server URL fails fast with a config classification."""
    import os
    from unittest.mock import patch

    with patch.dict(
        os.environ,
        {"GLEAN_API_TOKEN": "tok", "GLEAN_SERVER_URL": "my-company-be.glean.com"},
        clear=True,
    ):
        result = search(query="anything")

    assert result["status"] == "error"
    assert result["error_type"] == "config"
    assert result["suggested_action"] == "check_configuration"
    assert result["error"] is not None and "http" in result["error"]
