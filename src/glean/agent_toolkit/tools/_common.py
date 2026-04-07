"""Shared helpers for built-in stub tools."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel

from glean.api_client import Glean, models
from glean.api_client.utils import BackoffStrategy, RetryConfig


def api_client() -> Glean:
    """Get the Glean API client.

    .. deprecated::
        Use :class:`~glean.agent_toolkit.context.GleanContext` instead.
    """
    from glean.agent_toolkit.context import GleanContext

    return GleanContext().get_client()


def clean_query(query: str) -> str:
    """Clean up query string with basic formatting.

    Args:
        query: The search query

    Returns:
        Cleaned query string
    """
    if query is None:
        return ""

    return query.strip()


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
    *,
    client: Glean | None = None,
) -> dict[str, Any]:
    """Execute a Glean stub tool and wrap the response.

    Args:
        tool_display_name: Display name for the tool
        parameters: Tool parameters
        client: Optional pre-configured Glean client. When ``None``,
            falls back to creating one from environment variables.

    Returns:
        Tool execution result wrapped in success/error format
    """
    try:
        if client is not None:
            g_client = client
        else:
            g_client = api_client()

        if hasattr(g_client, "__enter__"):
            with g_client as gc:
                result = gc.client.tools.run(
                    name=tool_display_name,
                    parameters=parameters,
                )
        else:
            result = g_client.client.tools.run(
                name=tool_display_name,
                parameters=parameters,
            )
        return {"result": serialize_tool_result(result)}
    except ValueError as e:
        return {"error": f"Parameter validation error: {str(e)}", "result": None}
    except Exception as e:
        return {"error": str(e), "result": None}


def serialize_tool_result(value: Any) -> Any:
    """Normalize SDK response payloads into plain dicts.

    Calls ``model_dump(by_alias=True)`` on Pydantic models so downstream
    adapters receive plain dicts with camelCase field aliases preserved.
    Pydantic handles recursive serialization of nested models natively.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True)
    return value
