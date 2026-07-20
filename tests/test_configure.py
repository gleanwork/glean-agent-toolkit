"""Tests for module-level configure() and the process-default context.

configure() sets a process-wide default used whenever a tool, adapter, or
get_tools() call is made without an explicit context/client/credentials.
Explicit per-call arguments always win over the configured defaults.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import glean.agent_toolkit.context as context_module
from glean.agent_toolkit import configure, get_tools
from glean.agent_toolkit.context import GleanContext, get_default_context
from glean.agent_toolkit.tools._transport import execute_tool
from glean.agent_toolkit.tools.search import search
from glean.api_client import models


def _mock_client(marker: str = "default") -> MagicMock:
    client = MagicMock()
    client.marker = marker
    client.client.search.query.return_value = models.SearchResponse(results=[])
    return client


def test_configure_sets_default_context_used_by_tools() -> None:
    client = _mock_client("configured")

    configure(client=client)
    result = search(query="hello")

    assert result["status"] == "ok"
    client.client.search.query.assert_called_once()


def test_configure_default_used_by_execute_tool_seam() -> None:
    client = _mock_client("configured")

    configure(client=client)
    result = execute_tool("glean_search", {"query": "hi"})

    assert result["status"] == "ok"
    client.client.search.query.assert_called_once()


def test_explicit_ctx_overrides_configured_default() -> None:
    default_client = _mock_client("default")
    explicit_client = _mock_client("explicit")

    configure(client=default_client)
    result = search(GleanContext(client=explicit_client), query="hello")

    assert result["status"] == "ok"
    explicit_client.client.search.query.assert_called_once()
    default_client.client.search.query.assert_not_called()


def test_configure_is_idempotent_and_replaceable() -> None:
    first = _mock_client("first")
    second = _mock_client("second")

    configure(client=first)
    configure(client=second)

    assert get_default_context().get_client() is second


def test_get_default_context_without_configure_is_env_driven() -> None:
    """No configure() call keeps the fresh, env-driven per-call context."""
    assert context_module._default_context is None

    ctx_a = get_default_context()
    ctx_b = get_default_context()

    assert isinstance(ctx_a, GleanContext)
    assert ctx_a is not ctx_b  # no hidden shared state without opt-in


def test_get_tools_uses_configured_default() -> None:
    client = _mock_client("configured")
    configure(client=client)

    tools = get_tools("langchain", include=["glean_search"])
    assert len(tools) == 1

    output = tools[0].invoke({"query": "via configure"})
    assert isinstance(output, str)
    client.client.search.query.assert_called_once()


def test_get_tools_explicit_client_wins_over_configured_default() -> None:
    default_client = _mock_client("default")
    explicit_client = _mock_client("explicit")
    configure(client=default_client)

    tools = get_tools("langchain", include=["glean_search"], client=explicit_client)
    tools[0].invoke({"query": "explicit wins"})

    explicit_client.client.search.query.assert_called_once()
    default_client.client.search.query.assert_not_called()


def test_configure_validates_server_url_scheme() -> None:
    import pytest

    from glean.agent_toolkit.context import GleanConfigurationError

    with pytest.raises(GleanConfigurationError, match="http"):
        configure(server_url="your-company-be.glean.com")


def test_configure_with_credentials_builds_matching_client() -> None:
    with patch.dict(os.environ, {}, clear=True):
        with patch("glean.agent_toolkit.context.Glean") as mock_glean:
            configure(api_token="tok", server_url="https://configured-be.glean.com")
            get_default_context().get_client()

    assert mock_glean.call_args.kwargs["api_token"] == "tok"
    assert mock_glean.call_args.kwargs["server_url"] == "https://configured-be.glean.com"
