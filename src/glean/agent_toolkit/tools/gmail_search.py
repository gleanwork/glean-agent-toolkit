"""Gmail Search tool for searching email messages."""

from __future__ import annotations

from typing import Any, Annotated

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool


@tool_spec(
    name="gmail_search",
    description=(
        "Search Gmail for emails with advanced filtering capabilities.\n"
        "- Only use this tool if the user asks for email.\n"
        "- Results returned are not exhaustive; we can only return the top 10 emails sorted by "
        "recency (most recent first)."
    ),
)
def gmail_search(
    query: Annotated[
        str,
        Field(
            description="Gmail search query with optional filters. Supports keywords plus filters like 'from:', 'to:', 'has:', 'subject:', 'is:', 'label:', 'after:', 'before:'",
            examples=[
                "urgent emails from:boss@company.com",
                "has:attachment before:2024-01-01",
                "subject:invoice is:unread",
                "project updates to:team@company.com",
                "from:client@external.com after:2024-01-01"
            ]
        )
    ]
) -> dict[str, Any]:
    """Search Gmail messages based on the query.
    
    Args:
        query: Gmail search query with optional filters like 'from:person@domain.com has:attachment'
    """
    parameters = convert_to_tool_params(query=query)
    return run_tool("Gmail Search", parameters)
