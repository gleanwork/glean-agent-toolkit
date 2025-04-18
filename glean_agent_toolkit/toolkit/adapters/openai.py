"""Adapter for OpenAI tools."""

from typing import Any

try:
    import openai
except ImportError:
    openai = None  # type: ignore


class OpenAIAdapter:
    """Adapter for OpenAI tools."""

    def __init__(self, tool_spec: Any) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        if openai is None:
            raise ImportError(
                "OpenAI package is required for OpenAI adapter. "
                "Install it with `pip install agent_toolkit[openai]`."
            )
        self.tool_spec = tool_spec

    def to_tool(self) -> dict[str, Any]:
        """Convert to OpenAI tool format.

        Returns:
            OpenAI tool specification
        """
        return {
            "type": "function",
            "function": {
                "name": self.tool_spec.name,
                "description": self.tool_spec.description,
                "parameters": self.tool_spec.input_schema,
            },
        }

    def to_callable(self) -> Any:
        """Get the callable for OpenAI function calling.

        Returns:
            The callable function
        """
        return self.tool_spec.function
