"""Transport-level response contract tests for search, chat, and read_document.

The tests in tests/tools/* mock the Glean client with MagicMock identity
stubs, so they never prove the real ``glean-api-client`` can deserialize a
realistic API response. These tests mock at the HTTP layer (pytest-httpx)
with response JSON shaped like the real backend payloads and verify:

1. The outbound request body matches the wire contract of the endpoint.
2. Deserialization runs through the real SDK models
   (``SearchResponse``, ``ChatResponse``, ``GetDocumentsResponse``).
3. The tool returns a correct, fully structured ``ToolResult``.
"""

from __future__ import annotations

import json
from typing import Any

from pytest_httpx import HTTPXMock

from glean.agent_toolkit.tools import chat
from glean.agent_toolkit.tools.read_document import read_document
from glean.agent_toolkit.tools.search import search

BASE_URL = "https://test-instance-be.glean.com"
SEARCH_URL = f"{BASE_URL}/rest/api/v1/search"
CHAT_URL = f"{BASE_URL}/rest/api/v1/chat"
GET_DOCUMENTS_URL = f"{BASE_URL}/rest/api/v1/getdocuments"


def _request_body(httpx_mock: HTTPXMock) -> dict[str, Any]:
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    return json.loads(requests[0].content)


# ---------------------------------------------------------------------------
# search -> POST /rest/api/v1/search (SearchResponse)
# ---------------------------------------------------------------------------


REALISTIC_SEARCH_RESPONSE: dict[str, Any] = {
    "results": [
        {
            "title": "Q3 Financial Results",
            "url": "https://drive.google.com/file/d/abc123",
            "document": {
                "id": "doc-1",
                "datasource": "gdrive",
                "title": "Q3 Financial Results",
                "url": "https://drive.google.com/file/d/abc123",
            },
            "snippets": [
                {"text": "Revenue grew 18% quarter over quarter.", "mimeType": "text/plain"}
            ],
        },
        {
            "title": "Q3 Board Deck",
            "url": "https://docs.google.com/presentation/d/def456",
            "document": {"id": "doc-2", "datasource": "gdrive"},
            "snippets": [{"text": "Q3 highlights and FY outlook."}],
        },
    ],
    "trackingToken": "tracking-token-1",
    "hasMoreResults": False,
    "backendTimeMillis": 42,
}


def test_search_deserializes_realistic_search_response(httpx_mock: HTTPXMock) -> None:
    """A realistic SearchResponse round-trips into the shaped ToolResult."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json=REALISTIC_SEARCH_RESPONSE,
    )

    result = search(query="quarterly financial results", page_size=2)

    assert result["status"] == "ok"
    assert result["error"] is None

    payload = result["result"]
    assert payload["result_count"] == 2
    assert payload["has_more_results"] is False
    assert payload["results"][0] == {
        "title": "Q3 Financial Results",
        "url": "https://drive.google.com/file/d/abc123",
        "snippets": ["Revenue grew 18% quarter over quarter."],
        "datasource": "gdrive",
        "document_id": "doc-1",
    }

    body = _request_body(httpx_mock)
    assert body["query"] == "quarterly financial results"
    assert body["pageSize"] == 2
    assert "requestOptions" not in body


def test_search_sends_datasources_and_filters_on_the_wire(httpx_mock: HTTPXMock) -> None:
    """Structured args map to requestOptions on the typed endpoint."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"results": []},
    )

    filters = [
        {"field": "type", "values": ["Presentation"]},
        {"field": "from", "values": ["bot"], "exclude": True},
    ]
    result = search(query="sprint tasks", datasources=["jira", "confluence"], filters=filters)

    assert result["status"] == "ok"
    assert result["result"] == {"results": [], "result_count": 0, "has_more_results": False}

    body = _request_body(httpx_mock)
    options = body["requestOptions"]
    assert options["datasourcesFilter"] == ["jira", "confluence"]
    assert options["facetFilters"] == [
        {
            "fieldName": "type",
            "values": [{"value": "Presentation", "relationType": "EQUALS"}],
        },
        {
            "fieldName": "from",
            "values": [{"value": "bot", "relationType": "NOT_EQUALS"}],
        },
    ]


def test_search_http_401_maps_to_auth_error(httpx_mock: HTTPXMock) -> None:
    """A 401 from the transport becomes a classified error ToolResult.

    401 is deliberately used here because the SDK retries 429/5xx with
    backoff; 401 fails fast.
    """
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        status_code=401,
        json={"error": "Invalid token"},
    )

    result = search(query="anything")

    assert result["status"] == "error"
    assert result["result"] is None
    assert result["error_type"] == "auth"
    assert result["suggested_action"] == "check_credentials"
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# glean_chat -> POST /rest/api/v1/chat (ChatResponse)
# ---------------------------------------------------------------------------


REALISTIC_CHAT_RESPONSE: dict[str, Any] = {
    "messages": [
        {
            "author": "USER",
            "messageType": "CONTENT",
            "fragments": [{"text": "What is our parental leave policy?"}],
        },
        {
            "author": "GLEAN_AI",
            "messageType": "CONTENT",
            "fragments": [
                {"text": "Parental leave is 16 weeks, "},
                {"text": "fully paid for all new parents."},
            ],
            "citations": [
                {
                    "sourceDocument": {
                        "id": "doc-policy-1",
                        "title": "Parental Leave Policy",
                        "url": "https://wiki.example.com/hr/parental-leave",
                        "datasource": "confluence",
                    }
                },
                {
                    # Duplicate URL: must be deduplicated in sources.
                    "sourceDocument": {
                        "id": "doc-policy-1",
                        "title": "Parental Leave Policy",
                        "url": "https://wiki.example.com/hr/parental-leave",
                    }
                },
                {
                    "sourceDocument": {
                        "id": "doc-policy-2",
                        "title": "Benefits Overview",
                        "url": "https://wiki.example.com/hr/benefits",
                    }
                },
            ],
        },
    ],
    "chatId": "chat-456",
    "followUpPrompts": ["How do I request leave?"],
    "backendTimeMillis": 1234,
}


def test_chat_deserializes_realistic_chat_response(httpx_mock: HTTPXMock) -> None:
    """Fragments and citations from a realistic /chat payload are extracted."""
    httpx_mock.add_response(method="POST", url=CHAT_URL, json=REALISTIC_CHAT_RESPONSE)

    result = chat(message="What is our parental leave policy?")

    assert result["status"] == "ok"
    assert result["error"] is None

    chat_result = result["result"]
    # Only GLEAN_AI-authored fragments contribute to the answer.
    assert "Parental leave is 16 weeks," in chat_result["answer"]
    assert "fully paid for all new parents." in chat_result["answer"]
    assert "What is our parental leave policy?" not in chat_result["answer"]

    # Citations are deduplicated by URL and serialized with aliases.
    urls = [source["url"] for source in chat_result["sources"]]
    assert urls == [
        "https://wiki.example.com/hr/parental-leave",
        "https://wiki.example.com/hr/benefits",
    ]
    assert chat_result["sources"][0]["title"] == "Parental Leave Policy"

    body = _request_body(httpx_mock)
    fragments = body["messages"][0]["fragments"]
    assert fragments == [{"text": "What is our parental leave policy?"}]


def test_chat_response_without_citations_yields_empty_sources(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=CHAT_URL,
        json={
            "messages": [
                {
                    "author": "GLEAN_AI",
                    "messageType": "CONTENT",
                    "fragments": [{"text": "I could not find anything relevant."}],
                }
            ]
        },
    )

    result = chat(message="Something obscure")

    assert result["status"] == "ok"
    assert result["result"]["answer"] == "I could not find anything relevant."
    assert result["result"]["sources"] == []


# ---------------------------------------------------------------------------
# read_document -> POST /rest/api/v1/getdocuments (GetDocumentsResponse)
# ---------------------------------------------------------------------------


REALISTIC_DOCUMENTS_RESPONSE: dict[str, Any] = {
    "documents": {
        "glean_15349475685754208208": {
            "id": "glean_15349475685754208208",
            "title": "Engineering Onboarding Guide",
            "url": "https://docs.google.com/document/d/onboarding",
            "datasource": "gdrive",
            "docType": "document",
            "content": {
                "fullTextList": [
                    "Welcome to the engineering team.",
                    "Start with the environment setup runbook.",
                ]
            },
            "metadata": {
                "author": {"name": "Test User", "obfuscatedId": "abc123"},
                "createTime": "2025-01-15T09:30:00Z",
            },
        }
    }
}


def test_read_document_by_id_deserializes_realistic_response(httpx_mock: HTTPXMock) -> None:
    """A realistic getdocuments payload round-trips through the SDK models."""
    httpx_mock.add_response(
        method="POST",
        url=GET_DOCUMENTS_URL,
        json=REALISTIC_DOCUMENTS_RESPONSE,
    )

    result = read_document(document_id="glean_15349475685754208208")

    assert result["status"] == "ok"
    assert result["error"] is None

    document = result["result"]["documents"]["glean_15349475685754208208"]
    assert document["title"] == "Engineering Onboarding Guide"
    assert document["datasource"] == "gdrive"
    # camelCase alias must be preserved through serialize_tool_result.
    assert document["content"]["fullTextList"] == [
        "Welcome to the engineering team.",
        "Start with the environment setup runbook.",
    ]

    body = _request_body(httpx_mock)
    assert body["documentSpecs"] == [{"id": "glean_15349475685754208208"}]
    assert body["includeFields"] == ["DOCUMENT_CONTENT"]


def test_read_document_by_url_sends_url_spec(httpx_mock: HTTPXMock) -> None:
    doc_url = "https://docs.google.com/document/d/onboarding"
    httpx_mock.add_response(
        method="POST",
        url=GET_DOCUMENTS_URL,
        json=REALISTIC_DOCUMENTS_RESPONSE,
    )

    result = read_document(url=f"  {doc_url}  ")  # cleaned before hitting the wire

    assert result["status"] == "ok"

    body = _request_body(httpx_mock)
    assert body["documentSpecs"] == [{"url": doc_url}]


def test_read_document_not_found_error_entry(httpx_mock: HTTPXMock) -> None:
    """A per-document error entry deserializes as DocumentOrError."""
    httpx_mock.add_response(
        method="POST",
        url=GET_DOCUMENTS_URL,
        json={"documents": {"glean_missing": {"error": "Document not found"}}},
    )

    result = read_document(document_id="glean_missing")

    assert result["status"] == "ok"
    assert result["result"]["documents"]["glean_missing"] == {"error": "Document not found"}
