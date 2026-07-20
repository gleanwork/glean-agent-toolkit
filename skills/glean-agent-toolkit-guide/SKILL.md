---
name: glean-agent-toolkit-guide
description: "How to use the Glean Agent Toolkit SDK. Use when building agents that integrate Glean enterprise search via the glean-agent-toolkit Python package. Triggers on: 'glean-agent-toolkit', 'glean agent toolkit', 'GleanContext', 'configure', 'get_tools', 'as_openai_tool', 'as_langchain_tool', 'as_crewai_tool', 'as_adk_tool', '@tool_spec'."
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

`get_tools()` is the primary API. It returns the nine built-in Glean tools converted to a specific framework's format.

```python
from glean.agent_toolkit import get_tools

# The built-in Glean tools for a framework
tools = get_tools("openai")       # list of OpenAI FunctionTool objects
tools = get_tools("langchain")    # list of LangChain StructuredTool objects
tools = get_tools("crewai")       # list of CrewAI BaseTool objects
tools = get_tools("adk")          # list of Google ADK FunctionTool objects
```

By default only the built-in `glean_*` tools are returned. Custom `@tool_spec` tools require explicit opt-in: `builtin=False` (custom only), `builtin=None` (everything), or list them in `include=`.

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
    server_url="https://your-company-be.glean.com",  # full URL incl. https://
)
```

`server_url` must include the `http(s)://` scheme; a bare hostname fails fast with a clear error.

### `configure()` — process-wide defaults

```python
import glean.agent_toolkit

glean.agent_toolkit.configure(
    api_token="your-glean-api-token",
    server_url="https://your-company-be.glean.com",  # or instance="your-company"
)

tools = glean.agent_toolkit.get_tools("langchain")  # uses the configured defaults
```

`configure()` sets a process default used whenever no explicit context/client/credentials are supplied (tools, adapters, and `get_tools()` all honor it, sharing one HTTP client). It is idempotent and overridable per call.

## Advanced: `GleanContext` — Client Lifecycle

`GleanContext` is the dependency injection object that provides Glean API client access to every tool. It is the first parameter of every tool function, but adapters bind it automatically so LLM frameworks never see it. Most users only need env vars or `configure()`; use `GleanContext` for explicit client lifecycle control (`close()`/context manager) or multiple Glean instances in one process.

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
| `glean_chat`             | `chat`              | Conversational Q&A with Glean Assistant        |
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
    chat,
    read_document,
    web_search,
    calendar_search,
    employee_search,
    code_search,
    gmail_search,
    outlook_search,
)
```

The old `glean_chat` import name still works but is deprecated (emits `DeprecationWarning`); the tool ID stays `glean_chat`.

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

## Results and Error Handling

Direct Python calls to a tool function return a `ToolResult` TypedDict, and never raise (missing credentials included):

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

Framework adapters (`get_tools()`, `.as_*_tool()`) unwrap this envelope before handing results to the framework: on success they deliver the raw `result` payload (JSON-serialized where the framework expects strings); on failure a compact `{"error", "error_type", "suggested_action"}` dict. Custom tools that return non-envelope values pass through unchanged.

### Error types

| `error_type`   | Meaning                        | `suggested_action` |
| -------------- | ------------------------------ | ------------------ |
| `"auth"`       | 401/403, or missing API token/credentials | `"check_credentials"` |
| `"config"`     | Invalid server URL, unreachable/unresolvable host | `"check_configuration"` |
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

Built-in tools are natively async end to end: framework async invocation (`await tool.ainvoke(...)` in LangChain, `on_invoke_tool` in the OpenAI Agents SDK, `run_async` in ADK) flows through the Glean SDK's async HTTP client with no thread-pool round-trip.

For direct async use of a tool spec:

```python
from glean.agent_toolkit.tools import search

result = await search.tool_spec.async_function(query="roadmap")
```

Custom `@tool_spec` tools may be `async def`; the coroutine becomes the native async path. Custom sync tools get an `asyncio.to_thread` async wrapper automatically. Caveat: calling an `async def` tool synchronously works outside an event loop (sync bridge via `asyncio.run`) but raises a clear `RuntimeError` inside a running event loop — use the async path there.

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
