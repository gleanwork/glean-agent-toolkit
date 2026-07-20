"""Shared helpers for built-in stub tools."""

from __future__ import annotations

import asyncio
import concurrent.futures
import functools
from typing import Any, Literal, TypedDict

from pydantic import BaseModel

from glean.api_client import Glean, models

_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=10)

ErrorType = Literal["auth", "validation", "api", "timeout", "not_found", "rate_limit"]
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


def _sdk_error_status_code(exc: Exception) -> int | None:
    """Return the HTTP status code carried by a Glean SDK error, if any."""
    try:
        from glean.api_client.errors import GleanBaseError
    except ImportError:  # pragma: no cover - SDK is a hard dependency
        return None

    if isinstance(exc, GleanBaseError):
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
    return None


def _classify_status_code(status_code: int) -> tuple[ErrorType, SuggestedAction]:
    """Map an HTTP status code to an error type and suggested action."""
    if status_code in (401, 403):
        return "auth", "check_credentials"
    if status_code == 404:
        return "not_found", "rephrase_query"
    if status_code == 408:
        return "timeout", "retry"
    if status_code == 429:
        return "rate_limit", "retry"
    if status_code in (400, 422):
        return "validation", "rephrase_query"
    if status_code >= 500:
        return "api", "retry"
    return "api", "retry"


def _is_timeout_exception(exc: Exception) -> bool:
    """Whether *exc* is a known timeout exception class."""
    if isinstance(exc, TimeoutError):
        return True
    try:
        import httpx
    except ImportError:  # pragma: no cover - httpx ships with the SDK
        return False
    return isinstance(exc, httpx.TimeoutException)


def _classify_error(exc: Exception) -> tuple[ErrorType, SuggestedAction]:
    """Classify an exception into an error type and suggested action.

    Glean SDK errors are classified by their HTTP status code first; the
    string heuristics below remain as a fallback for non-SDK exceptions.
    """
    status_code = _sdk_error_status_code(exc)
    if status_code is not None:
        return _classify_status_code(status_code)

    msg = str(exc).lower()

    if _is_timeout_exception(exc) or "timeout" in msg or "timed out" in msg:
        return "timeout", "retry"

    if isinstance(exc, ValueError):
        return "validation", "rephrase_query"

    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
        return "auth", "check_credentials"

    if "404" in msg or "not found" in msg:
        return "not_found", "rephrase_query"

    if "429" in msg or "rate limit" in msg or "too many requests" in msg:
        return "rate_limit", "retry"

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


def run_with_error_handling(fn: Any, *args: Any, **kwargs: Any) -> ToolResult:
    """Call *fn* and wrap the outcome in a ``ToolResult``.

    On success the return value is passed through :func:`make_ok`.
    On failure the exception is classified via :func:`_classify_error`.
    """
    try:
        result = fn(*args, **kwargs)
        return make_ok(result)
    except Exception as e:
        error_type, suggested_action = _classify_error(e)
        return make_error(str(e), error_type, suggested_action)


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
) -> ToolResult:
    """Execute a Glean stub tool and wrap the response.

    Legacy entry point retained for backward compatibility; execution is
    delegated to the transport seam's ``ToolsCallBackend`` so the
    ``tools/call`` plumbing lives in one place.

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

        from glean.agent_toolkit.tools._transport import ToolsCallBackend

        backend = ToolsCallBackend(tool_display_name)
        return make_ok(backend.call_raw(client, parameters))
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
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _EXECUTOR, functools.partial(run_tool, tool_display_name, parameters, client=client)
    )


def serialize_tool_result(value: Any) -> Any:
    """Normalize SDK response payloads into plain dicts.

    Calls ``model_dump(by_alias=True)`` on Pydantic models so downstream
    adapters receive plain dicts with camelCase field aliases preserved.
    Pydantic handles recursive serialization of nested models natively.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True)
    return value
