"""Read Document tool for fetching full content by document ID or URL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

import glean.agent_toolkit.tools._common as common
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, make_error
from glean.agent_toolkit.tools._transport import (
    TypedBackend,
    execute_tool,
    execute_tool_async,
    register_backend,
)
from glean.api_client import Glean, models
from glean.api_client.client_documents import ClientDocuments

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


def _build_get_documents_request(
    document_id: str | None,
    url: str | None,
) -> models.GetDocumentsRequest:
    """Build the ``GetDocumentsRequest`` for a document ID or URL spec."""
    include_fields = [models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT]

    if document_id is not None:
        return models.GetDocumentsRequest(
            document_specs=[models.DocumentSpec2(id=document_id)],
            include_fields=include_fields,
        )
    return models.GetDocumentsRequest(
        document_specs=[models.DocumentSpec1(url=common.clean_query(url or ""))],
        include_fields=include_fields,
    )


def _retrieve_documents(
    client: Glean,
    *,
    document_id: str | None = None,
    url: str | None = None,
) -> Any:
    """Perform the typed ``POST /rest/api/v1/getdocuments`` call."""
    documents_client: ClientDocuments = client.client.documents
    request = _build_get_documents_request(document_id, url)

    from glean.agent_toolkit.tools._compat import resolve_kwarg, resolve_method

    retrieve_fn = resolve_method(documents_client, "retrieve", "get")
    # glean-api-client renamed the kwarg from `request` (<=0.6.x) to
    # `get_documents_request` (>=0.15.x).
    request_kwarg = resolve_kwarg(retrieve_fn, "get_documents_request", "request")
    return retrieve_fn(**{request_kwarg: request})


async def _retrieve_documents_async(
    client: Glean,
    *,
    document_id: str | None = None,
    url: str | None = None,
) -> Any:
    """Native async twin of :func:`_retrieve_documents` (``documents.retrieve_async``)."""
    documents_client: ClientDocuments = client.client.documents
    request = _build_get_documents_request(document_id, url)

    from glean.agent_toolkit.tools._compat import resolve_kwarg, resolve_method

    retrieve_fn = resolve_method(documents_client, "retrieve_async", "get_async")
    request_kwarg = resolve_kwarg(retrieve_fn, "get_documents_request", "request")
    return await retrieve_fn(**{request_kwarg: request})


register_backend(
    "glean_read_document",
    TypedBackend(_retrieve_documents, async_fn=_retrieve_documents_async),
)


def _validate_exactly_one(document_id: str | None, url: str | None) -> ToolResult | None:
    """Return a validation error unless exactly one locator is provided."""
    if (document_id is not None and url is not None) or (document_id is None and url is None):
        return make_error(
            "Provide exactly one of document_id or url",
            error_type="validation",
            suggested_action="rephrase_query",
        )
    return None


@tool_spec(
    name="glean_read_document",
    description=(
        "Retrieve the full content of a document by its Glean ID or URL. "
        "Use after glean_search to read a specific result in full.\n"
        "INSTRUCTIONS:\n"
        "- Provide exactly one of document_id or url, not both.\n"
        "- Requires instance settings: queryapi.getDocuments.enabled and "
        "queryapi.getDocuments.content.enabled."
    ),
)
def read_document(
    ctx: GleanContext | None = None,
    *,
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
) -> ToolResult:
    """Fetch full document content using the Glean Client API.

    One of document_id or url must be provided. If both or neither are provided,
    an error will be returned.

    Args:
        ctx: Optional Glean context for client injection.
        document_id: Glean document ID.
        url: Document URL to resolve and read.
    """
    error = _validate_exactly_one(document_id, url)
    if error is not None:
        return error

    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    return execute_tool(
        "glean_read_document",
        {"document_id": document_id, "url": url},
        client=client,
    )


@read_document.native_async
async def _read_document_async(
    ctx: GleanContext | None = None,
    *,
    document_id: str | None = None,
    url: str | None = None,
) -> ToolResult:
    """Native async twin of :func:`read_document` (same validation, async seam)."""
    error = _validate_exactly_one(document_id, url)
    if error is not None:
        return error

    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    return await execute_tool_async(
        "glean_read_document",
        {"document_id": document_id, "url": url},
        client=ctx.get_client(),
    )
