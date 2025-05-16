"""Gmail Search stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="gmail_search",
    description="Search Gmail messages accessible to the agent.",
)
def gmail_search(query: str, max_results: int | None = 20) -> dict[str, Any]:
    """Stub implementation."""
    raise NotImplementedError("Gmail Search tool backend not yet integrated.")
