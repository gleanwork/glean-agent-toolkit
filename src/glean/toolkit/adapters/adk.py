"""Adapter for Google Agent Development Kit (ADK)."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from glean.toolkit.adapters.base import BaseAdapter
from glean.toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from google.adk.tools import FunctionTool as AdkFunctionTool  # pragma: no cover

HAS_ADK: bool
AdkFunctionTool: Any  # Forward declaration for type hint


class _FallbackAdkFunctionTool:
    """Fallback for google.adk.tools.FunctionTool.

    This lightweight stand-in mimics the public attributes accessed by tests
    (``name``, ``description``, ``schema`` and ``func``). It purposefully keeps
    the same runtime surface as the real ADK ``FunctionTool`` so that unit
    tests exercising the adapter behave consistently even when the dependency
    is missing.
    """

    name: str
    description: str | None
    func: Callable[..., Any]
    schema: dict[str, Any] | None

    def __init__(self, func: Callable[..., Any]) -> None:  # noqa: D401 – keep signature minimal
        self.func = func
        self.name = func.__name__
        self.description = func.__doc__
        self.schema = None  # Set later by the adapter


try:
    from google.adk.tools import FunctionTool as _ActualAdkFunctionTool  # Changed import

    AdkFunctionTool = _ActualAdkFunctionTool  # Assign to the forward-declared variable
    HAS_ADK = True
except ImportError:  # pragma: no cover
    AdkFunctionTool = _FallbackAdkFunctionTool  # type: ignore[misc,assignment]
    HAS_ADK = False


class ADKAdapter(BaseAdapter[Any]):
    """Adapter for Google ADK tools."""

    def __init__(self, tool_spec: ToolSpec) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        super().__init__(tool_spec)
        if not HAS_ADK:
            raise ImportError(
                "Google Agent Development Kit (ADK) is required for ADK adapter. "
                "Install it with `pip install agent_toolkit[adk]` or `pip install google-adk`."
            )

    def to_tool(self) -> Any:
        """Convert to Google ADK FunctionTool format.

        Returns:
            An ADK FunctionTool instance
        """
        # Ensure the wrapped function advertises the intended description so that
        # ``tool.description`` matches the ``ToolSpec`` description even when the
        # original callable lacks a docstring (common in tests).
        func = self.tool_spec.function
        if not func.__doc__:
            func.__doc__ = self.tool_spec.description

        # The real ADK ``FunctionTool`` only accepts the callable. Parameter
        # schema is inferred automatically from the signature. We still attach
        # the original JSON schema to the returned instance so downstream code
        # ‑ and our unit tests ‑ can access it in a uniform fashion.
        tool = AdkFunctionTool(func=func)

        # Attach the JSON schema for convenience/testing parity.
        setattr(tool, "schema", self.tool_spec.input_schema)

        return tool

    # _create_wrapped_function is no longer strictly needed if FunctionTool takes the original func
    # However, ADK's FunctionTool might expect a specific signature or handling of ToolContext.
    # For now, let's assume the direct function is okay. If ADK requires a specific wrapper
    # (e.g., to inject ToolContext or handle specific return types), this might need adjustment.
    # The original _create_wrapped_function just returned the function itself after wrapping.
