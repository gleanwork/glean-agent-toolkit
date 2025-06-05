"""Base adapter class for converting tool specifications to framework-specific formats."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from glean.agent_toolkit.spec import ToolSpec

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
    def to_tool(self) -> T:
        """Convert to framework-specific tool format.

        Returns:
            The framework-specific representation of the tool
        """
        pass
