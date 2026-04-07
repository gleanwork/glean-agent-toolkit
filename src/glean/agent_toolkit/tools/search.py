"""Enterprise Search tool for searching company documents and data."""

from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import run_tool

# TODO: Replace with POST /api/search when available — this mapping can be deleted.


def _build_search_params(
    query: str,
    datasources: list[str] | None,
    filters: list[dict[str, Any]] | None,
    page_size: int,
) -> dict[str, Any]:
    """Map new search parameters to the current tools/call API format.

    ``ToolsCallParameter.value`` accepts only strings, so complex values
    are JSON-encoded before being sent to the stub-tool API.
    """
    from glean.api_client import models

    params: dict[str, models.ToolsCallParameter] = {
        "query": models.ToolsCallParameter(name="query", value=query),
    }

    if datasources is not None:
        params["datasources"] = models.ToolsCallParameter(
            name="datasources", value=json.dumps(datasources)
        )

    if filters is not None:
        params["filters"] = models.ToolsCallParameter(name="filters", value=json.dumps(filters))

    if page_size != 10:
        params["pageSize"] = models.ToolsCallParameter(name="pageSize", value=str(page_size))

    return params


@tool_spec(
    name="search",
    description=(
        "Finds relevant documents in the company.\n"
        "INSTRUCTIONS:\n"
        "- This is your primary tool to access all knowledge within the company.\n"
        "- The results returned are not exhaustive; we only return the top few most relevant "
        "documents to a query.\n"
        '- For analytics questions such as "how many documents..." use the "statistics" '
        "field in the output."
    ),
)
def search(
    query: Annotated[
        str,
        Field(
            description=(
                "Search query string. Supports inline operators "
                "(e.g. 'from:jane type:document app:confluence')."
            ),
        ),
    ],
    datasources: Annotated[
        list[str] | None,
        Field(
            default=None,
            description=(
                "Restrict results to specific datasources "
                "(e.g. ['confluence', 'jira', 'zendesk', 'salesforce', 'slack', 'gmail']). "
                "Omit to search all sources."
            ),
        ),
    ] = None,
    filters: Annotated[
        list[dict[str, Any]] | None,
        Field(
            default=None,
            description=(
                "Structured filters. Each filter: {field: str, values: list[str], exclude?: bool}. "
                "Multiple values in a filter are OR'd. Multiple filters are AND'd. "
                "Supports built-in fields (type, owner, from, author, channel, status) "
                "and custom datasource properties."
            ),
        ),
    ] = None,
    page_size: Annotated[
        int,
        Field(
            default=10,
            description="Number of results to return (1-100).",
        ),
    ] = 10,
) -> dict[str, Any]:
    """Search Glean for relevant documents.

    Args:
        query: Search query with optional inline operators.
        datasources: Restrict to specific datasources.
        filters: Structured field filters (AND'd together, values OR'd within).
        page_size: Number of results to return (1-100, default 10).
    """
    parameters = _build_search_params(query, datasources, filters, page_size)
    return run_tool("Glean Search", parameters)
