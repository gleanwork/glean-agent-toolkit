"""Tests for get_tools() and configure()."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glean.agent_toolkit import get_tools
from glean.agent_toolkit.registry import get_registry
from glean.agent_toolkit.tools._common import _config, configure

try:
    from glean.agent_toolkit.adapters.openai import HAS_OPENAI
except ImportError:
    HAS_OPENAI = False

try:
    from glean.agent_toolkit.adapters.langchain import HAS_LANGCHAIN
except ImportError:
    HAS_LANGCHAIN = False

try:
    from glean.agent_toolkit.adapters.crewai import HAS_CREWAI
except ImportError:
    HAS_CREWAI = False

try:
    from glean.agent_toolkit.adapters.adk import HAS_ADK
except ImportError:
    HAS_ADK = False


@pytest.fixture(autouse=True)
def _reset_config():
    """Reset module-level config after each test."""
    yield
    configure(api_token=None, server_url=None)


def _registered_tool_names() -> list[str]:
    return [s.name for s in get_registry().list()]


@pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI not installed")
class TestGetToolsOpenAI:
    def test_returns_all_tools(self):
        tools = get_tools("openai")
        registered = _registered_tool_names()
        assert len(tools) == len(registered)
        assert len(tools) > 0

    def test_include_filter(self):
        tools = get_tools("openai", include=["search"])
        assert len(tools) == 1

    def test_exclude_filter(self):
        all_tools = get_tools("openai")
        filtered = get_tools("openai", exclude=["search"])
        assert len(filtered) == len(all_tools) - 1

    def test_include_and_exclude_raises(self):
        with pytest.raises(ValueError, match="Cannot specify both"):
            get_tools("openai", include=["search"], exclude=["web_search"])

    def test_include_empty_returns_empty(self):
        tools = get_tools("openai", include=[])
        assert tools == []

    def test_exclude_empty_returns_all(self):
        all_tools = get_tools("openai")
        filtered = get_tools("openai", exclude=[])
        assert len(filtered) == len(all_tools)


@pytest.mark.skipif(not HAS_LANGCHAIN, reason="LangChain not installed")
class TestGetToolsLangChain:
    def test_returns_all_tools(self):
        tools = get_tools("langchain")
        registered = _registered_tool_names()
        assert len(tools) == len(registered)
        assert len(tools) > 0

    def test_include_filter(self):
        tools = get_tools("langchain", include=["search", "web_search"])
        assert len(tools) == 2


def test_unknown_framework_raises():
    with pytest.raises(ValueError, match="Unknown framework"):
        get_tools("nonexistent")  # type: ignore[arg-type]


class TestConfigure:
    def test_configure_sets_values(self):
        configure(api_token="tok-123", server_url="https://example.com")
        assert _config["api_token"] == "tok-123"
        assert _config["server_url"] == "https://example.com"

    def test_configure_clears_with_none(self):
        configure(api_token="tok-123", server_url="https://example.com")
        configure(api_token=None, server_url=None)
        assert _config["api_token"] is None
        assert _config["server_url"] is None

    def test_get_tools_passes_config(self):
        """Verify that api_token/server_url params call configure()."""
        with patch("glean.agent_toolkit.configure") as mock_configure:
            # This will fail at adapter instantiation if the framework isn't
            # installed, but configure() should still be called first.
            try:
                get_tools(
                    "openai",
                    api_token="tok-abc",
                    server_url="https://test.glean.com",
                )
            except ImportError:
                pass
            mock_configure.assert_called_once_with(
                api_token="tok-abc", server_url="https://test.glean.com"
            )

    def test_get_tools_skips_configure_when_no_creds(self):
        """configure() should not be called when neither param is passed."""
        with patch("glean.agent_toolkit.configure") as mock_configure:
            try:
                get_tools("openai")
            except ImportError:
                pass
            mock_configure.assert_not_called()


class TestConfigureIntegrationWithApiClient:
    def test_api_client_uses_configured_token(self):
        """api_client() should prefer configured values over env vars."""
        configure(api_token="configured-token", server_url="https://configured.glean.com")
        from glean.agent_toolkit.tools._common import api_client

        # We can't actually connect, but we can verify it doesn't raise
        # ValueError about missing env vars by patching the Glean constructor.
        with patch("glean.agent_toolkit.tools._common.Glean") as mock_glean:
            api_client()
            call_kwargs = mock_glean.call_args
            assert call_kwargs.kwargs["api_token"] == "configured-token"
            assert call_kwargs.kwargs["server_url"] == "https://configured.glean.com"

    def test_api_client_falls_back_to_env(self):
        """api_client() should fall back to env vars when config is unset."""
        configure(api_token=None, server_url=None)
        env = {"GLEAN_API_TOKEN": "env-token", "GLEAN_SERVER_URL": "https://env.glean.com"}
        with patch.dict("os.environ", env, clear=False), patch(
            "glean.agent_toolkit.tools._common.Glean"
        ) as mock_glean:
            from glean.agent_toolkit.tools._common import api_client

            api_client()
            call_kwargs = mock_glean.call_args
            assert call_kwargs.kwargs["api_token"] == "env-token"
            assert call_kwargs.kwargs["server_url"] == "https://env.glean.com"
