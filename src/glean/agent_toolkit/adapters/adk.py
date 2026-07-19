"""Google ADK adapter for converting tool specifications."""

from __future__ import annotations

import inspect
import types
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias, Union, get_args, get_origin

from glean.agent_toolkit.adapters.base import BaseAdapter
from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

if TYPE_CHECKING:
    from google.adk.tools.function_tool import FunctionTool as _RealAdkFunctionTool
else:
    _RealAdkFunctionTool = Any  # type: ignore

HAS_ADK: bool


class _FallbackAdkFunctionTool:
    """Fallback for google.adk.tools.FunctionTool.

    This lightweight stand-in mimics the public attributes accessed by tests
    (``name``, ``description`` and ``func``). It purposefully keeps the same
    runtime surface as the real ADK ``FunctionTool`` so that unit tests
    exercising the adapter behave consistently even when the dependency is
    missing.
    """

    name: str
    description: str | None
    func: Callable[..., Any]

    def __init__(self, func: Callable[..., Any]) -> None:  # noqa: ANN101, D401
        self.func = func
        self.name = func.__name__
        self.description = func.__doc__


try:
    from google.adk.tools.function_tool import FunctionTool as _RuntimeAdkFunctionTool

    HAS_ADK = True
except ImportError:  # pragma: no cover
    _RuntimeAdkFunctionTool = _FallbackAdkFunctionTool  # type: ignore
    HAS_ADK = False

# Single alias used for typing and at runtime
AdkFunctionTool: TypeAlias = _RealAdkFunctionTool | _FallbackAdkFunctionTool

_JSON_TYPE_TO_ANNOTATION: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def _annotation_from_json_schema(prop_schema: dict[str, Any]) -> Any:
    """Map a JSON-schema property to a Python type annotation.

    ADK derives function declarations exclusively from the wrapper's
    signature, so the JSON schema stored on the ToolSpec must be translated
    back into real Python annotations.

    Args:
        prop_schema: JSON schema for a single property.

    Returns:
        A Python type annotation suitable for a function signature.
    """
    if "anyOf" in prop_schema:
        members = [
            _annotation_from_json_schema(sub)
            for sub in prop_schema["anyOf"]
            if isinstance(sub, dict)
        ]
        if not members:
            return Any
        annotation = members[0]
        for member in members[1:]:
            annotation = annotation | member
        return annotation

    json_type = prop_schema.get("type")
    if json_type == "array":
        items = prop_schema.get("items")
        if isinstance(items, dict):
            item_annotation = _annotation_from_json_schema(items)
            if item_annotation is not Any:
                return list[item_annotation]
        return list
    if json_type == "object":
        return dict[str, Any]
    if not isinstance(json_type, str):
        return Any
    return _JSON_TYPE_TO_ANNOTATION.get(json_type, Any)


def _is_optional_annotation(annotation: Any) -> bool:
    """Return ``True`` if *annotation* already permits ``None``."""
    if annotation is Any or annotation is type(None):
        return True
    if isinstance(annotation, types.UnionType) or get_origin(annotation) is Union:
        return type(None) in get_args(annotation)
    return False


class ADKAdapter(BaseAdapter["AdkFunctionTool"]):
    """Adapter for Google ADK tools."""

    def __init__(self, tool_spec: ToolSpec, ctx: GleanContext | None = None) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
            ctx: Optional GleanContext to bind into tool invocations.
        """
        super().__init__(tool_spec, ctx)
        if not HAS_ADK:
            raise ImportError(
                "Google Agent Development Kit (ADK) is required for ADK adapter. "
                "Install it with `pip install glean-agent-toolkit[adk]` or "
                "`pip install google-adk`."
            )

    def _build_parameters(self) -> list[inspect.Parameter]:
        """Build explicit signature parameters from the tool's input schema.

        Returns:
            Ordered ``inspect.Parameter`` list (required parameters first).
        """
        schema = self.tool_spec.input_schema or {}
        properties: dict[str, Any] = schema.get("properties") or {}
        required = set(schema.get("required") or ())

        parameters: list[inspect.Parameter] = []
        for prop_name, prop_schema in properties.items():
            prop_schema = prop_schema if isinstance(prop_schema, dict) else {}
            annotation = _annotation_from_json_schema(prop_schema)
            if prop_name in required:
                default: Any = inspect.Parameter.empty
            else:
                default = prop_schema.get("default")
                if default is None and not _is_optional_annotation(annotation):
                    annotation = annotation | None
            parameters.append(
                inspect.Parameter(
                    prop_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=default,
                    annotation=annotation,
                )
            )

        # Required parameters must precede optional ones in a valid signature.
        parameters.sort(key=lambda param: param.default is not inspect.Parameter.empty)
        return parameters

    def _find_context_param_name(self) -> str | None:
        """Find the name of the underlying function's context parameter.

        The decorator excludes ``GleanContext`` parameters from the input
        schema, so any signature parameter absent from the schema properties
        is the context parameter.

        Returns:
            The context parameter name, or ``None`` if the function does not
            accept a context.
        """
        schema = self.tool_spec.input_schema or {}
        properties: dict[str, Any] = schema.get("properties") or {}
        try:
            signature = inspect.signature(self.tool_spec.function)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None
        for param_name, param in signature.parameters.items():
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            if param_name not in properties:
                return param_name
        return None

    def _build_adk_function(self) -> Callable[..., Any]:
        """Build a wrapper with a real, explicit signature for ADK.

        ADK builds function declarations from ``inspect.signature`` and
        invokes tools with keyword arguments, so the wrapper exposes the
        schema-derived parameters directly and binds the Glean context (when
        present) inside the closure.

        Returns:
            An async wrapper function (sync if no async implementation
            exists) whose signature mirrors the tool's input schema.
        """
        tool_spec = self.tool_spec
        parameters = self._build_parameters()
        signature = inspect.Signature(parameters)

        bound_kwargs: dict[str, Any] = {}
        if self.ctx is not None:
            ctx_param_name = self._find_context_param_name()
            if ctx_param_name is not None:
                bound_kwargs[ctx_param_name] = self.ctx

        async_func = tool_spec.async_function
        sync_func = tool_spec.function

        def _to_kwargs(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
            call_kwargs = dict(bound_kwargs)
            for value, parameter in zip(args, parameters, strict=False):
                call_kwargs[parameter.name] = value
            call_kwargs.update(kwargs)
            return call_kwargs

        wrapper: Callable[..., Any]
        if async_func is not None:

            async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await async_func(**_to_kwargs(args, kwargs))

            wrapper = _async_wrapper
        else:

            def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return sync_func(**_to_kwargs(args, kwargs))

            wrapper = _sync_wrapper

        wrapper.__name__ = tool_spec.name
        wrapper.__qualname__ = tool_spec.name
        wrapper.__doc__ = tool_spec.description
        wrapper.__signature__ = signature  # type: ignore[attr-defined]
        wrapper.__annotations__ = {parameter.name: parameter.annotation for parameter in parameters}
        return wrapper

    def to_tool(self) -> AdkFunctionTool:
        """Convert to Google ADK FunctionTool format.

        Builds an async wrapper whose signature is derived from the tool's
        input schema so that ADK's function declaration exposes real, typed
        parameters and ``run_async`` forwards arguments correctly.

        Returns:
            An ADK FunctionTool instance
        """
        func = self._build_adk_function()

        tool = _RuntimeAdkFunctionTool(func=func)  # type: ignore[arg-type]
        tool.name = self.tool_spec.name

        return tool
