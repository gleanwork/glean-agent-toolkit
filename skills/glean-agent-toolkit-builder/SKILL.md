---
name: glean-agent-toolkit-builder
description: "How to create custom tools for the Glean Agent Toolkit. Use when building new tool integrations, extending the toolkit with custom Glean API calls, or creating new @tool_spec decorated functions. Triggers on: 'create tool', 'new tool', 'custom tool', '@tool_spec', 'tool_spec decorator', 'add a tool'."
---

# Glean Agent Toolkit — Tool Builder Guide

## Tool Anatomy

Every tool in the toolkit is a Python function decorated with `@tool_spec`. The decorator:

1. Extracts an input JSON schema from the function signature (via Pydantic)
2. Creates a `ToolSpec` dataclass wrapping the function
3. Registers the spec in the global `Registry` singleton
4. Attaches `.as_openai_tool()`, `.as_langchain_tool()`, `.as_crewai_tool()`, `.as_adk_tool()` convenience methods

### Minimal tool

```python
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.context import GleanContext

@tool_spec(
    name="my_tool",
    description="Does something useful.",
)
def my_tool(
    ctx: GleanContext | None = None,
    *,
    query: str,
) -> dict:
    # ctx is injected by adapters; LLM frameworks never see it
    client = ctx.get_client()
    # ... call Glean API ...
    return {"answer": "result"}
```

**Rules:**
- First parameter must be `ctx: GleanContext | None = None`
- Use `*` separator — all remaining params are keyword-only (visible to the LLM)
- `name` in the decorator is the tool name exposed to LLMs
- `description` is the tool description exposed to LLMs

## Input Schema with `Annotated` and `Field`

Use `typing.Annotated` with `pydantic.Field` to add descriptions, examples, and constraints. The decorator uses Pydantic's `create_model` to generate JSON Schema from these annotations.

```python
from typing import Annotated, Any
from pydantic import Field
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools._common import ToolResult

@tool_spec(
    name="glean_example_search",
    description="Search for examples in the company knowledge base.",
)
def example_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description="Search query with optional filters.",
            examples=["API documentation", "security policy updated:past_week"],
        ),
    ],
    datasources: Annotated[
        list[str] | None,
        Field(description="Restrict to specific datasources."),
    ] = None,
    page_size: Annotated[
        int,
        Field(description="Number of results to return.", ge=1, le=100),
    ] = 10,
) -> ToolResult:
    ...
```

Parameters with defaults become optional in the schema. Parameters without defaults are required. The `GleanContext` parameter is automatically excluded from the schema.

## Output Model

Use the `output_model` parameter to attach a Pydantic model to the tool spec. This generates an output JSON schema and provides structured typing.

```python
from pydantic import BaseModel
from glean.agent_toolkit.decorators import tool_spec

class ChatResult(BaseModel):
    answer: str
    sources: list[dict[str, Any]]

@tool_spec(
    name="my_chat_tool",
    description="Chat with an AI assistant.",
    output_model=ChatResult,
)
def my_chat(ctx: GleanContext | None = None, *, message: str) -> ToolResult:
    ...
```

## Two Implementation Patterns

### Pattern 1: Stub tools via `run_tool()` (for Glean's tools.run endpoint)

Most built-in tools use this pattern. They map parameters to `ToolsCallParameter` objects and delegate to `run_tool()`, which calls the Glean `tools.run` (or `tools.execute`) API endpoint.

Reference: `search.py`

```python
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import (
    ToolResult,
    convert_to_tool_params,
    run_tool,
)
from glean.agent_toolkit.context import GleanContext

@tool_spec(
    name="glean_my_search",
    description="Search for something specific.",
)
def my_search(
    ctx: GleanContext | None = None,
    *,
    query: str,
    page_size: int = 10,
) -> ToolResult:
    ctx = ctx or GleanContext()
    client = ctx.get_client()

    # convert_to_tool_params wraps each value in a ToolsCallParameter
    parameters = convert_to_tool_params(query=query, pageSize=str(page_size))

    # run_tool calls the Glean tools.run API and wraps the result in ToolResult
    return run_tool("My Search Display Name", parameters, client=client)
```

Key functions from `_common.py`:
- `convert_to_tool_params(**kwargs)` — wraps values into `models.ToolsCallParameter(name=key, value=value)` dicts
- `run_tool(tool_display_name, parameters, *, client=None)` — calls Glean's `tools.run`/`tools.execute` endpoint, returns `ToolResult`
- `arun_tool(...)` — async version of `run_tool`

### Pattern 2: Direct API calls (for non-tools.run endpoints)

Some tools call Glean API endpoints directly instead of going through `tools.run`. This is used when the Glean API has a dedicated endpoint (like `client.chat.create()`).

Reference: `chat.py`

```python
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import (
    ToolResult,
    run_with_error_handling,
    serialize_tool_result,
)
from glean.agent_toolkit.context import GleanContext

@tool_spec(
    name="glean_my_chat",
    description="Chat with Glean Assistant.",
    output_model=ChatResult,
)
def my_chat(
    ctx: GleanContext | None = None,
    *,
    message: str,
) -> ToolResult:
    ctx = ctx or GleanContext()
    client = ctx.get_client()

    def _do_chat() -> dict:
        with client as g_client:
            response = g_client.client.chat.create(
                messages=[{"fragments": [{"text": message}]}],
            )
        # Process response...
        return {"answer": "...", "sources": []}

    # run_with_error_handling calls the function and wraps in ToolResult
    return run_with_error_handling(_do_chat)
```

Key functions:
- `run_with_error_handling(fn, *args, **kwargs)` — calls `fn`, wraps success in `make_ok()`, catches exceptions and wraps in `make_error()` with classification
- `serialize_tool_result(value)` — calls `.model_dump(by_alias=True)` on Pydantic models, passes through plain values

## Error Handling Helpers

All helpers are in `glean.agent_toolkit.tools._common`:

```python
from glean.agent_toolkit.tools._common import (
    make_ok,
    make_error,
    run_with_error_handling,
    _classify_error,
    ToolResult,
    ErrorType,
    SuggestedAction,
)
```

### `make_ok(result)` — Build a success ToolResult

```python
return make_ok({"documents": [...]})
# → {"status": "ok", "result": {...}, "error": None, "error_type": None, "suggested_action": None}
```

Note: when a tool that returns a `ToolResult` envelope is converted through a framework adapter (`get_tools()`, `.as_*_tool()`), the adapter unwraps the envelope before handing it to the framework — the raw `result` payload on success, or a compact `{"error", "error_type", "suggested_action"}` dict on failure. Direct Python callers always see the full envelope. Custom tools are also not returned by `get_tools()` by default; opt in with `builtin=False`, `builtin=None`, or `include=`.

### `make_error(message, error_type, suggested_action)` — Build an error ToolResult

```python
return make_error("Token expired", error_type="auth", suggested_action="check_credentials")
```

### `_classify_error(exc)` — Classify an exception

Returns `(error_type, suggested_action)` tuple. Classification logic:
- `TimeoutError` or "timeout" in message → `("timeout", "retry")`
- `ValueError` → `("validation", "rephrase_query")`
- 401/403 in message → `("auth", "check_credentials")`
- 404 in message → `("not_found", "rephrase_query")`
- 429 in message → `("rate_limit", "retry")`
- `OSError` or fallback → `("api", "retry")`

### `run_with_error_handling(fn, *args, **kwargs)` — Call and wrap

Calls `fn(*args, **kwargs)`. On success returns `make_ok(result)`. On exception, classifies and returns `make_error(...)`.

## Registration

After creating your tool module, add it to `src/glean/agent_toolkit/tools/__init__.py`:

1. Add the module name to `_tool_modules`:

```python
_tool_modules: list[str] = [
    "search",
    "web_search",
    # ... existing modules ...
    "my_new_tool",  # your new module
]
```

2. Add the explicit import and export:

```python
from .my_new_tool import my_new_tool  # noqa: E402

__all__: list[str] = [
    # ... existing exports ...
    "my_new_tool",
]
```

The `@tool_spec` decorator calls `get_registry().register(spec)` automatically when the module is imported, so adding it to `_tool_modules` is sufficient for registration.

## Testing

Use `GleanContext` dependency injection for testing. Pass a mock or fake `Glean` client directly — do not use `unittest.mock.patch`.

```python
from unittest.mock import MagicMock
from glean.agent_toolkit.context import GleanContext

def test_my_tool():
    # Create a mock Glean client
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    # Inject via GleanContext
    ctx = GleanContext(client=mock_client)

    # Call the tool with injected context
    result = my_tool(ctx, query="test")

    assert result["status"] == "ok"
```

For tools using `run_tool()`, the client is passed through:

```python
def test_search_tool():
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    # Configure the mock to return expected data
    mock_run = MagicMock(return_value={"results": []})
    mock_client.client.tools.run = mock_run

    ctx = GleanContext(client=mock_client)
    result = search(ctx, query="test query")

    assert result["status"] == "ok"
```

## Complete Example: Custom Tool from Scratch

Here is a full example of a custom tool that searches Glean for people and returns structured results.

### 1. Create `src/glean/agent_toolkit/tools/team_search.py`

```python
"""Search for teams and their members."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import (
    ToolResult,
    run_with_error_handling,
    serialize_tool_result,
)

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


class TeamSearchResult(BaseModel):
    """Structured result from team search."""

    teams: list[dict[str, Any]]
    total_count: int


@tool_spec(
    name="glean_team_search",
    description=(
        "Search for teams and their members within the organization. "
        "Returns team name, members, and department information."
    ),
    output_model=TeamSearchResult,
)
def team_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description="Team name, department, or member name to search for.",
            examples=["backend engineering", "product design", "Jane Smith's team"],
        ),
    ],
    include_members: Annotated[
        bool,
        Field(description="Whether to include team member details."),
    ] = True,
) -> ToolResult:
    """Search for teams matching the query.

    Args:
        ctx: Optional Glean context for client injection.
        query: The team search query.
        include_members: Whether to include member details in results.
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()

    def _do_search() -> dict[str, Any]:
        with client as g_client:
            response = g_client.client.search.query(query=query)
        results = serialize_tool_result(response)
        return TeamSearchResult(
            teams=results.get("results", []),
            total_count=len(results.get("results", [])),
        ).model_dump()

    return run_with_error_handling(_do_search)
```

### 2. Register in `tools/__init__.py`

Add `"team_search"` to `_tool_modules`, then add the import and export:

```python
from .team_search import team_search  # noqa: E402

# Add "team_search" to __all__
```

### 3. Use it

```python
from glean.agent_toolkit.tools import team_search

# Direct call
result = team_search(query="backend engineering")

# As an OpenAI tool
openai_tool = team_search.as_openai_tool()

# Via get_tools (automatically included after registration)
from glean.agent_toolkit import get_tools
all_tools = get_tools("langchain")  # includes team_search
```
