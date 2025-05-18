"""Employee Search stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="employee_search",
    description="Search for employees by name, team, or expertise.",
)
def employee_search(query: str, max_results: int | None = 10) -> dict[str, Any]:
    """Stub implementation."""
    raise NotImplementedError("Employee Search tool backend not yet integrated.")
