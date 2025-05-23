"""Outlook Search tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="outlook_search",
    description="Search for emails in Outlook mailbox.",
)
def outlook_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search Outlook messages based on the query."""
    return run_tool("Outlook Search", parameters)
