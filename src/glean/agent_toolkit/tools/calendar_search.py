"""Calendar Search tool for searching calendar events."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import run_tool
from glean.api_client import models


@tool_spec(
    name="calendar_search",
    description="Searches over all the calendar meetings of the company.",
)
def calendar_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search the calendar for meetings."""
    return run_tool("Meeting Lookup", parameters)
