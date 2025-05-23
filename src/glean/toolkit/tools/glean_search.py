"""Glean Search tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="glean_search",
    description="Search Glean for relevant documents given a natural-language query.",
)
def glean_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search Glean for relevant documents using the query."""
    return run_tool("Glean Search", parameters)
