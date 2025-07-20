"""Gmail Search tool for searching email messages."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool


@tool_spec(
    name="gmail_search",
    description=(
        "Finds relevant emails in the user's mailbox.\n"
        "- Only use this tool if the user asks for email.\n"
        "- Results returned are not exhaustive; we can only return the top 10 emails sorted by "
        "recency (most recent first)."
    ),
)
def gmail_search(query: str) -> dict[str, Any]:
    """Search Gmail messages based on the query.
    
    Args:
        query: Gmail search query with optional filters like 'from:person@domain.com has:attachment'
    """
    parameters = convert_to_tool_params(query=query)
    return run_tool("Gmail Search", parameters)
