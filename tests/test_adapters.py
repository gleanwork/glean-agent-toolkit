"""Tests for the adapters."""

import sys
from unittest import mock

import pytest

from toolkit.spec import ToolSpec


def create_mock_tool_spec() -> ToolSpec:
    """Create a mock tool spec for testing."""
    def add(a: int, b: int) -> int:
        return a + b

    return ToolSpec(
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


def test_openai_adapter_import_error() -> None:
    """Test OpenAI adapter import error."""
    # Mock openai import error
    with mock.patch.dict(sys.modules, {"openai": None}):
        from toolkit.adapters.openai import OpenAIAdapter

        with pytest.raises(ImportError):
            OpenAIAdapter(create_mock_tool_spec())


def test_openai_adapter() -> None:
    """Test OpenAI adapter."""
    # Mock openai module
    mock_openai = mock.MagicMock()
    with mock.patch.dict(sys.modules, {"openai": mock_openai}):
        from toolkit.adapters.openai import OpenAIAdapter

        tool_spec = create_mock_tool_spec()
        adapter = OpenAIAdapter(tool_spec)

        # Test to_tool
        tool = adapter.to_tool()
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "add"
        assert tool["function"]["description"] == "Add two integers"
        assert "parameters" in tool["function"]


def test_adk_adapter_import_error() -> None:
    """Test ADK adapter import error."""
    # Mock genai import error
    with mock.patch.dict(sys.modules, {"google.generativeai": None}):
        from toolkit.adapters.adk import ADKAdapter

        with pytest.raises(ImportError):
            ADKAdapter(create_mock_tool_spec())


def test_langchain_adapter_import_error() -> None:
    """Test LangChain adapter import error."""
    # Mock langchain import error
    with mock.patch.dict(sys.modules, {"langchain": None}):
        from toolkit.adapters.langchain import LangChainAdapter

        with pytest.raises(ImportError):
            LangChainAdapter(create_mock_tool_spec())


def test_crewai_adapter_import_error() -> None:
    """Test CrewAI adapter import error."""
    # Mock crewai import error
    with mock.patch.dict(sys.modules, {"crewai": None}):
        from toolkit.adapters.crewai import CrewAIAdapter

        with pytest.raises(ImportError):
            CrewAIAdapter(create_mock_tool_spec())
