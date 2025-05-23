"""Meeting Lookup tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="meeting_lookup",
    description="Retrieve meeting details from calendar services.",
)
def meeting_lookup(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search calendar meetings based on the query."""
    return run_tool("Meeting Lookup", parameters)
