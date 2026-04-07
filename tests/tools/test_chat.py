"""Tests for the Chat tool."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# The __init__.py shadows the module name with `from .chat import chat`,
# so we must grab the actual module from sys.modules.
import glean.agent_toolkit.tools  # noqa: F401 — force submodule loading

_chat_mod = sys.modules["glean.agent_toolkit.tools.chat"]
ChatResult = _chat_mod.ChatResult
chat_fn = _chat_mod.chat


def _make_fragment(text: str) -> MagicMock:
    frag = MagicMock()
    frag.text = text
    return frag


def _make_citation(title: str = "", url: str = "", datasource_name: str = "") -> MagicMock:
    citation = MagicMock()
    doc = MagicMock()
    doc.title = title
    doc.url = url
    ds = MagicMock()
    ds.datasource_name = datasource_name
    ds.instance = None
    doc.datasource = ds if datasource_name else None
    citation.source_document = doc
    return citation


def _make_message(author_str: str, texts: list, citations: list | None = None) -> MagicMock:
    msg = MagicMock()
    msg.author = MagicMock()
    msg.author.__str__ = MagicMock(return_value=f"Author.{author_str}")
    msg.fragments = [_make_fragment(t) for t in texts]
    msg.citations = citations
    return msg


def _mock_chat_context(response: object) -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.client.chat.create.return_value = response
    return ctx


class TestChatResult:
    """Tests for the ChatResult model."""

    def test_minimal(self):
        r = ChatResult(answer="hello")
        assert r.answer == "hello"
        assert r.sources == []

    def test_with_sources(self):
        r = ChatResult(answer="hi", sources=[{"title": "Doc", "url": "https://example.com"}])
        assert len(r.sources) == 1
        assert r.sources[0]["title"] == "Doc"

    def test_serialization(self):
        r = ChatResult(answer="x", sources=[{"title": "T"}])
        d = r.model_dump()
        assert d == {"answer": "x", "sources": [{"title": "T"}]}


class TestChatTool:
    """Tests for the chat tool function."""

    def test_success(self):
        response = MagicMock()
        response.messages = [
            _make_message("GLEAN_AI", ["The answer is 42."], [
                _make_citation("Guide", "https://example.com/guide", "confluence"),
            ]),
        ]
        ctx = _mock_chat_context(response)

        with patch.object(_chat_mod, "api_client", return_value=ctx):
            result = chat_fn(query="What is the meaning of life?")

        assert result is not None
        assert "result" in result
        assert result.get("error") is None
        assert result["result"]["answer"] == "The answer is 42."
        assert len(result["result"]["sources"]) == 1
        assert result["result"]["sources"][0]["title"] == "Guide"
        assert result["result"]["sources"][0]["url"] == "https://example.com/guide"
        assert result["result"]["sources"][0]["datasource"] == "confluence"

    def test_multiple_fragments(self):
        response = MagicMock()
        response.messages = [
            _make_message("GLEAN_AI", ["Part one.", "Part two."]),
        ]
        ctx = _mock_chat_context(response)

        with patch.object(_chat_mod, "api_client", return_value=ctx):
            result = chat_fn(query="multi-part answer")

        assert result["result"]["answer"] == "Part one.\nPart two."

    def test_skips_user_messages(self):
        response = MagicMock()
        response.messages = [
            _make_message("USER", ["user question"]),
            _make_message("GLEAN_AI", ["assistant answer"]),
        ]
        ctx = _mock_chat_context(response)

        with patch.object(_chat_mod, "api_client", return_value=ctx):
            result = chat_fn(query="test")

        assert result["result"]["answer"] == "assistant answer"

    def test_deduplicates_sources(self):
        response = MagicMock()
        response.messages = [
            _make_message("GLEAN_AI", ["answer"], [
                _make_citation("Doc A", "https://a.com"),
                _make_citation("Doc A", "https://a.com"),
                _make_citation("Doc B", "https://b.com"),
            ]),
        ]
        ctx = _mock_chat_context(response)

        with patch.object(_chat_mod, "api_client", return_value=ctx):
            result = chat_fn(query="test")

        assert len(result["result"]["sources"]) == 2

    def test_empty_response(self):
        response = MagicMock()
        response.messages = []
        ctx = _mock_chat_context(response)

        with patch.object(_chat_mod, "api_client", return_value=ctx):
            result = chat_fn(query="test")

        assert result["result"]["answer"] == ""
        assert result["result"]["sources"] == []

    def test_none_messages(self):
        response = MagicMock()
        response.messages = None
        ctx = _mock_chat_context(response)

        with patch.object(_chat_mod, "api_client", return_value=ctx):
            result = chat_fn(query="test")

        assert result["result"]["answer"] == ""

    def test_api_error(self):
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.client.chat.create.side_effect = Exception("API Error")

        with patch.object(_chat_mod, "api_client", return_value=ctx):
            result = chat_fn(query="test")

        assert result is not None
        assert "error" in result
        assert result["result"] is None
        assert "API Error" in result["error"]

    def test_validation_error(self):
        with patch.object(_chat_mod, "api_client", side_effect=ValueError("bad token")):
            result = chat_fn(query="test")

        assert "error" in result
        assert result["result"] is None
        assert "bad token" in result["error"]

    def test_tool_spec_attached(self):
        assert hasattr(chat_fn, "tool_spec")
        assert chat_fn.tool_spec.name == "glean_chat"
        assert "Glean Assistant" in chat_fn.tool_spec.description

    def test_output_model_attached(self):
        assert chat_fn.tool_spec.output_model is ChatResult
