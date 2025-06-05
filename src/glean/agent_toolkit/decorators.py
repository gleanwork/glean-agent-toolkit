"""Decorators for creating tool specifications."""

import functools
import inspect
from collections.abc import Callable
from typing import Any, Protocol, TypedDict, TypeVar, cast

from pydantic import BaseModel

from glean.agent_toolkit.registry import get_registry
from glean.agent_toolkit.spec import ToolSpec


class InputSchema(TypedDict):
    """JSON Schema for tool input."""

    type: str
    properties: dict[str, Any]
    required: list[str]


CallableT = Callable[..., Any]


class ToolSpecFunction(Protocol):
    """Protocol for functions decorated with tool_spec."""

    tool_spec: ToolSpec

    def as_openai_tool(self) -> dict[str, Any] | Any:
        """Convert to OpenAI tool format.

        Returns:
            OpenAI tool specification
        """
        ...

    def as_adk_tool(self) -> Any:
        """Convert to Google ADK tool format.

        Returns:
            Google ADK tool
        """
        ...

    def as_langchain_tool(self) -> Any:
        """Convert to LangChain tool format.

        Returns:
            LangChain tool
        """
        ...

    def as_crewai_tool(self) -> Any:
        """Convert to CrewAI tool format.

        Returns:
            CrewAI tool
        """
        ...

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the function.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        ...

    __name__: str


def tool_spec(
    name: str,
    description: str,
    output_model: type[BaseModel] | None = None,
    version: str | None = None,
) -> Callable[[CallableT], ToolSpecFunction]:
    """Decorator for registering a function as a tool.

    Args:
        name: Name of the tool
        description: Description of the tool
        output_model: Optional Pydantic model for the output
        version: Optional version string

    Returns:
        Decorated function with tool spec attached
    """

    def decorator(func: CallableT) -> ToolSpecFunction:
        """Decorator function.

        Args:
            func: Function to decorate

        Returns:
            Decorated function
        """
        sig = inspect.signature(func)
        params = {}
        out_type = None

        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                params[param_name] = param.annotation

        if sig.return_annotation != inspect.Signature.empty:
            out_type = sig.return_annotation

        input_schema: InputSchema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        required_fields: list[str] = []

        for param_name, param in sig.parameters.items():
            if param.default is param.empty:
                required_fields.append(param_name)

        input_schema["required"] = required_fields

        if params:
            for param_name, param_type in params.items():
                if isinstance(param_type, type) and issubclass(param_type, str):
                    input_schema["properties"][param_name] = {"type": "string"}
                elif isinstance(param_type, type) and issubclass(param_type, int):
                    input_schema["properties"][param_name] = {"type": "integer"}
                elif isinstance(param_type, type) and issubclass(param_type, float):
                    input_schema["properties"][param_name] = {"type": "number"}
                elif isinstance(param_type, type) and issubclass(param_type, bool):
                    input_schema["properties"][param_name] = {"type": "boolean"}
                elif param_type is list or param_type is list[str]:
                    input_schema["properties"][param_name] = {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                elif param_type is list[int]:
                    input_schema["properties"][param_name] = {
                        "type": "array",
                        "items": {"type": "integer"},
                    }
                else:
                    input_schema["properties"][param_name] = {"type": "string"}

        output_schema: dict[str, Any] = {"type": "object"}
        if out_type is not None and hasattr(out_type, "model_json_schema"):
            output_schema = out_type.model_json_schema()
        elif out_type is int:
            output_schema = {"type": "integer"}
        elif out_type is float:
            output_schema = {"type": "number"}
        elif out_type is bool:
            output_schema = {"type": "boolean"}
        elif out_type is str:
            output_schema = {"type": "string"}
        elif out_type is list or out_type is list[str]:
            output_schema = {
                "type": "array",
                "items": {"type": "string"},
            }
        elif out_type is list[int]:
            output_schema = {
                "type": "array",
                "items": {"type": "integer"},
            }

        tool_spec_obj = ToolSpec(
            name=name,
            description=description,
            function=func,
            input_schema=cast(dict[str, Any], input_schema),
            output_schema=output_schema,
            version=version,
            output_model=(
                output_model
                if isinstance(output_model, type) and issubclass(output_model, BaseModel)
                else None
            ),
        )

        get_registry().register(tool_spec_obj)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper that preserves the original function's call semantics.

            Args:
                *args: Positional arguments
                **kwargs: Keyword arguments

            Returns:
                The result of the function call
            """
            return func(*args, **kwargs)

        def as_openai_tool() -> dict[str, Any] | Any:
            """Convert to OpenAI tool format.

            Returns:
                OpenAI tool specification
            """
            from glean.agent_toolkit.adapters.openai import OpenAIAdapter

            adapter = tool_spec_obj.get_adapter("openai")
            if adapter is None:
                adapter = OpenAIAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("openai", adapter)

            return adapter.to_tool()

        def as_adk_tool() -> Any:
            """Convert to Google ADK tool format.

            Returns:
                Google ADK tool
            """
            from glean.agent_toolkit.adapters.adk import ADKAdapter

            adapter = tool_spec_obj.get_adapter("adk")
            if adapter is None:
                adapter = ADKAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("adk", adapter)

            return adapter.to_tool()

        def as_langchain_tool() -> Any:
            """Convert to LangChain tool format.

            Returns:
                LangChain tool
            """
            from glean.agent_toolkit.adapters.langchain import LangChainAdapter

            adapter = tool_spec_obj.get_adapter("langchain")
            if adapter is None:
                adapter = LangChainAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("langchain", adapter)

            return adapter.to_tool()

        def as_crewai_tool() -> Any:
            """Convert to CrewAI tool format.

            Returns:
                CrewAI tool
            """
            from glean.agent_toolkit.adapters.crewai import CrewAIAdapter

            adapter = tool_spec_obj.get_adapter("crewai")
            if adapter is None:
                adapter = CrewAIAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("crewai", adapter)

            return adapter.to_tool()

        wrapper.as_openai_tool = as_openai_tool  # type: ignore
        wrapper.as_adk_tool = as_adk_tool  # type: ignore
        wrapper.as_langchain_tool = as_langchain_tool  # type: ignore
        wrapper.as_crewai_tool = as_crewai_tool  # type: ignore
        wrapper.tool_spec = tool_spec_obj  # type: ignore

        return cast(ToolSpecFunction, wrapper)

    return decorator
