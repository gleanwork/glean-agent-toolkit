"""Gemini Web Search stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="gemini_web_search",
    description="Query Google Gemini search for public web information.",
)
def gemini_web_search(query: str, max_results: int | None = 10) -> dict[str, Any]:
    """Stub implementation."""
    raise NotImplementedError("Gemini Web Search tool backend not yet integrated.")
