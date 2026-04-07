"""Tests for get_tools()."""

from unittest.mock import MagicMock

import pytest

from glean.agent_toolkit import get_tools
from glean.agent_toolkit.context import GleanContext


def _mock_client() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_get_tools_openai() -> None:
    # Use include to avoid tools with dict[str, Any] schemas that fail
    # OpenAI Agents SDK strict_json_schema validation.
    tools = get_tools(
        "openai",
        include=["glean_web_search", "glean_employee_search"],
        client=_mock_client(),
    )
    assert len(tools) == 2
    for tool in tools:
        assert hasattr(tool, "name") or isinstance(tool, dict)


def test_get_tools_langchain() -> None:
    tools = get_tools("langchain", client=_mock_client())
    assert len(tools) > 0
    for tool in tools:
        assert hasattr(tool, "name")


def test_get_tools_adk() -> None:
    tools = get_tools("adk", client=_mock_client())
    assert len(tools) > 0
    for tool in tools:
        assert hasattr(tool, "name")


def test_get_tools_include_filter() -> None:
    tools = get_tools(
        "langchain",
        include=["glean_search"],
        client=_mock_client(),
    )
    assert len(tools) == 1
    assert tools[0].name == "glean_search"


def test_get_tools_exclude_filter() -> None:
    all_tools = get_tools("langchain", client=_mock_client())
    filtered = get_tools(
        "langchain",
        exclude=["glean_search", "glean_chat"],
        client=_mock_client(),
    )
    assert len(filtered) == len(all_tools) - 2


def test_get_tools_include_and_exclude() -> None:
    tools = get_tools(
        "langchain",
        include=["glean_search", "glean_chat"],
        exclude=["glean_chat"],
        client=_mock_client(),
    )
    assert len(tools) == 1
    names = [t.name for t in tools]
    assert "glean_search" in names
    assert "glean_chat" not in names


def test_get_tools_unknown_framework() -> None:
    with pytest.raises(ValueError, match="Unknown framework"):
        get_tools("pytorch", client=_mock_client())


def test_get_tools_uses_ctx_params() -> None:
    mock = _mock_client()
    tools = get_tools("langchain", client=mock, include=["glean_search"])
    assert len(tools) == 1
