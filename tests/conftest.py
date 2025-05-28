"""Global fixtures for tests."""

import json
import pathlib
from typing import Any, TypeAlias  # Added Any for recursive type definition initially

import pytest

# Define JSON types for better hinting
JSONPrimitive: TypeAlias = str | int | float | bool | None
# For the recursive part, we need to use forward references with strings if
# defined at the top level this way, or use a slightly different approach.
# Let's use Any for now and refine if needed or use a more complex setup.
# A common pattern is to use a forward reference string for the recursive type itself.
JSONValue: TypeAlias = JSONPrimitive | list[Any] | dict[str, Any]

# More precise recursive definition (often requires Python 3.9+ for direct recursion
# in TypeAlias or careful ordering)
# This definition is more accurate for truly arbitrary JSON
JSON: TypeAlias = str | int | float | bool | None | list["JSON"] | dict[str, "JSON"]


FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
TOOLS_RUN_ENDPOINT_REGEX = r"https://[a-zA-Z0-9_-]+-be\.glean\.com/rest/api/v1/tools/run"

@pytest.fixture
def json_fixture_data(request: pytest.FixtureRequest) -> JSON:  # Hinting with the new JSON type
    """Loads a JSON fixture based on a @pytest.mark.load_json marker.

    The marker should specify the base name of the JSON file (without .json)
    located in the tests/fixtures directory.

    Usage in a test:
        @pytest.mark.load_json("my_data_file")
        def test_something(json_fixture_data: JSON):
            data = json_fixture_data  # data is the parsed content of my_data_file.json
            ...
    """
    marker = request.node.get_closest_marker("load_json")
    if not marker:
        raise pytest.UsageError(
            "Test using 'json_fixture_data' must be decorated"
            "with @pytest.mark.load_json('fixture_file_basename')"
        )

    fixture_basename = marker.args[0]
    fixture_path = FIXTURES_DIR / f"{fixture_basename}.json"

    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture file {fixture_path} (derived from basename '{fixture_basename}') not found."
        )

    with open(fixture_path, encoding="utf-8") as f:
        # json.load can return any of the JSON types, matching our JSON type alias
        loaded_data: JSON = json.load(f)
        return loaded_data
