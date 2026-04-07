"""OpenAI adapter for converting tool specifications."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias, TypedDict

from glean.agent_toolkit.adapters.base import BaseAdapter
from glean.agent_toolkit.spec import ToolSpec
from glean.agent_toolkit.tools._common import _classify_error, make_error

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

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

    def __init__(self, tool_spec: ToolSpec, ctx: GleanContext | None = None) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
            ctx: Optional GleanContext to bind into tool invocations.
        """
        super().__init__(tool_spec, ctx)
        if not HAS_OPENAI:
            raise ImportError(
                "OpenAI package is required for OpenAI adapter. "
                "Install it with `pip install glean-agent-toolkit[openai]`."
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
        async_func = self.tool_spec.async_function
        sync_func = self.tool_spec.function
        if self.ctx is not None:
            async_func = functools.partial(async_func, self.ctx) if async_func else None
            sync_func = functools.partial(sync_func, self.ctx)

        async def on_invoke_tool(ctx: Any, input_str: str) -> str:
            """Function that invokes the tool with parameters.

            The OpenAI Agents SDK expects string returns from tool invocations.
            Uses the async wrapper when available, falling back to sync.
            """
            try:
                params = json.loads(input_str) if input_str else {}
                if async_func is not None:
                    result = await async_func(**params)
                else:
                    result = sync_func(**params)
                if isinstance(result, str):
                    return result
                return json.dumps(result, default=str)
            except Exception as e:
                error_type, suggested_action = _classify_error(e)
                return json.dumps(make_error(str(e), error_type, suggested_action))

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
