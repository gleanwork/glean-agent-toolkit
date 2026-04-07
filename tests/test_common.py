import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools._common import run_tool, serialize_tool_result
from glean.api_client import models


class TestGleanContext:
    """Test GleanContext client creation."""

    def test_context_with_server_url(self) -> None:
        """Test GleanContext with explicit server_url."""
        with patch("glean.agent_toolkit.context.Glean") as mock_glean:
            ctx = GleanContext(api_token="test-token", server_url="https://example-be.glean.com")
            ctx.get_client()
            mock_glean.assert_called_once_with(
                api_token="test-token",
                server_url="https://example-be.glean.com",
                retry_config=ANY,
            )

    def test_context_with_instance(self) -> None:
        """Test GleanContext with explicit instance."""
        with patch("glean.agent_toolkit.context.Glean") as mock_glean:
            ctx = GleanContext(api_token="test-token", instance="test-instance")
            ctx.get_client()
            mock_glean.assert_called_once_with(
                api_token="test-token",
                instance="test-instance",
                retry_config=ANY,
            )

    def test_context_server_url_takes_precedence(self) -> None:
        """Test that server_url takes precedence over instance."""
        with patch("glean.agent_toolkit.context.Glean") as mock_glean:
            ctx = GleanContext(
                api_token="test-token",
                server_url="https://example-be.glean.com",
                instance="test-instance",
            )
            ctx.get_client()
            mock_glean.assert_called_once_with(
                api_token="test-token",
                server_url="https://example-be.glean.com",
                retry_config=ANY,
            )

    def test_context_missing_token(self) -> None:
        """Test GleanContext with missing token."""
        with patch.dict(os.environ, {}, clear=True):
            ctx = GleanContext(instance="test-instance")
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN"):
                ctx.get_client()

    def test_context_missing_server_url_and_instance(self) -> None:
        """Test GleanContext with missing server URL and instance."""
        with patch.dict(os.environ, {}, clear=True):
            ctx = GleanContext(api_token="test-token")
            with pytest.raises(ValueError, match="GLEAN_SERVER_URL or GLEAN_INSTANCE"):
                ctx.get_client()

    def test_context_missing_all(self) -> None:
        """Test GleanContext with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            ctx = GleanContext()
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN"):
                ctx.get_client()

    def test_context_empty_token_falls_back_to_env(self) -> None:
        """Test GleanContext with empty explicit token falls back to env."""
        with patch.dict(
            os.environ, {"GLEAN_API_TOKEN": "", "GLEAN_INSTANCE": "test-instance"}, clear=True
        ):
            ctx = GleanContext()
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN"):
                ctx.get_client()

    def test_context_env_fallback_server_url(self) -> None:
        """Test GleanContext falls back to env vars."""
        with patch.dict(
            os.environ,
            {
                "GLEAN_API_TOKEN": "env-token",
                "GLEAN_SERVER_URL": "https://env-be.glean.com",
            },
            clear=True,
        ):
            with patch("glean.agent_toolkit.context.Glean") as mock_glean:
                ctx = GleanContext()
                ctx.get_client()
                mock_glean.assert_called_once_with(
                    api_token="env-token",
                    server_url="https://env-be.glean.com",
                    retry_config=ANY,
                )

    def test_context_env_fallback_instance(self) -> None:
        """Test GleanContext falls back to GLEAN_INSTANCE env var."""
        with patch.dict(
            os.environ,
            {
                "GLEAN_API_TOKEN": "env-token",
                "GLEAN_INSTANCE": "test-instance",
            },
            clear=True,
        ):
            with patch("glean.agent_toolkit.context.Glean") as mock_glean:
                ctx = GleanContext()
                ctx.get_client()
                mock_glean.assert_called_once_with(
                    api_token="env-token",
                    instance="test-instance",
                    retry_config=ANY,
                )

    def test_context_uses_injected_client(self) -> None:
        """Test that GleanContext returns pre-injected client."""
        fake_client = MagicMock()
        ctx = GleanContext(client=fake_client)
        assert ctx.get_client() is fake_client


class TestRunTool:
    """Test run_tool function."""

    def test_run_tool_success_with_client(self) -> None:
        """Test successful tool execution with injected client."""
        mock_result = {"documents": [{"title": "Test Document"}]}
        parameters = {"query": models.ToolsCallParameter(name="query", value="test query")}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.client.tools.run.return_value = mock_result

        result = run_tool("Test Tool", parameters, client=mock_client)

        assert result == {"result": mock_result}
        mock_client.client.tools.run.assert_called_once_with(
            name="Test Tool",
            parameters=parameters,
        )

    def test_run_tool_api_error_with_client(self) -> None:
        """Test tool execution with API error using injected client."""
        parameters = {"query": models.ToolsCallParameter(name="query", value="test query")}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.client.tools.run.side_effect = Exception("API Error")

        result = run_tool("Test Tool", parameters, client=mock_client)

        assert result == {"error": "API Error", "result": None}

    def test_run_tool_empty_parameters(self) -> None:
        """Test tool execution with empty parameters."""
        mock_result = {"status": "success"}
        parameters = {}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.client.tools.run.return_value = mock_result

        result = run_tool("Test Tool", parameters, client=mock_client)

        assert result == {"result": mock_result}
        mock_client.client.tools.run.assert_called_once_with(
            name="Test Tool",
            parameters={},
        )

    def test_run_tool_value_error(self) -> None:
        """Test tool execution when ValueError is raised."""
        parameters = {"query": models.ToolsCallParameter(name="query", value="test query")}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.client.tools.run.side_effect = ValueError("Bad param")

        result = run_tool("Test Tool", parameters, client=mock_client)

        assert result == {
            "error": "Parameter validation error: Bad param",
            "result": None,
        }
