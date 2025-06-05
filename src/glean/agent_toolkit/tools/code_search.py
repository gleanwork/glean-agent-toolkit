"""Code Search tool for searching code repositories."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import run_tool
from glean.api_client import models


@tool_spec(
    name="code_search",
    description=(
        "Searches over all code changes made in the company.\n"
        "INSTRUCTIONS:\n"
        "- Use this tool to help users find information in or about code, add new code, etc. "
        "Prefer including code snippets in your response.\n"
        "- This is your primary tool to access knowledge present in the company's code "
        "repositories.\n"
        "- The results returned are not exhaustive; we only return the top few most relevant "
        "results to a query."
    ),
)
def code_search(
    parameters: dict[str, models.ToolsCallParameter],
) -> dict[str, Any]:
    """Search code repositories based on the query."""
    return run_tool("Code Search", parameters)
