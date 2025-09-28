"""Shared helpers for built-in stub tools."""

from __future__ import annotations

import os
import re
from typing import Any

from glean.api_client import Glean, models
from glean.api_client.utils import BackoffStrategy, RetryConfig


def api_client() -> Glean:
    """Get the Glean API client."""
    instance = os.getenv("GLEAN_INSTANCE")
    api_token = os.getenv("GLEAN_API_TOKEN")

    if not api_token or not instance:
        raise ValueError("GLEAN_API_TOKEN and GLEAN_INSTANCE environment variables are required")

    return Glean(api_token=api_token, instance=instance, retry_config=_build_retry_config())


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
    multiplier = _parse_retry_env_float("GLEAN_RETRY_MULTIPLIER", 1.1)
    jitter_ms = _parse_retry_env_int("GLEAN_RETRY_JITTER_MS", 100)
    retry_on_rate_limit = os.getenv("GLEAN_RETRY_ON_RATE_LIMIT", "true").lower() != "false"

    return RetryConfig(
        strategy="backoff",
        backoff_strategy=BackoffStrategy(
            initial=initial,
            maximum=maximum,
            multiplier=multiplier,
            jitter=jitter_ms,
        ),
        retry_on_rate_limit=retry_on_rate_limit,
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
            result = g_client.client.tools.run(
                name=tool_display_name,
                parameters=parameters,
            )
        return {"result": result}
    except ValueError as e:
        return {"error": f"Parameter validation error: {str(e)}", "result": None}
    except Exception as e:
        return {"error": str(e), "result": None}
