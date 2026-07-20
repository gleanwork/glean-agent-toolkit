"""Cross-framework invocation contract matrix.

Parametrizes ALL built-in tools across every supported framework
(LangChain, OpenAI Agents SDK, CrewAI, Google ADK) and drives each
converted tool through the framework's own native invocation path with
the Glean HTTP layer mocked at the transport level via pytest-httpx.

Each matrix cell asserts three contracts:

1. Invocation succeeds through the framework layer (no adapter glue is
   bypassed -- ``tool.invoke``/``ainvoke`` for LangChain,
   ``on_invoke_tool`` for OpenAI Agents, ``run_async`` for ADK, and
   ``tool.run`` for CrewAI).
2. The caller's arguments arrive in the outbound HTTP request body,
   mapped to the correct wire format for the endpoint the tool hits.
3. A structured ``ToolResult``-shaped payload comes back through the
   framework layer with the response payload intact.

The per-fix regression tests (test_langchain_invocation.py and friends)
mock at the ``run_tool`` seam; this matrix goes one layer deeper and
exercises the real ``glean-api-client`` request/response cycle.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from glean.agent_toolkit import get_tools

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


BASE_URL = "https://test-instance-be.glean.com"
TOOLS_CALL_URL = f"{BASE_URL}/rest/api/v1/tools/call"
SEARCH_URL = f"{BASE_URL}/rest/api/v1/search"
CHAT_URL = f"{BASE_URL}/rest/api/v1/chat"
GET_DOCUMENTS_URL = f"{BASE_URL}/rest/api/v1/getdocuments"

TOOL_RESULT_KEYS = {"status", "result", "error", "error_type", "suggested_action"}


# ---------------------------------------------------------------------------
# Tool cases: one per built-in tool
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolCase:
    """One row of the matrix: a built-in tool plus its wire-level contract."""

    tool_name: str
    args: dict[str, Any]
    url: str
    response_json: dict[str, Any]
    # (request_body) -> None; asserts the invocation args reached the wire.
    check_request: Callable[[dict[str, Any]], None]
    # (tool_result["result"]) -> None; asserts the response payload survived.
    check_result: Callable[[Any], None]


def _tools_call_case(
    tool_name: str,
    display_name: str,
    args: dict[str, Any],
    expected_params: dict[str, str],
) -> ToolCase:
    """Build a case for a tool backed by POST /rest/api/v1/tools/call."""
    raw_response = {
        "results": [
            {
                "title": f"{tool_name} result",
                "url": f"https://example.com/{tool_name}",
                "snippets": [{"snippet": f"Snippet for {tool_name}."}],
            }
        ]
    }

    def check_request(body: dict[str, Any]) -> None:
        assert body["name"] == display_name
        for param_name, expected_value in expected_params.items():
            wire_param = body["parameters"][param_name]
            assert wire_param["name"] == param_name
            assert wire_param["value"] == expected_value

    def check_result(result: Any) -> None:
        # serialize_tool_result preserves camelCase aliases from the SDK model.
        assert result["rawResponse"] == raw_response
        # Older glean-api-client versions (e.g. 0.6.x) dump unset optional
        # fields as explicit None ("error": None); newer versions omit them.
        # Accept both: the contract is "no tool-level error".
        assert result.get("error") is None

    return ToolCase(
        tool_name=tool_name,
        args=args,
        url=TOOLS_CALL_URL,
        response_json={"rawResponse": raw_response},
        check_request=check_request,
        check_result=check_result,
    )


def _search_case() -> ToolCase:
    """Build the case for glean_search (typed POST /rest/api/v1/search)."""
    query = "quarterly financial results"

    def check_request(body: dict[str, Any]) -> None:
        assert body["query"] == query
        assert body["pageSize"] == 5

    def check_result(result: Any) -> None:
        assert result["result_count"] == 1
        assert result["has_more_results"] is False
        assert result["results"] == [
            {
                "title": "Q3 Financial Results",
                "url": "https://drive.example.com/doc/abc123",
                "snippets": ["Revenue grew 18% quarter over quarter."],
                "datasource": "gdrive",
                "document_id": "doc-1",
            }
        ]

    return ToolCase(
        tool_name="glean_search",
        args={"query": query, "page_size": 5},
        url=SEARCH_URL,
        response_json={
            "results": [
                {
                    "title": "Q3 Financial Results",
                    "url": "https://drive.example.com/doc/abc123",
                    "document": {"id": "doc-1", "datasource": "gdrive"},
                    "snippets": [{"text": "Revenue grew 18% quarter over quarter."}],
                }
            ],
            "hasMoreResults": False,
        },
        check_request=check_request,
        check_result=check_result,
    )


def _chat_case() -> ToolCase:
    message = "What is our vacation policy?"
    answer = "The vacation policy grants 20 days per year."
    source_url = "https://wiki.example.com/policies/vacation"

    def check_request(body: dict[str, Any]) -> None:
        assert body["messages"][0]["fragments"][0]["text"] == message

    def check_result(result: Any) -> None:
        assert answer in result["answer"]
        assert [source["url"] for source in result["sources"]] == [source_url]

    return ToolCase(
        tool_name="glean_chat",
        args={"message": message},
        url=CHAT_URL,
        response_json={
            "messages": [
                {
                    "author": "GLEAN_AI",
                    "messageType": "CONTENT",
                    "fragments": [{"text": answer}],
                    "citations": [
                        {
                            "sourceDocument": {
                                "id": "doc-1",
                                "title": "Vacation Policy",
                                "url": source_url,
                            }
                        }
                    ],
                }
            ],
            "chatId": "chat-123",
        },
        check_request=check_request,
        check_result=check_result,
    )


def _read_document_case() -> ToolCase:
    document_id = "glean_123456789"
    full_text = "Welcome to the onboarding guide."

    def check_request(body: dict[str, Any]) -> None:
        assert body["documentSpecs"] == [{"id": document_id}]
        assert "DOCUMENT_CONTENT" in body["includeFields"]

    def check_result(result: Any) -> None:
        document = result["documents"][document_id]
        assert document["title"] == "Onboarding Guide"
        assert document["content"]["fullTextList"] == [full_text]

    return ToolCase(
        tool_name="glean_read_document",
        args={"document_id": document_id},
        url=GET_DOCUMENTS_URL,
        response_json={
            "documents": {
                document_id: {
                    "id": document_id,
                    "title": "Onboarding Guide",
                    "url": "https://docs.example.com/onboarding",
                    "content": {"fullTextList": [full_text]},
                }
            }
        },
        check_request=check_request,
        check_result=check_result,
    )


TOOL_CASES: list[ToolCase] = [
    # Multi-arg case: query + page_size must both reach the wire (typed endpoint).
    _search_case(),
    _tools_call_case(
        "glean_web_search",
        "Gemini Web Search",
        args={"query": "latest AI news"},
        expected_params={"query": "latest AI news"},
    ),
    _tools_call_case(
        "glean_calendar_search",
        "Meeting Lookup",
        args={"query": "sprint planning meeting"},
        expected_params={"query": "sprint planning meeting"},
    ),
    _tools_call_case(
        "glean_employee_search",
        "Employee Search",
        args={"query": "engineering managers"},
        expected_params={"query": "engineering managers"},
    ),
    _tools_call_case(
        "glean_code_search",
        "Code Search",
        args={"query": "class UserManager"},
        expected_params={"query": "class UserManager"},
    ),
    _tools_call_case(
        "glean_gmail_search",
        "Gmail Search",
        args={"query": "from:boss@company.com is:unread"},
        expected_params={"query": "from:boss@company.com is:unread"},
    ),
    _tools_call_case(
        "glean_outlook_search",
        "Outlook Search",
        args={"query": "importance:high project updates"},
        expected_params={"query": "importance:high project updates"},
    ),
    _chat_case(),
    _read_document_case(),
]

TOOL_CASE_IDS = [case.tool_name for case in TOOL_CASES]


# ---------------------------------------------------------------------------
# Framework drivers: one per native invocation path
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrameworkDriver:
    """One column of the matrix: a framework plus its native invocation path."""

    framework: str
    # (converted_tool, args) -> parsed ToolResult dict.
    invoke: Callable[[Any, dict[str, Any]], Awaitable[dict[str, Any]]]
    # Whether the driver exercises the tool's async path. Async cells also
    # assert the NATIVE async chain: asyncio.to_thread is poisoned, so any
    # hidden sync-in-a-thread round-trip fails the cell.
    is_async: bool = False


async def _invoke_langchain(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    output = tool.invoke(dict(args))
    assert isinstance(output, str)
    return json.loads(output)


async def _invoke_langchain_async(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    output = await tool.ainvoke(dict(args))
    assert isinstance(output, str)
    return json.loads(output)


async def _invoke_openai(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    ctx_stub = SimpleNamespace()  # the adapter ignores the SDK run context
    output = await tool.on_invoke_tool(ctx_stub, json.dumps(args))
    assert isinstance(output, str)
    return json.loads(output)


async def _invoke_crewai(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    output = tool.run(**args)
    assert isinstance(output, str)
    return json.loads(output)


async def _invoke_adk(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    result = await tool.run_async(args=dict(args), tool_context=None)
    assert isinstance(result, dict)
    return result


FRAMEWORK_DRIVERS = [
    pytest.param(
        FrameworkDriver("langchain", _invoke_langchain),
        id="langchain-invoke",
        marks=pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed"),
    ),
    pytest.param(
        FrameworkDriver("langchain", _invoke_langchain_async, is_async=True),
        id="langchain-ainvoke",
        marks=pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed"),
    ),
    pytest.param(
        FrameworkDriver("openai", _invoke_openai, is_async=True),
        id="openai-on_invoke_tool",
        marks=pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI Agents SDK not installed"),
    ),
    pytest.param(
        FrameworkDriver("crewai", _invoke_crewai),
        id="crewai-run",
        marks=pytest.mark.skipif(not HAS_CREWAI, reason="CrewAI not installed"),
    ),
    pytest.param(
        FrameworkDriver("adk", _invoke_adk, is_async=True),
        id="adk-run_async",
        marks=pytest.mark.skipif(not HAS_ADK, reason="Google ADK not installed"),
    ),
]


# ---------------------------------------------------------------------------
# The matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", TOOL_CASES, ids=TOOL_CASE_IDS)
@pytest.mark.parametrize("driver", FRAMEWORK_DRIVERS)
async def test_invocation_matrix(
    driver: FrameworkDriver,
    case: ToolCase,
    httpx_mock: HTTPXMock,
    request: pytest.FixtureRequest,
) -> None:
    """Every built-in tool must be invocable through every framework."""
    httpx_mock.add_response(method="POST", url=case.url, json=case.response_json)

    if driver.is_async:
        # Built-in tools promise a NATIVE async chain: framework async
        # invocation -> tool async twin -> execute_tool_async -> the SDK's
        # *_async methods. The fixture poisons asyncio.to_thread and the
        # sync HTTP client, so this cell fails if the async path secretly
        # runs the sync client in a worker thread.
        request.getfixturevalue("no_thread_roundtrip")

    tools = get_tools(driver.framework, include=[case.tool_name])
    assert len(tools) == 1, f"{case.tool_name} missing from get_tools({driver.framework!r})"
    tool = tools[0]

    # (a) Invocation succeeds through the framework's native path.
    tool_result = await driver.invoke(tool, case.args)

    # (c) A structured ToolResult-shaped payload returns.
    assert set(tool_result) == TOOL_RESULT_KEYS
    assert tool_result["status"] == "ok", tool_result
    assert tool_result["error"] is None
    assert tool_result["error_type"] is None
    assert tool_result["suggested_action"] is None
    case.check_result(tool_result["result"])

    # (b) The invocation arguments arrived in the outbound HTTP request body.
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    http_request = requests[0]
    assert http_request.method == "POST"
    assert str(http_request.url) == case.url
    assert http_request.headers["authorization"].startswith("Bearer ")
    case.check_request(json.loads(http_request.content))
