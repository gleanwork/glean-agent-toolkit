"""Calendar Search tool."""

from __future__ import annotations

from typing import Any

from glean.api_client import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="calendar_search",
    description="Searches over all the calendar meetings of the company.",
)
def calendar_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search the calendar for meetings."""
    return run_tool("Meeting Lookup", parameters)
