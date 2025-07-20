"""Code Search tool for searching code repositories."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool


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
def code_search(query: str) -> dict[str, Any]:
    """Search code repositories based on the query.
    
    Args:
        query: Code search query with optional filters like 'owner:person updated:past_week'
    """
    parameters = convert_to_tool_params(query=query)
    return run_tool("Code Search", parameters)
