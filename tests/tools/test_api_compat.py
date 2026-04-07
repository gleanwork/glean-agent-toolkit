"""Tests that verify the toolkit calls the correct glean-api-client methods.

These tests will fail early in CI if the upstream API client renames methods,
giving a clear signal rather than silent breakage.
"""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock, patch

import pytest

from glean.agent_toolkit.tools._compat import (
    check_api_client_compatibility,
    get_api_client_version,
    resolve_method,
)


class TestResolveMethod:
    def test_preferred_method_found(self) -> None:
        obj = MagicMock(spec=["run"])
        result = resolve_method(obj, "run", "execute")
        assert result == obj.run

    def test_fallback_used_with_warning(self) -> None:
        obj = MagicMock(spec=["execute"])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_method(obj, "run", "execute")

        assert result == obj.execute
        assert len(w) == 1
        assert "run" in str(w[0].message)
        assert "execute" in str(w[0].message)
        assert issubclass(w[0].category, DeprecationWarning)

    def test_no_method_found_raises(self) -> None:
        obj = MagicMock(spec=[])
        with pytest.raises(AttributeError, match="None of the expected methods"):
            resolve_method(obj, "run", "execute", "call")

    def test_error_message_includes_version(self) -> None:
        obj = MagicMock(spec=[])
        with pytest.raises(AttributeError, match="glean-api-client=="):
            resolve_method(obj, "run")


class TestGetApiClientVersion:
    def test_returns_version_string(self) -> None:
        ver = get_api_client_version()
        assert ver is not None
        assert isinstance(ver, str)
        # Should look like a version number
        assert "." in ver

    def test_returns_none_when_missing(self) -> None:
        from importlib.metadata import PackageNotFoundError

        with patch(
            "glean.agent_toolkit.tools._compat.version",
            side_effect=PackageNotFoundError,
        ):
            assert get_api_client_version() is None


class TestCheckApiClientCompatibility:
    def test_no_warnings_for_current_version(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_api_client_compatibility()
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0


class TestToolsRunMethodExists:
    """Verify that the current glean-api-client exposes the methods we call."""

    def test_tools_run_method_exists(self) -> None:
        """client.tools must have a 'run' method."""
        from glean.api_client.tools import Tools

        assert hasattr(Tools, "run"), (
            "glean-api-client no longer exposes 'Tools.run()'. "
            "The upstream API client may have renamed this method."
        )

    def test_documents_retrieve_method_exists(self) -> None:
        """client.documents must have a 'retrieve' method."""
        from glean.api_client.client_documents import ClientDocuments

        assert hasattr(ClientDocuments, "retrieve"), (
            "glean-api-client no longer exposes 'ClientDocuments.retrieve()'. "
            "The upstream API client may have renamed this method."
        )


class TestRunToolAttributeError:
    """Verify run_tool surfaces a clear error when methods are missing."""

    def test_run_tool_attribute_error(self) -> None:
        from glean.agent_toolkit.tools._common import run_tool

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = MagicMock()
            # Remove 'run' and all fallbacks from tools
            mock_tools = MagicMock(spec=[])
            mock_client.client.tools = mock_tools
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = run_tool("Glean Search", {})

        assert result["result"] is None
        assert "API client compatibility error" in result["error"]
        assert "None of the expected methods" in result["error"]


class TestReadDocumentAttributeError:
    """Verify read_document surfaces a clear error when methods are missing."""

    def test_read_document_attribute_error(self) -> None:
        from glean.agent_toolkit.tools.read_document import read_document

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = MagicMock()
            mock_docs = MagicMock(spec=[])
            mock_client.client.documents = mock_docs
            mock_api_client.return_value.__enter__.return_value = mock_client

            result = read_document(document_id="glean_123")

        assert result["result"] is None
        assert "API client compatibility error" in result["error"]


class TestRunToolFallback:
    """Verify run_tool falls back gracefully when preferred method is renamed."""

    def test_run_tool_uses_fallback(self) -> None:
        from glean.agent_toolkit.tools._common import run_tool

        with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
            mock_client = MagicMock()
            # Simulate: 'run' is gone, but 'execute' exists
            mock_tools = MagicMock(spec=["execute"])
            mock_tools.execute.return_value = {"data": "ok"}
            mock_client.client.tools = mock_tools
            mock_api_client.return_value.__enter__.return_value = mock_client

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = run_tool("Glean Search", {})

        assert result["result"] == {"data": "ok"}
        assert any("falling back" in str(x.message) for x in w)
