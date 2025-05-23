"""Expert Search tool."""

from __future__ import annotations

from typing import Any

from glean import models
from glean.toolkit.decorators import tool_spec
from glean.toolkit.tools._common import run_tool


@tool_spec(
    name="expert_search",
    description="Find internal experts on a given subject across company knowledge.",
)
def expert_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search for internal experts on a topic."""
    return run_tool("Expert Search", parameters)
