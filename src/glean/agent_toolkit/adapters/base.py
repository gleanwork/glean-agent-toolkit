"""Base adapter class for converting tool specifications to framework-specific formats."""

from __future__ import annotations

import operator
from abc import ABC, abstractmethod
from functools import reduce
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

T = TypeVar("T")

_TOOL_RESULT_KEYS = frozenset({"status", "result", "error", "error_type", "suggested_action"})


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
