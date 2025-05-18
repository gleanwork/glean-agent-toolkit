"""Expert Search stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="expert_search",
    description="Find internal experts on a given subject across company knowledge.",
)
def expert_search(topic: str, max_results: int | None = 5) -> dict[str, Any]:
    """Stub implementation."""
    raise NotImplementedError("Expert Search tool backend not yet integrated.")
