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

## Framework Examples

### OpenAI

```python
from glean_agent_toolkit.toolkit import tool_spec
import openai

# Define your tool
@tool_spec(
    name="glean_search",
    description="Search Glean for documents matching a query",
    version="1.0.0",
)
def glean_search(query: str, max_results: int = 5):
    # Your implementation here
    return {"results": [...], "total_results": 10}

# Convert to OpenAI tool format
openai_tool = glean_search.as_openai_tool()

# Use with OpenAI client
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": "Search for information about Agent Toolkit"}],
    tools=[openai_tool],
)
```

### Google ADK

```python
from glean_agent_toolkit.toolkit import tool_spec
from google.adk import Agent

# Define your tool
@tool_spec(
    name="glean_search",
    description="Search Glean for documents matching a query"
)
def glean_search(query: str, max_results: int = 5):
    # Your implementation here
    return {"results": [...], "total_results": 10}

# Convert to ADK tool
adk_tool = glean_search.as_adk_tool()

# Use with Google ADK
agent = Agent(tools=[adk_tool])
response = agent.generate_content("Find documents about Agent Toolkit")
```

### LangChain

```python
from glean_agent_toolkit.toolkit import tool_spec
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI

# Define your tool
@tool_spec(
    name="glean_search",
    description="Search Glean for documents matching a query"
)
def glean_search(query: str, max_results: int = 5):
    # Your implementation here
    return {"results": [...], "total_results": 10}

# Convert to LangChain tool
langchain_tool = glean_search.as_langchain_tool()

# Use with LangChain
llm = ChatOpenAI(model="gpt-4-turbo")
agent = create_react_agent(llm=llm, tools=[langchain_tool])
agent_executor = AgentExecutor(agent=agent, tools=[langchain_tool])
result = agent_executor.invoke({"input": "Search for Agent Toolkit documents"})
```

### CrewAI

```python
from glean_agent_toolkit.toolkit import tool_spec
from crewai import Agent, Task, Crew

# Define your tool
@tool_spec(
    name="glean_search",
    description="Search Glean for documents matching a query"
)
def glean_search(query: str, max_results: int = 5):
    # Your implementation here
    return {"results": [...], "total_results": 10}

# Convert to CrewAI tool
crewai_tool = glean_search.as_crewai_tool()

# Use with CrewAI
researcher = Agent(
    role="Researcher",
    goal="Find relevant information",
    tools=[crewai_tool]
)

research_task = Task(
    description="Search for information about the Agent Toolkit",
    agent=researcher
)

crew = Crew(agents=[researcher], tasks=[research_task])
result = crew.kickoff()
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