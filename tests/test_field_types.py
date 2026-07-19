"""Regression tests for JSON schema -> Python type mapping in get_field_type.

Pydantic emits optional parameters as ``{"anyOf": [{...}, {"type": "null"}]}``
with no top-level ``"type"`` key. Prior to the fix, get_field_type ignored
``anyOf`` entirely and degraded every optional parameter to ``str``, which
corrupted the args_schema used by the LangChain and CrewAI adapters.
"""

from __future__ import annotations

import types
import typing
from typing import Any, get_args, get_origin

from glean.agent_toolkit.adapters.base import get_field_type


def _is_union(annotation: Any) -> bool:
    """True for both ``typing.Union[...]`` and PEP 604 ``X | Y`` unions."""
    return get_origin(annotation) in (typing.Union, types.UnionType)


def _is_optional_of(annotation: Any, inner_check: Any) -> bool:
    """Return True if annotation is ``X | None`` where X satisfies inner_check.

    ``inner_check`` may be a concrete type/typing construct to compare for
    equality, or a callable predicate applied to the non-None member.
    """
    if not _is_union(annotation):
        return False
    args = [a for a in get_args(annotation) if a is not type(None)]
    if type(None) not in get_args(annotation) or len(args) != 1:
        return False
    inner = args[0]
    if callable(inner_check) and not isinstance(inner_check, type):
        return bool(inner_check(inner))
    return inner == inner_check


class TestGetFieldType:
    """Unit tests for get_field_type."""

    def test_anyof_optional_str(self) -> None:
        schema = {"anyOf": [{"type": "string"}, {"type": "null"}]}
        assert get_field_type(schema) == (str | None)

    def test_anyof_optional_list_of_str(self) -> None:
        schema = {
            "anyOf": [
                {"items": {"type": "string"}, "type": "array"},
                {"type": "null"},
            ]
        }
        assert get_field_type(schema) == (list[str] | None)

    def test_array_of_objects(self) -> None:
        schema = {"type": "array", "items": {"type": "object"}}
        assert get_field_type(schema) == list[dict[str, Any]]

    def test_array_without_items(self) -> None:
        result = get_field_type({"type": "array"})
        assert get_origin(result) is list
        assert get_args(result) == (Any,)

    def test_nested_anyof(self) -> None:
        schema = {
            "anyOf": [
                {"anyOf": [{"type": "integer"}, {"type": "string"}]},
                {"type": "null"},
            ]
        }
        result = get_field_type(schema)
        assert _is_union(result)
        assert set(get_args(result)) == {int, str, type(None)}

    def test_general_union(self) -> None:
        schema = {"anyOf": [{"type": "integer"}, {"type": "string"}]}
        result = get_field_type(schema)
        assert _is_union(result)
        assert set(get_args(result)) == {int, str}

    def test_scalar_types_preserved(self) -> None:
        assert get_field_type({"type": "string"}) is str
        assert get_field_type({"type": "integer"}) is int
        assert get_field_type({"type": "number"}) is float
        assert get_field_type({"type": "boolean"}) is bool
        assert get_field_type({"type": "object"}) == dict[str, Any]

    def test_ref_falls_back_to_any(self) -> None:
        assert get_field_type({"$ref": "#/$defs/SomeModel"}) is Any

    def test_string_enum_maps_to_str(self) -> None:
        assert get_field_type({"type": "string", "enum": ["a", "b"]}) is str

    def test_use_date_types_preserved(self) -> None:
        from datetime import date, datetime

        assert (
            get_field_type({"type": "string", "format": "date-time"}, use_date_types=True)
            is datetime
        )
        assert get_field_type({"type": "string", "format": "date"}, use_date_types=True) is date
        assert get_field_type({"type": "string", "format": "date-time"}) is str

    def test_anyof_optional_datetime_with_date_types(self) -> None:
        from datetime import datetime

        schema = {
            "anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}],
        }
        assert get_field_type(schema, use_date_types=True) == (datetime | None)


class TestSearchArgsSchemaIntegration:
    """Integration: the built-in search tool's LangChain args_schema."""

    def _build_schema(self) -> Any:
        from glean.agent_toolkit.adapters.langchain import LangChainAdapter
        from glean.agent_toolkit.tools import search

        adapter = LangChainAdapter(search.tool_spec)
        model = adapter._create_args_schema()
        assert model is not None
        return model

    def test_datasources_is_optional_list_of_str(self) -> None:
        model = self._build_schema()
        annotation = model.model_fields["datasources"].annotation
        assert _is_optional_of(annotation, list[str]), (
            f"datasources should be list[str] | None, got {annotation!r}"
        )

    def test_filters_is_optional_list_of_dict(self) -> None:
        model = self._build_schema()
        annotation = model.model_fields["filters"].annotation

        def _is_list_of_dict(inner: Any) -> bool:
            if get_origin(inner) is not list:
                return False
            (item,) = get_args(inner)
            return item is dict or get_origin(item) is dict

        assert _is_optional_of(annotation, _is_list_of_dict), (
            f"filters should be list[dict[...]] | None, got {annotation!r}"
        )

    def test_page_size_is_int(self) -> None:
        model = self._build_schema()
        assert model.model_fields["page_size"].annotation is int

    def test_query_is_required_str(self) -> None:
        model = self._build_schema()
        field = model.model_fields["query"]
        assert field.annotation is str
        assert field.is_required()
