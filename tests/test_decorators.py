"""Tests for the decorators module."""

from unittest import mock

from pydantic import BaseModel

from toolkit import tool_spec


def test_tool_spec_decorator() -> None:
    """Test the tool_spec decorator."""
    @tool_spec(name="add", description="Add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    # Check that the function still works
    assert add(2, 3) == 5

    # Check that helper methods were added
    assert hasattr(add, "as_openai_tool")
    assert hasattr(add, "as_adk_tool")
    assert hasattr(add, "as_langchain_tool")
    assert hasattr(add, "as_crewai_tool")

    # Check that tool_spec was attached
    assert hasattr(add, "tool_spec")
    assert add.tool_spec.name == "add"
    assert add.tool_spec.description == "Add two integers"


def test_tool_spec_with_output_model() -> None:
    """Test the tool_spec decorator with an output model."""
    class Result(BaseModel):
        sum: int
        message: str

    @tool_spec(name="add_with_model", description="Add with model", output_model=Result)
    def add_with_model(a: int, b: int) -> Result:
        return Result(sum=a + b, message=f"Sum of {a} and {b} is {a + b}")

    # Check that the function still works
    result = add_with_model(2, 3)
    assert result.sum == 5
    assert result.message == "Sum of 2 and 3 is 5"

    # Check that tool_spec was attached with correct output model
    assert add_with_model.tool_spec.output_model == Result


def test_openai_tool_conversion() -> None:
    """Test conversion to OpenAI tool format."""
    @tool_spec(name="multiply", description="Multiply two integers")
    def multiply(a: int, b: int) -> int:
        return a * b

    # Mock the OpenAIAdapter
    adapter_mock = mock.MagicMock()
    adapter_mock.to_tool.return_value = {"mocked": "tool"}

    with mock.patch("toolkit.adapters.openai.OpenAIAdapter", return_value=adapter_mock):
        # First call should create and cache the adapter
        assert multiply.as_openai_tool() == {"mocked": "tool"}

        # Second call should use cached adapter
        multiply.as_openai_tool()

        # Verify adapter was created only once
        assert multiply.tool_spec.get_adapter("openai") is adapter_mock
