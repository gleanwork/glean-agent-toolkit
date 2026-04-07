import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools._common import run_tool
from glean.api_client import models


class TestGleanContext:
    """Test GleanContext constructor and get_client."""

    def test_injected_client_returned_directly(self) -> None:
        mock_client = MagicMock()
        ctx = GleanContext(client=mock_client)
        assert ctx.get_client() is mock_client

    def test_client_cached_after_creation(self) -> None:
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "tok",
            "GLEAN_SERVER_URL": "https://example-be.glean.com",
        }, clear=True):
            with patch("glean.agent_toolkit.context.Glean") as mock_glean:
                ctx = GleanContext()
                c1 = ctx.get_client()
                c2 = ctx.get_client()
                assert c1 is c2
                mock_glean.assert_called_once()

    def test_explicit_params_override_env(self) -> None:
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "env-token",
            "GLEAN_SERVER_URL": "https://env.glean.com",
        }, clear=True):
            with patch("glean.agent_toolkit.context.Glean") as mock_glean:
                ctx = GleanContext(
                    api_token="explicit-token",
                    server_url="https://explicit.glean.com",
                )
                ctx.get_client()
                mock_glean.assert_called_once_with(
                    api_token="explicit-token",
                    server_url="https://explicit.glean.com",
                    retry_config=ANY,
                )

    def test_missing_token_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            ctx = GleanContext()
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN"):
                ctx.get_client()

    def test_missing_server_url_and_instance_raises(self) -> None:
        with patch.dict(os.environ, {"GLEAN_API_TOKEN": "tok"}, clear=True):
            ctx = GleanContext()
            with pytest.raises(ValueError, match="GLEAN_SERVER_URL or GLEAN_INSTANCE"):
                ctx.get_client()

    def test_instance_fallback(self) -> None:
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "tok",
            "GLEAN_INSTANCE": "my-inst",
        }, clear=True):
            with patch("glean.agent_toolkit.context.Glean") as mock_glean:
                ctx = GleanContext()
                ctx.get_client()
                mock_glean.assert_called_once_with(
                    api_token="tok",
                    instance="my-inst",
                    retry_config=ANY,
                )


class TestRunTool:
    """Test run_tool function with injected client."""

    @staticmethod
    def _mock_client(return_value=None, side_effect=None) -> MagicMock:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        if side_effect is not None:
            client.client.tools.run.side_effect = side_effect
        else:
            client.client.tools.run.return_value = return_value
        return client

    def test_run_tool_success(self) -> None:
        mock_result = {"documents": [{"title": "Test Document"}]}
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }
        client = self._mock_client(return_value=mock_result)

        result = run_tool("Test Tool", parameters, client=client)

        assert result["status"] == "ok"
        assert result["result"] == mock_result
        assert result["error"] is None
        assert result["error_type"] is None
        assert result["suggested_action"] is None
        client.client.tools.run.assert_called_once_with(
            name="Test Tool",
            parameters=parameters
        )

    def test_run_tool_api_error(self) -> None:
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }
        client = self._mock_client(side_effect=Exception("API Error"))

        result = run_tool("Test Tool", parameters, client=client)

        assert result["status"] == "error"
        assert result["error"] == "API Error"
        assert result["result"] is None
        assert result["error_type"] == "api"
        assert result["suggested_action"] == "retry"

    def test_run_tool_connection_error(self) -> None:
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }
        client = self._mock_client(side_effect=ConnectionError("Network error"))

        result = run_tool("Test Tool", parameters, client=client)

        assert result["status"] == "error"
        assert result["error"] == "Network error"
        assert result["error_type"] == "api"
        assert result["suggested_action"] == "retry"

    def test_run_tool_empty_parameters(self) -> None:
        mock_result = {"status": "success"}
        client = self._mock_client(return_value=mock_result)

        result = run_tool("Test Tool", {}, client=client)

        assert result["status"] == "ok"
        assert result["result"] == mock_result
        client.client.tools.run.assert_called_once_with(
            name="Test Tool",
            parameters={}
        )

    def test_run_tool_auth_error(self) -> None:
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }
        client = self._mock_client(side_effect=Exception("HTTP 401 Unauthorized"))

        result = run_tool("Test Tool", parameters, client=client)

        assert result["status"] == "error"
        assert result["error_type"] == "auth"
        assert result["suggested_action"] == "check_credentials"

    def test_run_tool_timeout_error(self) -> None:
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }
        client = self._mock_client(side_effect=TimeoutError("request timed out"))

        result = run_tool("Test Tool", parameters, client=client)

        assert result["status"] == "error"
        assert result["error_type"] == "timeout"
        assert result["suggested_action"] == "retry"

    def test_run_tool_client_creation_error(self) -> None:
        """Test that run_tool without client falls back to GleanContext."""
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch.dict(os.environ, {}, clear=True):
            result = run_tool("Test Tool", parameters)

        assert result["status"] == "error"
        assert result["error"] is not None and "GLEAN_API_TOKEN" in result["error"]
        assert result["error_type"] == "validation"
