"""Base adapter class for converting tool specifications to framework-specific formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

T = TypeVar("T")


def get_field_type(schema: dict[str, Any], *, use_date_types: bool = False) -> type:
    """Determine the Python type from a JSON schema property.

    Args:
        schema: JSON schema property definition.
        use_date_types: When ``True``, map ``date-time`` and ``date``
            string formats to :class:`~datetime.datetime` and
            :class:`~datetime.date` respectively.
    """
    if "enum" in schema:
        return str

    schema_type = schema.get("type", "string")
    schema_format = schema.get("format", "")

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
        return list
    elif schema_type == "object":
        return dict
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
