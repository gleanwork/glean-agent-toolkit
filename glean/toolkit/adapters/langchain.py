"""Adapter for LangChain tools."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from glean.toolkit.adapters.base import BaseAdapter
from glean.toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from langchain.tools import Tool as LangchainTool  # pragma: no cover
    from pydantic import Field as PydanticField  # pragma: no cover
    from pydantic import create_model as pydantic_create_model

HAS_LANGCHAIN: bool

Tool: Any = object
Field: Any = object
create_model: Any = object


class _FallbackLangchainTool:
    """Fallback for langchain.tools.Tool."""

    name: str
    description: str
    func: Any
    args_schema: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        pass


def _fallback_pydantic_field(*args: Any, **kwargs: Any) -> Any:  # noqa: N802
    """Fallback for pydantic.Field."""
    return None


def _fallback_pydantic_create_model(*args: Any, **kwargs: Any) -> Any:
    """Fallback for pydantic.create_model."""
    return None


try:
    from langchain.tools import Tool as _ActualLangchainToolImport  # type: ignore
    from pydantic import Field as _ActualPydanticFieldImport  # type: ignore
    from pydantic import create_model as _actual_pydantic_create_model_import

    Tool = _ActualLangchainToolImport
    Field = _ActualPydanticFieldImport
    create_model = _actual_pydantic_create_model_import
    HAS_LANGCHAIN = True
except ImportError:  # pragma: no cover
    Tool = _FallbackLangchainTool  # type: ignore[misc,assignment]
    Field = _fallback_pydantic_field
    create_model = _fallback_pydantic_create_model
    HAS_LANGCHAIN = False


class LangChainAdapter(BaseAdapter[Tool]):
    """Adapter for LangChain tools."""

    def __init__(self, tool_spec: ToolSpec) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        super().__init__(tool_spec)
        if not HAS_LANGCHAIN:
            raise ImportError(
                "LangChain package is required for LangChain adapter. "
                "Install it with `pip install agent_toolkit[langchain]`."
            )

    def to_tool(self) -> Tool:
        """Convert to LangChain tool format.

        Returns:
            LangChain Tool instance
        """
        return Tool(
            name=self.tool_spec.name,
            description=self.tool_spec.description,
            func=self.tool_spec.function,
            args_schema=self._create_args_schema(),
        )

    def _create_args_schema(self) -> type[BaseModel] | None:
        """Create a Pydantic model for the arguments schema.

        Returns:
            A Pydantic model class or None if no properties
        """
        props = self.tool_spec.input_schema.get("properties", {})
        required = self.tool_spec.input_schema.get("required", [])

        if not props:
            return None

        field_defs: dict[str, tuple[type, Any]] = {}

        for name, schema in props.items():
            field_type = self._get_field_type(schema)
            is_required = name in required

            description = schema.get("description", "")

            if is_required:
                field_defs[name] = (field_type, Field(..., description=description))
            else:
                field_defs[name] = (field_type, Field(None, description=description))

        model = create_model(f"{self.tool_spec.name}Schema", **field_defs)  # type: ignore
        return cast(type[BaseModel], model)

    def _get_field_type(self, schema: dict[str, Any]) -> type:
        """Determine the Python type from JSON schema property.

        Args:
            schema: JSON schema property definition

        Returns:
            Appropriate Python type
        """
        if "enum" in schema:
            return str

        schema_type = schema.get("type", "string")
        schema_format = schema.get("format", "")

        if schema_type == "string":
            if schema_format == "date-time":
                return datetime
            elif schema_format == "date":
                return date
            return str
        elif schema_type == "integer":
            return int
        elif schema_type == "number":
            return float
        elif schema_type == "boolean":
            return bool
        elif schema_type == "array":
            return list
        elif schema_type == "object":
            return dict
        else:
            return str
