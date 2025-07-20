"""Tests for enhanced parameter schemas with Field metadata."""

import pytest
from typing import Annotated, Any
from pydantic import Field
from pydantic.fields import FieldInfo

from glean.agent_toolkit.decorators import (
    _extract_field_info,
    _create_property_schema,
    tool_spec,
)
from glean.agent_toolkit.adapters.openai import OpenAIAdapter


class TestFieldInfoExtraction:
    """Test extraction of Field metadata from Annotated types."""

    def test_extract_simple_annotated_type(self):
        """Test extracting Field info from a simple Annotated type."""
        annotation = Annotated[str, Field(description="Test description")]
        
        base_type, field_info = _extract_field_info(annotation)
        
        assert base_type == str
        assert isinstance(field_info, FieldInfo)
        assert field_info.description == "Test description"

    def test_extract_annotated_with_examples(self):
        """Test extracting Field info with examples."""
        annotation = Annotated[
            str, 
            Field(
                description="Query with examples",
                examples=["example1", "example2"]
            )
        ]
        
        base_type, field_info = _extract_field_info(annotation)
        
        assert base_type == str
        assert field_info is not None
        assert field_info.description == "Query with examples"
        assert field_info.examples == ["example1", "example2"]

    def test_extract_non_annotated_type(self):
        """Test handling of non-Annotated types."""
        base_type, field_info = _extract_field_info(str)
        
        assert base_type == str
        assert field_info is None

    def test_extract_annotated_without_field(self):
        """Test Annotated type without Field metadata."""
        annotation = Annotated[str, "some other metadata"]
        
        base_type, field_info = _extract_field_info(annotation)
        
        assert base_type == str
        assert field_info is None


class TestPropertySchemaCreation:
    """Test creation of JSON schema properties from type and Field info."""

    def test_create_basic_string_schema(self):
        """Test creating schema for basic string type."""
        schema = _create_property_schema(str, None)
        
        assert schema == {"type": "string"}

    def test_create_enhanced_string_schema(self):
        """Test creating schema with Field metadata."""
        field_info = Field(
            description="Test description",
            examples=["example1", "example2"]
        )
        
        schema = _create_property_schema(str, field_info)
        
        expected = {
            "type": "string",
            "description": "Test description",
            "examples": ["example1", "example2"]
        }
        assert schema == expected

    def test_create_schema_different_types(self):
        """Test schema creation for different base types."""
        assert _create_property_schema(int, None) == {"type": "integer"}
        assert _create_property_schema(float, None) == {"type": "number"}
        assert _create_property_schema(bool, None) == {"type": "boolean"}

    def test_create_list_schema(self):
        """Test schema creation for list types."""
        schema = _create_property_schema(list[str], None)
        expected = {
            "type": "array",
            "items": {"type": "string"}
        }
        assert schema == expected


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
        
        expected_schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Test query parameter",
                    "examples": ["test example"]
                }
            },
            "required": ["query"]
        }
        
        assert tool_spec_obj.input_schema == expected_schema

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
        assert enhanced_prop["description"] == "Enhanced parameter"
        assert enhanced_prop["examples"] == ["example"]
        
        # Basic parameter should only have type
        basic_prop = schema["properties"]["basic_param"]
        assert basic_prop == {"type": "string"}


class TestStringBasedWorkaround:
    """Test the string-based workaround for typing edge cases."""

    def test_string_annotation_extraction(self):
        """Test extraction from string representation of Annotated type."""
        # This simulates what happens when typing gets converted to string
        param_str = 'Annotated[str, Field(description="String test", examples=["str_example"])]'
        
        # Mock a type that has this string representation
        class MockType:
            def __str__(self):
                return param_str
        
        mock_type = MockType()
        base_type, field_info = _extract_field_info(mock_type)
        
        # Should extract the Field info from string
        assert base_type == str
        assert field_info is not None
        assert field_info.description == "String test"
        assert field_info.examples == ["str_example"]

    def test_malformed_string_annotation(self):
        """Test handling of malformed string annotations."""
        class MockType:
            def __str__(self):
                return "Invalid[str, broken syntax"
        
        mock_type = MockType()
        base_type, field_info = _extract_field_info(mock_type)
        
        # Should fall back to original type
        assert base_type == mock_type
        assert field_info is None 