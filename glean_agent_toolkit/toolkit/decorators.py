"""Decorators for creating tool specifications."""

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar, cast, get_type_hints

from pydantic import BaseModel, TypeAdapter

from toolkit.registry import get_registry
from toolkit.spec import ToolSpec

T = TypeVar("T", bound=Callable)


def tool_spec(
    name: str,
    description: str,
    output_model: type[BaseModel] | None = None,
    version: str | None = None,
) -> Callable[[T], T]:
    """Decorator to register a function as a tool.

    Args:
        name: The name of the tool
        description: A description of what the tool does
        output_model: Optional pydantic model for the output
        version: Optional version string

    Returns:
        A decorator function
    """

    def decorator(func: T) -> T:
        """Wrap a function with tool specification metadata.

        Args:
            func: The function to wrap

        Returns:
            The wrapped function
        """
        sig = inspect.signature(func)
        hints = get_type_hints(func)

        # Extract return type annotation
        return_type = hints.get("return")
        if output_model is not None:
            # Use provided output model
            out_type = output_model
        elif return_type is not None:
            # Use return type annotation
            out_type = return_type
        else:
            # Default to Any
            out_type = Any

        # Generate JSON schema for input parameters
        params = {}
        for param_name, param in sig.parameters.items():
            if param.annotation is not param.empty:
                params[param_name] = param.annotation

        input_schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param_name, param in sig.parameters.items():
            if param.default is param.empty:
                input_schema["required"].append(param_name)

        # Use TypeAdapter to generate schemas
        if params:
            param_model = TypeAdapter(dict[str, Any]).create_type_adapter(params)
            input_schema["properties"] = param_model.json_schema()["properties"]

        # Generate output schema
        output_adapter = TypeAdapter(out_type)
        output_schema = output_adapter.json_schema()

        # Create tool spec
        tool_spec_obj = ToolSpec(
            name=name,
            description=description,
            function=func,
            input_schema=input_schema,
            output_schema=output_schema,
            version=version,
            output_model=output_model if isinstance(output_model, type) and issubclass(output_model, BaseModel) else None,
        )

        # Register the tool
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

        # Add helper methods
        def as_openai_tool() -> dict[str, Any]:
            """Convert to OpenAI tool format.

            Returns:
                OpenAI tool specification
            """
            from toolkit.adapters.openai import OpenAIAdapter

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
            from toolkit.adapters.adk import ADKAdapter

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
            from toolkit.adapters.langchain import LangChainAdapter

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
            from toolkit.adapters.crewai import CrewAIAdapter

            adapter = tool_spec_obj.get_adapter("crewai")
            if adapter is None:
                adapter = CrewAIAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("crewai", adapter)

            return adapter.to_tool()

        # Attach helper methods to the wrapper
        wrapper.as_openai_tool = as_openai_tool  # type: ignore
        wrapper.as_adk_tool = as_adk_tool  # type: ignore
        wrapper.as_langchain_tool = as_langchain_tool  # type: ignore
        wrapper.as_crewai_tool = as_crewai_tool  # type: ignore
        wrapper.tool_spec = tool_spec_obj  # type: ignore

        return cast(T, wrapper)

    return decorator
