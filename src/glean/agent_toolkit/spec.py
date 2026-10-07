"""Tool specification dataclass."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass
class ToolSpec:
    """Specification for a tool.

    Note:
        ``output_schema`` and ``output_model`` are advisory metadata only.
        They describe the tool's return value for documentation, validation
        by callers, and future use, but are **not** consumed by the framework
        adapters: adapters serialize whatever the tool function returns and
        do not validate or coerce it against these fields.

    Attributes:
        name: The name of the tool
        description: A description of what the tool does
        function: The function that implements the tool
        async_function: Async twin of *function*. The decorator sets this
            automatically: an ``asyncio.to_thread`` wrapper for sync
            functions, or the function itself when it is an ``async def``.
            A truly native implementation can replace it via the decorated
            function's ``native_async`` hook.
        input_schema: JSON schema for the input parameters
        output_schema: JSON schema for the output value (advisory; see note above)
        version: Optional version string
        output_model: Optional pydantic model for the output (advisory; see note above)
        input_model: Pydantic model of the input parameters that ``input_schema``
            was generated from. Adapters hand it to frameworks that accept a
            model directly so enums, bounds, and defaults survive unchanged.
            ``None`` for specs built by hand; adapters then fall back to
            ``input_schema``.
        context_param: Name of the function parameter that receives the
            :class:`~glean.agent_toolkit.context.GleanContext`, or ``None``
            if the function takes no context. Adapters inject the context by
            this name, never positionally.
    """

    name: str
    description: str
    function: Callable
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    version: str | None = None
    output_model: type[BaseModel] | None = None
    async_function: Callable[..., Coroutine[Any, Any, Any]] | None = None
    input_model: type[BaseModel] | None = None
    context_param: str | None = None
    _adapters: dict[str, Any] = field(default_factory=dict)

    def get_adapter(self, name: str) -> Any | None:
        """Get a cached adapter instance.

        Args:
            name: The name of the adapter

        Returns:
            The adapter instance
        """
        return self._adapters.get(name)

    def set_adapter(self, name: str, adapter: Any) -> None:
        """Set an adapter instance.

        Args:
            name: The name of the adapter
            adapter: The adapter instance
        """
        self._adapters[name] = adapter
