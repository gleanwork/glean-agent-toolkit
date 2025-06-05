"""Tool specification dataclass."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass
class ToolSpec:
    """Specification for a tool.

    Attributes:
        name: The name of the tool
        description: A description of what the tool does
        function: The function that implements the tool
        input_schema: JSON schema for the input parameters
        output_schema: JSON schema for the output value
        version: Optional version string
        output_model: Optional pydantic model for the output
    """

    name: str
    description: str
    function: Callable
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    version: str | None = None
    output_model: type[BaseModel] | None = None
    _adapters: dict[str, Any] = field(default_factory=dict)

    def get_adapter(self, name: str) -> Any | None:
        """Get a cached adapter instance.

        Args:
            name: The name of the adapter

        Returns:
            The adapter instance
        """
        return self._adapters.get(name)

    def set_adapter(self, name: str, adapter: Any) -> None:
        """Set an adapter instance.

        Args:
            name: The name of the adapter
            adapter: The adapter instance
        """
        self._adapters[name] = adapter
