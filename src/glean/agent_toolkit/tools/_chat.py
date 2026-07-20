"""Chat tool for conversational Q&A with Glean Assistant.

Lives in a private module (``_chat``) so that ``glean.agent_toolkit.tools.chat``
resolves to the tool *callable* rather than being shadowed by a submodule.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import (
    ToolResult,
    serialize_tool_result,
)
from glean.agent_toolkit.tools._transport import (
    TypedBackend,
    execute_tool,
    make_async_tool,
    register_backend,
)
from glean.api_client import Glean

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


class ChatResult(BaseModel):
    """Structured result from a Glean chat interaction."""

    answer: str
    sources: list[dict[str, Any]]


def _extract_answer(response: Any) -> str:
    """Extract the answer text from GLEAN_AI-authored message fragments."""
    messages = getattr(response, "messages", None) or []
    fragments: list[str] = []
    for msg in messages:
        author = getattr(msg, "author", None)
        if author == "GLEAN_AI":
            for frag in getattr(msg, "fragments", []) or []:
                text = getattr(frag, "text", None)
                if text:
                    fragments.append(text)
    return "\n".join(f for f in fragments if f).strip()


def _iter_citations(msg: Any) -> list[Any]:
    """Collect citations from a message, tolerating old and new SDK shapes.

    glean-api-client >= 0.15 attaches a ``citation`` to each
    ``ChatMessageFragment``; the message-level ``ChatMessage.citations`` list
    is deprecated (removal scheduled for 2026-10-15). Older SDKs only expose
    the message-level list. Prefer fragment-level citations and fall back to
    the legacy list when the fragments carry none.
    """
    citations = [
        citation
        for frag in getattr(msg, "fragments", None) or []
        if (citation := getattr(frag, "citation", None)) is not None
    ]
    if citations:
        return citations
    return list(getattr(msg, "citations", None) or [])


def _extract_sources(response: Any) -> list[dict[str, Any]]:
    """Deduplicate and extract citation sources from the response."""
    messages = getattr(response, "messages", None) or []
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for msg in messages:
        for citation in _iter_citations(msg):
            doc = getattr(citation, "source_document", None)
            if doc is None:
                continue
            url = getattr(doc, "url", None) or ""
            if url and url not in seen:
                seen.add(url)
                entry = serialize_tool_result(doc) if hasattr(doc, "model_dump") else {"url": url}
                sources.append(entry)
    return sources


def _create_chat(client: Glean, *, message: str) -> Any:
    """Perform the typed ``POST /rest/api/v1/chat`` call."""
    return client.client.chat.create(
        messages=[{"fragments": [{"text": message}]}],
    )


async def _create_chat_async(client: Glean, *, message: str) -> Any:
    """Native async twin of :func:`_create_chat` (``chat.create_async``)."""
    return await client.client.chat.create_async(
        messages=[{"fragments": [{"text": message}]}],
    )


def _shape_chat_response(response: Any) -> dict[str, Any]:
    """Shape a ``ChatResponse`` into the ``ChatResult`` payload."""
    answer = _extract_answer(response)
    sources = _extract_sources(response)
    return ChatResult(answer=answer, sources=sources).model_dump()


register_backend(
    "glean_chat",
    TypedBackend(_create_chat, _shape_chat_response, async_fn=_create_chat_async),
)


@tool_spec(
    name="glean_chat",
    description=(
        "Ask Glean Assistant a question and get an AI-generated answer "
        "grounded in company knowledge. Use this for complex questions "
        "that benefit from synthesis across multiple sources.\n"
        "INSTRUCTIONS:\n"
        "- Prefer glean_search for simple document lookup.\n"
        "- Use this tool when you need a synthesized, reasoned answer."
    ),
    output_model=ChatResult,
)
def chat(
    ctx: GleanContext | None = None,
    *,
    message: Annotated[
        str,
        Field(
            description="The question or message to send to Glean Assistant.",
            examples=[
                "What is our company's parental leave policy?",
                "Summarize the Q3 engineering roadmap.",
            ],
        ),
    ],
) -> ToolResult:
    """Send a message to Glean Assistant and return the answer with sources.

    Args:
        ctx: Optional Glean context for client injection.
        message: The question to ask Glean Assistant.
    """
    return execute_tool("glean_chat", {"message": message}, ctx=ctx)


chat.native_async(make_async_tool("glean_chat"))
