from unittest import mock

from pydantic import BaseModel

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.registry import get_registry


class OutputModel(BaseModel):
    """Output model for testing."""

    result: int


def test_tool_spec_decorator() -> None:
    """Test tool_spec decorator."""

    @tool_spec(
        name="add",
        description="Add two integers",
    )
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    # Test function still works
    assert add(3, 4) == 7

    # Test wrapper has tool_spec attribute
    assert hasattr(add, "tool_spec")

    # Test tool spec attributes
    assert add.tool_spec.name == "add"
    assert add.tool_spec.description == "Add two integers"
    assert add.tool_spec.function.__name__ == add.__name__

    # Test input schema was generated
    assert add.tool_spec.input_schema["type"] == "object"
    assert "a" in add.tool_spec.input_schema["properties"]
    assert "b" in add.tool_spec.input_schema["properties"]
    assert add.tool_spec.input_schema["properties"]["a"]["type"] == "integer"
    assert add.tool_spec.input_schema["properties"]["b"]["type"] == "integer"

    # Test output schema was generated
    assert add.tool_spec.output_schema["type"] == "integer"

    # Test tool is registered
    registry = get_registry()
    assert registry.get("add") is add.tool_spec


def test_tool_spec_decorator_with_output_model() -> None:
    """Test tool_spec decorator with output model."""

    @tool_spec(name="add", description="Add two integers", output_model=OutputModel)
    def add(a: int, b: int) -> OutputModel:
        """Add two integers."""
        return OutputModel(result=a + b)

    # Test function still works
    result = add(3, 4)
    assert isinstance(result, OutputModel)
    assert result.result == 7

    # Test tool spec attributes
    assert add.tool_spec.output_model is OutputModel
    assert "properties" in add.tool_spec.output_schema
    assert "result" in add.tool_spec.output_schema["properties"]


def test_helper_methods() -> None:
    """Test helper methods."""

    @tool_spec(name="add", description="Add two integers")
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    # Test as_openai_tool
    with mock.patch("glean.agent_toolkit.adapters.openai.OpenAIAdapter") as mock_adapter:
        mock_adapter.return_value.to_tool.return_value = {"type": "function"}
        assert add.as_openai_tool() == {"type": "function"}

    # Test as_adk_tool
    with mock.patch("glean.agent_toolkit.adapters.adk.ADKAdapter") as mock_adapter:
        mock_adapter.return_value.to_tool.return_value = "adk_tool"
        assert add.as_adk_tool() == "adk_tool"

    # Test as_langchain_tool
    with mock.patch("glean.agent_toolkit.adapters.langchain.LangChainAdapter") as mock_adapter:
        mock_adapter.return_value.to_tool.return_value = "langchain_tool"
        assert add.as_langchain_tool() == "langchain_tool"

    # Test as_crewai_tool
    with mock.patch("glean.agent_toolkit.adapters.crewai.CrewAIAdapter") as mock_adapter:
        mock_adapter.return_value.to_tool.return_value = "crewai_tool"
        assert add.as_crewai_tool() == "crewai_tool"
