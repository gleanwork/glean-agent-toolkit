"""Decorators for creating tool specifications."""

from __future__ import annotations

import asyncio
import functools
import inspect
import types
import typing
from collections.abc import Callable, Coroutine
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, TypeAdapter, create_model
from pydantic.fields import FieldInfo

from glean.agent_toolkit.registry import get_registry
from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


def _is_context_param(param: inspect.Parameter, func: Callable | None = None) -> bool:
    """Return ``True`` if *param* is a ``GleanContext`` annotation.

    Uses :func:`typing.get_type_hints` to robustly resolve string
    annotations (e.g. from ``from __future__ import annotations``).
    Falls back to substring matching only when resolution fails.
    """
    from glean.agent_toolkit.context import GleanContext

    if param.annotation is inspect.Parameter.empty:
        return False

    # Prefer resolved type hints when a function reference is available
    if func is not None:
        try:
            hints = typing.get_type_hints(func)
            ann = hints.get(param.name)
            if ann is not None:
                if ann is GleanContext:
                    return True
                origin = get_origin(ann)
                args = get_args(ann)
                if origin is Union or isinstance(ann, types.UnionType):
                    return any(a is GleanContext for a in args)
                return False
        except Exception:
            pass  # Fall through to string/runtime matching

    ann = param.annotation

    # String annotation fallback
    if isinstance(ann, str):
        return (
            ann == "GleanContext"
            or ann.endswith(".GleanContext")
            or "GleanContext |" in ann
            or "| GleanContext" in ann
        )

    if ann is GleanContext:
        return True

    if isinstance(ann, types.UnionType):
        return any(a is GleanContext for a in ann.__args__)

    if get_origin(ann) is Union:
        return any(a is GleanContext for a in get_args(ann))

    return False


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

    return param_type, None


_SKIPPED_PARAM_KINDS = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def _resolve_annotation(func: Callable | None, param: inspect.Parameter) -> Any:
    """Resolve *param*'s annotation to a real type, keeping ``Annotated`` metadata.

    String annotations (from ``from __future__ import annotations``) are
    evaluated against the tool function's own module, so types imported
    there (enums, ``Literal``, ``Field``) resolve correctly. Each parameter
    is resolved independently: a name that only exists under
    ``TYPE_CHECKING`` (commonly ``GleanContext``) must not stop the other
    parameters from resolving. Unresolvable annotations are returned as-is.
    """
    annotation = param.annotation
    if not isinstance(annotation, str) or func is None:
        return annotation

    from glean.agent_toolkit.context import GleanContext

    target = inspect.unwrap(func)
    holder = types.SimpleNamespace(__annotations__={param.name: annotation})
    try:
        hints = typing.get_type_hints(
            holder,
            globalns=getattr(target, "__globals__", {}),
            localns={"GleanContext": GleanContext},
            include_extras=True,
        )
    except Exception:
        return annotation
    return hints.get(param.name, annotation)


def _build_input_model(
    name: str, signature: inspect.Signature, func: Callable | None = None
) -> tuple[type[BaseModel] | None, str | None]:
    """Build the pydantic model for a tool's LLM-facing parameters.

    The ``GleanContext`` parameter and ``*args``/``**kwargs`` are excluded.
    Defaults always come from the Python signature, including for
    ``Annotated[T, Field(...)] = default`` parameters.

    Args:
        name: Tool name, used to name the model.
        signature: Function signature to analyze.
        func: The original function, used for annotation resolution.

    Returns:
        ``(model, context_param)``. ``model`` is ``None`` when pydantic
        cannot build a model from the annotations; ``context_param`` is the
        name of the ``GleanContext`` parameter, if any.
    """
    fields: dict[str, Any] = {}
    context_param: str | None = None

    for param_name, param in signature.parameters.items():
        if _is_context_param(param, func):
            context_param = context_param or param_name
            continue
        if param.kind in _SKIPPED_PARAM_KINDS:
            continue
        if param.annotation is inspect.Parameter.empty:
            annotation: Any = str
        else:
            annotation = _resolve_annotation(func, param)
        default = ... if param.default is inspect.Parameter.empty else param.default
        fields[param_name] = (annotation, default)

    try:
        model = create_model("DynamicInputModel", **fields)
        # create_model defers unresolvable forward references instead of
        # raising; building the schema surfaces them here.
        model.model_json_schema()
    except Exception:
        return None, context_param
    model.__doc__ = f"Arguments for the {name!r} tool."
    return model, context_param


def _schema_from_model(model: type[BaseModel]) -> dict[str, Any]:
    """Return the JSON schema for *model*, normalized to an object schema."""
    schema = model.model_json_schema()
    # The docstring is set for the model's own sake; keep it out of the
    # LLM-facing schema to match what the decorator always emitted.
    schema.pop("description", None)
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    schema.setdefault("required", [])
    return schema


def _create_pydantic_input_schema(
    signature: inspect.Signature, func: Callable | None = None
) -> dict[str, Any]:
    """Create a JSON schema for the tool's LLM-facing parameters.

    Args:
        signature: Function signature to analyze
        func: The original function, used for robust annotation resolution.

    Returns:
        JSON schema dictionary
    """
    model, _ = _build_input_model("tool", signature, func)
    if model is not None:
        return _schema_from_model(model)
    return _fallback_input_schema(signature, func)


def _fallback_input_schema(signature: inspect.Signature, func: Callable | None) -> dict[str, Any]:
    """Best-effort per-parameter schema when no pydantic model can be built."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in signature.parameters.items():
        if _is_context_param(param, func) or param.kind in _SKIPPED_PARAM_KINDS:
            continue
        if param.default is param.empty:
            required.append(param_name)

        try:
            param_type, _ = _extract_field_info(_resolve_annotation(func, param))
            properties[param_name] = TypeAdapter(param_type).json_schema()
        except Exception:
            properties[param_name] = {"type": "string"}

    return {"type": "object", "properties": properties, "required": required}


CallableT = Callable[..., Any]


def _make_sync_bridge(
    name: str, func: Callable[..., Coroutine[Any, Any, Any]]
) -> Callable[..., Any]:
    """Build a sync entry point for an ``async def`` tool implementation.

    The bridge runs the coroutine to completion with :func:`asyncio.run`
    when no event loop is running. Inside a running loop a blocking bridge
    would deadlock or require a hidden thread, so it raises a clear
    ``RuntimeError`` directing callers to the async path instead.

    Args:
        name: Tool name, used in the error message.
        func: The coroutine function to bridge.

    Returns:
        A synchronous callable with the same signature as *func*.
    """

    @functools.wraps(func)
    def _sync_bridge(*args: Any, **kwargs: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(func(*args, **kwargs))
        raise RuntimeError(
            f"Tool '{name}' is implemented as an async function and cannot be "
            "called synchronously from inside a running event loop. "
            "Use the tool's async path (e.g. `await` its async_function or the "
            "framework's async invocation) instead."
        )

    return _sync_bridge


class ToolSpecFunction(Protocol):
    """Protocol for functions decorated with tool_spec."""

    tool_spec: ToolSpec

    def native_async(
        self, async_fn: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        """Register a native async implementation for this tool.

        Args:
            async_fn: Coroutine function mirroring the tool's signature.

        Returns:
            The registered coroutine function, unchanged.
        """
        ...

    def as_openai_tool(self, ctx: GleanContext | None = None) -> dict[str, Any] | Any:
        """Convert to OpenAI tool format.

        Args:
            ctx: Optional context bound into tool invocations. When omitted,
                configuration falls back to ``configure()`` defaults or
                environment variables.

        Returns:
            OpenAI tool specification
        """
        ...

    def as_adk_tool(self, ctx: GleanContext | None = None) -> Any:
        """Convert to Google ADK tool format.

        Args:
            ctx: Optional context bound into tool invocations. When omitted,
                configuration falls back to ``configure()`` defaults or
                environment variables.

        Returns:
            Google ADK tool
        """
        ...

    def as_langchain_tool(self, ctx: GleanContext | None = None) -> Any:
        """Convert to LangChain tool format.

        Args:
            ctx: Optional context bound into tool invocations. When omitted,
                configuration falls back to ``configure()`` defaults or
                environment variables.

        Returns:
            LangChain tool
        """
        ...

    def as_crewai_tool(self, ctx: GleanContext | None = None) -> Any:
        """Convert to CrewAI tool format.

        Args:
            ctx: Optional context bound into tool invocations. When omitted,
                configuration falls back to ``configure()`` defaults or
                environment variables.

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

        # Build the input model once; the JSON schema is derived from it and
        # adapters reuse the model itself, so nothing is lost in translation.
        input_model, context_param = _build_input_model(name, sig, func)
        if input_model is not None:
            input_schema_dict = _schema_from_model(input_model)
        else:
            input_schema_dict = _fallback_input_schema(sig, func)
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

        async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await asyncio.to_thread(functools.partial(func, *args, **kwargs))

        if inspect.iscoroutinefunction(func):
            # Native async tool: the decorated coroutine function IS the
            # async path. The sync path bridges via asyncio.run() and
            # refuses (with a clear error) to run inside an event loop.
            sync_function = _make_sync_bridge(name, func)
            async_function: Callable[..., Coroutine[Any, Any, Any]] = func
        else:
            sync_function = func
            async_function = _async_wrapper

        tool_spec_obj = ToolSpec(
            name=name,
            description=description,
            function=sync_function,
            input_schema=cast(dict[str, Any], input_schema),
            output_schema=output_schema,
            version=version,
            output_model=(
                output_model
                if isinstance(output_model, type) and issubclass(output_model, BaseModel)
                else None
            ),
            async_function=async_function,
            input_model=input_model,
            context_param=context_param,
        )

        get_registry().register(tool_spec_obj)

        wrapper: Callable[..., Any]
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def _awaitable_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Wrapper that preserves the original coroutine's semantics.

                Args:
                    *args: Positional arguments
                    **kwargs: Keyword arguments

                Returns:
                    The awaited result of the coroutine function
                """
                return await func(*args, **kwargs)

            wrapper = _awaitable_wrapper
        else:

            @functools.wraps(func)
            def _plain_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Wrapper that preserves the original function's call semantics.

                Args:
                    *args: Positional arguments
                    **kwargs: Keyword arguments

                Returns:
                    The result of the function call
                """
                return func(*args, **kwargs)

            wrapper = _plain_wrapper

        def native_async(
            async_fn: Callable[..., Coroutine[Any, Any, Any]],
        ) -> Callable[..., Coroutine[Any, Any, Any]]:
            """Register *async_fn* as the tool's native async implementation.

            Replaces the auto-generated thread-offloading wrapper with a
            truly async twin of the decorated function (same call shape).
            Usable as a plain call or as a decorator over an ``async def``.

            Args:
                async_fn: Coroutine function mirroring the tool's signature.

            Returns:
                The registered coroutine function, unchanged.
            """
            tool_spec_obj.async_function = async_fn
            return async_fn

        def as_openai_tool(ctx: GleanContext | None = None) -> dict[str, Any] | Any:
            """Convert to OpenAI tool format.

            Args:
                ctx: Optional context bound into tool invocations. When omitted,
                    configuration falls back to environment variables.

            Returns:
                OpenAI tool specification
            """
            from glean.agent_toolkit.adapters.openai import OpenAIAdapter

            if ctx is not None:
                # Never reuse a cached (ctx-less) adapter for an explicit
                # context; build a fresh adapter bound to this ctx.
                return OpenAIAdapter(tool_spec_obj, ctx).to_tool()

            adapter = tool_spec_obj.get_adapter("openai")
            if adapter is None:
                adapter = OpenAIAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("openai", adapter)

            return adapter.to_tool()

        def as_adk_tool(ctx: GleanContext | None = None) -> Any:
            """Convert to Google ADK tool format.

            Args:
                ctx: Optional context bound into tool invocations. When omitted,
                    configuration falls back to environment variables.

            Returns:
                Google ADK tool
            """
            from glean.agent_toolkit.adapters.adk import ADKAdapter

            if ctx is not None:
                return ADKAdapter(tool_spec_obj, ctx).to_tool()

            adapter = tool_spec_obj.get_adapter("adk")
            if adapter is None:
                adapter = ADKAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("adk", adapter)

            return adapter.to_tool()

        def as_langchain_tool(ctx: GleanContext | None = None) -> Any:
            """Convert to LangChain tool format.

            Args:
                ctx: Optional context bound into tool invocations. When omitted,
                    configuration falls back to environment variables.

            Returns:
                LangChain tool
            """
            from glean.agent_toolkit.adapters.langchain import LangChainAdapter

            if ctx is not None:
                return LangChainAdapter(tool_spec_obj, ctx).to_tool()

            adapter = tool_spec_obj.get_adapter("langchain")
            if adapter is None:
                adapter = LangChainAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("langchain", adapter)

            return adapter.to_tool()

        def as_crewai_tool(ctx: GleanContext | None = None) -> Any:
            """Convert to CrewAI tool format.

            Args:
                ctx: Optional context bound into tool invocations. When omitted,
                    configuration falls back to environment variables.

            Returns:
                CrewAI tool
            """
            from glean.agent_toolkit.adapters.crewai import CrewAIAdapter

            if ctx is not None:
                return CrewAIAdapter(tool_spec_obj, ctx).to_tool()

            adapter = tool_spec_obj.get_adapter("crewai")
            if adapter is None:
                adapter = CrewAIAdapter(tool_spec_obj)
                tool_spec_obj.set_adapter("crewai", adapter)

            return adapter.to_tool()

        wrapper.tool_spec = tool_spec_obj  # type: ignore
        wrapper.native_async = native_async  # type: ignore
        wrapper.as_openai_tool = as_openai_tool  # type: ignore
        wrapper.as_adk_tool = as_adk_tool  # type: ignore
        wrapper.as_langchain_tool = as_langchain_tool  # type: ignore
        wrapper.as_crewai_tool = as_crewai_tool  # type: ignore

        return cast(ToolSpecFunction, wrapper)

    return decorator
