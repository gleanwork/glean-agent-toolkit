"""Tests for the registry module."""


from toolkit.registry import Registry, get_registry
from toolkit.spec import ToolSpec


def test_registry_singleton() -> None:
    """Test that get_registry returns a singleton instance."""
    registry1 = get_registry()
    registry2 = get_registry()
    assert registry1 is registry2


def test_registry_register() -> None:
    """Test registering a tool specification."""
    registry = Registry()

    # Create a mock tool spec
    def dummy_func() -> None:
        pass

    tool_spec = ToolSpec(
        name="test_tool",
        description="Test tool",
        function=dummy_func,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )

    # Register the tool
    registry.register(tool_spec)

    # Check that it was registered
    assert registry.get("test_tool") is tool_spec


def test_registry_get_nonexistent() -> None:
    """Test getting a non-existent tool."""
    registry = Registry()
    assert registry.get("nonexistent") is None


def test_registry_list() -> None:
    """Test listing registered tools."""
    registry = Registry()

    # Create mock tool specs
    def dummy_func() -> None:
        pass

    tool1 = ToolSpec(
        name="tool1",
        description="Tool 1",
        function=dummy_func,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )

    tool2 = ToolSpec(
        name="tool2",
        description="Tool 2",
        function=dummy_func,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )

    # Register the tools
    registry.register(tool1)
    registry.register(tool2)

    # Check that list returns all registered tools
    tools = registry.list()
    assert len(tools) == 2
    assert tool1 in tools
    assert tool2 in tools
