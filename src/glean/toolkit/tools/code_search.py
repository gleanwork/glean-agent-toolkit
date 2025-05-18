"""Code Search stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="code_search",
    description="Search the company source-code index.",
)
def code_search(
    query: str,
    repo: str | None = None,
    max_results: int | None = 10,
) -> dict[str, Any]:
    """Stub implementation."""
    raise NotImplementedError("Code Search tool backend not yet integrated.")
