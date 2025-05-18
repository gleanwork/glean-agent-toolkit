"""Adapter for Google Agent Development Kit (ADK)."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias

from glean.toolkit.adapters.base import BaseAdapter
from glean.toolkit.spec import ToolSpec

# Optional dependency handling
if TYPE_CHECKING:
    from google.adk.tools import FunctionTool as _RealAdkFunctionTool
else:
    _RealAdkFunctionTool = Any  # type: ignore

HAS_ADK: bool


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
    from google.adk.tools import FunctionTool as _RuntimeAdkFunctionTool

    HAS_ADK = True
except ImportError:  # pragma: no cover
    _RuntimeAdkFunctionTool = _FallbackAdkFunctionTool  # type: ignore
    HAS_ADK = False

# Single alias used for typing and at runtime
AdkFunctionTool: TypeAlias = _RealAdkFunctionTool | _FallbackAdkFunctionTool


class ADKAdapter(BaseAdapter["AdkFunctionTool"]):
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

    def to_tool(self) -> "AdkFunctionTool":
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

        # Instantiate ADK FunctionTool (real or fallback). Parameter schema is
        # inferred automatically by ADK; we still attach the original JSON
        # schema so downstream code can access it consistently.

        tool = _RuntimeAdkFunctionTool(func=func)  # type: ignore[arg-type]

        # Attach JSON schema for parity with other adapters
        setattr(tool, "schema", self.tool_spec.input_schema)

        return tool
