"""Outlook Search stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="outlook_search",
    description="Search Outlook mail messages accessible to the agent.",
)
def outlook_search(query: str, max_results: int | None = 20) -> dict[str, Any]:
    """Stub implementation."""
    raise NotImplementedError("Outlook Search tool backend not yet integrated.")
