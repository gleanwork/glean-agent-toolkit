"""Live tool-level e2e tests: every built-in tool invoked against a real Glean instance.

Each test uses a cheap, deterministic-ish query and asserts the ToolResult
envelope plus the shape of the success payload. Feature-unavailable responses
skip with the server's reason; auth failures fail loudly (see _live.py).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from glean.agent_toolkit.tools import (
    calendar_search,
    code_search,
    employee_search,
    glean_chat,
    gmail_search,
    outlook_search,
    read_document,
    search,
    web_search,
)
from tests.e2e._live import skip_if_tools_call_payload_error, unwrap_ok_or_skip

pytestmark = pytest.mark.e2e

SEARCH_PAYLOAD_KEYS = {"results", "result_count", "has_more_results"}
SEARCH_RESULT_ITEM_KEYS = {"title", "url", "snippets", "datasource", "document_id"}


def _live_search(query: str = "glean", page_size: int = 5) -> dict[str, Any]:
    """Run glean_search live and return the shaped payload (or skip/fail)."""
    result = search(query=query, page_size=page_size)
    payload = unwrap_ok_or_skip(result, "glean_search")
    assert isinstance(payload, dict)
    assert set(payload) == SEARCH_PAYLOAD_KEYS
    return payload


def test_search_live() -> None:
    payload = _live_search()

    assert isinstance(payload["results"], list)
    assert payload["result_count"] == len(payload["results"])
    assert isinstance(payload["has_more_results"], bool)
    for item in payload["results"]:
        assert set(item) == SEARCH_RESULT_ITEM_KEYS
        assert isinstance(item["snippets"], list)


# CI-sentinel prefix (QA convention on the shared test instance) for anything
# that creates server-side artifacts. Chat is the only built-in that does
# (it creates a chat session); everything else in this suite is read-only.
E2E_SENTINEL = "gat-e2e-ci"


def test_chat_live() -> None:
    result = glean_chat(message=f"{E2E_SENTINEL}: In one short sentence, what is Glean used for?")
    payload = unwrap_ok_or_skip(result, "glean_chat")

    assert isinstance(payload, dict)
    assert set(payload) == {"answer", "sources"}
    assert isinstance(payload["answer"], str)
    assert payload["answer"].strip(), "glean_chat returned an empty answer"
    assert isinstance(payload["sources"], list)


def test_read_document_live() -> None:
    # Chain off a live search so the test adapts to whatever the instance indexes.
    search_payload = _live_search(page_size=10)
    document_ids = [
        item["document_id"] for item in search_payload["results"] if item.get("document_id")
    ]
    if not document_ids:
        pytest.skip("glean_read_document: live search returned no documents with IDs to read")

    result = read_document(document_id=document_ids[0])
    payload = unwrap_ok_or_skip(result, "glean_read_document")

    assert isinstance(payload, dict)
    documents = payload.get("documents")
    if not documents:
        pytest.skip(
            "glean_read_document: server returned no document content "
            "(queryapi.getDocuments may be disabled on this instance)"
        )
    assert isinstance(documents, dict)
    assert len(documents) >= 1


# Tools backed by the assistant-UI ``tools/call`` endpoint. Their payloads are
# server-shaped blobs, so shape assertions are intentionally loose: a
# non-empty dict with no tool-level error. Unknown/disabled tools surface as
# 4xx (skip via unwrap_ok_or_skip) or a 200 with an ``error`` field (skip via
# skip_if_tools_call_payload_error).
TOOLS_CALL_CASES: list[tuple[str, Callable[..., Any], str]] = [
    ("glean_employee_search", employee_search, "engineer"),
    ("glean_web_search", web_search, "what is the capital of France"),
    ("glean_calendar_search", calendar_search, "meeting"),
    ("glean_code_search", code_search, "def main"),
    ("glean_gmail_search", gmail_search, "meeting"),
    ("glean_outlook_search", outlook_search, "meeting"),
]


@pytest.mark.parametrize(
    ("tool_name", "tool_fn", "query"),
    TOOLS_CALL_CASES,
    ids=[case[0] for case in TOOLS_CALL_CASES],
)
def test_tools_call_backed_tool_live(
    tool_name: str, tool_fn: Callable[..., Any], query: str
) -> None:
    result = tool_fn(query=query)
    payload = unwrap_ok_or_skip(result, tool_name)

    skip_if_tools_call_payload_error(payload, tool_name)
    assert isinstance(payload, dict), f"{tool_name}: expected dict payload, got {type(payload)!r}"
    assert payload, f"{tool_name}: expected a non-empty payload"
