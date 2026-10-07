"""Base adapter class for converting tool specifications to framework-specific formats."""

from __future__ import annotations

import inspect
import json
import operator
from abc import ABC, abstractmethod
from collections.abc import Mapping
from functools import reduce
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

T = TypeVar("T")

_TOOL_RESULT_KEYS = frozenset({"status", "result", "error", "error_type", "suggested_action"})
_COMPACT_ERROR_KEYS = frozenset({"error", "error_type", "suggested_action"})


def unwrap_tool_result(value: Any) -> Any:
    """Unwrap a ``ToolResult`` envelope into the framework-facing payload.

    Adapters deliver the raw ``result`` payload to the framework on
    success, and a compact ``{"error", "error_type", "suggested_action"}``
    dict on failure, instead of the full five-key envelope. Values that are
    not a ``ToolResult`` envelope (e.g. returns from custom ``@tool_spec``
    tools) pass through unchanged. Direct Python callers of the tool
    functions still receive the full envelope.
    """
    if (
        isinstance(value, dict)
        and set(value) == _TOOL_RESULT_KEYS
        and value.get("status") in ("ok", "error")
    ):
        if value["status"] == "ok":
            return value["result"]
        return {
            "error": value["error"],
            "error_type": value["error_type"],
            "suggested_action": value["suggested_action"],
        }
    return value


def resolve_context_param(tool_spec: ToolSpec) -> str | None:
    """Return the name of the parameter that receives the ``GleanContext``.

    Specs built by :func:`~glean.agent_toolkit.decorators.tool_spec` record
    it in ``context_param``. For specs built by hand, a parameter annotated
    as ``GleanContext`` wins; otherwise any named parameter missing from the
    input schema is treated as the context parameter.

    Returns:
        The parameter name, or ``None`` if the function takes no context.
    """
    if tool_spec.context_param is not None:
        return tool_spec.context_param
    if tool_spec.input_model is not None:
        # Built by the decorator, which found no context parameter.
        return None

    from glean.agent_toolkit.decorators import _is_context_param

    try:
        parameters = inspect.signature(tool_spec.function).parameters
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None

    named = [
        param
        for param in parameters.values()
        if param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]
    for param in named:
        if _is_context_param(param, tool_spec.function):
            return param.name
    properties = (tool_spec.input_schema or {}).get("properties") or {}
    for param in named:
        if param.name not in properties:
            return param.name
    return None


def _call_kwargs(
    tool_spec: ToolSpec, ctx: GleanContext | None, arguments: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the LLM-supplied *arguments* and bind the context by name.

    When the spec carries an input model, the supplied arguments are
    validated against it first: values are coerced to the declared types
    (models routinely send ``"3"`` for an integer) and constraints such as
    ``ge``/``le`` are enforced in every framework, including those that drop
    them from the schema. A ``ValidationError`` propagates to the caller,
    which turns it into the compact ``validation`` error payload.
    """
    call_kwargs = dict(arguments)
    model = tool_spec.input_model
    if model is not None:
        parsed = model.model_validate(call_kwargs)
        call_kwargs = {
            name: getattr(parsed, name) for name in call_kwargs if name in model.model_fields
        }
    if ctx is not None:
        context_param = resolve_context_param(tool_spec)
        if context_param is not None:
            call_kwargs[context_param] = ctx
    return call_kwargs


def error_payload(exc: Exception) -> dict[str, Any]:
    """Classify *exc* into the compact framework-facing error payload."""
    from glean.agent_toolkit.tools._common import error_result_from_exception

    return unwrap_tool_result(error_result_from_exception(exc))


def is_error_payload(payload: Any) -> bool:
    """Whether *payload* is the compact error payload produced on failure."""
    return isinstance(payload, dict) and set(payload) == _COMPACT_ERROR_KEYS


def invoke_tool(tool_spec: ToolSpec, ctx: GleanContext | None, arguments: Mapping[str, Any]) -> Any:
    """Run a tool synchronously and return the framework-facing payload.

    This is the single call path shared by every adapter: the context is
    injected by parameter name, an exception becomes the compact error
    payload (exactly as a built-in tool's error ``ToolResult`` does), and
    ``ToolResult`` envelopes are unwrapped.

    Args:
        tool_spec: The tool to run.
        ctx: Context to inject, or ``None`` to inject nothing.
        arguments: The arguments supplied by the framework.

    Returns:
        The raw result payload, or the compact error payload on failure.
    """
    try:
        result = tool_spec.function(**_call_kwargs(tool_spec, ctx, arguments))
    except Exception as exc:
        return error_payload(exc)
    return unwrap_tool_result(result)


async def ainvoke_tool(
    tool_spec: ToolSpec, ctx: GleanContext | None, arguments: Mapping[str, Any]
) -> Any:
    """Async twin of :func:`invoke_tool`, using the tool's async function.

    Falls back to the synchronous function when the spec has no async
    function.
    """
    if tool_spec.async_function is None:
        return invoke_tool(tool_spec, ctx, arguments)
    try:
        result = await tool_spec.async_function(**_call_kwargs(tool_spec, ctx, arguments))
    except Exception as exc:
        return error_payload(exc)
    return unwrap_tool_result(result)


def payload_to_text(payload: Any) -> str:
    """Serialize a payload for frameworks that expect string tool output."""
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, default=str)


def get_field_type(schema: dict[str, Any], *, use_date_types: bool = False) -> Any:
    """Determine the Python type from a JSON schema property.

    Handles scalar types, ``anyOf``/``oneOf`` unions (including the
    ``Optional`` pattern emitted by Pydantic for parameters with a ``None``
    default), typed arrays, objects, and enums. ``$ref`` schemas fall back
    to :data:`~typing.Any`.

    Args:
        schema: JSON schema property definition.
        use_date_types: When ``True``, map ``date-time`` and ``date``
            string formats to :class:`~datetime.datetime` and
            :class:`~datetime.date` respectively.

    Returns:
        The Python type (or typing construct, e.g. ``list[str] | None``)
        corresponding to the schema.
    """
    if not isinstance(schema, dict):
        return Any

    if "$ref" in schema:
        return Any

    union_members = schema.get("anyOf") or schema.get("oneOf")
    if union_members:
        has_null = False
        member_types: list[Any] = []
        for member in union_members:
            if isinstance(member, dict) and member.get("type") == "null":
                has_null = True
                continue
            member_type = get_field_type(member, use_date_types=use_date_types)
            if member_type not in member_types:
                member_types.append(member_type)

        if not member_types:
            result: Any = Any
        else:
            result = reduce(operator.or_, member_types)

        if has_null:
            return result | None
        return result

    schema_type = schema.get("type", "string")
    schema_format = schema.get("format", "")

    if "enum" in schema and schema_type == "string":
        return str

    if schema_type == "string":
        if use_date_types:
            if schema_format == "date-time":
                from datetime import datetime

                return datetime
            if schema_format == "date":
                from datetime import date

                return date
        return str
    elif schema_type == "integer":
        return int
    elif schema_type == "number":
        return float
    elif schema_type == "boolean":
        return bool
    elif schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            item_type = get_field_type(items, use_date_types=use_date_types)
            return list[item_type]  # type: ignore[valid-type]
        return list[Any]
    elif schema_type == "object":
        return dict[str, Any]
    elif schema_type == "null":
        return type(None)
    else:
        return str


class BaseAdapter(Generic[T], ABC):
    """Base adapter for converting ToolSpec to framework-specific formats."""

    def __init__(self, tool_spec: ToolSpec, ctx: GleanContext | None = None) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
            ctx: Optional GleanContext to bind into tool invocations.
        """
        self.tool_spec = tool_spec
        self.ctx = ctx

    @abstractmethod
    def to_tool(self) -> T:
        """Convert to framework-specific tool format.

        Returns:
            The framework-specific representation of the tool
        """
        pass
