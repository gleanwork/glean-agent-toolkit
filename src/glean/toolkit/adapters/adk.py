"""Adapter for Google Agent Development Kit (ADK)."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from glean.toolkit.adapters.base import BaseAdapter
from glean.toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from google.adk.tools import RestApiTool  # pragma: no cover

HAS_ADK: bool


class _FallbackAdkTool:
    """Fallback for google.adk.tools.RestApiTool."""

    name: str
    description: str
    function: Any
    schema: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        pass


try:
    from google.adk.tools import RestApiTool as _ActualAdkTool  # type: ignore

    RestApiTool = _ActualAdkTool
    HAS_ADK = True
except ImportError:  # pragma: no cover
    RestApiTool = _FallbackAdkTool  # type: ignore[misc,assignment]
    HAS_ADK = False


class ADKAdapter(BaseAdapter["RestApiTool"]):
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

    def to_tool(self) -> "RestApiTool":
        """Convert to Google ADK tool format.

        Returns:
            An ADK RestApiTool instance
        """
        return RestApiTool(
            name=self.tool_spec.name,
            description=self.tool_spec.description,
            schema=self.tool_spec.input_schema,
            function=self._create_wrapped_function(),
        )

    def _create_wrapped_function(self) -> Callable[..., Any]:
        """Create a function wrapper suitable for ADK.

        Returns:
            A wrapped function compatible with ADK
        """
        original_func = self.tool_spec.function

        def wrapped_func(**kwargs: Any) -> Any:
            """Wrapper function for ADK compatibility."""
            return original_func(**kwargs)

        wrapped_func.__name__ = original_func.__name__
        wrapped_func.__doc__ = original_func.__doc__

        return wrapped_func
