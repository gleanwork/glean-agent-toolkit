"""Read Document tool for fetching full content by document ID or URL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

import glean.agent_toolkit.tools._common as common
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, _classify_error, make_error, make_ok
from glean.api_client import models
from glean.api_client.client_documents import ClientDocuments

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


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

    try:
        with client as g_client:
            documents_client: ClientDocuments = g_client.client.documents

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

            from glean.agent_toolkit.tools._compat import resolve_method

            retrieve_fn = resolve_method(documents_client, "retrieve", "get")
            result = retrieve_fn(request=request)

        return make_ok(common.serialize_tool_result(result))
    except Exception as e:
        error_type, suggested_action = _classify_error(e)
        return make_error(str(e), error_type, suggested_action)
