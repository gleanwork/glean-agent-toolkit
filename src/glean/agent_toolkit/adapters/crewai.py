"""CrewAI adapter for converting tool specifications."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Union, cast

from pydantic import BaseModel

from glean.agent_toolkit.adapters.base import BaseAdapter
from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from crewai.tools import BaseTool as CrewBaseTool
else:
    CrewBaseTool = Any  # type: ignore  # noqa: N816

from pydantic import Field as PydanticField  # type: ignore
from pydantic import create_model as pydantic_create_model

HAS_CREWAI: bool


class _FallbackCrewBaseTool:
    """Fallback for crewai.tools.BaseTool."""

    name: str
    description: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        pass

    def _run(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D401
        ...


def _fallback_field(*args: Any, **kwargs: Any) -> Any:  # noqa: N802
    """Fallback for pydantic.Field."""
    return None


def _fallback_create_model(*args: Any, **kwargs: Any) -> Any:
    """Fallback for pydantic.create_model."""
    return None


try:
    from crewai.tools import BaseTool as _ActualCrewBaseTool  # type: ignore
    from pydantic import Field as _ActualField  # type: ignore
    from pydantic import create_model as _actual_create_model

    BaseTool = _ActualCrewBaseTool
    Field = _ActualField
    create_model = _actual_create_model
    HAS_CREWAI = True
except ImportError:  # pragma: no cover
    BaseTool = _FallbackCrewBaseTool  # type: ignore[assignment]
    Field = _fallback_field  # type: ignore[assignment]
    create_model = _fallback_create_model  # type: ignore[assignment]
    HAS_CREWAI = False


class GleanCrewAITool(BaseTool):  # type: ignore[misc]
    """CrewAI tool implementation for Glean tools."""

    name: str  # CrewAI BaseTool requires name and description
    description: str  # CrewAI BaseTool requires name and description
    # Reuse BaseTool's built-in placeholder default for ``args_schema`` so that
    # CrewAI can lazily infer a schema when one isn't supplied. We intentionally
    # *do not* override the attribute here to avoid accidentally setting it to
    # ``None`` and breaking CrewAI's internal description generation logic.

    _function: Callable[..., Any]

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable[..., Any],
        args_schema: type[BaseModel] | None = None,
    ) -> None:
        """Initialize the tool.

        Args:
            name: The name of the tool
            description: A description of the tool
            function: The function to call when the tool is invoked
            args_schema: Optional schema for the arguments
        """
        super().__init__(name=name, description=description)

        self._function = function

        # Only override ``args_schema`` when we actually created one; otherwise
        # leave the placeholder so CrewAI can lazily generate a schema.
        if args_schema is not None:
            self.args_schema = args_schema

        object.__setattr__(self, "_tool_spec_ref", None)

    def _run(self, **kwargs: Any) -> Any:
        """Run the tool with the given arguments.

        Args:
            **kwargs: The arguments to pass to the function

        Returns:
            The result of calling the function
        """
        return self._function(**kwargs)


CrewAIToolType = CrewBaseTool | BaseTool  # type: ignore[valid-type]


class CrewAIAdapter(BaseAdapter[CrewAIToolType]):
    """Adapter for CrewAI tools."""

    def __init__(self, tool_spec: ToolSpec) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        super().__init__(tool_spec)
        if not HAS_CREWAI:
            raise ImportError(
                "CrewAI package is required for CrewAI adapter. "
                "Install it with `pip install agent_toolkit[crewai]`. "
                "Note: CrewAI requires Python 3.10 or higher."
            )

    def to_tool(self) -> CrewAIToolType:
        """Convert to CrewAI tool format.

        Returns:
            A CrewAI BaseTool instance
        """
        # Create and configure the tool
        created_args_schema = self._create_args_schema()

        tool = GleanCrewAITool(
            name=self.tool_spec.name,
            description=self.tool_spec.description,
            function=self.tool_spec.function,
            args_schema=created_args_schema,
        )

        # Store the tool_spec reference for testing
        object.__setattr__(tool, "_tool_spec_ref", self.tool_spec)

        return tool

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
                field_defs[name] = (field_type, PydanticField(..., description=description))
            else:
                field_defs[name] = (field_type, PydanticField(None, description=description))

        model_name = f"{self.tool_spec.name}ArgsSchema"
        model = pydantic_create_model(model_name, **field_defs)  # type: ignore

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

        if schema_type == "string":
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
