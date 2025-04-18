"""Tests for the CLI module."""

import json
from unittest import mock

import pytest
from typer.testing import CliRunner

from toolkit.cli import app
from toolkit.spec import ToolSpec


@pytest.fixture
def mock_registry() -> mock.MagicMock:
    """Create a mock registry for testing."""
    mock_reg = mock.MagicMock()

    def dummy_func() -> None:
        pass

    tool1 = ToolSpec(
        name="tool1",
        description="Tool 1",
        function=dummy_func,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        version="1.0",
    )

    tool2 = ToolSpec(
        name="tool2",
        description="Tool 2",
        function=dummy_func,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )

    # Set up the mock
    mock_reg.list.return_value = [tool1, tool2]
    mock_reg.get.side_effect = lambda name: tool1 if name == "tool1" else None

    return mock_reg


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


def test_list_tools(runner: CliRunner, mock_registry: mock.MagicMock) -> None:
    """Test listing tools."""
    with mock.patch("toolkit.cli.get_registry", return_value=mock_registry):
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "tool1" in result.stdout
        assert "Tool 1" in result.stdout
        assert "1.0" in result.stdout
        assert "tool2" in result.stdout
        assert "Tool 2" in result.stdout
        assert "N/A" in result.stdout


def test_list_empty(runner: CliRunner) -> None:
    """Test listing when no tools are registered."""
    empty_registry = mock.MagicMock()
    empty_registry.list.return_value = []

    with mock.patch("toolkit.cli.get_registry", return_value=empty_registry):
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No tools registered" in result.stdout


def test_export_schema(runner: CliRunner, mock_registry: mock.MagicMock) -> None:
    """Test exporting a schema."""
    with mock.patch("toolkit.cli.get_registry", return_value=mock_registry):
        result = runner.invoke(app, ["export-schema", "tool1"])

        assert result.exit_code == 0
        # Verify JSON output
        data = json.loads(result.stdout)
        assert data["name"] == "tool1"
        assert data["description"] == "Tool 1"
        assert data["version"] == "1.0"


def test_export_schema_not_found(runner: CliRunner, mock_registry: mock.MagicMock) -> None:
    """Test exporting a schema for a non-existent tool."""
    with mock.patch("toolkit.cli.get_registry", return_value=mock_registry):
        result = runner.invoke(app, ["export-schema", "nonexistent"])

        assert result.exit_code == 1
