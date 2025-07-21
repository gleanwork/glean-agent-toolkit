"""Calendar Search tool for searching calendar events."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool


@tool_spec(
    name="calendar_search",
    description=(
        "Searches over all the calendar meetings of the company.\n"
        "INSTRUCTIONS:\n"
        "- Use this tool to find meetings, calendar events, and schedule information.\n"
        "- The results returned are not exhaustive; we only return the top few most relevant "
        "meetings to a query.\n"
        "- Can extract meeting transcripts if available when searching for meeting content."
    ),
)
def calendar_search(
    query: Annotated[
        str,
        Field(
            description=(
                "Calendar search query with optional filters. Supports meeting topics, "
                "participant names, and various calendar search filters - the API will determine which filters are valid"
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
) -> dict[str, Any]:
    """Search the calendar for meetings.

    Args:
        query: Calendar search query with optional filters - API will validate filter syntax
    """
    parameters = convert_to_tool_params(query=query)
    return run_tool("Meeting Lookup", parameters)
