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
def test_openai_adapter_integration() -> None:
    """Test OpenAI adapter with actual dependency."""
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
        assert getattr(tool, "name", "add") == "add"
        assert "Add two integers" in getattr(tool, "description", "")
        assert hasattr(tool, "params_json_schema")
        assert hasattr(tool, "on_invoke_tool")

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
    assert getattr(tool, "name", "") == "add"
    assert "Add two integers" in getattr(tool, "description", "")

    # Test the tool can be used
    assert callable(getattr(tool, "func", lambda: None))
    assert hasattr(tool, "schema")


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
    assert getattr(tool, "name", "") == "add"
    assert "Add two integers" in getattr(tool, "description", "")
    assert callable(getattr(tool, "func", lambda: None))

    # Test args_schema was created properly
    assert tool.args_schema is not None


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
    from glean.agent_toolkit.adapters.crewai import CrewAIAdapter

    tool_spec = create_mock_tool_spec()
    adapter = CrewAIAdapter(tool_spec)

    # Test to_tool method
    tool = adapter.to_tool()
    assert getattr(tool, "name", "") == "add"
    assert hasattr(tool, "description")
    # Reference the spec via the special attribute
    assert hasattr(tool, "_tool_spec_ref")

    # Test the tool can be run if arguments match
    if hasattr(tool, "_run"):
        result = tool._run(a=3, b=5)
        assert result == 8
