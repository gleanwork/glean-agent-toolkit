"""Code Search tool for searching code repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


@tool_spec(
    name="glean_code_search",
    description=(
        "Search internal code repositories for functions, classes, files, and commits. "
        "Use this for questions about the company's codebase. "
        "Returns matching code snippets and file references.\n"
        "INSTRUCTIONS:\n"
        "- Primary tool for internal code knowledge.\n"
        "- Prefer including code snippets in your response.\n"
        "- Returns top relevant results, not exhaustive."
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
) -> ToolResult:
    """Search code repositories based on the query.

    Args:
        ctx: Optional Glean context for client injection.
        query: Code search query with optional filters - API will validate filter syntax
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    parameters = convert_to_tool_params(query=query)
    return run_tool("Code Search", parameters, client=client)
