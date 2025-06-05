"""Glean Search tool for searching company documents and data."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import run_tool
from glean.api_client import models


@tool_spec(
    name="glean_search",
    description=(
        "Finds relevant documents in the company.\n"
        "INSTRUCTIONS:\n"
        "- This is your primary tool to access all knowledge within the company.\n"
        "- The results returned are not exhaustive; we only return the top few most relevant "
        "documents to a query.\n"
        '- For analytics questions such as "how many documents..." use the "statistics" '
        "field in the output."
    ),
)
def glean_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search Glean for relevant documents using the query."""
    return run_tool("Glean Search", parameters)
