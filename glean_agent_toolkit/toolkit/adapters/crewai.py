"""Adapter for CrewAI tools."""

from typing import Any

try:
    import crewai
except ImportError:
    crewai = None  # type: ignore


class CrewAIAdapter:
    """Adapter for CrewAI tools."""

    def __init__(self, tool_spec: Any) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        if crewai is None:
            raise ImportError(
                "CrewAI package is required for CrewAI adapter. "
                "Install it with `pip install agent_toolkit[crewai]`. "
                "Note: CrewAI requires Python 3.10 or higher."
            )
        self.tool_spec = tool_spec

    def to_tool(self) -> Any:
        """Convert to CrewAI tool format.

        CrewAI expects tools to be simple callable functions.

        Returns:
            The original function
        """
        return self.tool_spec.function
