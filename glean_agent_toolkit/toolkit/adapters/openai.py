"""Adapter for OpenAI tools."""

import json
from collections.abc import Callable
from typing import Any, TypedDict, Union

from glean_agent_toolkit.toolkit.adapters.base import BaseAdapter
from glean_agent_toolkit.toolkit.spec import ToolSpec

# Define this at module level for consistency
HAS_OPENAI = False
openai = None  # type: ignore
FunctionTool = None  # type: ignore

try:
    import openai
    from agents.tool import FunctionTool

    HAS_OPENAI = True
except ImportError:
    pass  # Variables remain None


class OpenAIFunctionDef(TypedDict):
    """Type definition for OpenAI function definition."""

    name: str
    description: str
    parameters: dict[str, Any]


class OpenAIToolDef(TypedDict):
    """Type definition for OpenAI tool definition."""

    type: str
    function: OpenAIFunctionDef


class OpenAIAdapter(BaseAdapter[Union[dict[str, Any], "FunctionTool"]]):
    """Adapter for OpenAI tools."""

    def __init__(self, tool_spec: ToolSpec) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        super().__init__(tool_spec)
        if not HAS_OPENAI:
            raise ImportError(
                "OpenAI package is required for OpenAI adapter. "
                "Install it with `pip install agent_toolkit[openai]`."
            )

    def to_tool(self) -> Union[dict[str, Any], "FunctionTool"]:
        """Convert to OpenAI tool format.

        This method tries to use the OpenAI Agents SDK if available,
        falling back to the standard OpenAI function calling format if not.

        Returns:
            OpenAI tool specification or Agents SDK FunctionTool
        """
        if FunctionTool is not None:
            # Use OpenAI Agents SDK FunctionTool
            return self.to_agents_tool()
        else:
            # Fallback to standard OpenAI function calling
            return self.to_standard_tool()

    def to_standard_tool(self) -> OpenAIToolDef:
        """Convert to standard OpenAI function tool format.

        Returns:
            OpenAI function calling specification
        """
        return {
            "type": "function",
            "function": {
                "name": self.tool_spec.name,
                "description": self.tool_spec.description,
                "parameters": self.tool_spec.input_schema,
            },
        }

    def to_agents_tool(self) -> "FunctionTool":
        """Convert to OpenAI Agents SDK FunctionTool.

        Returns:
            An OpenAI Agents SDK FunctionTool
        """
        original_func = self.tool_spec.function

        # Create the on_invoke_tool function
        async def on_invoke_tool(ctx: Any, input_str: str) -> Any:
            """Function that invokes the tool with parameters."""
            try:
                params = json.loads(input_str) if input_str else {}
                result = original_func(**params)
                return result
            except Exception as e:
                return f"Error executing tool: {str(e)}"

        # Create the FunctionTool
        return FunctionTool(
            name=self.tool_spec.name,
            description=self.tool_spec.description,
            params_json_schema=self.tool_spec.input_schema,
            on_invoke_tool=on_invoke_tool,
            strict_json_schema=True,
        )

    def to_callable(self) -> Callable:
        """Get the callable for OpenAI function calling.

        Returns:
            The callable function
        """
        return self.tool_spec.function
