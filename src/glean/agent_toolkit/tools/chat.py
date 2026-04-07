"""Chat tool for conversational Q&A with Glean Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, make_error, make_ok, serialize_tool_result

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
            fragments.append(getattr(msg, "message_text", "") or "")
            for frag in getattr(msg, "fragments", []) or []:
                text = getattr(frag, "text", None)
                if text:
                    fragments.append(text)
    return "\n".join(f for f in fragments if f).strip()


def _extract_sources(response: Any) -> list[dict[str, Any]]:
    """Deduplicate and extract citation sources from the response."""
    messages = getattr(response, "messages", None) or []
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for msg in messages:
        for citation in getattr(msg, "citations", []) or []:
            doc = getattr(citation, "source_document", None)
            if doc is None:
                continue
            url = getattr(doc, "url", None) or ""
            if url and url not in seen:
                seen.add(url)
                entry = serialize_tool_result(doc) if hasattr(doc, "model_dump") else {"url": url}
                sources.append(entry)
    return sources


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
def glean_chat(
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
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()

    try:
        with client as g_client:
            response = g_client.client.chat.create(
                messages=[{"fragments": [{"text": message}]}],
            )

        answer = _extract_answer(response)
        sources = _extract_sources(response)
        chat_result = ChatResult(answer=answer, sources=sources)
        return make_ok(chat_result.model_dump())
    except Exception as e:
        from glean.agent_toolkit.tools._common import _classify_error

        error_type, suggested_action = _classify_error(e)
        return make_error(str(e), error_type, suggested_action)
