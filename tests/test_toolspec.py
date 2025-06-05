from pydantic import BaseModel

from glean.agent_toolkit.spec import ToolSpec


class SampleModel(BaseModel):
    """Sample model for ToolSpec testing."""
    
    value: str


class TestToolSpec:
    """Test ToolSpec class functionality."""

    def test_toolspec_creation(self) -> None:
        """Test basic ToolSpec creation."""
        def test_func(param: str) -> str:
            return param

        spec = ToolSpec(
            name="test",
            description="Test function",
            function=test_func,
            input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
            output_schema={"type": "string"}
        )

        assert spec.name == "test"
        assert spec.description == "Test function"
        assert spec.function == test_func
        assert spec.version is None
        assert spec.output_model is None

    def test_toolspec_with_version(self) -> None:
        """Test ToolSpec creation with version."""
        def test_func() -> str:
            return "test"

        spec = ToolSpec(
            name="test",
            description="Test function",
            function=test_func,
            input_schema={"type": "object"},
            output_schema={"type": "string"},
            version="1.2.3"
        )

        assert spec.version == "1.2.3"

    def test_toolspec_with_output_model(self) -> None:
        """Test ToolSpec creation with output model."""
        def test_func() -> SampleModel:
            return SampleModel(value="test")

        spec = ToolSpec(
            name="test",
            description="Test function",
            function=test_func,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            output_model=SampleModel
        )

        assert spec.output_model == SampleModel

    def test_toolspec_adapter_storage(self) -> None:
        """Test adapter storage and retrieval."""
        def test_func() -> str:
            return "test"

        spec = ToolSpec(
            name="test",
            description="Test function",
            function=test_func,
            input_schema={"type": "object"},
            output_schema={"type": "string"}
        )

        # Initially no adapters
        assert spec.get_adapter("openai") is None
        assert spec.get_adapter("langchain") is None

        # Set adapters
        mock_adapter1 = "mock_openai_adapter"
        mock_adapter2 = "mock_langchain_adapter"
        
        spec.set_adapter("openai", mock_adapter1)
        spec.set_adapter("langchain", mock_adapter2)

        # Retrieve adapters
        assert spec.get_adapter("openai") == mock_adapter1
        assert spec.get_adapter("langchain") == mock_adapter2

        # Non-existent adapter returns None
        assert spec.get_adapter("nonexistent") is None

    def test_toolspec_adapter_overwrite(self) -> None:
        """Test adapter overwriting."""
        def test_func() -> str:
            return "test"

        spec = ToolSpec(
            name="test",
            description="Test function",
            function=test_func,
            input_schema={"type": "object"},
            output_schema={"type": "string"}
        )

        # Set initial adapter
        spec.set_adapter("openai", "adapter1")
        assert spec.get_adapter("openai") == "adapter1"

        # Overwrite adapter
        spec.set_adapter("openai", "adapter2")
        assert spec.get_adapter("openai") == "adapter2"

    def test_toolspec_empty_schemas(self) -> None:
        """Test ToolSpec with minimal schemas."""
        def test_func() -> None:
            pass

        spec = ToolSpec(
            name="test",
            description="Test function",
            function=test_func,
            input_schema={},
            output_schema={}
        )

        assert spec.input_schema == {}
        assert spec.output_schema == {}

    def test_toolspec_complex_schemas(self) -> None:
        """Test ToolSpec with complex schemas."""
        def test_func() -> None:
            pass

        complex_input_schema = {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer", "minimum": 0},
                "param3": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["param1", "param2"]
        }

        complex_output_schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "success": {"type": "boolean"}
                    }
                }
            }
        }

        spec = ToolSpec(
            name="test",
            description="Test function",
            function=test_func,
            input_schema=complex_input_schema,
            output_schema=complex_output_schema
        )

        assert spec.input_schema == complex_input_schema
        assert spec.output_schema == complex_output_schema

    def test_toolspec_function_preservation(self) -> None:
        """Test that ToolSpec preserves function behavior."""
        def test_func(a: int, b: int) -> int:
            return a + b

        spec = ToolSpec(
            name="add",
            description="Add function",
            function=test_func,
            input_schema={"type": "object"},
            output_schema={"type": "integer"}
        )

        # Function should still work through ToolSpec
        assert spec.function(3, 5) == 8
        assert spec.function(10, -2) == 8

    def test_toolspec_name_validation(self) -> None:
        """Test ToolSpec name handling."""
        def test_func() -> str:
            return "test"

        # Test with various valid names
        valid_names = ["test", "test_function", "testFunction", "test123", "Test"]
        
        for name in valid_names:
            spec = ToolSpec(
                name=name,
                description="Test function",
                function=test_func,
                input_schema={"type": "object"},
                output_schema={"type": "string"}
            )
            assert spec.name == name

    def test_toolspec_description_handling(self) -> None:
        """Test ToolSpec description handling."""
        def test_func() -> str:
            return "test"

        descriptions = [
            "Simple description",
            "Multi-line\ndescription\nwith newlines",
            "Description with special chars: !@#$%^&*()",
            "",  # Empty description
        ]

        for desc in descriptions:
            spec = ToolSpec(
                name="test",
                description=desc,
                function=test_func,
                input_schema={"type": "object"},
                output_schema={"type": "string"}
            )
            assert spec.description == desc 