"""Outlook Search tool for searching email messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


@tool_spec(
    name="glean_outlook_search",
    description=(
        "Search Outlook emails by sender, recipient, subject, date, or content. "
        "Use only when the user asks about email in a Microsoft/Outlook environment. "
        "For Gmail/Google email, use glean_gmail_search instead.\n"
        "INSTRUCTIONS:\n"
        "- Returns up to 10 emails sorted by recency.\n"
        "- Supports filters: from, to, importance, hasattachment, date ranges."
    ),
)
def outlook_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description=(
                "Outlook search query with optional filters. Supports keywords and "
                "various email search filters - the API will determine which "
                "filters are valid and available"
            ),
            examples=[
                "urgent emails from:boss@company.com",
                "hasattachment:true received>2024-01-01",
                "project updates to:team@company.com",
                "importance:high isRead:false",
                "from:client@external.com received:2024-01-15",
            ],
        ),
    ],
) -> ToolResult:
    """Search Outlook messages based on the query.

    Args:
        ctx: Optional Glean context for client injection.
        query: Outlook search query with optional filters - API will validate filter syntax
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    parameters = convert_to_tool_params(query=query)
    return run_tool("Outlook Search", parameters, client=client)
