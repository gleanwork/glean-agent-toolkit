"""Outlook Search tool for searching email messages."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import run_tool
from glean.api_client import models


@tool_spec(
    name="outlook_search",
    description=(
        "Finds relevant emails in the user's mailbox.\n"
        "- Only use this tool if the user asks for email.\n"
        "- Results returned are not exhaustive; we can only return the top 10 emails sorted by "
        "recency (most recent first)."
    ),
)
def outlook_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search Outlook messages based on the query."""
    return run_tool("Outlook Search", parameters)
