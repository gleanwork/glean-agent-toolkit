"""Gmail Search tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="gmail_search",
    description="Search Gmail messages accessible to the agent.",
)
def gmail_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search Gmail messages based on the query."""
    return run_tool("Gmail Search", parameters)
