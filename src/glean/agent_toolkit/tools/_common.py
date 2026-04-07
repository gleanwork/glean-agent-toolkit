"""Shared helpers for built-in stub tools."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Literal, TypedDict

from pydantic import BaseModel

from glean.api_client import Glean, models
from glean.api_client.utils import BackoffStrategy, RetryConfig

ErrorType = Literal["auth", "validation", "api", "timeout", "not_found"]
SuggestedAction = Literal["retry", "check_credentials", "rephrase_query"]


class ToolResult(TypedDict):
    """Structured result returned by every tool invocation.

    Attributes:
        status: ``"ok"`` on success, ``"error"`` on failure.
        result: The payload on success, ``None`` on failure.
        error: Human-readable error message, ``None`` on success.
        error_type: Classification of the error, ``None`` on success.
        suggested_action: Hint for the caller/LLM, ``None`` on success.
    """

    status: Literal["ok", "error"]
    result: Any | None
    error: str | None
    error_type: ErrorType | None
    suggested_action: SuggestedAction | None


def _classify_error(exc: Exception) -> tuple[ErrorType, SuggestedAction]:
    """Classify an exception into an error type and suggested action."""
    msg = str(exc).lower()

    if isinstance(exc, TimeoutError) or "timeout" in msg or "timed out" in msg:
        return "timeout", "retry"

    if isinstance(exc, ValueError):
        return "validation", "rephrase_query"

    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
        return "auth", "check_credentials"

    if "404" in msg or "not found" in msg:
        return "not_found", "rephrase_query"

    if isinstance(exc, OSError):
        return "api", "retry"

    return "api", "retry"


def make_ok(result: Any) -> ToolResult:
    """Build a success ``ToolResult``."""
    return ToolResult(
        status="ok",
        result=result,
        error=None,
        error_type=None,
        suggested_action=None,
    )


def make_error(
    message: str,
    error_type: ErrorType = "api",
    suggested_action: SuggestedAction = "retry",
) -> ToolResult:
    """Build an error ``ToolResult``."""
    return ToolResult(
        status="error",
        result=None,
        error=message,
        error_type=error_type,
        suggested_action=suggested_action,
    )


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
    *,
    client: Glean | None = None,
) -> ToolResult:
    """Execute a Glean stub tool and wrap the response.

    Args:
        tool_display_name: Display name for the tool
        parameters: Tool parameters
        client: Optional pre-configured Glean client. When ``None``,
            a default client is created via :class:`GleanContext`.

    Returns:
        Structured ``ToolResult`` with status, result/error, and classification.
    """
    try:
        if client is None:
            from glean.agent_toolkit.context import GleanContext

            client = GleanContext().get_client()

        with client as g_client:
            from glean.agent_toolkit.tools._compat import resolve_method

            run_fn = resolve_method(g_client.client.tools, "run", "execute")
            result = run_fn(
                name=tool_display_name,
                parameters=parameters,
            )
        return make_ok(serialize_tool_result(result))
    except Exception as e:
        error_type, suggested_action = _classify_error(e)
        return make_error(str(e), error_type, suggested_action)


async def arun_tool(
    tool_display_name: str,
    parameters: dict[str, models.ToolsCallParameter],
    *,
    client: Glean | None = None,
) -> ToolResult:
    """Async version of :func:`run_tool`.

    Delegates to ``asyncio.to_thread`` because the Glean API client
    has no native async support yet.

    Args:
        tool_display_name: Display name for the tool
        parameters: Tool parameters
        client: Optional pre-configured Glean client.

    Returns:
        Structured ``ToolResult`` with status, result/error, and classification.
    """
    return await asyncio.to_thread(run_tool, tool_display_name, parameters, client=client)


def serialize_tool_result(value: Any) -> Any:
    """Normalize SDK response payloads into plain dicts.

    Calls ``model_dump(by_alias=True)`` on Pydantic models so downstream
    adapters receive plain dicts with camelCase field aliases preserved.
    Pydantic handles recursive serialization of nested models natively.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True)
    return value
