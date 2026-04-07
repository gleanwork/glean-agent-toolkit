"""Base adapter class for converting tool specifications to framework-specific formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

T = TypeVar("T")


class BaseAdapter(Generic[T], ABC):
    """Base adapter for converting ToolSpec to framework-specific formats."""

    def __init__(self, tool_spec: ToolSpec) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        self.tool_spec = tool_spec

    @abstractmethod
    def to_tool(self, ctx: GleanContext | None = None) -> T:
        """Convert to framework-specific tool format.

        Args:
            ctx: Optional GleanContext to bind into the tool function.

        Returns:
            The framework-specific representation of the tool
        """
        pass
