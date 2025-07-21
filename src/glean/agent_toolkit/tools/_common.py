"""Shared helpers for built-in stub tools."""

from __future__ import annotations

import os
import re
from typing import Any

from glean.api_client import Glean, models


def api_client() -> Glean:
    """Get the Glean API client."""
    instance = os.getenv("GLEAN_INSTANCE")
    api_token = os.getenv("GLEAN_API_TOKEN")

    if not api_token or not instance:
        raise ValueError("GLEAN_API_TOKEN and GLEAN_INSTANCE environment variables are required")

    return Glean(api_token=api_token, instance=instance)


def clean_query(query: str) -> str:
    """Clean up query string with basic formatting.

    Args:
        query: The search query

    Returns:
        Cleaned query string

    Raises:
        ValueError: If query is empty
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    return query.strip()


def convert_to_tool_params(query: str) -> dict[str, Any]:
    """Convert query to tool parameters format.

    Args:
        query: The cleaned query string

    Returns:
        Dictionary of tool parameters
    """
    return {"query": clean_query(query)}


def run_tool(
    tool_display_name: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Execute a Glean stub tool and wrap the response.

    Args:
        tool_display_name: Display name for the tool
        parameters: Tool parameters

    Returns:
        Tool execution result wrapped in success/error format
    """
    try:
        # Clean query if it exists
        if "query" in parameters:
            query_param = parameters["query"]
            if hasattr(query_param, "value"):
                cleaned_query = clean_query(query_param.value)
                parameters["query"] = models.ToolsCallParameter(name="query", value=cleaned_query)

        with api_client() as g_client:
            result = g_client.client.tools.run(
                name=tool_display_name,
                parameters=parameters,
            )

            return {"result": result}
    except ValueError as ve:
        return {"error": f"Parameter validation error: {str(ve)}", "result": None}
    except Exception as exc:
        return {"error": str(exc), "result": None}
