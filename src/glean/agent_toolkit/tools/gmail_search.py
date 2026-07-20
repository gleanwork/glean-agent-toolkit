"""Gmail Search tool for searching email messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult
from glean.agent_toolkit.tools._transport import (
    ToolsCallBackend,
    execute_tool,
    make_async_tool,
    register_backend,
)

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

register_backend("glean_gmail_search", ToolsCallBackend("Gmail Search"))


@tool_spec(
    name="glean_gmail_search",
    description=(
        "Search Gmail emails by sender, recipient, subject, date, or content. "
        "Use only when the user asks about email in a Google Workspace environment. "
        "For Outlook/Microsoft email, use glean_outlook_search instead.\n"
        "INSTRUCTIONS:\n"
        "- Returns up to 10 emails sorted by recency.\n"
        "- Supports filters: from, to, subject, has:attachment, is:unread, date ranges."
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
    return execute_tool("glean_gmail_search", {"query": query}, ctx=ctx)


gmail_search.native_async(make_async_tool("glean_gmail_search"))
