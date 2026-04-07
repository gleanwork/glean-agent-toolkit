"""Chat tool for conversing with Glean Assistant."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import api_client, serialize_tool_result


class ChatResult(BaseModel):
    """Typed response from Glean Chat."""

    answer: str
    sources: list[dict[str, Any]] = []


def _extract_answer(messages: list[Any]) -> str:
    """Extract the assistant's answer text from chat response messages.

    Concatenates text fragments from all GLEAN_AI-authored messages.
    """
    parts: list[str] = []
    for msg in messages:
        author = getattr(msg, "author", None)
        if author is not None and str(author) != "Author.GLEAN_AI":
            continue
        for frag in getattr(msg, "fragments", None) or []:
            text = getattr(frag, "text", None)
            if text:
                parts.append(text)
    return "\n".join(parts)


def _extract_sources(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract simplified source references from chat response citations."""
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for msg in messages:
        for citation in getattr(msg, "citations", None) or []:
            doc = getattr(citation, "source_document", None)
            if doc is None:
                continue
            title = getattr(doc, "title", None) or ""
            url = getattr(doc, "url", None) or ""
            key = url or title
            if not key or key in seen:
                continue
            seen.add(key)
            source: dict[str, Any] = {}
            if title:
                source["title"] = title
            if url:
                source["url"] = url
            datasource = getattr(doc, "datasource", None)
            if datasource:
                ds_name = getattr(datasource, "datasource_name", None) or getattr(
                    datasource, "instance", None
                )
                if ds_name:
                    source["datasource"] = ds_name
            if source:
                sources.append(source)
    return sources


@tool_spec(
    name="glean_chat",
    description=(
        "Ask Glean Assistant a question about company knowledge. "
        "Returns a synthesized answer with sources. "
        "Use for complex questions that need reasoning across multiple documents."
    ),
    output_model=ChatResult,
)
def chat(
    query: Annotated[
        str,
        Field(
            description="Question to ask Glean Assistant",
            examples=[
                "What is our company's remote work policy?",
                "Summarize the Q4 earnings report",
                "How does our authentication system work?",
            ],
        ),
    ],
) -> dict[str, Any]:
    """Ask Glean Assistant a question and get a synthesized answer.

    Args:
        query: The question to ask Glean Assistant
    """
    from glean.api_client import models

    try:
        with api_client() as g_client:
            response = g_client.client.chat.create(
                messages=[
                    models.ChatMessage(
                        author=models.Author.USER,
                        fragments=[models.ChatMessageFragment(text=query)],
                    ),
                ],
            )

        resp_messages = getattr(response, "messages", None) or []
        answer = _extract_answer(resp_messages)
        sources = _extract_sources(resp_messages)

        return {
            "result": ChatResult(answer=answer, sources=sources).model_dump(),
        }
    except ValueError as e:
        return {"error": f"Parameter validation error: {str(e)}", "result": None}
    except Exception as e:
        return {"error": str(e), "result": None}
