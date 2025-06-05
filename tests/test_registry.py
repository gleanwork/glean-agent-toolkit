from glean.agent_toolkit.registry import Registry, get_registry
from glean.agent_toolkit.spec import ToolSpec


def test_registry_init() -> None:
    """Test registry initialization."""
    registry = Registry()
    assert registry._tools == {}


def test_registry_register() -> None:
    """Test registry register method."""
    registry = Registry()

    def add(a: int, b: int) -> int:
        return a + b

    tool_spec = ToolSpec(
        name="add",
        description="Add two integers",
        function=add,
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
        output_schema={"type": "integer"},
    )

    registry.register(tool_spec)
    assert registry._tools == {"add": tool_spec}


def test_registry_get() -> None:
    """Test registry get method."""
    registry = Registry()

    def add(a: int, b: int) -> int:
        return a + b

    tool_spec = ToolSpec(
        name="add",
        description="Add two integers",
        function=add,
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
        output_schema={"type": "integer"},
    )

    registry.register(tool_spec)
    assert registry.get("add") is tool_spec
    assert registry.get("non_existent") is None


def test_registry_list() -> None:
    """Test registry list method."""
    registry = Registry()

    def add(a: int, b: int) -> int:
        return a + b

    def multiply(a: int, b: int) -> int:
        return a * b

    add_spec = ToolSpec(
        name="add",
        description="Add two integers",
        function=add,
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
        output_schema={"type": "integer"},
    )

    multiply_spec = ToolSpec(
        name="multiply",
        description="Multiply two integers",
        function=multiply,
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
        output_schema={"type": "integer"},
    )

    registry.register(add_spec)
    registry.register(multiply_spec)

    tools = registry.list()
    assert len(tools) == 2
    assert add_spec in tools
    assert multiply_spec in tools


def test_get_registry() -> None:
    """Test get_registry function."""
    registry1 = get_registry()
    registry2 = get_registry()
    assert registry1 is registry2
