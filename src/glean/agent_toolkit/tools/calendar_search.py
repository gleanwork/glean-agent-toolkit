"""Calendar Search tool for searching calendar events."""

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

register_backend("glean_calendar_search", ToolsCallBackend("Meeting Lookup"))


@tool_spec(
    name="glean_calendar_search",
    description=(
        "Search company calendar meetings and events. "
        "Returns meeting details and can extract transcripts. "
        "Use this for scheduling, meeting history, or finding past discussions.\n"
        "INSTRUCTIONS:\n"
        "- Returns top relevant meetings, not exhaustive.\n"
        "- Supports filtering by participants, date ranges, and topics.\n"
        "- Can extract meeting transcripts when available."
    ),
)
def calendar_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description=(
                "Calendar search query with optional filters. Supports meeting topics, "
                "participant names, and various calendar search filters - "
                "the API will determine which filters are valid"
            ),
            examples=[
                "sprint planning meeting",
                "participants:john.doe@company.com",
                "quarterly business review after:2024-01-01",
                "one-on-one meetings participants:manager@company.com",
                "project kickoff topic:API development extract_transcript:true",
            ],
        ),
    ],
) -> ToolResult:
    """Search the calendar for meetings.

    Args:
        ctx: Optional Glean context for client injection.
        query: Calendar search query with optional filters - API will validate filter syntax
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    return execute_tool("glean_calendar_search", {"query": query}, client=client)


calendar_search.native_async(make_async_tool("glean_calendar_search"))
