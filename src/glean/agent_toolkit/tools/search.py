"""Enterprise Search tool for searching company documents and data."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


def _build_search_params(
    query: str,
    datasources: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    page_size: int = 10,
) -> dict[str, Any]:
    """Map high-level search parameters to ToolsCallParameter format.

    Args:
        query: The search query string.
        datasources: Optional list of datasource names to restrict results.
        filters: Optional structured filters ``[{field, values, exclude?}]``.
        page_size: Number of results per page.

    Returns:
        Kwargs suitable for :func:`convert_to_tool_params`.
    """
    # TODO: Replace with POST /api/search when available — this mapping can be deleted.
    params: dict[str, Any] = {"query": query, "pageSize": str(page_size)}

    if datasources:
        params["datasources"] = json.dumps(datasources)

    if filters:
        params["filters"] = json.dumps(filters)

    return params


@tool_spec(
    name="glean_search",
    description=(
        "Search internal company documents, wikis, tickets, and knowledge bases. "
        "Use this instead of web_search when looking for internal/company information. "
        "Returns the top matching documents.\n"
        "INSTRUCTIONS:\n"
        "- Primary tool for all internal company knowledge.\n"
        "- Returns top relevant results, not exhaustive.\n"
        '- For count queries ("how many..."), use the "statistics" field in the output.'
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

    Args:
        ctx: Optional Glean context for client injection.
        query: Search query with optional filters - API will validate filter syntax.
        datasources: Optional list of datasource names to filter by.
        filters: Optional structured filters ``[{field, values, exclude?}]``.
        page_size: Number of results per page (default 10).
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    raw_params = _build_search_params(query, datasources, filters, page_size)
    parameters = convert_to_tool_params(**raw_params)
    return run_tool("Glean Search", parameters, client=client)
