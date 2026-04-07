"""Tests for the Read Document tool."""

from unittest.mock import MagicMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.read_document import read_document
from glean.api_client import models


def _make_ctx(mock_client: MagicMock | None = None) -> GleanContext:
    if mock_client is None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
    return GleanContext(client=mock_client)


def test_read_document_by_id_success() -> None:
    mock_result = {"content": {"text": "Hello world"}}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.documents.retrieve.return_value = mock_result
    ctx = _make_ctx(mock_client)

    result = read_document(ctx, document_id="glean_123")

    assert result == {"result": mock_result}
    mock_client.client.documents.retrieve.assert_called_once()
    sent = mock_client.client.documents.retrieve.call_args.kwargs["request"]
    assert isinstance(sent, models.GetDocumentsRequest)
    assert len(sent.document_specs) == 1
    assert isinstance(sent.document_specs[0], models.DocumentSpec2)
    assert sent.document_specs[0].id == "glean_123"
    assert models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT in (sent.include_fields or [])


def test_read_document_by_url_success() -> None:
    mock_result = {"content": {"text": "Hello world"}}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.documents.retrieve.return_value = mock_result
    ctx = _make_ctx(mock_client)

    result = read_document(ctx, url="https://docs.google.com/document/d/REDACTED")

    assert result == {"result": mock_result}
    mock_client.client.documents.retrieve.assert_called_once()
    sent = mock_client.client.documents.retrieve.call_args.kwargs["request"]
    assert isinstance(sent, models.GetDocumentsRequest)
    assert len(sent.document_specs) == 1
    assert isinstance(sent.document_specs[0], models.DocumentSpec1)
    assert sent.document_specs[0].url == "https://docs.google.com/document/d/REDACTED"
    assert models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT in (sent.include_fields or [])


def test_read_document_invalid_params() -> None:
    result = read_document()
    assert result["error"].startswith("Provide exactly one")

    result = read_document(document_id="glean_1", url="https://example.com")
    assert result["error"].startswith("Provide exactly one")


def test_read_document_api_exception() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.documents.retrieve.side_effect = Exception("API Error")
    ctx = _make_ctx(mock_client)

    result = read_document(ctx, url="https://unknown.example.com/abc")
    assert result["error"] == "API Error"
    assert result["result"] is None


def test_read_document_serializes_model_with_aliases() -> None:
    from pydantic import BaseModel, ConfigDict, Field

    class FakeResponse(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        full_text_list: list[str] = Field(alias="fullTextList")

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.documents.retrieve.return_value = FakeResponse(fullTextList=["hello"])
    ctx = _make_ctx(mock_client)

    result = read_document(ctx, document_id="glean_123")

    assert result.get("error") is None
    assert result["result"] == {"fullTextList": ["hello"]}
