"""Shared helpers for the live e2e suite.

The central design decision lives in :func:`unwrap_ok_or_skip`: a red e2e run
must mean a real regression, not per-instance configuration drift. Built-in
tools depend on server-side features and connectors (see
docs/prerequisites.md), so when the live API reports a tool/feature as
unavailable we SKIP with the server's reason. Auth failures and unexpected
server/transport errors FAIL loudly.
"""

from __future__ import annotations

from typing import Any

import pytest

TOOL_RESULT_KEYS = frozenset({"status", "result", "error", "error_type", "suggested_action"})

# Error classifications that indicate the instance does not have the
# feature/tool configured (unknown tools/call name, disabled endpoints,
# unconfigured connectors surface as 400/404/422) rather than a toolkit bug.
_FEATURE_UNAVAILABLE_ERROR_TYPES = frozenset({"validation", "not_found"})


def assert_tool_result_envelope(result: Any) -> None:
    """Assert *result* is a well-formed ``ToolResult`` envelope."""
    assert isinstance(result, dict), f"expected ToolResult dict, got {type(result)!r}"
    assert set(result) == TOOL_RESULT_KEYS, f"unexpected ToolResult keys: {sorted(result)}"
    assert result["status"] in ("ok", "error")
    if result["status"] == "ok":
        assert result["error"] is None
        assert result["error_type"] is None
        assert result["suggested_action"] is None
    else:
        assert result["result"] is None
        assert result["error"]


def unwrap_ok_or_skip(result: Any, tool_name: str) -> Any:
    """Return the success payload, or skip/fail based on the error class.

    - ``status == "ok"``: return ``result["result"]``.
    - ``error_type == "auth"``: FAIL loudly (bad credentials are never
      instance config drift; the whole run is meaningless).
    - ``error_type`` in validation/not_found: SKIP with the server's reason
      (tool or feature not configured on this instance).
    - ``error_type == "rate_limit"``: SKIP (transient, not a regression).
    - anything else (api/timeout/config): FAIL (real server, transport, or
      configuration problem).
    """
    assert_tool_result_envelope(result)

    if result["status"] == "ok":
        return result["result"]

    _skip_or_fail_for_error(result["error_type"], result["error"], tool_name)
    raise AssertionError("unreachable")  # pragma: no cover


COMPACT_ERROR_KEYS = frozenset({"error", "error_type", "suggested_action"})


def unwrap_adapter_payload_or_skip(payload: Any, tool_name: str) -> Any:
    """Return a framework-path payload, or skip/fail on the compact error dict.

    Framework adapters deliver the RAW result payload on success and a
    compact ``{"error", "error_type", "suggested_action"}`` dict on failure
    (the ``ToolResult`` envelope is unwrapped at the adapter layer). Apply
    the same skip/fail policy as :func:`unwrap_ok_or_skip`.
    """
    if isinstance(payload, dict) and set(payload) == COMPACT_ERROR_KEYS:
        _skip_or_fail_for_error(payload["error_type"], payload["error"], tool_name)
    return payload


def _skip_or_fail_for_error(error_type: Any, error: Any, tool_name: str) -> None:
    """Shared skip/fail policy for live error classifications."""
    if error_type == "auth":
        pytest.fail(
            f"{tool_name}: authentication failure against live instance "
            f"(check GLEAN_API_TOKEN / GLEAN_SERVER_URL / GLEAN_INSTANCE; Glean-issued "
            f"user tokens are revoked when the backing test user is signed out of all "
            f"sessions -- the token may need to be re-minted): {error}"
        )
    if error_type in _FEATURE_UNAVAILABLE_ERROR_TYPES:
        pytest.skip(f"{tool_name}: unavailable on this instance ({error_type}): {error}")
    if error_type == "rate_limit":
        pytest.skip(
            f"{tool_name}: rate-limited by live instance even after retries "
            f"(likely QA post-deploy-validation contention on the shared test "
            f"instance, not a toolkit regression): {error}"
        )

    pytest.fail(f"{tool_name}: live call failed ({error_type}): {error}")


def skip_if_tools_call_payload_error(payload: Any, tool_name: str) -> None:
    """Skip when a 200-level ``tools/call`` payload carries a tool-level error.

    The assistant-UI ``tools/call`` endpoint can respond 200 with an ``error``
    field in the body when the underlying tool is disabled or misconfigured
    for the instance; that is config drift, not a toolkit regression.
    """
    if isinstance(payload, dict):
        error = payload.get("error")
        if error:
            pytest.skip(f"{tool_name}: server reported a tool-level error: {error}")
