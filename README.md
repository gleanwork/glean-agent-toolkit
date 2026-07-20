# Glean Agent Toolkit

The Glean Agent Toolkit makes it easy to integrate Glean's powerful search and knowledge discovery capabilities into your AI agents. Use our pre-built tools with popular agent frameworks like OpenAI Assistants, LangChain, CrewAI, and Google's Agent Development Kit (ADK), or adapt your own custom tools for cross-framework use.

## Key Features

- **Production-Ready Glean Tools:** Instantly add capabilities like enterprise search, employee lookup, calendar search, Gmail search, and more to your agents.
- **Framework Adapters:** Seamlessly convert Glean tools into formats compatible with major agent SDKs.
- **Custom Tool Creation:** Define your own tools once using the `@tool_spec` decorator and use them across any supported framework.

## Compatibility & Reliability

- Requires Python 3.10+
- Built-in retries are enabled via the Python client’s `RetryConfig`.
- See `docs/prerequisites.md` for server-level configuration and connector requirements.

### Retry configuration (env vars)

| Variable                  | Default | Description                                              | Example |
| ------------------------- | ------- | -------------------------------------------------------- | ------- |
| `GLEAN_RETRY_INITIAL`     | `1`     | Initial backoff interval in seconds                      | `2`     |
| `GLEAN_RETRY_MAX`         | `50`    | Maximum backoff interval in seconds                      | `8`     |
| `GLEAN_RETRY_MULTIPLIER`  | `1.1`   | Backoff multiplier/exponent                              | `2.0`   |
| `GLEAN_RETRY_MAX_ELAPSED` | `60`    | Total time limit in seconds before giving up on retries  | `30`    |

Intervals are expressed in seconds; the multiplier is a unitless exponent. Retries cover transient failures such as HTTP 429/5xx and connection timeouts. Set these before constructing any Glean client usage.

```bash
# Example: bounded retries
export GLEAN_RETRY_INITIAL=1
export GLEAN_RETRY_MAX=8
export GLEAN_RETRY_MULTIPLIER=2.0
export GLEAN_RETRY_MAX_ELAPSED=30
```

## Installation

Install with all framework adapters (recommended):

```bash snippet=readme/snippet-03.bash
pip install "glean-agent-toolkit[all]"
```

Or install the base toolkit and add extras as needed:

```bash snippet=readme/snippet-01.bash
pip install glean-agent-toolkit
```

### Extras reference

| Extra        | Installs                      | Use case                         |
| ------------ | ----------------------------- | -------------------------------- |
| `[openai]`   | `openai`, `openai-agents`     | OpenAI Agents SDK / Assistants   |
| `[langchain]`| `langchain-core`              | LangChain / LangGraph agents     |
| `[crewai]`   | `crewai`                      | CrewAI multi-agent workflows     |
| `[adk]`      | `google-adk`                  | Google Agent Development Kit     |
| `[all]`      | All of the above              | Full framework support           |

```bash snippet=readme/snippet-02.bash
pip install glean-agent-toolkit[openai]
pip install glean-agent-toolkit[adk]
pip install glean-agent-toolkit[langchain]
pip install glean-agent-toolkit[crewai]
```

Note: The `[openai]` extra installs both the standard `openai` Python library (for direct API interactions like Chat Completions) and the `openai-agents` library used by the "OpenAI Agents SDK" example below — no separate install is needed.

## Prerequisites

Before using any Glean tools, you'll need:

1. **Glean API credentials**: Obtain these from your Glean administrator
2. **Environment variables**:

   ```bash
   export GLEAN_API_TOKEN="your-api-token"
   export GLEAN_SERVER_URL="https://your-company-be.glean.com"
   ```

See `docs/prerequisites.md` for instance-level connector and Admin settings required per tool.

## Quickstart Example: Company Assistant with Google ADK

Here's a complete example that demonstrates the power of the Glean Agent Toolkit. We'll build a "Company Assistant" using Google's Agent Development Kit (ADK) that can help employees find information, discover colleagues, and search company resources.

### Step 1: Create Project Directory

First, create the project structure:

```bash snippet=readme/snippet-06.bash
mkdir company_assistant/
cd company_assistant/
```

### Step 2: Create the Agent File

Create `company_assistant/agent.py` with your agent definition:

```python snippet=readme/snippet-01.py
import os

from google.adk.agents import Agent

from glean.agent_toolkit.tools import calendar_search, employee_search, gmail_search, search

# Ensure environment variables are set
required_env_vars = ["GLEAN_API_TOKEN", "GLEAN_SERVER_URL"]
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable must be set")

# For Google ADK, you also need authentication
# Either set GOOGLE_API_KEY for Google AI Studio, or use gcloud auth for Vertex AI
if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"):
    raise ValueError("Either GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT must be set for ADK")

# Convert Glean tools to Google ADK format
company_search = search.as_adk_tool()
people_finder = employee_search.as_adk_tool()
meeting_search = calendar_search.as_adk_tool()
email_search = gmail_search.as_adk_tool()

# Create a Company Assistant agent
root_agent = Agent(
    name="company_assistant",
    model="gemini-2.0-flash",
    description="""Company Assistant that helps employees find information, people, and resources
    within the organization.""",
    instruction="""You are a helpful company assistant that helps employees find information,
    people, and resources within the organization. You have access to:

    - Company knowledge base and documents (use glean_search)
    - Employee directory and contact information (use glean_employee_search)
    - Calendar and meeting information (use glean_calendar_search)
    - Email search capabilities (use glean_gmail_search)

    Always be helpful, professional, and respect privacy. When searching for people,
    only share appropriate business contact information.""",
    tools=[company_search, people_finder, meeting_search, email_search],
)
```

### Step 3: Create Package Init File

Create `company_assistant/__init__.py` to import your agent:

```python snippet=readme/snippet-02.py
from . import agent
```

### Step 4: Configure Environment Variables

Create `company_assistant/.env` with your credentials:

```bash snippet=readme/snippet-07.bash
# company_assistant/.env

# Authentication for Google ADK (choose one)
GOOGLE_API_KEY=your-google-ai-studio-api-key
# OR for Vertex AI:
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=us-central1

# Glean credentials
GLEAN_API_TOKEN=your-glean-api-token
GLEAN_SERVER_URL=https://your-company-be.glean.com
```

### Step 5: Run Your Agent

From the parent directory (outside `company_assistant/`), run your Company Assistant:

```bash
adk web
```

### Real-World Queries You Can Handle

Once set up, your Company Assistant can handle requests like:

- _"Find our security guidelines for handling customer data"_
- _"Who's the product manager for the mobile app team?"_
- _"Show me emails about the budget planning meeting from last week"_
- _"I need the engineering team's architecture docs for the payment system"_
- _"Find all the design review meetings scheduled for this month"_
- _"Who worked on the API authentication project? I need to ask them some questions"_

This type of assistant can dramatically improve employee productivity by making company knowledge instantly accessible through natural conversation.

## Available Tools

| Tool name                | Import name         | Description                                    |
| ------------------------ | ------------------- | ---------------------------------------------- |
| `glean_search`           | `search`            | Search internal documents and knowledge bases  |
| `glean_chat`             | `glean_chat`        | Conversational Q&A with Glean Assistant        |
| `glean_read_document`    | `read_document`     | Read full document content by ID or URL        |
| `glean_web_search`       | `web_search`        | Search the public web for external information |
| `glean_calendar_search`  | `calendar_search`   | Find meetings and calendar events              |
| `glean_employee_search`  | `employee_search`   | Search employees by name, team, or department  |
| `glean_code_search`      | `code_search`       | Search source code repositories                |
| `glean_gmail_search`     | `gmail_search`      | Search Gmail messages and conversations        |
| `glean_outlook_search`   | `outlook_search`    | Search Outlook mail and calendar items         |

### Explicit imports

```python
from glean.agent_toolkit.tools import search, glean_chat, read_document
from glean.agent_toolkit.tools import web_search, calendar_search
from glean.agent_toolkit.tools import employee_search, code_search
from glean.agent_toolkit.tools import gmail_search, outlook_search
```

### Adapter methods

Each tool function exposes adapter methods for framework conversion:

| Method                | Returns                          | Framework           |
| --------------------- | -------------------------------- | ------------------- |
| `.as_openai_tool()`   | `FunctionTool` or `dict`         | OpenAI Agents SDK   |
| `.as_langchain_tool()` | `langchain_core.tools.StructuredTool` | LangChain / LangGraph |
| `.as_crewai_tool()`   | `CrewAI BaseTool`                | CrewAI              |
| `.as_adk_tool()`      | `google.adk FunctionTool`        | Google ADK          |

You can also use `get_tools()` to get all tools adapted for a framework at once:

```python
from glean.agent_toolkit import get_tools

langchain_tools = get_tools("langchain")
openai_tools = get_tools("openai", include=["glean_search", "glean_chat"])
```

### Web Research with Context

```python snippet=readme/snippet-09.py
from glean.agent_toolkit.tools import web_search

# External information gathering
web_tool = web_search.as_langchain_tool()

# Example queries:
# "Latest industry trends in machine learning"
# "Current market analysis for SaaS companies"
# "Recent news about our competitors"
```

## Quick Start Examples

### Using `search` with Different Frameworks

#### OpenAI Agents SDK

```python snippet=readme/snippet-03.py
import os

from agents import Agent, Runner

from glean.agent_toolkit.tools import search

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_SERVER_URL"), "GLEAN_SERVER_URL must be set"
assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY must be set"

# Create an agent with the Glean search tool
agent = Agent(
    name="KnowledgeAssistant",
    instructions="""You help users find information from the company knowledge base using
    Glean search.""",
    tools=[search.as_openai_tool()],  # Convert to an Agents SDK FunctionTool
)

# Run a search query
result = Runner.run_sync(agent, "Find our Q4 planning documents")
print(f"Search results: {result.final_output}")
```

#### LangChain

```python snippet=readme/snippet-04.py
import os

# NOTE: AgentExecutor requires the full `langchain` package (not just langchain-core).
# Install with: pip install langchain
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from glean.agent_toolkit.tools import search

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_SERVER_URL"), "GLEAN_SERVER_URL must be set"

# Convert to LangChain tool format
langchain_tool = search.as_langchain_tool()

llm = ChatOpenAI(model="gpt-4", temperature=0)
tools = [langchain_tool]

prompt_template = """You are a helpful assistant with access to company knowledge.
Use the search tool to find relevant information when users ask questions.

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

```python snippet=readme/snippet-05.py
import os

from crewai import Agent, Crew, Task

from glean.agent_toolkit.tools import search

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_SERVER_URL"), "GLEAN_SERVER_URL must be set"

# Convert to CrewAI tool format
crewai_tool = search.as_crewai_tool()

# Create a research agent
researcher = Agent(
    role="Corporate Knowledge Researcher",
    goal="Find and summarize relevant company information",
    backstory="""You are an expert at navigating company knowledge bases to find accurate,
    up-to-date information.""",
    tools=[crewai_tool],
    verbose=True,
)

# Create a research task
research_task = Task(
    description="""Find information about our company's remote work policy and summarize the key
    points.""",
    expected_output="""A clear summary of the remote work policy including eligibility,
    expectations, and guidelines.""",
    agent=researcher,
)

# Execute the research
crew = Crew(agents=[researcher], tasks=[research_task])
result = crew.kickoff()
print(result)
```

### Real-World Use Cases

#### Employee Directory Search

```python snippet=readme/snippet-06.py
from glean.agent_toolkit.tools import employee_search

# Find engineering team members
engineering_team = employee_search.as_langchain_tool()

# Example usage in an agent:
# "Who are the senior engineers in the backend team?"
# "Find Sarah Johnson's contact information"
# "List all product managers in the San Francisco office"
```

#### Code Discovery

```python snippet=readme/snippet-07.py
from glean.agent_toolkit.tools import code_search

# Search company codebases
code_tool = code_search.as_langchain_tool()

# Example queries:
# "Find authentication middleware implementations"
# "Show me recent changes to the payment processing module"
# "Locate configuration files for the staging environment"
```

#### Email and Calendar Integration

```python snippet=readme/snippet-08.py
from glean.agent_toolkit.tools import calendar_search, gmail_search

# Search emails and meetings
gmail_tool = gmail_search.as_langchain_tool()
calendar_tool = calendar_search.as_langchain_tool()

# Example queries:
# "Find emails about the product launch from last month"
# "Show me my meetings with the design team this week"
# "Search for messages containing budget discussions"
```

## Creating Custom Tools with `@tool_spec`

Define your own tools that work across all supported frameworks:

```python snippet=readme/snippet-10.py
import os

import requests
from pydantic import BaseModel

from glean.agent_toolkit import tool_spec


class WeatherResponse(BaseModel):
    temperature: float
    condition: str
    humidity: int
    city: str


@tool_spec(
    name="get_current_weather",
    description="Get current weather information for a specified city",
    output_model=WeatherResponse,
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
        temperature=data["temp"], condition=data["condition"], humidity=data["humidity"], city=city
    )


# Use across frameworks
openai_weather = get_weather.as_openai_tool()
langchain_weather = get_weather.as_langchain_tool()
crewai_weather = get_weather.as_crewai_tool()
```

## Agent Skills

The `skills/` directory contains [Agent Skills](https://agentskills.io) — structured instructions that teach AI coding agents how to use the Glean Agent Toolkit effectively. Skills are supported by Claude Code, Cursor, GitHub Copilot, VS Code, Gemini CLI, OpenAI Codex, Goose, Amp, Roo Code, Junie, and [many others](https://agentskills.io).

### Install

Use [`npx skills`](https://github.com/agentskills/agentskills) to install into your agent:

```bash
# Install all skills at once
npx skills add https://github.com/gleanwork/glean-agent-toolkit
```

```bash
# Or install individual skills
npx skills add https://github.com/gleanwork/glean-agent-toolkit/tree/main/skills/glean-agent-toolkit-guide
npx skills add https://github.com/gleanwork/glean-agent-toolkit/tree/main/skills/glean-agent-toolkit-builder
```

### Available Skills

| Skill | Description |
| --- | --- |
| `glean-agent-toolkit-guide` | How to use the SDK: `get_tools()`, `GleanContext`, adapters, error handling, async |
| `glean-agent-toolkit-builder` | How to create custom tools with `@tool_spec` |

## Contributing

Interested in contributing? Check out our [Contributing Guide](CONTRIBUTING.md) for instructions on setting up the development environment and submitting changes.

## License

This project is licensed under the [MIT License](LICENSE).
