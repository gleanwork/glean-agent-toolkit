"""Adapter for Google ADK tools."""

from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore


class ADKAdapter:
    """Adapter for Google ADK tools."""

    def __init__(self, tool_spec: Any) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        if genai is None:
            raise ImportError(
                "Google Generative AI package is required for ADK adapter. "
                "Install it with `pip install agent_toolkit[adk]`."
            )
        self.tool_spec = tool_spec

    def to_tool(self) -> Any:
        """Convert to Google ADK tool format.

        Returns:
            Google ADK RestApiTool
        """
        from google.generativeai.types import RestApiTool

        return RestApiTool(
            tool_name=self.tool_spec.name,
            description=self.tool_spec.description,
            schema=self.tool_spec.input_schema,
            function=self.tool_spec.function,
        )
