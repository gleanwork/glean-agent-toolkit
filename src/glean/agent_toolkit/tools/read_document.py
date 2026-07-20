"""Read Document tool for fetching full content by document ID or URL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

import glean.agent_toolkit.tools._common as common
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, make_error
from glean.agent_toolkit.tools._transport import TypedBackend, execute_tool, register_backend
from glean.api_client import Glean, models
from glean.api_client.client_documents import ClientDocuments

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


def _retrieve_documents(
    client: Glean,
    *,
    document_id: str | None = None,
    url: str | None = None,
) -> Any:
    """Perform the typed ``POST /rest/api/v1/getdocuments`` call."""
    documents_client: ClientDocuments = client.client.documents

    include_fields = [models.GetDocumentsRequestIncludeField.DOCUMENT_CONTENT]

    if document_id is not None:
        request = models.GetDocumentsRequest(
            document_specs=[models.DocumentSpec2(id=document_id)],
            include_fields=include_fields,
        )
    else:
        request = models.GetDocumentsRequest(
            document_specs=[models.DocumentSpec1(url=common.clean_query(url or ""))],
            include_fields=include_fields,
        )

    from glean.agent_toolkit.tools._compat import resolve_kwarg, resolve_method

    retrieve_fn = resolve_method(documents_client, "retrieve", "get")
    # glean-api-client renamed the kwarg from `request` (<=0.6.x) to
    # `get_documents_request` (>=0.15.x).
    request_kwarg = resolve_kwarg(retrieve_fn, "get_documents_request", "request")
    return retrieve_fn(**{request_kwarg: request})


register_backend("glean_read_document", TypedBackend(_retrieve_documents))


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
    if (document_id is not None and url is not None) or (document_id is None and url is None):
        return make_error(
            "Provide exactly one of document_id or url",
            error_type="validation",
            suggested_action="rephrase_query",
        )

    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    return execute_tool(
        "glean_read_document",
        {"document_id": document_id, "url": url},
        client=client,
    )
