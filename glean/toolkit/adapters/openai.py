"""Adapter for OpenAI tools."""

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypedDict, Union

from glean.toolkit.adapters.base import BaseAdapter
from glean.toolkit.spec import ToolSpec

# ---------------------------------------------------------------------------
# Optional dependency handling
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    from agents.tool import FunctionTool as AgentsFunctionTool  # pragma: no cover

HAS_OPENAI: bool

# Initialize as a variable
FunctionTool: Any = object


class _FallbackOpenAIFunctionTool:
    """Fallback for agents.tool.FunctionTool."""

    name: str
    description: str
    params_json_schema: Any
    on_invoke_tool: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        pass  # Stub constructor


try:
    import openai  # noqa: F401 # type: ignore
    from agents.tool import FunctionTool as _ActualAgentsFunctionTool  # type: ignore

    FunctionTool = _ActualAgentsFunctionTool
    HAS_OPENAI = True
except ImportError:  # pragma: no cover
    FunctionTool = _FallbackOpenAIFunctionTool  # type: ignore[misc,assignment]
    HAS_OPENAI = False


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
        if HAS_OPENAI and FunctionTool is not _FallbackOpenAIFunctionTool:
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
