"""Cross-framework contract tests for user-defined ``@tool_spec`` tools.

The invocation matrix in ``test_invocation_matrix.py`` covers the built-in
tools only. These tests drive *custom* tools through ``get_tools`` and each
framework's native invocation path, covering regressions that shipped in
0.8.0:

* tools without a ``GleanContext`` parameter received the context as their
  first positional argument (``got multiple values for argument``, or the
  context silently landing in the first parameter);
* ``Annotated[T, Field(...)] = default`` lost its default unless the module
  used ``from __future__ import annotations``;
* LangChain, CrewAI, and ADK dropped enums, numeric bounds, and real defaults
  from the argument schema;
* a custom tool raising an exception behaved differently in every framework.

This module intentionally does NOT use ``from __future__ import annotations``:
the default-dropping bug only reproduced with real (non-string) annotations.
"""

import json
from collections.abc import Callable, Generator
from types import SimpleNamespace
from typing import Annotated, Any, Literal

import pytest
from pydantic import Field

from glean.agent_toolkit import GleanContext, get_registry, get_tools, tool_spec

try:
    from glean.agent_toolkit.adapters.langchain import HAS_LANGCHAIN
except ImportError:  # pragma: no cover
    HAS_LANGCHAIN = False

try:
    from glean.agent_toolkit.adapters.openai import HAS_OPENAI
except ImportError:  # pragma: no cover
    HAS_OPENAI = False

try:
    from glean.agent_toolkit.adapters.crewai import HAS_CREWAI
except ImportError:  # pragma: no cover
    HAS_CREWAI = False

try:
    from glean.agent_toolkit.adapters.adk import HAS_ADK
except ImportError:  # pragma: no cover
    HAS_ADK = False


COMPACT_ERROR_KEYS = {"error", "error_type", "suggested_action"}

ADD = "custom_add_no_ctx"
MODES = "custom_modes_annotated"
CTX_BY_NAME = "custom_ctx_keyword"
BOOM = "custom_boom"
ASYNC_ADD = "custom_async_add_no_ctx"
CUSTOM_TOOL_NAMES = [ADD, MODES, CTX_BY_NAME, BOOM, ASYNC_ADD]


@pytest.fixture
def custom_tools() -> Generator[None, None, None]:
    """Register the custom tools for one test, then remove them again."""

    @tool_spec(name=ADD, description="Add two integers.")
    def add(a: int, b: int = 5) -> dict[str, int]:
        return {"sum": a + b}

    @tool_spec(name=MODES, description="Echo a mode and a bounded count.")
    def modes(
        mode: Literal["fast", "slow"] = "slow",
        n: Annotated[int, Field(description="How many.", ge=1, le=3)] = 2,
    ) -> dict[str, Any]:
        return {"mode": mode, "n": n}

    @tool_spec(name=CTX_BY_NAME, description="Report whether a context was injected.")
    def ctx_keyword(query: str, glean: GleanContext | None = None) -> dict[str, Any]:
        return {"query": query, "has_ctx": isinstance(glean, GleanContext)}

    @tool_spec(name=BOOM, description="Always fails.")
    def boom(q: str) -> dict[str, Any]:
        raise RuntimeError("boom")

    @tool_spec(name=ASYNC_ADD, description="Add two integers asynchronously.")
    async def async_add(a: int, b: int = 5) -> dict[str, int]:
        return {"sum": a + b}

    yield

    registry = get_registry()
    for name in CUSTOM_TOOL_NAMES:
        registry._tools.pop(name, None)


# ---------------------------------------------------------------------------
# Framework drivers
# ---------------------------------------------------------------------------


def _parse(output: Any) -> Any:
    assert isinstance(output, str), output
    return json.loads(output)


async def _invoke_langchain(tool: Any, args: dict[str, Any]) -> Any:
    return _parse(tool.invoke(dict(args)))


async def _invoke_langchain_async(tool: Any, args: dict[str, Any]) -> Any:
    return _parse(await tool.ainvoke(dict(args)))


async def _invoke_openai(tool: Any, args: dict[str, Any]) -> Any:
    return _parse(await tool.on_invoke_tool(SimpleNamespace(), json.dumps(args)))


async def _invoke_crewai(tool: Any, args: dict[str, Any]) -> Any:
    return _parse(tool.run(**args))


async def _invoke_adk(tool: Any, args: dict[str, Any]) -> Any:
    result = await tool.run_async(args=dict(args), tool_context=None)
    assert isinstance(result, dict), result
    return result


DRIVERS = [
    pytest.param(
        ("langchain", _invoke_langchain),
        id="langchain-invoke",
        marks=pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed"),
    ),
    pytest.param(
        ("langchain", _invoke_langchain_async),
        id="langchain-ainvoke",
        marks=pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed"),
    ),
    pytest.param(
        ("openai", _invoke_openai),
        id="openai-on_invoke_tool",
        marks=pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI Agents SDK not installed"),
    ),
    pytest.param(
        ("crewai", _invoke_crewai),
        id="crewai-run",
        marks=pytest.mark.skipif(not HAS_CREWAI, reason="CrewAI not installed"),
    ),
    pytest.param(
        ("adk", _invoke_adk),
        id="adk-run_async",
        marks=pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed"),
    ),
]

Driver = tuple[str, Callable[[Any, dict[str, Any]], Any]]


def _tool(framework: str, name: str) -> Any:
    tools = get_tools(framework, include=[name])
    assert len(tools) == 1, f"{name} missing from get_tools({framework!r})"
    return tools[0]


# ---------------------------------------------------------------------------
# Invocation contracts
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("custom_tools")
@pytest.mark.parametrize("driver", DRIVERS)
async def test_tool_without_context_param_is_invocable(driver: Driver) -> None:
    """A custom tool with no GleanContext parameter must not receive one."""
    framework, invoke = driver
    assert await invoke(_tool(framework, ADD), {"a": 1}) == {"sum": 6}


@pytest.mark.usefixtures("custom_tools")
@pytest.mark.parametrize("driver", DRIVERS)
async def test_async_tool_without_context_param_is_invocable(driver: Driver) -> None:
    """Same contract for an ``async def`` custom tool.

    Sync drivers are skipped: they run inside this test's event loop, where
    the sync bridge for ``async def`` tools deliberately refuses to block.
    """
    framework, invoke = driver
    if invoke in (_invoke_langchain, _invoke_crewai):
        pytest.skip("sync invocation of an async tool inside a running event loop")
    assert await invoke(_tool(framework, ASYNC_ADD), {"a": 2, "b": 3}) == {"sum": 5}


@pytest.mark.usefixtures("custom_tools")
@pytest.mark.parametrize("driver", DRIVERS)
async def test_context_is_bound_by_parameter_name(driver: Driver) -> None:
    """The context reaches a GleanContext parameter wherever it is declared."""
    framework, invoke = driver
    payload = await invoke(_tool(framework, CTX_BY_NAME), {"query": "hello"})
    assert payload == {"query": "hello", "has_ctx": True}


@pytest.mark.usefixtures("custom_tools")
@pytest.mark.parametrize("driver", DRIVERS)
async def test_defaults_apply_when_arguments_are_omitted(driver: Driver) -> None:
    """Plain and ``Annotated[..., Field()]`` defaults survive into every framework."""
    framework, invoke = driver
    assert await invoke(_tool(framework, MODES), {}) == {"mode": "slow", "n": 2}


@pytest.mark.usefixtures("custom_tools")
@pytest.mark.parametrize("driver", DRIVERS)
async def test_arguments_are_coerced_to_declared_types(driver: Driver) -> None:
    """A model that sends ``"3"`` for an int parameter still gets ``3`` to the tool.

    Some frameworks (ADK, for example) pass model-supplied arguments through
    without validating them against the declared schema.
    """
    framework, invoke = driver
    assert await invoke(_tool(framework, MODES), {"n": "3"}) == {"mode": "slow", "n": 3}


@pytest.mark.usefixtures("custom_tools")
@pytest.mark.parametrize("driver", DRIVERS)
async def test_invalid_arguments_become_validation_errors(driver: Driver) -> None:
    """Out-of-range arguments are rejected before the tool function runs.

    Frameworks that validate natively (LangChain, CrewAI 1.x) raise, and
    their agent loops report the error back to the model. Everywhere else
    the toolkit's own validation returns the compact ``validation`` payload.
    """
    framework, invoke = driver
    try:
        payload = await invoke(_tool(framework, MODES), {"n": 7})
    except ValueError as exc:  # includes pydantic.ValidationError
        assert "less than or equal to 3" in str(exc)
        return
    assert set(payload) == COMPACT_ERROR_KEYS, payload
    assert payload["error_type"] == "validation"
    assert "less than or equal to 3" in payload["error"]


@pytest.mark.usefixtures("custom_tools")
@pytest.mark.parametrize("driver", DRIVERS)
async def test_raised_exception_becomes_compact_error(driver: Driver) -> None:
    """A custom tool's exception surfaces as the same compact error everywhere."""
    framework, invoke = driver
    payload = await invoke(_tool(framework, BOOM), {"q": "x"})
    assert set(payload) == COMPACT_ERROR_KEYS, payload
    assert payload["error"] == "boom"
    assert payload["error_type"] == "api"


# ---------------------------------------------------------------------------
# Schema contracts
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("custom_tools")
def test_tool_spec_schema_keeps_annotated_default() -> None:
    """The decorator records ``Annotated`` defaults without __future__ annotations."""
    spec = get_registry().get(MODES)
    assert spec is not None
    props = spec.input_schema["properties"]
    assert props["n"]["default"] == 2
    assert props["n"]["minimum"] == 1
    assert props["n"]["maximum"] == 3
    assert props["mode"]["enum"] == ["fast", "slow"]
    assert props["mode"]["default"] == "slow"
    assert spec.input_schema.get("required", []) == []


def _assert_rich_schema(schema: dict[str, Any]) -> None:
    props = schema["properties"]
    assert props["mode"]["enum"] == ["fast", "slow"]
    assert props["mode"]["default"] == "slow"
    assert props["n"]["minimum"] == 1
    assert props["n"]["maximum"] == 3
    assert props["n"]["default"] == 2
    assert props["n"]["description"] == "How many."
    assert not schema.get("required")


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
@pytest.mark.usefixtures("custom_tools")
def test_langchain_schema_keeps_enum_bounds_and_defaults() -> None:
    """LangChain sees the same argument schema the decorator built."""
    tool = _tool("langchain", MODES)
    _assert_rich_schema(tool.args_schema.model_json_schema())


@pytest.mark.skipif(not HAS_CREWAI, reason="CrewAI not installed")
@pytest.mark.usefixtures("custom_tools")
def test_crewai_schema_keeps_enum_bounds_and_defaults() -> None:
    """CrewAI sees the same argument schema the decorator built."""
    tool = _tool("crewai", MODES)
    _assert_rich_schema(tool.args_schema.model_json_schema())


@pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI Agents SDK not installed")
@pytest.mark.usefixtures("custom_tools")
def test_openai_schema_keeps_enum_and_bounds() -> None:
    """OpenAI's strict schema keeps enum and bounds (strict mode lists every field)."""
    props = _tool("openai", MODES).params_json_schema["properties"]
    assert props["mode"]["enum"] == ["fast", "slow"]
    assert props["n"]["minimum"] == 1
    assert props["n"]["maximum"] == 3


@pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed")
@pytest.mark.usefixtures("custom_tools")
def test_adk_declaration_keeps_enum_and_defaults() -> None:
    """ADK's function declaration is built from the real annotations.

    Numeric bounds are not asserted: ADK resolves annotations with
    ``get_type_hints`` without ``include_extras``, which strips
    ``Annotated`` constraints from every function tool, native or not.
    """
    tool = _tool("adk", MODES)
    declaration = tool._get_declaration()
    if declaration.parameters is not None:
        props = declaration.parameters.model_dump(exclude_none=True)["properties"]
        assert props["mode"]["enum"] == ["fast", "slow"]
    else:
        props = declaration.parameters_json_schema["properties"]
        assert props["mode"]["enum"] == ["fast", "slow"]
        assert props["mode"]["default"] == "slow"
        assert props["n"]["default"] == 2
    # The bounds are still on the wrapper's signature for ADK to use.
    import inspect

    assert "Ge(ge=1)" in str(inspect.signature(tool.func).parameters["n"].annotation)


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
@pytest.mark.usefixtures("custom_tools")
def test_langchain_rejects_out_of_range_argument() -> None:
    """Constraints are enforced before the tool function runs."""
    from pydantic import ValidationError

    tool = _tool("langchain", MODES)
    with pytest.raises(ValidationError):
        tool.invoke({"n": 7})


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
@pytest.mark.usefixtures("custom_tools")
def test_langchain_marks_failures_as_error_tool_messages() -> None:
    """Invoked with a ToolCall, a failure yields a ToolMessage with status='error'."""
    tool = _tool("langchain", BOOM)
    message = tool.invoke({"type": "tool_call", "id": "call-1", "name": BOOM, "args": {"q": "x"}})
    assert message.status == "error"
    assert json.loads(message.content)["error"] == "boom"
