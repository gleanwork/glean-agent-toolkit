"""Calendar Search tool for searching calendar events."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool


@tool_spec(
    name="calendar_search",
    description="Searches over all the calendar meetings of the company.",
)
def calendar_search(query: str) -> dict[str, Any]:
    """Search the calendar for meetings.
    
    Args:
        query: Calendar search query in JSON format with fields like participants, topic, after, before
    """
    parameters = convert_to_tool_params(query=query)
    return run_tool("Meeting Lookup", parameters)
