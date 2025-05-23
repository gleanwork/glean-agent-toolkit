"""Code Search tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="code_search",
    description="Search the company source-code index.",
)
def code_search(
    parameters: dict[str, models.ToolsCallParameter],
) -> dict[str, Any]:
    """Search code repositories based on the query."""
    return run_tool("Code Search", parameters)
