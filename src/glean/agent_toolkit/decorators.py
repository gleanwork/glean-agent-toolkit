"""Decorators for creating tool specifications."""

import functools
import inspect
from collections.abc import Callable
from typing import Annotated, Any, Protocol, TypedDict, TypeVar, cast, get_args, get_origin

from pydantic import BaseModel, Field, TypeAdapter, create_model
from pydantic.fields import FieldInfo

from glean.agent_toolkit.registry import get_registry
from glean.agent_toolkit.spec import ToolSpec


class InputSchema(TypedDict):
    """JSON Schema for tool input."""

    type: str
    properties: dict[str, Any]
    required: list[str]


def _extract_field_info(param_type: Any) -> tuple[Any, FieldInfo | None]:
    """Extract base type and Field metadata from a type annotation.

    Args:
        param_type: The parameter type annotation

    Returns:
        Tuple of (base_type, field_info) where field_info is None if no Field metadata
    """
    # Try get_origin first
    if get_origin(param_type) is Annotated:
        args = get_args(param_type)
        base_type = args[0]

        field_info = None
        for metadata in args[1:]:
            if isinstance(metadata, FieldInfo):
                field_info = metadata
                break

        return base_type, field_info

    # Handle case where annotation got converted to string but contains Annotated info
    param_str = str(param_type)
    if "Annotated[" in param_str and "Field(" in param_str:
        try:
            # Try to evaluate the string as a type annotation
            # This is a fallback for cases where type annotations got stringified
            import ast
            import typing

            # Simple string parsing fallback - use original type if parsing fails
            return param_type, None
        except Exception:
            # If parsing fails, return the original annotation
            return param_type, None

    return param_type, None


def _create_pydantic_input_schema(signature: inspect.Signature) -> dict[str, Any]:
    """Create a JSON schema using Pydantic's TypeAdapter for all parameters.
    
    Args:
        signature: Function signature to analyze
        
    Returns:
        JSON schema dictionary
    """
    fields = {}

    for param_name, param in signature.parameters.items():
        if param.annotation == inspect.Parameter.empty:
            # No annotation, default to Any with string type
            fields[param_name] = (str, ...)
        else:
            # Extract type and field info
            param_type, field_info = _extract_field_info(param.annotation)

            if param.default is param.empty:
                # Required parameter
                if field_info:
                    fields[param_name] = (param_type, field_info)
                else:
                    fields[param_name] = (param_type, ...)
            else:
                # Optional parameter with default
                if field_info:
                    fields[param_name] = (param_type, field_info)
                else:
                    fields[param_name] = (param_type, param.default)

    if not fields:
        # No parameters - return empty object schema
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    # Create a dynamic Pydantic model for all parameters
    try:
        DynamicModel = create_model('DynamicInputModel', **fields)
        schema = DynamicModel.model_json_schema()

        # Ensure it has the required structure
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema:
            schema["properties"] = {}
        if "required" not in schema:
            schema["required"] = []

        return schema
    except Exception:
        # Fallback to manual schema if Pydantic model creation fails
        properties = {}
        required = []

        for param_name, param in signature.parameters.items():
            if param.default is param.empty:
                required.append(param_name)

            # Use TypeAdapter for individual parameter types
            try:
                param_type, _ = _extract_field_info(param.annotation)
                adapter = TypeAdapter(param_type)
                param_schema = adapter.json_schema()
                properties[param_name] = param_schema
            except Exception:
                # Fallback to string type
                properties[param_name] = {"type": "string"}

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }


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

        # Use Pydantic's schema generation instead of manual creation
        input_schema_dict = _create_pydantic_input_schema(sig)
        input_schema = cast(InputSchema, input_schema_dict)

        # Generate output schema using Pydantic when possible
        output_schema: dict[str, Any] = {"type": "object"}
        out_type = sig.return_annotation

        if out_type != inspect.Signature.empty:
            try:
                if hasattr(out_type, "model_json_schema"):
                    # Pydantic model
                    output_schema = out_type.model_json_schema()
                else:
                    # Use TypeAdapter for other types
                    adapter = TypeAdapter(out_type)
                    output_schema = adapter.json_schema()
            except Exception:
                # Fallback for complex types
                if out_type is int:
                    output_schema = {"type": "integer"}
                elif out_type is float:
                    output_schema = {"type": "number"}
                elif out_type is bool:
                    output_schema = {"type": "boolean"}
                elif out_type is str:
                    output_schema = {"type": "string"}
                elif str(out_type).startswith("list") or str(out_type).startswith("List"):
                    output_schema = {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                else:
                    output_schema = {"type": "object"}

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

        wrapper.tool_spec = tool_spec_obj  # type: ignore
        wrapper.as_openai_tool = as_openai_tool  # type: ignore
        wrapper.as_adk_tool = as_adk_tool  # type: ignore
        wrapper.as_langchain_tool = as_langchain_tool  # type: ignore
        wrapper.as_crewai_tool = as_crewai_tool  # type: ignore

        return cast(ToolSpecFunction, wrapper)

    return decorator
