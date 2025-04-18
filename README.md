# Glean Agent Toolkit

A universal toolkit for creating agent tools that work with multiple agent frameworks, specialized for Glean.

## Installation

```bash
pip install glean_agent_toolkit
```

With specific adapters:

```bash
pip install glean_agent_toolkit[openai]
pip install glean_agent_toolkit[adk]
pip install glean_agent_toolkit[langchain]
pip install glean_agent_toolkit[crewai]
```

## Usage

```python
from toolkit import tool_spec

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

You can specify a custom output model:

```python
from pydantic import BaseModel
from toolkit import tool_spec

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

## CLI

The toolkit includes a CLI for listing and exporting tool schemas:

```bash
# List all registered tools
glean-toolkit list

# Export schema for a specific tool
glean-toolkit export-schema add
```

## Contributing

Interested in contributing? Check out our [Contributing Guide](CONTRIBUTING.md) for instructions on setting up the development environment and submitting changes. 