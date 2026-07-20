"""Private transport seam for the built-in tools.

Every built-in tool declares *which* backend executes it (the assistant-UI
``tools/call`` endpoint or a typed Client API endpoint) by registering a
backend instance in the module-level registry. Execution, ``ToolResult``
wrapping, error classification, and result-size capping all live here, so
swapping a tool's backend is a one-line declaration change rather than a
plumbing edit in the tool module.

This module is private; the public contract (tool signatures, tool names,
and the ``ToolResult`` envelope) is unchanged.
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from typing import TYPE_CHECKING, Any, Protocol

from glean.agent_toolkit.tools._common import (
    ToolResult,
    _classify_error,
    make_error,
    make_ok,
    serialize_tool_result,
)
from glean.api_client import Glean, models

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

MAX_RESULT_CHARS_ENV = "GLEAN_TOOL_MAX_RESULT_CHARS"
"""Environment variable that overrides the serialized-result size cap."""

DEFAULT_MAX_RESULT_CHARS = 40_000
"""Default cap on the serialized size of a tools-call result payload."""

TRUNCATION_MARKER = "[truncated]"
"""Marker appended to a truncated payload so the LLM can tell it was cut."""


def _max_result_chars() -> int:
    """Return the result-size cap, honoring the env override.

    A non-integer value falls back to the default; a value of zero or less
    disables truncation entirely.
    """
    raw = os.environ.get(MAX_RESULT_CHARS_ENV)
    if raw is None:
        return DEFAULT_MAX_RESULT_CHARS
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_MAX_RESULT_CHARS


def truncate_payload(payload: Any) -> Any:
    """Cap the serialized size of *payload*.

    When the JSON serialization of *payload* exceeds the configured cap
    (:data:`DEFAULT_MAX_RESULT_CHARS`, overridable via
    :data:`MAX_RESULT_CHARS_ENV`), the payload is replaced with a small
    dict carrying the truncated serialization, an explicit
    :data:`TRUNCATION_MARKER`, and a note explaining what happened. The
    ``ToolResult`` envelope keys are never altered — the marker lives
    inside the result payload.
    """
    limit = _max_result_chars()
    if limit <= 0:
        return payload

    try:
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        serialized = str(payload)

    if len(serialized) <= limit:
        return payload

    return {
        "truncated": True,
        "max_chars": limit,
        "note": (
            f"Serialized result exceeded {limit} characters and was truncated. "
            f"Set {MAX_RESULT_CHARS_ENV} to adjust the cap."
        ),
        "content": serialized[:limit] + TRUNCATION_MARKER,
    }


class Backend(Protocol):
    """A strategy for executing one built-in tool against the Glean API."""

    def execute(self, client: Glean, arguments: Mapping[str, Any]) -> Any:
        """Run the tool with *arguments* and return the shaped payload."""
        ...  # pragma: no cover

    async def execute_async(self, client: Glean, arguments: Mapping[str, Any]) -> Any:
        """Async twin of :meth:`execute`, using the SDK's native async calls."""
        ...  # pragma: no cover


def _coerce_parameter_value(value: Any) -> str:
    """Serialize a tool argument into a ``ToolsCallParameter`` string value."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | list | dict):
        return json.dumps(value)
    return str(value)


class ToolsCallBackend:
    """Backend for tools served by the assistant-UI ``tools/call`` endpoint.

    Wraps the ``client.client.tools.run`` / ``run_async`` paths (including
    the ``run``/``execute`` method-name compatibility shim) and applies the
    generic result-size cap, since this endpoint returns UI-shaped blobs
    of unbounded size.
    """

    def __init__(self, display_name: str) -> None:
        self.display_name = display_name

    def _build_parameters(
        self, arguments: Mapping[str, Any]
    ) -> dict[str, models.ToolsCallParameter]:
        """Map *arguments* to ``ToolsCallParameter`` objects, dropping ``None``s."""
        return {
            key: models.ToolsCallParameter(name=key, value=_coerce_parameter_value(value))
            for key, value in arguments.items()
            if value is not None
        }

    def execute(self, client: Glean, arguments: Mapping[str, Any]) -> Any:
        """Map *arguments* to ``ToolsCallParameter`` objects and execute."""
        return self.call_raw(client, self._build_parameters(arguments))

    async def execute_async(self, client: Glean, arguments: Mapping[str, Any]) -> Any:
        """Async twin of :meth:`execute` using the SDK's native ``run_async``."""
        return await self.call_raw_async(client, self._build_parameters(arguments))

    def call_raw(self, client: Glean, parameters: dict[str, models.ToolsCallParameter]) -> Any:
        """Execute with pre-built ``ToolsCallParameter`` objects."""
        from glean.agent_toolkit.tools._compat import resolve_method

        run_fn = resolve_method(client.client.tools, "run", "execute")
        result = run_fn(name=self.display_name, parameters=parameters)
        return truncate_payload(serialize_tool_result(result))

    async def call_raw_async(
        self, client: Glean, parameters: dict[str, models.ToolsCallParameter]
    ) -> Any:
        """Async twin of :meth:`call_raw` using the SDK's native async call."""
        from glean.agent_toolkit.tools._compat import resolve_method

        run_fn = resolve_method(client.client.tools, "run_async", "execute_async")
        result = await run_fn(name=self.display_name, parameters=parameters)
        return truncate_payload(serialize_tool_result(result))


class TypedBackend:
    """Backend for tools served by a typed Client API endpoint.

    Args:
        fn: Callable invoked as ``fn(client, **arguments)``; performs the
            typed SDK call and returns the raw SDK response.
        shaper: Optional callable that shapes the raw response into an
            LLM-friendly payload. When ``None``, the response is
            serialized as-is via ``serialize_tool_result``.
        async_fn: Optional native async twin of *fn*, awaited as
            ``await async_fn(client, **arguments)``. When ``None``,
            :meth:`execute_async` falls back to running *fn* in a
            worker thread via ``asyncio.to_thread``.
    """

    def __init__(
        self,
        fn: Callable[..., Any],
        shaper: Callable[[Any], Any] | None = None,
        async_fn: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self.fn = fn
        self.shaper = shaper
        self.async_fn = async_fn

    def _shape(self, response: Any) -> Any:
        """Shape the raw SDK response into the tool's payload."""
        if self.shaper is not None:
            return self.shaper(response)
        return serialize_tool_result(response)

    def execute(self, client: Glean, arguments: Mapping[str, Any]) -> Any:
        """Perform the typed call and shape the response."""
        return self._shape(self.fn(client, **arguments))

    async def execute_async(self, client: Glean, arguments: Mapping[str, Any]) -> Any:
        """Perform the typed call natively async, or via a worker thread.

        Uses ``async_fn`` when provided; otherwise degrades to
        ``asyncio.to_thread(fn, ...)`` so the sync SDK call never blocks
        the event loop.
        """
        if self.async_fn is not None:
            response = await self.async_fn(client, **arguments)
        else:
            response = await asyncio.to_thread(functools.partial(self.fn, client, **arguments))
        return self._shape(response)


_BACKENDS: dict[str, Backend] = {}


def register_backend(tool_name: str, backend: Backend) -> Backend:
    """Register (or replace) the backend for *tool_name* and return it."""
    _BACKENDS[tool_name] = backend
    return backend


def get_backend(tool_name: str) -> Backend | None:
    """Return the backend registered for *tool_name*, if any."""
    return _BACKENDS.get(tool_name)


def execute_tool(
    tool_name: str,
    arguments: Mapping[str, Any],
    *,
    client: Glean | None = None,
) -> ToolResult:
    """Execute the registered backend for *tool_name* and wrap the outcome.

    This is the single execution seam for all built-in tools: client
    resolution, backend dispatch, ``ToolResult`` wrapping, and error
    classification happen here.

    Args:
        tool_name: The registered tool name (e.g. ``"glean_search"``).
        arguments: The tool's high-level arguments.
        client: Optional pre-configured Glean client. When ``None``, a
            default client is created via ``GleanContext``.

    Returns:
        Structured ``ToolResult`` with status, result/error, and
        classification.
    """
    backend = _BACKENDS.get(tool_name)
    if backend is None:
        return make_error(
            f"No backend registered for tool '{tool_name}'",
            error_type="validation",
            suggested_action="rephrase_query",
        )

    try:
        if client is None:
            from glean.agent_toolkit.context import GleanContext

            client = GleanContext().get_client()

        return make_ok(backend.execute(client, arguments))
    except Exception as e:
        error_type, suggested_action = _classify_error(e)
        return make_error(str(e), error_type, suggested_action)


async def execute_tool_async(
    tool_name: str,
    arguments: Mapping[str, Any],
    *,
    client: Glean | None = None,
) -> ToolResult:
    """Async twin of :func:`execute_tool`.

    Dispatches to the backend's :meth:`Backend.execute_async` (native SDK
    async calls) and applies the same ``ToolResult`` wrapping, error
    classification, and result truncation as the sync path.

    Args:
        tool_name: The registered tool name (e.g. ``"glean_search"``).
        arguments: The tool's high-level arguments.
        client: Optional pre-configured Glean client. When ``None``, a
            default client is created via ``GleanContext``.

    Returns:
        Structured ``ToolResult`` with status, result/error, and
        classification.
    """
    backend = _BACKENDS.get(tool_name)
    if backend is None:
        return make_error(
            f"No backend registered for tool '{tool_name}'",
            error_type="validation",
            suggested_action="rephrase_query",
        )

    try:
        if client is None:
            from glean.agent_toolkit.context import GleanContext

            client = GleanContext().get_client()

        return make_ok(await backend.execute_async(client, arguments))
    except Exception as e:
        error_type, suggested_action = _classify_error(e)
        return make_error(str(e), error_type, suggested_action)


def make_async_tool(
    tool_name: str,
) -> Callable[..., Coroutine[Any, Any, ToolResult]]:
    """Build the native async twin of a seam-backed built-in tool.

    The returned coroutine function mirrors the shape of every built-in
    tool function -- an optional leading ``GleanContext`` plus the tool's
    keyword arguments -- and awaits :func:`execute_tool_async`, so tool
    modules can attach a fully native async path in one line::

        search.native_async(make_async_tool("glean_search"))

    Args:
        tool_name: The registered tool name to execute through the seam.

    Returns:
        An ``async def (ctx=None, **arguments) -> ToolResult`` function.
    """

    async def _async_tool(ctx: GleanContext | None = None, **arguments: Any) -> ToolResult:
        from glean.agent_toolkit.context import GleanContext

        ctx = ctx or GleanContext()
        return await execute_tool_async(tool_name, arguments, client=ctx.get_client())

    _async_tool.__name__ = f"{tool_name}_async"
    _async_tool.__qualname__ = f"{tool_name}_async"
    _async_tool.__doc__ = f"Native async execution of the '{tool_name}' tool."
    return _async_tool
