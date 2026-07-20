"""Tests for the adapters."""

import pytest

from glean.agent_toolkit.spec import ToolSpec

# Import HAS_X flags from adapter modules for consistency
try:
    from glean.agent_toolkit.adapters.openai import HAS_OPENAI
except ImportError:
    HAS_OPENAI = False

try:
    from glean.agent_toolkit.adapters.adk import HAS_ADK
except ImportError:
    HAS_ADK = False

try:
    from glean.agent_toolkit.adapters.langchain import HAS_LANGCHAIN
except ImportError:
    HAS_LANGCHAIN = False

try:
    from glean.agent_toolkit.adapters.crewai import HAS_CREWAI
except ImportError:
    HAS_CREWAI = False


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
    """Test OpenAI adapter import error only when OpenAI is not available."""
    if HAS_OPENAI:
        pytest.skip("OpenAI is installed, cannot test import error")

    with pytest.raises(ImportError):
        from glean.agent_toolkit.adapters.openai import OpenAIAdapter

        OpenAIAdapter(create_mock_tool_spec())


@pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI not installed")
def test_openai_adapter() -> None:
    """Test OpenAI adapter with actual dependency."""
    from glean.agent_toolkit.adapters.openai import OpenAIAdapter

    tool_spec = create_mock_tool_spec()
    adapter = OpenAIAdapter(tool_spec)

    # Test to_tool method - might return dict or FunctionTool depending on what's installed
    tool = adapter.to_tool()

    # Both formats should have the 'name' attribute/key
    if isinstance(tool, dict):
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "add"
        assert tool["function"]["description"] == "Add two integers"
        assert "parameters" in tool["function"]
    else:
        # It's a FunctionTool instance
        assert getattr(tool, "name", "") == "add"
        assert "Add two integers" in getattr(tool, "description", "")


@pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI not installed")
async def test_openai_adapter_integration() -> None:
    """Test OpenAI adapter with actual dependency."""
    import json

    from glean.agent_toolkit.adapters.openai import OpenAIAdapter

    tool_spec = create_mock_tool_spec()
    adapter = OpenAIAdapter(tool_spec)

    # Test to_tool method
    tool = adapter.to_tool()

    # Check if it's using the standard OpenAI format or the Agents SDK format
    if isinstance(tool, dict):
        # Standard format
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "add"
    else:
        # Agents SDK format
        assert tool.name == "add"
        assert "Add two integers" in tool.description
        assert tool.params_json_schema["properties"].keys() == {"a", "b"}
        # Drive the tool through the Agents SDK invocation path.
        result = await tool.on_invoke_tool(None, json.dumps({"a": 3, "b": 5}))
        assert result == "8"

    # Test to_callable method
    callable_fn = adapter.to_callable()
    assert callable(callable_fn)
    assert callable_fn(3, 5) == 8


def test_adk_adapter_import_error() -> None:
    """Test ADK adapter import error only when ADK is not available."""
    if HAS_ADK:
        pytest.skip("Google ADK is installed, cannot test import error")

    with pytest.raises(ImportError):
        from glean.agent_toolkit.adapters.adk import ADKAdapter

        ADKAdapter(create_mock_tool_spec())


@pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed")
def test_adk_adapter_integration() -> None:
    """Test ADK adapter with actual dependency."""
    from glean.agent_toolkit.adapters.adk import ADKAdapter

    tool_spec = create_mock_tool_spec()
    try:
        adapter = ADKAdapter(tool_spec)
    except ImportError:
        raise

    # Test to_tool method
    tool = adapter.to_tool()
    assert tool.name == "add"
    assert "Add two integers" in (tool.description or "")

    # The wrapper must expose a real, typed signature and actually execute.
    import inspect

    assert list(inspect.signature(tool.func).parameters) == ["a", "b"]
    assert tool.func(3, 5) == 8
    assert tool.func(a=4, b=6) == 10


@pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed")
async def test_read_document_as_adk_tool() -> None:
    """Ensure read_document can be adapted for ADK function calling."""
    import inspect

    from glean.agent_toolkit.tools.read_document import read_document

    tool = read_document.as_adk_tool()

    assert tool.name == "glean_read_document"
    # The wrapper signature must mirror the input schema (ctx excluded).
    assert list(inspect.signature(tool.func).parameters) == ["document_id", "url"]

    # Calling with neither document_id nor url short-circuits before any
    # network access, exercising the real wrapper end-to-end. The adapter
    # unwraps the ToolResult envelope into the compact error contract.
    result = await tool.func()
    assert result == {
        "error": "Provide exactly one of document_id or url",
        "error_type": "validation",
        "suggested_action": "rephrase_query",
    }


def test_langchain_adapter_import_error() -> None:
    """Test LangChain adapter import error only when LangChain is not available."""
    if HAS_LANGCHAIN:
        pytest.skip("LangChain is installed, cannot test import error")

    with pytest.raises(ImportError):
        from glean.agent_toolkit.adapters.langchain import LangChainAdapter

        LangChainAdapter(create_mock_tool_spec())


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
def test_langchain_adapter_integration() -> None:
    """Test LangChain adapter with actual dependency."""
    from glean.agent_toolkit.adapters.langchain import LangChainAdapter

    tool_spec = create_mock_tool_spec()
    adapter = LangChainAdapter(tool_spec)

    # Test to_tool method
    tool = adapter.to_tool()
    assert tool.name == "add"
    assert "Add two integers" in tool.description

    # Test args_schema was created properly
    assert tool.args_schema is not None
    assert set(tool.args_schema.model_fields) == {"a", "b"}

    # Drive the tool through LangChain's own invocation path.
    assert tool.invoke({"a": 3, "b": 5}) == "8"


def test_crewai_adapter_import_error() -> None:
    """Test CrewAI adapter import error only when CrewAI is not available."""
    if HAS_CREWAI:
        pytest.skip("CrewAI is installed, cannot test import error")

    with pytest.raises(ImportError):
        from glean.agent_toolkit.adapters.crewai import CrewAIAdapter

        CrewAIAdapter(create_mock_tool_spec())


@pytest.mark.skipif(not HAS_CREWAI, reason="CrewAI not installed")
def test_crewai_adapter_integration() -> None:
    """Test CrewAI adapter with actual dependency."""
    from typing import Any

    from glean.agent_toolkit.adapters.crewai import CrewAIAdapter

    tool_spec = create_mock_tool_spec()
    adapter = CrewAIAdapter(tool_spec)

    # Test to_tool method
    tool: Any = adapter.to_tool()
    assert tool.name == "add"
    assert "Add two integers" in tool.description
    # Reference the spec via the special attribute
    assert tool._tool_spec_ref is tool_spec
    assert tool.args_schema is not None
    assert set(tool.args_schema.model_fields) == {"a", "b"}

    # Drive the tool through CrewAI's public run path — _run returns str
    assert tool.run(a=3, b=5) == "8"
