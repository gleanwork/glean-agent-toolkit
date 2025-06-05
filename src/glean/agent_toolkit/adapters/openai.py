"""OpenAI adapter for converting tool specifications."""

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias, TypedDict, Union

from glean.agent_toolkit.adapters.base import BaseAdapter
from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from agents.tool import FunctionTool as _RealOpenAIFunctionTool
else:
    _RealOpenAIFunctionTool = Any  # type: ignore

HAS_OPENAI: bool


class _FallbackOpenAIFunctionTool:
    """Fallback for agents.tool.FunctionTool."""

    name: str
    description: str
    params_json_schema: Any
    on_invoke_tool: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        pass


try:
    import openai  # noqa: F401 # type: ignore
    from agents.tool import FunctionTool as _RuntimeFunctionTool  # type: ignore

    _RuntimeOpenAIFunctionTool = _RuntimeFunctionTool  # type: ignore
    HAS_OPENAI = True
except ImportError:  # pragma: no cover
    _RuntimeOpenAIFunctionTool = _FallbackOpenAIFunctionTool  # type: ignore
    HAS_OPENAI = False


OpenAIFunctionTool: TypeAlias = _RealOpenAIFunctionTool | _FallbackOpenAIFunctionTool


OpenAIToolType = dict[str, Any] | OpenAIFunctionTool


class OpenAIFunctionDef(TypedDict):
    """Type definition for OpenAI function definition."""

    name: str
    description: str
    parameters: dict[str, Any]


class OpenAIToolDef(TypedDict):
    """Type definition for OpenAI tool definition."""

    type: str
    function: OpenAIFunctionDef


class OpenAIAdapter(BaseAdapter[OpenAIToolType]):
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

    def to_tool(self) -> Any:
        """Convert to OpenAI tool format.

        This method tries to use the OpenAI Agents SDK if available,
        falling back to the standard OpenAI function calling format if not.

        Returns:
            OpenAI tool specification or Agents SDK FunctionTool
        """
        if HAS_OPENAI and _RuntimeOpenAIFunctionTool is not _FallbackOpenAIFunctionTool:
            return self.to_agents_tool()
        else:
            return self.to_standard_tool()

    def to_standard_tool(self) -> OpenAIToolDef:
        """Convert to standard OpenAI function tool format.

        Returns:
            OpenAI function calling specification
        """
        params_schema = (
            self.tool_spec.input_schema
            if self.tool_spec.input_schema
            else {"type": "object", "properties": {}}
        )

        return {
            "type": "function",
            "function": {
                "name": self.tool_spec.name,
                "description": self.tool_spec.description,
                "parameters": params_schema,
            },
        }

    def to_agents_tool(self) -> OpenAIFunctionTool:
        """Convert to OpenAI Agents SDK FunctionTool.

        Returns:
            An OpenAI Agents SDK FunctionTool
        """
        original_func = self.tool_spec.function

        async def on_invoke_tool(ctx: Any, input_str: str) -> Any:
            """Function that invokes the tool with parameters."""
            try:
                params = json.loads(input_str) if input_str else {}
                result = original_func(**params)
                return result
            except Exception as e:
                return f"Error executing tool: {str(e)}"

        params_json_schema_dict = (
            self.tool_spec.input_schema
            if self.tool_spec.input_schema
            else {"type": "object", "properties": {}}
        )

        return _RuntimeOpenAIFunctionTool(
            name=self.tool_spec.name,
            description=self.tool_spec.description,
            params_json_schema=params_json_schema_dict,
            on_invoke_tool=on_invoke_tool,
            strict_json_schema=True,
        )

    def to_callable(self) -> Callable:
        """Get the callable for OpenAI function calling.

        Returns:
            The callable function
        """
        return self.tool_spec.function
