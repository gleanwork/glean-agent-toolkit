"""Tests for the API compatibility helpers."""

import warnings

import pytest

from glean.agent_toolkit.tools._compat import (
    check_api_client_compatibility,
    get_api_client_version,
    resolve_method,
)


class _FakeClient:
    def run(self) -> str:
        return "run_result"


class _LegacyClient:
    def execute(self) -> str:
        return "execute_result"


class _EmptyClient:
    pass


def test_resolve_method_preferred() -> None:
    obj = _FakeClient()
    method = resolve_method(obj, "run", "execute")
    assert method() == "run_result"


def test_resolve_method_fallback_with_warning() -> None:
    obj = _LegacyClient()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        method = resolve_method(obj, "run", "execute")
        assert method() == "execute_result"
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "falling back to .execute()" in str(w[0].message)


def test_resolve_method_none_found() -> None:
    obj = _EmptyClient()
    with pytest.raises(AttributeError, match="has none of the expected methods"):
        resolve_method(obj, "run", "execute")


def test_resolve_method_no_fallbacks() -> None:
    obj = _EmptyClient()
    with pytest.raises(AttributeError):
        resolve_method(obj, "run")


def test_get_api_client_version_returns_string() -> None:
    result = get_api_client_version()
    # glean-api-client is installed in test env

    assert isinstance(result, str)


def test_check_api_client_compatibility_no_warning() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_api_client_compatibility()
        # No versions are flagged, so no warnings
        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0
