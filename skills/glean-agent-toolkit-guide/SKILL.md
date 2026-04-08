---
name: glean-agent-toolkit-guide
description: "How to use the Glean Agent Toolkit SDK. Use when building agents that need enterprise search, chat, or document retrieval via Glean. Triggers on: 'glean search', 'glean toolkit', 'glean agent', 'enterprise search tool', 'GleanContext', 'get_tools', 'as_openai_tool', 'as_langchain_tool'."
---

# Glean Agent Toolkit — Usage Guide

## Installation

Base install (no framework adapters):

```bash
pip install glean-agent-toolkit
```

With a specific framework adapter:

```bash
pip install "glean-agent-toolkit[openai]"     # OpenAI Agents SDK
pip install "glean-agent-toolkit[langchain]"   # LangChain / LangGraph
pip install "glean-agent-toolkit[crewai]"      # CrewAI
pip install "glean-agent-toolkit[adk]"         # Google Agent Development Kit
```

All adapters at once:

```bash
pip install "glean-agent-toolkit[all]"
```

## Quick Start with `get_tools()`

`get_tools()` is the primary API. It returns all Glean tools converted to a specific framework's format.

```python
from glean.agent_toolkit import get_tools

# Get all tools for a framework
tools = get_tools("openai")       # list of OpenAI FunctionTool objects
tools = get_tools("langchain")    # list of LangChain Tool objects
tools = get_tools("crewai")       # list of CrewAI BaseTool objects
tools = get_tools("adk")          # list of Google ADK FunctionTool objects
```

### Filtering tools

```python
# Only include specific tools
tools = get_tools("openai", include=["glean_search", "glean_chat"])

# Exclude specific tools
tools = get_tools("langchain", exclude=["glean_outlook_search"])
```

### Passing credentials explicitly

```python
tools = get_tools(
    "openai",
    api_token="your-glean-api-token",
    server_url="https://your-company-be.glean.com",
)
```

Or pass a pre-configured client:

```python
from glean.agent_toolkit import GleanContext

ctx = GleanContext(api_token="...", server_url="...")
tools = get_tools("openai", client=ctx.get_client())
```

## `GleanContext` — Dependency Injection

`GleanContext` is the dependency injection object that provides Glean API client access to every tool. It is the first parameter of every tool function, but adapters bind it automatically so LLM frameworks never see it.

```python
from glean.agent_toolkit.context import GleanContext

# From environment variables (GLEAN_API_TOKEN, GLEAN_SERVER_URL)
ctx = GleanContext()

# Explicit credentials
ctx = GleanContext(api_token="...", server_url="...")

# Or use instance name instead of server_url
ctx = GleanContext(api_token="...", instance="your-instance")

# Or inject a pre-built Glean client
from glean.api_client import Glean
client = Glean(api_token="...", server_url="...")
ctx = GleanContext(client=client)

# Get the underlying Glean API client
glean_client = ctx.get_client()
```

## Available Tools

All tools are registered under the `glean.agent_toolkit.tools` package. Each tool function name is the import name; each tool's `name` attribute (used by LLMs) is prefixed with `glean_`.

| Tool name (`spec.name`)  | Import name         | Description                                    |
| ------------------------ | ------------------- | ---------------------------------------------- |
| `glean_search`           | `search`            | Search internal documents and knowledge bases  |
| `glean_chat`             | `glean_chat`        | Conversational Q&A with Glean Assistant        |
| `glean_read_document`    | `read_document`     | Read full document content by ID or URL        |
| `glean_web_search`       | `web_search`        | Search the public web                          |
| `glean_calendar_search`  | `calendar_search`   | Find meetings and calendar events              |
| `glean_employee_search`  | `employee_search`   | Search employees by name, team, or department  |
| `glean_code_search`      | `code_search`       | Search source code repositories                |
| `glean_gmail_search`     | `gmail_search`      | Search Gmail messages and conversations        |
| `glean_outlook_search`   | `outlook_search`    | Search Outlook mail and calendar items         |

### Explicit imports

```python
from glean.agent_toolkit.tools import (
    search,
    glean_chat,
    read_document,
    web_search,
    calendar_search,
    employee_search,
    code_search,
    gmail_search,
    outlook_search,
)
```

## Per-Tool Direct Usage

Every tool function can be called directly. The first parameter is always `ctx: GleanContext | None = None`, followed by keyword-only arguments after `*`.

```python
from glean.agent_toolkit.tools import search
from glean.agent_toolkit.context import GleanContext

ctx = GleanContext()

# Call the tool directly
result = search(ctx, query="quarterly results", page_size=5)
```

### Adapter convenience methods

Each decorated tool function has adapter methods attached:

```python
from glean.agent_toolkit.tools import search

openai_tool   = search.as_openai_tool()     # OpenAI FunctionTool
langchain_tool = search.as_langchain_tool() # LangChain Tool
crewai_tool   = search.as_crewai_tool()     # CrewAI BaseTool
adk_tool      = search.as_adk_tool()        # Google ADK FunctionTool
```

## Error Handling

Every tool returns a `ToolResult` TypedDict:

```python
from glean.agent_toolkit.tools._common import ToolResult

# ToolResult structure:
{
    "status": "ok" | "error",
    "result": <payload> | None,       # present on success
    "error": <message> | None,        # present on failure
    "error_type": <ErrorType> | None, # classification on failure
    "suggested_action": <action> | None,
}
```

### Error types

| `error_type`   | Meaning                        | `suggested_action` |
| -------------- | ------------------------------ | ------------------ |
| `"auth"`       | 401/403 — bad or expired token | `"check_credentials"` |
| `"validation"` | Bad input / ValueError         | `"rephrase_query"` |
| `"api"`        | Generic API error              | `"retry"`          |
| `"timeout"`    | Request timed out              | `"retry"`          |
| `"not_found"`  | 404 — resource not found       | `"rephrase_query"` |
| `"rate_limit"` | 429 — too many requests        | `"retry"`          |

### Checking results

```python
result = search(ctx, query="roadmap")
if result["status"] == "ok":
    documents = result["result"]
else:
    print(f"Error ({result['error_type']}): {result['error']}")
    print(f"Suggested: {result['suggested_action']}")
```

## Framework-Specific Examples

### OpenAI Agents SDK

```python
from agents import Agent, Runner
from glean.agent_toolkit.tools import search

agent = Agent(
    name="KnowledgeAssistant",
    instructions="You help users find company information using Glean search.",
    tools=[search],  # Pass the tool function directly
)

result = Runner.run_sync(agent, "Find our Q4 planning documents")
print(result.final_output)
```

### LangChain

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from glean.agent_toolkit import get_tools

tools = get_tools("langchain")
llm = ChatOpenAI(model="gpt-4")
# ... set up prompt and agent as usual
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
```

### CrewAI

```python
from crewai import Agent, Crew, Task
from glean.agent_toolkit.tools import search

researcher = Agent(
    role="Corporate Researcher",
    goal="Find relevant company information",
    tools=[search.as_crewai_tool()],
)
```

### Google ADK

```python
from google.adk.agents import Agent
from glean.agent_toolkit.tools import search, employee_search

root_agent = Agent(
    name="company_assistant",
    model="gemini-2.0-flash",
    tools=[search.as_adk_tool(), employee_search.as_adk_tool()],
)
```

## Async Support

Every `ToolSpec` has an `async_function` that wraps the sync implementation via `asyncio.run_in_executor`. The `_common.py` module also provides `arun_tool` for async tool execution.

```python
from glean.agent_toolkit.tools._common import arun_tool

# Async version of run_tool — same signature
result = await arun_tool("Glean Search", parameters, client=client)
```

For direct async use of a tool spec:

```python
from glean.agent_toolkit.tools import search

spec = search.tool_spec
result = await spec.async_function(ctx, query="roadmap")
```

## Environment Variables

### Required

| Variable           | Description                                       |
| ------------------ | ------------------------------------------------- |
| `GLEAN_API_TOKEN`  | Your Glean API token                              |
| `GLEAN_SERVER_URL` | Glean backend URL (e.g. `https://company-be.glean.com`) |

You can use `GLEAN_INSTANCE` instead of `GLEAN_SERVER_URL` if preferred.

### Optional — Retry Configuration

| Variable                  | Default | Description                              |
| ------------------------- | ------- | ---------------------------------------- |
| `GLEAN_RETRY_INITIAL`     | `1.0`   | Initial backoff interval (seconds)       |
| `GLEAN_RETRY_MAX`         | `50.0`  | Maximum backoff interval (seconds)       |
| `GLEAN_RETRY_MULTIPLIER`  | `1.1`   | Backoff exponent/multiplier              |
| `GLEAN_RETRY_MAX_ELAPSED` | `60.0`  | Total retry time limit (seconds)         |

Set these before constructing any `GleanContext` or calling `get_tools()`.
