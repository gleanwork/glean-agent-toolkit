"""Enterprise Search tool for searching company documents and data."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool


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
    datasource: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Filter results to a specific datasource (e.g., 'confluence', "
                "'jira', 'zendesk', 'salesforce', 'slack', 'gmail'). "
                "Leave empty to search all sources."
            ),
        ),
    ] = None,
) -> dict[str, Any]:
    """Search Glean for relevant documents using the query.

    Args:
        query: Search query with optional filters - API will validate filter syntax
        datasource: Optional datasource name to restrict results to a single source
    """
    params: dict[str, Any] = {"query": query}
    if datasource is not None:
        params["datasource"] = datasource
    parameters = convert_to_tool_params(**params)
    return run_tool("Glean Search", parameters)
