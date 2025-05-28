"""Shared helpers for built-in stub tools."""

from __future__ import annotations

import os
from typing import Any

from glean.api_client import Glean, models


def api_client() -> Glean:
    """Get the Glean API client."""
    instance = os.getenv("GLEAN_INSTANCE")
    api_token = os.getenv("GLEAN_API_TOKEN")

    if not api_token or not instance:
        raise ValueError("GLEAN_API_TOKEN and GLEAN_INSTANCE environment variables are required")

    return Glean(api_token=api_token, instance=instance)


def run_tool(
    tool_display_name: str,
    parameters: dict[str, models.ToolsCallParameter],
) -> dict[str, Any]:
    """Execute a Glean stub tool and wrap the response."""
    try:
        with api_client() as g_client:
            result = g_client.client.tools.run(
                name=tool_display_name,
                parameters=parameters,
            )

            return {"result": result}
    except Exception as exc:
        return {"error": str(exc), "result": None}
