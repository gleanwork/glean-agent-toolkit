"""Employee Search tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="employee_search",
    description="Search for employees by name, team, or expertise.",
)
def employee_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search for employees based on the query."""
    return run_tool("Employee Search", parameters)
