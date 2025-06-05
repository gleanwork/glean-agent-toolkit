import os
from unittest import mock
from unittest.mock import patch

import pytest

from glean.agent_toolkit.tools._common import api_client, run_tool
from glean.api_client import models


class TestApiClient:
    """Test api_client function."""

    def test_api_client_success(self) -> None:
        """Test successful API client creation."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "test-token",
            "GLEAN_INSTANCE": "test-instance"
        }):
            with patch("glean.agent_toolkit.tools._common.Glean") as mock_glean:
                api_client()
                mock_glean.assert_called_once_with(
                    api_token="test-token",
                    instance="test-instance"
                )

    def test_api_client_missing_token(self) -> None:
        """Test API client creation with missing token."""
        with patch.dict(os.environ, {"GLEAN_INSTANCE": "test-instance"}, clear=True):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN and GLEAN_INSTANCE"):
                api_client()

    def test_api_client_missing_instance(self) -> None:
        """Test API client creation with missing instance."""
        with patch.dict(os.environ, {"GLEAN_API_TOKEN": "test-token"}, clear=True):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN and GLEAN_INSTANCE"):
                api_client()

    def test_api_client_missing_both(self) -> None:
        """Test API client creation with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN and GLEAN_INSTANCE"):
                api_client()

    def test_api_client_empty_token(self) -> None:
        """Test API client creation with empty token."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "",
            "GLEAN_INSTANCE": "test-instance"
        }):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN and GLEAN_INSTANCE"):
                api_client()

    def test_api_client_empty_instance(self) -> None:
        """Test API client creation with empty instance."""
        with patch.dict(os.environ, {
            "GLEAN_API_TOKEN": "test-token",
            "GLEAN_INSTANCE": ""
        }):
            with pytest.raises(ValueError, match="GLEAN_API_TOKEN and GLEAN_INSTANCE"):
                api_client()


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

            assert result == {"result": mock_result}
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

            assert result == {"error": "API Error", "result": None}

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

            assert result == {"error": "Network error", "result": None}

    def test_run_tool_empty_parameters(self) -> None:
        """Test tool execution with empty parameters."""
        mock_result = {"status": "success"}
        parameters = {}

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = mock.MagicMock()
            mock_client.client.tools.run.return_value = mock_result
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Test Tool", parameters)

            assert result == {"result": mock_result}
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

            # The run_tool function should catch the ValueError and return an error dict
            result = run_tool("Test Tool", parameters)

            assert result == {"error": "Missing credentials", "result": None} 