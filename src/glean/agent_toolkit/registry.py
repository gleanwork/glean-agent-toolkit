"""Tool registry for managing and retrieving tool specifications."""

import warnings

from glean.agent_toolkit.spec import ToolSpec


class Registry:
    """Registry for tool specifications."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool_spec: ToolSpec) -> None:
        """Register a tool specification.

        Re-registering an existing name emits a :class:`RuntimeWarning`
        and overwrites the previous entry (last write wins). Overwriting
        is intentionally allowed so module reloads in tests/dev do not
        raise at import time, but the warning surfaces accidental name
        collisions between unrelated tools.

        Args:
            tool_spec: The tool specification to register
        """
        if tool_spec.name in self._tools:
            warnings.warn(
                f"Tool {tool_spec.name!r} is already registered; overwriting the "
                "previous registration. Use a unique tool name if this is not a "
                "deliberate re-registration (e.g. a module reload).",
                RuntimeWarning,
                stacklevel=2,
            )
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

    def clear(self) -> None:
        """Remove all registered tools. Primarily for test isolation."""
        self._tools.clear()


_REGISTRY = Registry()


def get_registry() -> Registry:
    """Get the global registry instance.

    Returns:
        The global registry instance
    """
    return _REGISTRY
