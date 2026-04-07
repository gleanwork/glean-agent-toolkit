"""Shared helpers for built-in stub tools."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel

from glean.agent_toolkit.tools._compat import check_api_client_compatibility, resolve_method
from glean.api_client import Glean, models
from glean.api_client.utils import BackoffStrategy, RetryConfig

check_api_client_compatibility()


def api_client() -> Glean:
    """Get the Glean API client."""
    api_token = os.getenv("GLEAN_API_TOKEN")
    server_url = os.getenv("GLEAN_SERVER_URL")
    # GLEAN_INSTANCE is deprecated/legacy — prefer GLEAN_SERVER_URL
    instance = os.getenv("GLEAN_INSTANCE")

    if not api_token:
        raise ValueError("GLEAN_API_TOKEN environment variable is required")

    if server_url:
        return Glean(api_token=api_token, server_url=server_url, retry_config=_build_retry_config())
    elif instance:
        return Glean(api_token=api_token, instance=instance, retry_config=_build_retry_config())
    else:
        raise ValueError("GLEAN_SERVER_URL or GLEAN_INSTANCE environment variable is required")


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


def _parse_retry_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _parse_retry_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except Exception:
        return default


def _build_retry_config() -> RetryConfig:
    initial = _parse_retry_env_float("GLEAN_RETRY_INITIAL", 1.0)
    maximum = _parse_retry_env_float("GLEAN_RETRY_MAX", 50.0)
    exponent = _parse_retry_env_float("GLEAN_RETRY_MULTIPLIER", 1.1)
    max_elapsed = _parse_retry_env_float("GLEAN_RETRY_MAX_ELAPSED", 60.0)

    initial_interval = round(initial)
    max_interval = round(maximum)
    max_elapsed_time = round(max_elapsed)

    return RetryConfig(
        strategy="backoff",
        backoff=BackoffStrategy(
            initial_interval=initial_interval,
            max_interval=max_interval,
            exponent=exponent,
            max_elapsed_time=max_elapsed_time,
        ),
        retry_connection_errors=True,
    )


def run_tool(
    tool_display_name: str,
    parameters: dict[str, models.ToolsCallParameter],
) -> dict[str, Any]:
    """Execute a Glean stub tool and wrap the response.

    Args:
        tool_display_name: Display name for the tool
        parameters: Tool parameters

    Returns:
        Tool execution result wrapped in success/error format
    """
    try:
        with api_client() as g_client:
            tools_run = resolve_method(g_client.client.tools, "run", "execute", "call")
            result = tools_run(
                name=tool_display_name,
                parameters=parameters,
            )
        return {"result": serialize_tool_result(result)}
    except AttributeError as e:
        return {"error": f"API client compatibility error: {str(e)}", "result": None}
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
