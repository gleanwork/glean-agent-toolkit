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

    # Basic cleanup only
    query = query.strip()

    # Remove multiple spaces
    query = re.sub(r'\s+', ' ', query)

    return query


def convert_to_tool_params(**kwargs: Any) -> dict[str, models.ToolsCallParameter]:
    """Convert direct parameters to ToolsCallParameter format.

    Args:
        **kwargs: Direct parameter values

    Returns:
        Dictionary mapping parameter names to ToolsCallParameter objects
    """
    return {key: models.ToolsCallParameter(name=key, value=value) for key, value in kwargs.items()}


def run_tool(
    tool_display_name: str,
    parameters: dict[str, models.ToolsCallParameter],
) -> dict[str, Any]:
    """Execute a Glean stub tool and wrap the response.
    
    Args:
        tool_display_name: Display name for the tool
        parameters: Tool parameters
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
