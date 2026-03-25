from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.tools.read_document import read_document
from glean.api_client import models


def test_read_document_by_id_success() -> None:
    mock_result = {"content": {"text": "Hello world"}}

    with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
        mock_client = MagicMock()
        mock_client.client.documents.retrieve.return_value = mock_result
        mock_api_client.return_value.__enter__.return_value = mock_client

        result = read_document(document_id="glean_123")

        assert result == {"result": mock_result}
        mock_client.client.documents.retrieve.assert_called_once()
        sent = mock_client.client.documents.retrieve.call_args.kwargs["request"]
        assert isinstance(sent, models.GetDocumentsRequest)
        assert len(sent.document_specs) == 1
        assert isinstance(sent.document_specs[0], models.DocumentSpec2)
        assert sent.document_specs[0].id == "glean_123"
        assert models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT in (
            sent.include_fields or []
        )


def test_read_document_by_url_success() -> None:
    mock_result = {"content": {"text": "Hello world"}}

    with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
        mock_client = MagicMock()
        mock_client.client.documents.retrieve.return_value = mock_result
        mock_api_client.return_value.__enter__.return_value = mock_client

        result = read_document(url="https://docs.google.com/document/d/REDACTED")

        assert result == {"result": mock_result}
        mock_client.client.documents.retrieve.assert_called_once()
        sent = mock_client.client.documents.retrieve.call_args.kwargs["request"]
        assert isinstance(sent, models.GetDocumentsRequest)
        assert len(sent.document_specs) == 1
        assert isinstance(sent.document_specs[0], models.DocumentSpec1)
        assert sent.document_specs[0].url == "https://docs.google.com/document/d/REDACTED"
        assert models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT in (
            sent.include_fields or []
        )


def test_read_document_invalid_params() -> None:
    result = read_document()
    assert result["error"].startswith("Provide exactly one")

    result = read_document(document_id="glean_1", url="https://example.com")
    assert result["error"].startswith("Provide exactly one")


def test_read_document_api_exception() -> None:
    with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
        mock_client = MagicMock()
        mock_client.client.documents.retrieve.side_effect = Exception("API Error")
        mock_api_client.return_value.__enter__.return_value = mock_client

        result = read_document(url="https://unknown.example.com/abc")
        assert result["error"] == "API Error"
        assert result["result"] is None


def test_read_document_serializes_model_with_aliases() -> None:
    from pydantic import BaseModel, ConfigDict, Field

    class FakeResponse(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        full_text_list: list[str] = Field(alias="fullTextList")

    with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
        mock_client = MagicMock()
        mock_client.client.documents.retrieve.return_value = FakeResponse(
            fullTextList=["hello"]
        )
        mock_api_client.return_value.__enter__.return_value = mock_client

        result = read_document(document_id="glean_123")

        assert result.get("error") is None
        assert result["result"] == {"fullTextList": ["hello"]}
