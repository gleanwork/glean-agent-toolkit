"""Adapter for CrewAI tools."""

from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel

from glean.toolkit.adapters.base import BaseAdapter
from glean.toolkit.spec import ToolSpec

# Define this at module level for consistency
HAS_CREWAI = False
crewai = None  # type: ignore
BaseTool = None  # type: ignore
create_model = None  # type: ignore
Field = None  # type: ignore

try:
    import crewai
    from crewai.tools import BaseTool
    from pydantic import Field, create_model

    HAS_CREWAI = True
except ImportError:
    pass  # Variables remain None


# Define the tool class at the module level
class GleanCrewAITool(BaseTool):
    """CrewAI tool implementation for Glean tools."""

    # Custom field to store the function
    _function: Callable[..., Any] = None  # type: ignore

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
        # Pass the required fields to the parent constructor
        super().__init__(name=name, description=description)

        # Set our custom fields
        self._function = function
        self.args_schema = args_schema

        # Store a ref to the original tool spec for testing (not a field in the model)
        object.__setattr__(self, "_tool_spec_ref", None)

    def _run(self, **kwargs: Any) -> Any:
        """Run the tool with the given arguments.

        Args:
            **kwargs: The arguments to pass to the function

        Returns:
            The result of calling the function
        """
        return self._function(**kwargs)


class CrewAIAdapter(BaseAdapter[BaseTool]):
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

    def to_tool(self) -> BaseTool:
        """Convert to CrewAI tool format.

        Returns:
            A CrewAI BaseTool instance
        """
        # Create and configure the tool
        tool = GleanCrewAITool(
            name=self.tool_spec.name,
            description=self.tool_spec.description,
            function=self.tool_spec.function,
            args_schema=self._create_args_schema(),
        )

        # Store the tool_spec reference for testing
        object.__setattr__(tool, "_tool_spec_ref", self.tool_spec)

        return tool

    def _create_args_schema(self) -> type[BaseModel] | None:
        """Create a Pydantic model for the arguments schema.

        Returns:
            A Pydantic model class or None if no properties
        """
        # Extract properties from the input schema
        props = self.tool_spec.input_schema.get("properties", {})
        required = self.tool_spec.input_schema.get("required", [])

        if not props:
            return None

        # Create field definitions with proper type annotation
        # for mypy compatibility
        field_defs: dict[str, tuple[type, Any]] = {}

        for name, schema in props.items():
            # Map JSON schema types to Python types
            field_type = self._get_field_type(schema)
            is_required = name in required

            # Get field description if available
            description = schema.get("description", "")

            # Create appropriate field with type information
            if is_required:
                field_defs[name] = (field_type, Field(..., description=description))
            else:
                field_defs[name] = (field_type, Field(None, description=description))

        # Create the model - use type ignore since mypy has trouble with the dynamic usage
        model = create_model(f"{self.tool_spec.name}Schema", **field_defs)  # type: ignore
        return cast(type[BaseModel], model)

    def _get_field_type(self, schema: dict[str, Any]) -> type:
        """Determine the Python type from JSON schema property.

        Args:
            schema: JSON schema property definition

        Returns:
            Appropriate Python type
        """
        # Handle enum values if present
        if "enum" in schema:
            return str

        # Get the basic type from schema
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
            # Return list rather than specific type to avoid mypy issues
            return list
        elif schema_type == "object":
            return dict
        else:
            # Default fallback
            return str  # More strict than Any for mypy
