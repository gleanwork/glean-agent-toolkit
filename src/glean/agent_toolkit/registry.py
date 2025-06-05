"""Tool registry for managing and retrieving tool specifications."""

from glean.agent_toolkit.spec import ToolSpec


class Registry:
    """Registry for tool specifications."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool_spec: ToolSpec) -> None:
        """Register a tool specification.

        Args:
            tool_spec: The tool specification to register
        """
        self._tools[tool_spec.name] = tool_spec

    def get(self, name: str) -> ToolSpec | None:
        """Get a tool specification by name.

        Args:
            name: The name of the tool

        Returns:
            The tool specification, or None if not found
        """
        return self._tools.get(name)

    def list(self) -> list[ToolSpec]:
        """List all registered tool specifications.

        Returns:
            List of all registered tool specifications
        """
        return list(self._tools.values())


_REGISTRY = Registry()


def get_registry() -> Registry:
    """Get the global registry instance.

    Returns:
        The global registry instance
    """
    return _REGISTRY
