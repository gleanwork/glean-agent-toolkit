from typing import Optional, Union

from pydantic import BaseModel

from glean.agent_toolkit.decorators import tool_spec


class ComplexModel(BaseModel):
    """Complex model for testing."""

    id: int
    name: str
    tags: list[str]
    metadata: dict[str, str]
    is_active: bool = True


class NestedModel(BaseModel):
    """Nested model for testing."""

    value: int
    complex: ComplexModel


class TestSchemaGeneration:
    """Test schema generation for various parameter types."""

    def test_optional_parameters(self) -> None:
        """Test schema generation with optional parameters."""

        @tool_spec(name="test_optional", description="Test optional params")
        def test_func(required: str, optional: Optional[str] = None) -> str:
            return f"{required}-{optional or 'default'}"

        schema = test_func.tool_spec.input_schema
        assert "required" in schema["properties"]
        assert "optional" in schema["properties"]
        assert schema["required"] == ["required"]  # Only required param should be in required list

    def test_list_parameters(self) -> None:
        """Test schema generation with list parameters."""

        @tool_spec(name="test_lists", description="Test list params")
        def test_func(items: list[str], numbers: list[int]) -> list[str]:
            return [f"{item}-{num}" for item, num in zip(items, numbers)]

        schema = test_func.tool_spec.input_schema
        # Current implementation falls back to string for complex list types
        assert schema["properties"]["items"]["type"] == "string"
        assert schema["properties"]["numbers"]["type"] == "string"

    def test_union_types(self) -> None:
        """Test schema generation with Union types."""

        @tool_spec(name="test_union", description="Test union types")
        def test_func(value: Union[str, int]) -> str:
            return str(value)

        schema = test_func.tool_spec.input_schema
        # Union types default to string in our current implementation
        assert schema["properties"]["value"]["type"] == "string"

    def test_default_values(self) -> None:
        """Test schema generation with various default values."""

        @tool_spec(name="test_defaults", description="Test default values")
        def test_func(
            text: str = "default",
            number: int = 42,
            flag: bool = False,
            items: Optional[list[str]] = None
        ) -> str:
            return f"{text}-{number}-{flag}-{len(items or [])}"

        schema = test_func.tool_spec.input_schema
        assert schema["required"] == []  # All parameters have defaults

    def test_complex_output_model(self) -> None:
        """Test schema generation with complex output model."""

        @tool_spec(
            name="test_complex_output", 
            description="Test complex output",
            output_model=ComplexModel
        )
        def test_func(name: str) -> ComplexModel:
            return ComplexModel(
                id=1,
                name=name,
                tags=["test"],
                metadata={"source": "test"}
            )

        output_schema = test_func.tool_spec.output_schema
        assert "properties" in output_schema
        assert "id" in output_schema["properties"]
        assert "name" in output_schema["properties"]
        assert "tags" in output_schema["properties"]
        assert "metadata" in output_schema["properties"]

    def test_nested_model_output(self) -> None:
        """Test schema generation with nested model output."""

        @tool_spec(
            name="test_nested_output",
            description="Test nested output",
            output_model=NestedModel
        )
        def test_func(value: int) -> NestedModel:
            return NestedModel(
                value=value,
                complex=ComplexModel(
                    id=1,
                    name="test",
                    tags=[],
                    metadata={}
                )
            )

        output_schema = test_func.tool_spec.output_schema
        assert "properties" in output_schema
        assert "value" in output_schema["properties"]
        assert "complex" in output_schema["properties"]

    def test_no_parameters(self) -> None:
        """Test schema generation for function with no parameters."""

        @tool_spec(name="test_no_params", description="Test no params")
        def test_func() -> str:
            return "no params"

        schema = test_func.tool_spec.input_schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["required"] == []

    def test_unknown_type_fallback(self) -> None:
        """Test schema generation with unknown types falls back to string."""

        class CustomType:
            pass

        @tool_spec(name="test_unknown", description="Test unknown type")
        def test_func(custom: CustomType) -> str:
            return str(custom)

        schema = test_func.tool_spec.input_schema
        # Unknown types should fall back to string
        assert schema["properties"]["custom"]["type"] == "string"

    def test_dict_parameter(self) -> None:
        """Test schema generation with dict parameters."""

        @tool_spec(name="test_dict", description="Test dict params")
        def test_func(config: dict[str, str]) -> str:
            return str(config)

        schema = test_func.tool_spec.input_schema
        # Dict types currently fall back to string in our implementation
        assert schema["properties"]["config"]["type"] == "string"

    def test_mixed_parameter_types(self) -> None:
        """Test schema generation with mixed parameter types."""

        @tool_spec(name="test_mixed", description="Test mixed types")
        def test_func(
            text: str,
            number: int,
            decimal: float,
            flag: bool,
            items: list[str],
            optional_num: Optional[int] = None
        ) -> str:
            return "mixed"

        schema = test_func.tool_spec.input_schema
        assert schema["properties"]["text"]["type"] == "string"
        assert schema["properties"]["number"]["type"] == "integer"
        assert schema["properties"]["decimal"]["type"] == "number"
        # Boolean is treated as integer due to bool being a subclass of int
        assert schema["properties"]["flag"]["type"] == "integer"
        # List types fall back to string in current implementation
        assert schema["properties"]["items"]["type"] == "string"
        # Optional types also fall back to string
        assert schema["properties"]["optional_num"]["type"] == "string"
        
        # Only required parameters should be in the required list
        required_params = set(schema["required"])
        expected_required = {"text", "number", "decimal", "flag", "items"}
        assert required_params == expected_required

    def test_version_parameter(self) -> None:
        """Test schema generation with version parameter."""

        @tool_spec(name="test_version", description="Test version", version="1.0.0")
        def test_func(param: str) -> str:
            return param

        assert test_func.tool_spec.version == "1.0.0" 