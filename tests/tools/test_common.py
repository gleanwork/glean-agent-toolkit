from unittest.mock import MagicMock, patch

from glean.agent_toolkit.tools._common import run_tool, serialize_tool_result


class _AliasModel:
    def __init__(self, value: object) -> None:
        self.value = value

    def model_dump(self, by_alias: bool = False) -> dict[str, object]:
        if by_alias:
            return {"camelCaseField": self.value}
        return {"snake_case_field": self.value}


def test_serialize_tool_result_recursively_uses_aliases() -> None:
    payload = {
        "items": [_AliasModel("a"), _AliasModel("b")],
        "nested": _AliasModel({"child": _AliasModel("c")}),
    }

    result = serialize_tool_result(payload)

    assert result == {
        "items": [{"camelCaseField": "a"}, {"camelCaseField": "b"}],
        "nested": {"camelCaseField": {"child": {"camelCaseField": "c"}}},
    }


def test_run_tool_serializes_sdk_response() -> None:
    with patch("glean.agent_toolkit.tools._common.api_client") as mock_api_client:
        mock_client = MagicMock()
        mock_client.client.tools.run.return_value = _AliasModel("value")
        mock_api_client.return_value.__enter__.return_value = mock_client

        result = run_tool("Glean Search", {})

        assert result.get("error") is None
        assert result["result"] == {"camelCaseField": "value"}
