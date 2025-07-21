"""Tests for enhanced parameter schemas with Field metadata."""

from typing import Annotated, Any

import pytest
from pydantic import Field
from pydantic.fields import FieldInfo

from glean.agent_toolkit.adapters.openai import OpenAIAdapter
from glean.agent_toolkit.decorators import (
    _extract_field_info,
    tool_spec,
)


class TestFieldInfoExtraction:
    """Test extraction of Field metadata from Annotated types."""

    def test_extract_simple_annotated_type(self):
        """Test extracting Field info from a simple Annotated type."""
        annotation = Annotated[str, Field(description="Test description")]

        base_type, field_info = _extract_field_info(annotation)

        assert base_type is str
        assert isinstance(field_info, FieldInfo)
        assert field_info.description == "Test description"

    def test_extract_annotated_with_examples(self):
        """Test extracting Field info with examples."""
        annotation = Annotated[
            str,
            Field(
                description="Query with examples", examples=["example1", "example2"]
            ),
        ]

        base_type, field_info = _extract_field_info(annotation)

        assert base_type is str
        assert field_info is not None
        assert field_info.description == "Query with examples"
        assert field_info.examples == ["example1", "example2"]

    def test_extract_non_annotated_type(self):
        """Test handling of non-Annotated types."""
        base_type, field_info = _extract_field_info(str)

        assert base_type is str
        assert field_info is None

    def test_extract_annotated_without_field(self):
        """Test Annotated type without Field metadata."""
        annotation = Annotated[str, "some other metadata"]

        base_type, field_info = _extract_field_info(annotation)

        assert base_type is str
        assert field_info is None


class TestEnhancedToolSpecs:
    """Test enhanced tool specifications end-to-end."""

    def test_enhanced_tool_schema_generation(self):
        """Test that enhanced tool generates correct schema."""
        @tool_spec(name="test_tool", description="Test tool")
        def test_function(
            query: Annotated[
                str,
                Field(
                    description="Test query parameter",
                    examples=["test example"]
                )
            ]
        ) -> dict[str, Any]:
            return {}

        tool_spec_obj = test_function.tool_spec

        # Pydantic generates more complete schemas with titles
        schema = tool_spec_obj.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        
        query_prop = schema["properties"]["query"]
        assert query_prop["type"] == "string"
        assert query_prop["description"] == "Test query parameter"
        assert query_prop["examples"] == ["test example"]
        assert "query" in schema["required"]

    def test_enhanced_tool_openai_adapter(self):
        """Test that enhanced schema works with OpenAI adapter."""
        @tool_spec(name="test_tool", description="Test tool")
        def test_function(
            query: Annotated[
                str,
                Field(
                    description="Enhanced query parameter",
                    examples=["enhanced example"]
                )
            ]
        ) -> dict[str, Any]:
            return {}

        adapter = OpenAIAdapter(test_function.tool_spec)
        openai_tool = adapter.to_standard_tool()

        query_property = openai_tool["function"]["parameters"]["properties"]["query"]

        assert query_property["type"] == "string"
        assert query_property["description"] == "Enhanced query parameter"
        assert query_property["examples"] == ["enhanced example"]

    def test_mixed_parameters(self):
        """Test tool with mix of enhanced and basic parameters."""
        @tool_spec(name="test_tool", description="Test tool")
        def test_function(
            enhanced_param: Annotated[
                str,
                Field(description="Enhanced parameter", examples=["example"])
            ],
            basic_param: str
        ) -> dict[str, Any]:
            return {}

        schema = test_function.tool_spec.input_schema

        # Enhanced parameter should have description and examples
        enhanced_prop = schema["properties"]["enhanced_param"]
        assert enhanced_prop["type"] == "string"
        assert enhanced_prop["description"] == "Enhanced parameter"
        assert enhanced_prop["examples"] == ["example"]

        # Basic parameter should only have type
        basic_prop = schema["properties"]["basic_param"]
        assert basic_prop["type"] == "string"


class TestStringBasedWorkaround:
    """Test the string-based workaround for typing edge cases."""

    def test_string_annotation_fallback(self):
        """Test fallback handling for string-like annotations."""
        # This simulates what happens when typing gets converted to string
        param_str = 'Annotated[str, Field(description="String test", examples=["str_example"])]'

        # Mock a type that has this string representation
        class MockType:
            def __str__(self):
                return param_str

        mock_type = MockType()
        base_type, field_info = _extract_field_info(mock_type)

        # Should fall back gracefully
        assert base_type is mock_type
        assert field_info is None

    def test_malformed_string_annotation(self):
        """Test handling of malformed string annotations."""
        class MockType:
            def __str__(self):
                return "Invalid[str, broken syntax"

        mock_type = MockType()
        base_type, field_info = _extract_field_info(mock_type)

        # Should fall back to original type
        assert base_type is mock_type
        assert field_info is None 