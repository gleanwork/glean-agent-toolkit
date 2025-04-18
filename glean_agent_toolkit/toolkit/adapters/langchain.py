"""Adapter for LangChain tools."""

from typing import Any

try:
    import langchain
except ImportError:
    langchain = None  # type: ignore


class LangChainAdapter:
    """Adapter for LangChain tools."""

    def __init__(self, tool_spec: Any) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
        """
        if langchain is None:
            raise ImportError(
                "LangChain package is required for LangChain adapter. "
                "Install it with `pip install agent_toolkit[langchain]`."
            )
        self.tool_spec = tool_spec

    def to_tool(self) -> Any:
        """Convert to LangChain tool format.

        Returns:
            LangChain Tool instance
        """
        from langchain.tools import tool

        # Use the @tool decorator to create a tool with schema
        @tool(
            name=self.tool_spec.name,
            description=self.tool_spec.description,
            args_schema=self._create_args_schema(),
        )
        def wrapped_tool(*args: Any, **kwargs: Any) -> Any:
            return self.tool_spec.function(*args, **kwargs)

        return wrapped_tool

    def _create_args_schema(self) -> Any:
        """Create a Pydantic model for the arguments schema.

        Returns:
            A Pydantic model class
        """
        from pydantic import create_model

        # Extract properties from the input schema
        props = self.tool_spec.input_schema.get("properties", {})
        required = self.tool_spec.input_schema.get("required", [])

        # Create field definitions
        fields = {}
        for name, schema in props.items():
            # Default to Any for complex types
            field_type = Any
            field_default = ... if name in required else None

            # Add the field
            fields[name] = (field_type, field_default)

        # Create the model
        return create_model(f"{self.tool_spec.name}Schema", **fields)
