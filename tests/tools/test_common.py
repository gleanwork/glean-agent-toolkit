from unittest.mock import MagicMock

from pydantic import BaseModel, ConfigDict, Field

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools._common import run_tool, serialize_tool_result


class _Item(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    camel_case_field: str = Field(alias="camelCaseField")


class _Response(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    items: list[_Item]


def test_serialize_tool_result_uses_aliases() -> None:
    model = _Response(items=[_Item(camelCaseField="a"), _Item(camelCaseField="b")])

    result = serialize_tool_result(model)

    assert result == {"items": [{"camelCaseField": "a"}, {"camelCaseField": "b"}]}


def test_serialize_tool_result_passthrough() -> None:
    assert serialize_tool_result({"plain": "dict"}) == {"plain": "dict"}
    assert serialize_tool_result("string") == "string"
    assert serialize_tool_result(None) is None


def test_run_tool_serializes_sdk_response() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.client.tools.run.return_value = _Item(camelCaseField="value")

    result = run_tool("Glean Search", {}, client=mock_client)

    assert result.get("error") is None
    assert result["result"] == {"camelCaseField": "value"}
