"""Read Document tool for fetching full content by document ID or URL."""

from __future__ import annotations

from typing import Annotated, TypedDict

from pydantic import Field

import glean.agent_toolkit.tools._common as common
from glean.agent_toolkit.decorators import tool_spec
from glean.api_client import models
from glean.api_client.client_documents import ClientDocuments


class ReadDocumentSuccess(TypedDict):
    """Successful read document result payload."""

    result: models.GetDocumentsResponse


class ReadDocumentError(TypedDict):
    """Error result payload for read document."""

    error: str
    result: None


@tool_spec(
    name="read_document",
    description=(
        "Read the full content of a specific document by ID or URL.\n"
        "INSTRUCTIONS:\n"
        "- Provide exactly one of document_id or url.\n"
        "- The tool requires instance settings: queryapi.getDocuments.enabled and "
        "queryapi.getDocuments.content.enabled."
    ),
)
def read_document(
    document_id: Annotated[
        str | None,
        Field(
            description="Glean document ID (e.g., glean_123456789)",
            examples=["glean_15349475685754208208"],
        ),
    ] = None,
    url: Annotated[
        str | None,
        Field(
            description="Document URL to resolve and read",
            examples=[
                "https://docs.google.com/document/d/REDACTED",
                "https://company.slack.com/archives/C123/p1234567890",
            ],
        ),
    ] = None,
) -> ReadDocumentSuccess | ReadDocumentError:
    """Fetch full document content using the Glean Client API.

    One of document_id or url must be provided. If both or neither are provided,
    an error will be returned.
    """
    if bool(document_id) == bool(url):
        return {
            "error": "Provide exactly one of document_id or url",
            "result": None,
        }

    try:
        with common.api_client() as g_client:
            documents_client: ClientDocuments = g_client.client.documents

            include_fields = [models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT]

            if document_id:
                did = common.clean_query(document_id)
                request = models.GetDocumentsRequest(
                    document_specs=[models.DocumentSpec2(id=did)],
                    include_fields=include_fields,
                )
            else:
                request = models.GetDocumentsRequest(
                    document_specs=[models.DocumentSpec1(url=common.clean_query(url or ""))],
                    include_fields=include_fields,
                )

            result = documents_client.retrieve(request=request)

        return {"result": result}
    except Exception as e:
        return {"error": str(e), "result": None}
