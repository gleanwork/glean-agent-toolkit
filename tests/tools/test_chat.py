"""Tests for the Chat tool."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools.chat import ChatResult, glean_chat


def _make_chat_response(
    answer_text: str = "The answer is 42.",
    sources: list | None = None,
) -> SimpleNamespace:
    """Build a fake chat API response."""
    source_doc = SimpleNamespace(url="https://wiki.example.com/doc1")
    citation = SimpleNamespace(source_document=source_doc)

    msg = SimpleNamespace(
        author="GLEAN_AI",
        message_text=answer_text,
        fragments=[],
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
                message_text="answer",
                fragments=[],
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
        message_text="",
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
