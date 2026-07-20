"""Enterprise Search tool for searching company documents and data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult
from glean.agent_toolkit.tools._transport import (
    TypedBackend,
    execute_tool,
    make_async_tool,
    register_backend,
)
from glean.api_client import Glean, models

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

_SNIPPET_MAX_CHARS = 500


def _to_facet_filters(filters: list[dict[str, Any]] | None) -> list[models.FacetFilter]:
    """Map structured ``[{field, values, exclude?}]`` filters to facet filters.

    Each filter dict becomes a ``FacetFilter`` on ``field``; every value
    becomes a ``FacetFilterValue`` whose ``relationType`` is ``EQUALS``, or
    ``NOT_EQUALS`` when ``exclude`` is true. Filters within a values list
    are OR-ed and separate ``FacetFilter`` entries are AND-ed by the API.

    Raises:
        ValueError: If a filter dict is missing ``field`` or ``values``.
    """
    facet_filters: list[models.FacetFilter] = []
    for spec in filters or []:
        field = spec.get("field")
        values = spec.get("values")
        if not field or not values:
            raise ValueError(
                f"Each filter must include a non-empty 'field' and 'values'; got: {spec!r}"
            )
        relation_type = (
            models.RelationType.NOT_EQUALS if spec.get("exclude") else models.RelationType.EQUALS
        )
        facet_filters.append(
            models.FacetFilter(
                field_name=str(field),
                values=[
                    models.FacetFilterValue(value=str(value), relation_type=relation_type)
                    for value in values
                ],
            )
        )
    return facet_filters


def _search_request_options(
    datasources: list[str] | None,
    filters: list[dict[str, Any]] | None,
) -> models.SearchRequestOptions | None:
    """Build ``requestOptions`` from datasources and structured filters."""
    facet_filters = _to_facet_filters(filters)
    if not datasources and not facet_filters:
        return None
    return models.SearchRequestOptions(
        facet_bucket_size=0,
        datasources_filter=list(datasources) if datasources else None,
        facet_filters=facet_filters or None,
    )


def _query_search(
    client: Glean,
    *,
    query: str,
    datasources: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    page_size: int = 10,
) -> models.SearchResponse:
    """Perform a typed ``POST /rest/api/v1/search`` call.

    ``datasources`` maps to ``requestOptions.datasourcesFilter`` and
    structured ``filters`` map to ``requestOptions.facetFilters``.
    """
    return client.client.search.query(
        query=query,
        page_size=page_size,
        request_options=_search_request_options(datasources, filters),
    )


async def _query_search_async(
    client: Glean,
    *,
    query: str,
    datasources: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    page_size: int = 10,
) -> models.SearchResponse:
    """Native async twin of :func:`_query_search` (``search.query_async``)."""
    return await client.client.search.query_async(
        query=query,
        page_size=page_size,
        request_options=_search_request_options(datasources, filters),
    )


def _shape_search_response(response: Any) -> dict[str, Any]:
    """Shape a ``SearchResponse`` into a compact, LLM-friendly payload."""
    shaped_results: list[dict[str, Any]] = []
    for result in getattr(response, "results", None) or []:
        document = getattr(result, "document", None)
        snippets: list[str] = []
        for snippet in getattr(result, "snippets", None) or []:
            text = getattr(snippet, "text", None) or getattr(snippet, "snippet", None)
            if not text:
                continue
            text = text.strip()
            if len(text) > _SNIPPET_MAX_CHARS:
                text = text[:_SNIPPET_MAX_CHARS] + "..."
            snippets.append(text)

        shaped_results.append(
            {
                "title": getattr(result, "title", None) or getattr(document, "title", None),
                "url": getattr(result, "url", None) or getattr(document, "url", None),
                "snippets": snippets,
                "datasource": getattr(document, "datasource", None),
                "document_id": getattr(document, "id", None),
            }
        )

    return {
        "results": shaped_results,
        "result_count": len(shaped_results),
        "has_more_results": bool(getattr(response, "has_more_results", None)),
    }


register_backend(
    "glean_search",
    TypedBackend(_query_search, _shape_search_response, async_fn=_query_search_async),
)


@tool_spec(
    name="glean_search",
    description=(
        "Search internal company documents, wikis, tickets, and knowledge bases. "
        "Use this instead of web_search when looking for internal/company information. "
        "Returns the top matching documents.\n"
        "INSTRUCTIONS:\n"
        "- Primary tool for all internal company knowledge.\n"
        "- Returns top relevant results, not exhaustive.\n"
        '- Output is {"results": [{title, url, snippets, datasource, document_id}], '
        '"result_count", "has_more_results"}.\n'
        '- "result_count" is the number of returned results, not a total corpus '
        'count; "has_more_results" indicates more matches exist.'
    ),
)
def search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description=(
                "Glean search query with optional filters. Supports keywords and "
                "various search filters - the Glean API will determine which "
                "filters are valid and available"
            ),
            examples=[
                "quarterly financial results",
                "API documentation owner:engineering",
                "security policy updated:past_week",
                "project roadmap from:product-team",
                "meeting notes after:2024-01-01",
            ],
        ),
    ],
    datasources: Annotated[
        list[str] | None,
        Field(
            description="Restrict results to specific datasources (e.g. ['confluence', 'gdrive']).",
        ),
    ] = None,
    filters: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description=(
                "Structured search filters. Each dict has 'field' (str), "
                "'values' (list[str]), and optional 'exclude' (bool)."
            ),
        ),
    ] = None,
    page_size: Annotated[
        int,
        Field(
            description="Number of results to return per page.",
            ge=1,
            le=100,
        ),
    ] = 10,
) -> ToolResult:
    """Search Glean for relevant documents using the query.

    Uses the typed Search API (``POST /rest/api/v1/search``). ``datasources``
    map to the request's ``datasourcesFilter``; each structured filter maps
    to a facet filter whose values carry ``relationType`` ``EQUALS`` (or
    ``NOT_EQUALS`` when ``exclude`` is true). The success payload contains
    ``results`` (each with title, url, snippets, datasource, document_id),
    ``result_count``, and ``has_more_results``.

    Args:
        ctx: Optional Glean context for client injection.
        query: Search query with optional filters - API will validate filter syntax.
        datasources: Optional list of datasource names to filter by.
        filters: Optional structured filters ``[{field, values, exclude?}]``.
        page_size: Number of results per page (default 10).
    """
    return execute_tool(
        "glean_search",
        {
            "query": query,
            "datasources": datasources,
            "filters": filters,
            "page_size": page_size,
        },
        ctx=ctx,
    )


search.native_async(make_async_tool("glean_search"))
