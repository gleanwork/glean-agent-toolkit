"""Web Browser stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="web_browser",
    description="Fetch the HTML content (and optional text extraction) of a public URL.",
)
def web_browser(url: str, extract_text: bool | None = True) -> dict[str, Any]:
    """Stub implementation for Web Browser tool."""
    raise NotImplementedError("Web Browser tool backend not yet integrated.")
