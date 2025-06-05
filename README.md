# Glean Agent Toolkit

The Glean Agent Toolkit makes it easy to integrate Glean's powerful search and knowledge discovery capabilities into your AI agents. Use our pre-built tools with popular agent frameworks like OpenAI Assistants, LangChain, CrewAI, and Google's Agent Development Kit (ADK), or adapt your own custom tools for cross-framework use.

## Key Features

* **Production-Ready Glean Tools:** Instantly add capabilities like enterprise search, employee lookup, calendar search, Gmail search, and more to your agents.
* **Framework Adapters:** Seamlessly convert Glean tools into formats compatible with major agent SDKs.
* **Custom Tool Creation:** Define your own tools once using the `@tool_spec` decorator and use them across any supported framework.

## Installation

Install the base toolkit:

```bash
pip install glean-agent-toolkit
```

To include support for specific agent frameworks, install the relevant extras:

```bash
pip install glean-agent-toolkit[openai]
pip install glean-agent-toolkit[adk]
pip install glean-agent-toolkit[langchain]
pip install glean-agent-toolkit[crewai]
```

You can also install all extras:

```bash
pip install glean-agent-toolkit[all]
```

Note: The `[openai]` extra installs the standard `openai` Python library, used for direct API interactions like Chat Completions or the Assistants API. The example below for the "OpenAI Agents SDK" uses a separate library, `openai-agents`, which you'll need to install independently: `pip install openai-agents`.

## Prerequisites

Before using any Glean tools, you'll need:

1. **Glean API credentials**: Obtain these from your Glean administrator
2. **Environment variables**:
   ```bash
   export GLEAN_API_TOKEN="your-api-token"
   export GLEAN_INSTANCE="your-instance-name"
   ```

## Available Tools

The toolkit comes with a suite of production-ready tools that connect to various Glean functionalities:

* **`glean_search`**: Search your company's knowledge base for relevant documents and information
* **`web_search`**: Search the public web for up-to-date external information
* **`ai_web_search`**: Query Google Gemini for AI-powered web information
* **`calendar_search`**: Find meetings and calendar events
* **`employee_search`**: Search for employees by name, team, department, or expertise
* **`code_search`**: Search your company's source code repositories
* **`gmail_search`**: Search Gmail messages and conversations
* **`outlook_search`**: Search Outlook mail and calendar items

## Quick Start Examples

### Using `glean_search` with Different Frameworks

#### OpenAI Agents SDK

```python
import os
from glean.agent_toolkit.tools import glean_search
from agents import Agent, Runner

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_INSTANCE"), "GLEAN_INSTANCE must be set"
assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY must be set"

# Create an agent with the Glean search tool
agent = Agent(
    name="KnowledgeAssistant",
    instructions="You help users find information from the company knowledge base using Glean search.",
    tools=[glean_search.func]  # Use the underlying function
)

# Run a search query
result = Runner.run_sync(agent, "Find our Q4 planning documents")
print(f"Search results: {result.final_output}")
```

#### LangChain

```python
import os
from glean.agent_toolkit.tools import glean_search
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_INSTANCE"), "GLEAN_INSTANCE must be set"

# Convert to LangChain tool format
langchain_tool = glean_search.as_langchain_tool()

llm = ChatOpenAI(model="gpt-4", temperature=0)
tools = [langchain_tool]

prompt_template = """You are a helpful assistant with access to company knowledge.
Use the glean_search tool to find relevant information when users ask questions.

Tools available:
{tools}

Use this format:
Question: {input}
Thought: I should search for information about this topic
Action: {tool_names}
Action Input: your search query
Observation: the search results
Thought: I can now provide a helpful response
Final Answer: your response based on the search results

Question: {input}
{agent_scratchpad}"""

prompt = ChatPromptTemplate.from_template(prompt_template)
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Search for company information
result = agent_executor.invoke({"input": "What is our vacation policy?"})
print(result["output"])
```

#### CrewAI

```python
import os
from glean.agent_toolkit.tools import glean_search
from crewai import Agent, Task, Crew

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_INSTANCE"), "GLEAN_INSTANCE must be set"

# Convert to CrewAI tool format
crewai_tool = glean_search.as_crewai_tool()

# Create a research agent
researcher = Agent(
    role="Corporate Knowledge Researcher",
    goal="Find and summarize relevant company information",
    backstory="You are an expert at navigating company knowledge bases to find accurate, up-to-date information.",
    tools=[crewai_tool],
    verbose=True
)

# Create a research task
research_task = Task(
    description="Find information about our company's remote work policy and summarize the key points.",
    expected_output="A clear summary of the remote work policy including eligibility, expectations, and guidelines.",
    agent=researcher
)

# Execute the research
crew = Crew(agents=[researcher], tasks=[research_task])
result = crew.kickoff()
print(result)
```

### Real-World Use Cases

#### Employee Directory Search

```python
from glean.agent_toolkit.tools import employee_search

# Find engineering team members
engineering_team = employee_search.as_langchain_tool()

# Example usage in an agent:
# "Who are the senior engineers in the backend team?"
# "Find Sarah Johnson's contact information"
# "List all product managers in the San Francisco office"
```

#### Code Discovery

```python
from glean.agent_toolkit.tools import code_search

# Search company codebases
code_tool = code_search.as_langchain_tool()

# Example queries:
# "Find authentication middleware implementations"
# "Show me recent changes to the payment processing module"
# "Locate configuration files for the staging environment"
```

#### Email and Calendar Integration

```python
from glean.agent_toolkit.tools import gmail_search, calendar_search

# Search emails and meetings
gmail_tool = gmail_search.as_langchain_tool()
calendar_tool = calendar_search.as_langchain_tool()

# Example queries:
# "Find emails about the product launch from last month"
# "Show me my meetings with the design team this week"
# "Search for messages containing budget discussions"
```

#### Web Research with Context

```python
from glean.agent_toolkit.tools import web_search, ai_web_search

# External information gathering
web_tool = web_search.as_langchain_tool()
ai_web_tool = ai_web_search.as_langchain_tool()

# Example queries:
# "Latest industry trends in machine learning"
# "Current market analysis for SaaS companies"
# "Recent news about our competitors"
```

## Creating Custom Tools with `@tool_spec`

Define your own tools that work across all supported frameworks:

```python
from glean.agent_toolkit import tool_spec
from pydantic import BaseModel
import requests

class WeatherResponse(BaseModel):
    temperature: float
    condition: str
    humidity: int
    city: str

@tool_spec(
    name="get_current_weather",
    description="Get current weather information for a specified city",
    output_model=WeatherResponse
)
def get_weather(city: str, units: str = "celsius") -> WeatherResponse:
    """Fetch current weather for a city."""
    # Replace with actual weather API call
    api_key = os.getenv("WEATHER_API_KEY")
    response = requests.get(
        f"https://api.weather.com/v1/current?key={api_key}&q={city}&units={units}"
    )
    data = response.json()
    
    return WeatherResponse(
        temperature=data["temp"],
        condition=data["condition"],
        humidity=data["humidity"],
        city=city
    )

# Use across frameworks
openai_weather = get_weather.as_openai_tool()
langchain_weather = get_weather.as_langchain_tool()
crewai_weather = get_weather.as_crewai_tool()
```

## Contributing

Interested in contributing? Check out our [Contributing Guide](CONTRIBUTING.md) for instructions on setting up the development environment and submitting changes.

## License

This project is licensed under the [MIT License](LICENSE). 