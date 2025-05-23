"""Gemini Web Search tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="gemini_web_search",
    description="Query Google Gemini search for public web information.",
)
def gemini_web_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search the web using Gemini."""
    return run_tool("Gemini Web Search", parameters)
