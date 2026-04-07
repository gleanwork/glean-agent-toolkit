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
