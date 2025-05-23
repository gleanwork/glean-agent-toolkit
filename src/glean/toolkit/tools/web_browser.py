"""Web Browser tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="web_browser",
    description="Fetch the HTML content (and optional text extraction) of a public URL.",
)
def web_browser(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Browse web content from a URL."""
    return run_tool("Web Browser", parameters)
