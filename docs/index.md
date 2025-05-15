# Glean Agent Toolkit Documentation

## Overview

Glean Agent Toolkit is a universal toolkit for creating agent tools that work with multiple agent frameworks including:

- OpenAI Assistants API
- Google Generative AI Developer Kit (ADK)
- LangChain/LangGraph
- CrewAI

It provides a uniform interface for defining tools once and using them across different agent frameworks, specifically for Glean use cases.

## Installation

```bash
pip install glean-agent-toolkit
```

With specific adapters:

```bash
pip install glean-agent-toolkit[openai]
pip install glean-agent-toolkit[adk]
pip install glean-agent-toolkit[langchain]
pip install glean-agent-toolkit[crewai]
```

## Basic Usage

```python
from glean.toolkit import tool_spec

@tool_spec(name="add", description="Add two integers")
def add(a: int, b: int) -> int:
    return a + b

# Use with OpenAI
openai_tool = add.as_openai_tool()

# Use with Google ADK
adk_tool = add.as_adk_tool()

# Use with LangChain
langchain_tool = add.as_langchain_tool()

# Use with CrewAI
crewai_tool = add.as_crewai_tool()
```

## Advanced Usage

### Custom Output Models

```python
from pydantic import BaseModel
from glean.toolkit import tool_spec

class Response(BaseModel):
    result: int
    explanation: str

@tool_spec(
    name="multiply",
    description="Multiply two integers",
    output_model=Response
)
def multiply(a: int, b: int) -> Response:
    product = a * b
    return Response(
        result=product,
        explanation=f"The product of {a} and {b} is {product}"
    )
```

## CLI Usage

The toolkit includes a CLI for listing and exporting tool schemas:

```bash
# List all registered tools
glean-toolkit list

# Export schema for a specific tool
glean-toolkit export-schema add
```

## API Reference

### `tool_spec` Decorator

```python
def tool_spec(
    name: str,
    description: str,
    output_model: Optional[Type[BaseModel]] = None,
    version: Optional[str] = None,
) -> Callable[[T], T]:
    """Decorator to register a function as a tool."""
```

### Registry

```python
def get_registry() -> Registry:
    """Get the global registry instance."""
```

### Tool Specification

```python
@dataclass
class ToolSpec:
    """Specification for a tool."""
    name: str
    description: str
    function: Callable
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    version: Optional[str] = None
    output_model: Optional[Type[BaseModel]] = None
```