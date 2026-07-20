"""Tests for the Chat tool."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.chat import ChatResult, glean_chat
from glean.api_client import models

# Feature detection mirroring the version-tolerant extraction in chat.py:
# glean-api-client >= 0.15 adds ChatMessageFragment.citation (new API) and
# deprecates ChatMessage.citations (removal scheduled 2026-10-15). Older SDKs
# (e.g. 0.6.0) only have the message-level list.
_FRAGMENT_HAS_CITATION = "citation" in models.ChatMessageFragment.model_fields
_MESSAGE_HAS_CITATIONS = "citations" in models.ChatMessage.model_fields

# Typed as Any because pyright checks constructor calls against the installed
# SDK's declarations, while these builders pass fields that only some
# supported SDK versions declare; the runtime feature-detection guards above
# ensure only valid shapes are constructed.
_ChatMessage: Any = models.ChatMessage
_ChatMessageFragment: Any = models.ChatMessageFragment


def _make_citation(url: str) -> models.ChatMessageCitation:
    """Build a real SDK citation wrapping a real Document."""
    return models.ChatMessageCitation(source_document=models.Document(url=url))


def _make_fragment_citation_message(text: str, urls: list[str]) -> object:
    """Build a GLEAN_AI message carrying citations on its fragments (new API)."""
    if _FRAGMENT_HAS_CITATION:
        fragments = [_ChatMessageFragment(text=text)] + [
            _ChatMessageFragment(citation=_make_citation(url)) for url in urls
        ]
        return _ChatMessage(author="GLEAN_AI", fragments=fragments)
    # Installed SDK predates ChatMessageFragment.citation; use stand-ins for
    # the fragment/message shape (citation and document stay real models).
    fragments = [SimpleNamespace(text=text)] + [
        SimpleNamespace(citation=_make_citation(url)) for url in urls
    ]
    return SimpleNamespace(author="GLEAN_AI", fragments=fragments)


def _make_message_citation_message(text: str, urls: list[str]) -> object:
    """Build a GLEAN_AI message carrying message-level citations (legacy API)."""
    citations = [_make_citation(url) for url in urls]
    if _MESSAGE_HAS_CITATIONS:
        return _ChatMessage(
            author="GLEAN_AI",
            fragments=[_ChatMessageFragment(text=text)],
            citations=citations,
        )
    # Installed SDK has removed the deprecated ChatMessage.citations list
    # (post 2026-10-15); use a stand-in to keep exercising the legacy path.
    return SimpleNamespace(
        author="GLEAN_AI",
        fragments=[SimpleNamespace(text=text)],
        citations=citations,
    )


def _make_chat_response(
    answer_text: str = "The answer is 42.",
    sources: list | None = None,
) -> SimpleNamespace:
    """Build a fake chat API response."""
    source_doc = SimpleNamespace(url="https://wiki.example.com/doc1")
    citation = SimpleNamespace(source_document=source_doc)

    msg = SimpleNamespace(
        author="GLEAN_AI",
        fragments=[SimpleNamespace(text=answer_text)],
        citations=sources if sources is not None else [citation],
    )
    return SimpleNamespace(messages=[msg])


def _make_ctx(
    chat_return: object = None,
    chat_side_effect: Exception | None = None,
) -> GleanContext:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    if chat_side_effect is not None:
        mock_client.client.chat.create.side_effect = chat_side_effect
    else:
        mock_client.client.chat.create.return_value = (
            chat_return if chat_return is not None else _make_chat_response()
        )
    return GleanContext(client=mock_client)


def test_glean_chat_success() -> None:
    ctx = _make_ctx()

    result = glean_chat(ctx, message="What is our vacation policy?")

    assert result["status"] == "ok"
    assert result["error"] is None
    payload = result["result"]
    assert payload["answer"] == "The answer is 42."
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["url"] == "https://wiki.example.com/doc1"


def test_glean_chat_api_error() -> None:
    ctx = _make_ctx(chat_side_effect=Exception("Chat API Error"))

    result = glean_chat(ctx, message="anything")

    assert result["status"] == "error"
    assert result["error"] == "Chat API Error"
    assert result["result"] is None


def test_glean_chat_deduplicates_sources() -> None:
    source_doc = SimpleNamespace(url="https://wiki.example.com/dup")
    citation = SimpleNamespace(source_document=source_doc)
    response = SimpleNamespace(
        messages=[
            SimpleNamespace(
                author="GLEAN_AI",
                fragments=[SimpleNamespace(text="answer")],
                citations=[citation, citation, citation],
            )
        ]
    )
    ctx = _make_ctx(chat_return=response)

    result = glean_chat(ctx, message="test")

    assert result["status"] == "ok"
    assert len(result["result"]["sources"]) == 1


def test_glean_chat_empty_response() -> None:
    response = SimpleNamespace(messages=[])
    ctx = _make_ctx(chat_return=response)

    result = glean_chat(ctx, message="test")

    assert result["status"] == "ok"
    assert result["result"]["answer"] == ""
    assert result["result"]["sources"] == []


def test_glean_chat_extracts_fragments() -> None:
    fragment = SimpleNamespace(text="fragment text")
    msg = SimpleNamespace(
        author="GLEAN_AI",
        fragments=[fragment],
        citations=[],
    )
    response = SimpleNamespace(messages=[msg])
    ctx = _make_ctx(chat_return=response)

    result = glean_chat(ctx, message="test")

    assert result["status"] == "ok"
    assert "fragment text" in result["result"]["answer"]


def test_chat_result_model() -> None:
    cr = ChatResult(answer="hello", sources=[{"url": "http://example.com"}])
    assert cr.answer == "hello"
    assert len(cr.sources) == 1


def test_glean_chat_fragment_level_citations() -> None:
    """New API (SDK >= 0.15): citations attached to individual fragments."""
    urls = ["https://wiki.example.com/a", "https://wiki.example.com/b"]
    msg = _make_fragment_citation_message("fragment answer", urls)
    ctx = _make_ctx(chat_return=SimpleNamespace(messages=[msg]))

    result = glean_chat(ctx, message="test")

    assert result["status"] == "ok"
    assert result["result"]["answer"] == "fragment answer"
    assert [s["url"] for s in result["result"]["sources"]] == urls


def test_glean_chat_message_level_citations_legacy() -> None:
    """Legacy API: citations carried on the message-level ``citations`` list."""
    urls = ["https://wiki.example.com/a", "https://wiki.example.com/b"]
    msg = _make_message_citation_message("legacy answer", urls)
    ctx = _make_ctx(chat_return=SimpleNamespace(messages=[msg]))

    result = glean_chat(ctx, message="test")

    assert result["status"] == "ok"
    assert result["result"]["answer"] == "legacy answer"
    assert [s["url"] for s in result["result"]["sources"]] == urls


def test_citation_shapes_produce_identical_sources() -> None:
    """Both citation shapes must yield the exact same ChatResult sources."""
    urls = ["https://wiki.example.com/a", "https://wiki.example.com/b"]

    new_msg = _make_fragment_citation_message("same answer", urls)
    old_msg = _make_message_citation_message("same answer", urls)

    new_result = glean_chat(
        _make_ctx(chat_return=SimpleNamespace(messages=[new_msg])), message="q"
    )
    old_result = glean_chat(
        _make_ctx(chat_return=SimpleNamespace(messages=[old_msg])), message="q"
    )

    assert new_result["status"] == old_result["status"] == "ok"
    assert new_result["result"]["sources"] == old_result["result"]["sources"]
    assert new_result["result"] == old_result["result"]


def test_glean_chat_prefers_fragment_citations_over_message_citations() -> None:
    """When both shapes are present, fragment-level citations win."""
    fragment_url = "https://wiki.example.com/fragment"
    legacy_url = "https://wiki.example.com/legacy"

    if _FRAGMENT_HAS_CITATION and _MESSAGE_HAS_CITATIONS:
        msg: object = _ChatMessage(
            author="GLEAN_AI",
            fragments=[
                _ChatMessageFragment(text="answer"),
                _ChatMessageFragment(citation=_make_citation(fragment_url)),
            ],
            citations=[_make_citation(legacy_url)],
        )
    else:
        # No installed SDK version carries both shapes on real models
        # (0.6.0 lacks fragment.citation; post-removal SDKs lack citations),
        # so use a stand-in message to exercise the preference logic.
        msg = SimpleNamespace(
            author="GLEAN_AI",
            fragments=[
                SimpleNamespace(text="answer"),
                SimpleNamespace(citation=_make_citation(fragment_url)),
            ],
            citations=[_make_citation(legacy_url)],
        )
    ctx = _make_ctx(chat_return=SimpleNamespace(messages=[msg]))

    result = glean_chat(ctx, message="test")

    assert result["status"] == "ok"
    assert [s["url"] for s in result["result"]["sources"]] == [fragment_url]
