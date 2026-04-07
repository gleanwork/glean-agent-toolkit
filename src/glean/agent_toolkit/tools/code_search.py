"""Code Search tool for searching code repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


@tool_spec(
    name="code_search",
    description=(
        "Searches over all code changes made in the company.\n"
        "INSTRUCTIONS:\n"
        "- Use this tool to help users find information in or about code, add new code, etc. "
        "Prefer including code snippets in your response.\n"
        "- This is your primary tool to access knowledge present in the company's code "
        "repositories.\n"
        "- The results returned are not exhaustive; we only return the top few most relevant "
        "results to a query."
    ),
)
def code_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description=(
                "Code search query with optional filters. Supports function names, "
                "class names, file paths, and various search filters - "
                "the API will determine which filters are valid"
            ),
            examples=[
                "function login validation",
                "class UserManager",
                "API endpoint security owner:backend-team",
                "database connection pool updated:past_month",
                "error handling middleware from:infrastructure",
            ],
        ),
    ],
) -> dict[str, Any]:
    """Search code repositories based on the query.

    Args:
        ctx: Glean context for client access
        query: Code search query with optional filters - API will validate filter syntax
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    parameters = convert_to_tool_params(query=query)
    client = ctx.get_client()
    return run_tool("Code Search", parameters, client=client)
