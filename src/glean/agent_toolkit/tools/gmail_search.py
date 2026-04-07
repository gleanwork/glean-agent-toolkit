"""Gmail Search tool for searching email messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


@tool_spec(
    name="gmail_search",
    description=(
        "Search Gmail for emails with advanced filtering capabilities.\n"
        "- Only use this tool if the user asks for email.\n"
        "- Results returned are not exhaustive; we can only return the top 10 emails sorted by "
        "recency (most recent first)."
    ),
)
def gmail_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description=(
                "Gmail search query with optional filters. Supports keywords and "
                "various email search filters - the API will determine which "
                "filters are valid and available"
            ),
            examples=[
                "urgent emails from:boss@company.com",
                "has:attachment before:2024-01-01",
                "subject:invoice is:unread",
                "project updates to:team@company.com",
                "from:client@external.com after:2024-01-01",
            ],
        ),
    ],
) -> ToolResult:
    """Search Gmail messages based on the query.

    Args:
        ctx: Optional Glean context for client injection.
        query: Gmail search query with optional filters - API will validate filter syntax
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    parameters = convert_to_tool_params(query=query)
    return run_tool("Gmail Search", parameters, client=client)
