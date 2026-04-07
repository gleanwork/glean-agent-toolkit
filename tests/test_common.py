import os
from unittest import mock
from unittest.mock import ANY, patch

import pytest

from glean.agent_toolkit.tools._common import api_client, run_tool
from glean.api_client import models


class TestApiClient:
    """Test api_client function."""

    def test_api_client_with_server_url(self) -> None:
        """Test API client creation with GLEAN_SERVER_URL."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "test-token",
            "GLEAN_SERVER_URL": "https://example-be.glean.com",
        }, clear=True):
            with patch("glean.agent_toolkit.tools._common.Glean") as mock_glean:
                api_client()
                mock_glean.assert_called_once_with(
                    api_token="test-token",
                    server_url="https://example-be.glean.com",
                    retry_config=ANY,
                )

    def test_api_client_with_instance(self) -> None:
        """Test API client creation with GLEAN_INSTANCE."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "test-token",
            "GLEAN_INSTANCE": "test-instance",
        }, clear=True):
            with patch("glean.agent_toolkit.tools._common.Glean") as mock_glean:
                api_client()
                mock_glean.assert_called_once_with(
                    api_token="test-token",
                    instance="test-instance",
                    retry_config=ANY,
                )

    def test_api_client_server_url_takes_precedence(self) -> None:
        """Test that GLEAN_SERVER_URL takes precedence over GLEAN_INSTANCE."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "test-token",
            "GLEAN_SERVER_URL": "https://example-be.glean.com",
            "GLEAN_INSTANCE": "test-instance",
        }, clear=True):
            with patch("glean.agent_toolkit.tools._common.Glean") as mock_glean:
                api_client()
                mock_glean.assert_called_once_with(
                    api_token="test-token",
                    server_url="https://example-be.glean.com",
                    retry_config=ANY,
                )

    def test_api_client_missing_token(self) -> None:
        """Test API client creation with missing token."""
        with patch.dict(os.environ, {"GLEAN_INSTANCE": "test-instance"}, clear=True):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN"):
                api_client()

    def test_api_client_missing_server_url_and_instance(self) -> None:
        """Test API client creation with missing server URL and instance."""
        with patch.dict(os.environ, {"GLEAN_API_TOKEN": "test-token"}, clear=True):
            with pytest.raises(ValueError, match="GLEAN_SERVER_URL or GLEAN_INSTANCE"):
                api_client()

    def test_api_client_missing_all(self) -> None:
        """Test API client creation with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN"):
                api_client()

    def test_api_client_empty_token(self) -> None:
        """Test API client creation with empty token."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "",
            "GLEAN_INSTANCE": "test-instance"
        }, clear=True):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN"):
                api_client()

    def test_api_client_empty_server_url_falls_back_to_instance(self) -> None:
        """Test that empty GLEAN_SERVER_URL falls back to GLEAN_INSTANCE."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "test-token",
            "GLEAN_SERVER_URL": "",
            "GLEAN_INSTANCE": "test-instance",
        }, clear=True):
            with patch("glean.agent_toolkit.tools._common.Glean") as mock_glean:
                api_client()
                mock_glean.assert_called_once_with(
                    api_token="test-token",
                    instance="test-instance",
                    retry_config=ANY,
                )


class TestRunTool:
    """Test run_tool function."""

    def test_run_tool_success(self) -> None:
        """Test successful tool execution."""
        mock_result = {"documents": [{"title": "Test Document"}]}
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.return_value = mock_result
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "ok"
            assert result["result"] == mock_result
            assert result["error"] is None
            assert result["error_type"] is None
            assert result["suggested_action"] is None
            mock_client.client.tools.run.assert_called_once_with(
                name="Test Tool",
                parameters=parameters
            )

    def test_run_tool_api_error(self) -> None:
        """Test tool execution with API error."""
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.side_effect = Exception("API Error")
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "error"
            assert result["error"] == "API Error"
            assert result["result"] is None
            assert result["error_type"] == "api"
            assert result["suggested_action"] == "retry"
            assert mock_client.client.tools.run.call_count >= 1

    def test_run_tool_connection_error(self) -> None:
        """Test tool execution with connection error."""
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.side_effect = ConnectionError("Network error")
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "error"
            assert result["error"] == "Network error"
            assert result["error_type"] == "api"
            assert result["suggested_action"] == "retry"
            assert mock_client.client.tools.run.call_count >= 1

    def test_run_tool_transient_then_success(self) -> None:
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.side_effect = [Exception("temporary 500")]
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "error"
            assert result["error"] == "temporary 500"
            assert mock_client.client.tools.run.call_count == 1

    def test_run_tool_empty_parameters(self) -> None:
        """Test tool execution with empty parameters."""
        mock_result = {"status": "success"}
        parameters = {}

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.return_value = mock_result
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "ok"
            assert result["result"] == mock_result
            mock_client.client.tools.run.assert_called_once_with(
                name="Test Tool",
                parameters={}
            )

    def test_run_tool_client_creation_error(self) -> None:
        """Test tool execution when API client creation fails."""
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_api_client.side_effect = ValueError("Missing credentials")

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "error"
            assert result["error"] == "Missing credentials"
            assert result["error_type"] == "validation"
            assert result["suggested_action"] == "rephrase_query"

    def test_run_tool_auth_error(self) -> None:
        """Test tool execution with authentication error."""
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.side_effect = Exception("HTTP 401 Unauthorized")
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "error"
            assert result["error_type"] == "auth"
            assert result["suggested_action"] == "check_credentials"

    def test_run_tool_timeout_error(self) -> None:
        """Test tool execution with timeout error."""
        parameters = {
            "query": models.ToolsCallParameter(name="query", value="test query")
        }

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.side_effect = TimeoutError("request timed out")
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result["status"] == "error"
            assert result["error_type"] == "timeout"
            assert result["suggested_action"] == "retry"
