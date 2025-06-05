"""LangChain adapter for converting tool specifications."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, TypeAlias, Union, cast

from pydantic import BaseModel

from glean.agent_toolkit.adapters.base import BaseAdapter
from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from langchain.tools import Tool as LangchainTool  # pragma: no cover
else:
    LangchainTool = Any  # type: ignore  # noqa: N816

from pydantic import Field as PydanticField  # type: ignore
from pydantic import create_model as pydantic_create_model

ToolClass: Any = object
Field: Any = object
create_model = pydantic_create_model


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

    ToolClass = _ActualLangchainToolImport
    Field = _ActualPydanticFieldImport
    create_model = _actual_pydantic_create_model_import
    HAS_LANGCHAIN = True
except ImportError:  # pragma: no cover
    ToolClass = _FallbackLangchainTool  # type: ignore[assignment]
    Field = _fallback_pydantic_field
    create_model = _fallback_pydantic_create_model
    HAS_LANGCHAIN = False


if TYPE_CHECKING:
    LangChainToolType: TypeAlias = "LangchainTool"
else:
    from typing import Any as LangChainToolType  # type: ignore


class LangChainAdapter(BaseAdapter[LangChainToolType]):
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

    def to_tool(self) -> Any:
        """Convert to LangChain tool format.

        Returns:
            LangChain Tool instance
        """
        return ToolClass(
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
        json_schema = self.tool_spec.input_schema

        props = json_schema.get("properties", {})
        required = json_schema.get("required", [])

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
