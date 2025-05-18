"""Glean Search stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="glean_search",
    description="Search Glean for relevant documents given a natural-language query.",
)
def glean_search(query: str, max_results: int | None = 10) -> dict[str, Any]:
    """Stub implementation for Glean Search."""
    raise NotImplementedError("Glean Search tool backend not yet integrated.")
