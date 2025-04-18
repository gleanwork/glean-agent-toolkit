"""Adapter for Google Agent Development Kit (ADK)."""

from collections.abc import Callable
from typing import Any

from glean_agent_toolkit.toolkit.adapters.base import BaseAdapter
from glean_agent_toolkit.toolkit.spec import ToolSpec

# Define this at module level for consistency
HAS_ADK = False
google = None  # type: ignore
RestApiTool = None  # type: ignore

try:
    import google.adk
    from google.adk.tools import RestApiTool

    HAS_ADK = True
except ImportError:
    pass  # Variables remain None


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
        # The RestApiTool is the most similar to our tool spec format
        # It lets us define a function with a JSON schema
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

        # Copy metadata
        wrapped_func.__name__ = original_func.__name__
        wrapped_func.__doc__ = original_func.__doc__

        return wrapped_func
