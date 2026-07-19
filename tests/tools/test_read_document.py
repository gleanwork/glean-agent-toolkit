"""Tests for the Read Document tool."""

from unittest.mock import MagicMock

from pydantic import BaseModel, ConfigDict, Field

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.read_document import read_document
from glean.api_client import models


def _make_ctx(
    *,
    documents_return: object = None,
    documents_side_effect: Exception | None = None,
) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    if documents_side_effect is not None:
        mock_client.client.documents.retrieve.side_effect = documents_side_effect
    else:
        mock_client.client.documents.retrieve.return_value = documents_return
    return GleanContext(client=mock_client)


def _sent_request(mock_retrieve: MagicMock) -> object:
    """Extract the request model regardless of which kwarg name was used."""
    kwargs = mock_retrieve.call_args.kwargs
    return kwargs.get("get_documents_request", kwargs.get("request"))


def test_read_document_by_id_success() -> None:
    mock_result = {"content": {"text": "Hello world"}}
    ctx = _make_ctx(documents_return=mock_result)

    result = read_document(ctx, document_id="glean_123")

    assert result["status"] == "ok"
    assert result["result"] == mock_result
    assert result["error"] is None

    mock_client = ctx.get_client()
    mock_client.client.documents.retrieve.assert_called_once()  # type: ignore[union-attr]
    sent = _sent_request(mock_client.client.documents.retrieve)  # type: ignore[union-attr,arg-type]
    assert isinstance(sent, models.GetDocumentsRequest)
    assert len(sent.document_specs) == 1
    assert isinstance(sent.document_specs[0], models.DocumentSpec2)
    assert sent.document_specs[0].id == "glean_123"
    assert models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT in (
        sent.include_fields or []
    )


def test_read_document_by_url_success() -> None:
    mock_result = {"content": {"text": "Hello world"}}
    ctx = _make_ctx(documents_return=mock_result)

    result = read_document(ctx, url="https://docs.google.com/document/d/REDACTED")

    assert result["status"] == "ok"
    assert result["result"] == mock_result
    assert result["error"] is None

    mock_client = ctx.get_client()
    mock_client.client.documents.retrieve.assert_called_once()  # type: ignore[union-attr]
    sent = _sent_request(mock_client.client.documents.retrieve)  # type: ignore[union-attr,arg-type]
    assert isinstance(sent, models.GetDocumentsRequest)
    assert len(sent.document_specs) == 1
    assert isinstance(sent.document_specs[0], models.DocumentSpec1)
    assert sent.document_specs[0].url == "https://docs.google.com/document/d/REDACTED"
    assert models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT in (
        sent.include_fields or []
    )


def test_read_document_invalid_params() -> None:
    result = read_document()
    assert result["status"] == "error"
    assert result["error"].startswith("Provide exactly one")
    assert result["error_type"] == "validation"
    assert result["suggested_action"] == "rephrase_query"

    result = read_document(document_id="glean_1", url="https://example.com")
    assert result["status"] == "error"
    assert result["error"].startswith("Provide exactly one")
    assert result["error_type"] == "validation"


def test_read_document_api_exception() -> None:
    ctx = _make_ctx(documents_side_effect=Exception("API Error"))

    result = read_document(ctx, url="https://unknown.example.com/abc")

    assert result["status"] == "error"
    assert result["error"] == "API Error"
    assert result["result"] is None
    assert result["error_type"] == "api"
    assert result["suggested_action"] == "retry"


def test_read_document_serializes_model_with_aliases() -> None:
    class FakeResponse(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        full_text_list: list[str] = Field(alias="fullTextList")

    ctx = _make_ctx(documents_return=FakeResponse(fullTextList=["hello"]))

    result = read_document(ctx, document_id="glean_123")

    assert result["status"] == "ok"
    assert result.get("error") is None
    assert result["result"] == {"fullTextList": ["hello"]}


class _NewStyleDocuments:
    """Simulates glean-api-client >=0.15.x: retrieve(*, get_documents_request)."""

    def __init__(self) -> None:
        self.requests: list[object] = []

    def retrieve(self, *, get_documents_request: object) -> object:
        self.requests.append(get_documents_request)
        return {"content": {"text": "new-style"}}


class _OldStyleDocuments:
    """Simulates glean-api-client 0.6.x: retrieve(*, request)."""

    def __init__(self) -> None:
        self.requests: list[object] = []

    def retrieve(self, *, request: object) -> object:
        self.requests.append(request)
        return {"content": {"text": "old-style"}}


def _make_ctx_with_documents(documents: object) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.documents = documents
    return GleanContext(client=mock_client)


def test_read_document_new_sdk_kwarg() -> None:
    """retrieve accepting only get_documents_request (>=0.15.x) must work."""
    documents = _NewStyleDocuments()
    ctx = _make_ctx_with_documents(documents)

    result = read_document(ctx, document_id="glean_123")

    assert result["status"] == "ok"
    assert result["result"] == {"content": {"text": "new-style"}}
    assert len(documents.requests) == 1
    sent = documents.requests[0]
    assert isinstance(sent, models.GetDocumentsRequest)
    spec = sent.document_specs[0]
    assert isinstance(spec, models.DocumentSpec2)
    assert spec.id == "glean_123"


def test_read_document_old_sdk_kwarg() -> None:
    """retrieve accepting only request (0.6.x) must still work."""
    documents = _OldStyleDocuments()
    ctx = _make_ctx_with_documents(documents)

    result = read_document(ctx, document_id="glean_123")

    assert result["status"] == "ok"
    assert result["result"] == {"content": {"text": "old-style"}}
    assert len(documents.requests) == 1
    sent = documents.requests[0]
    assert isinstance(sent, models.GetDocumentsRequest)
    spec = sent.document_specs[0]
    assert isinstance(spec, models.DocumentSpec2)
    assert spec.id == "glean_123"
