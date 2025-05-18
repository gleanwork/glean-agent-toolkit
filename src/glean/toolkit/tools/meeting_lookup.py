"""Meeting Lookup stub tool."""

from __future__ import annotations

from typing import Any

from glean.toolkit.decorators import tool_spec


@tool_spec(
    name="meeting_lookup",
    description="Retrieve details of upcoming or past meetings from the calendar service.",
)
def meeting_lookup(title_filter: str | None = None, date: str | None = None) -> dict[str, Any]:
    """Stub implementation."""
    raise NotImplementedError("Meeting Lookup tool backend not yet integrated.")
