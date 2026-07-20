"""Live error-path e2e test: validate status-code classification against real responses.

The unit suite asserts the 401/403 -> auth mapping against mocked responses;
this test proves the classification holds for a REAL server rejection.
"""

from __future__ import annotations

import os

import pytest

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.tools import search
from tests.e2e._live import assert_tool_result_envelope

pytestmark = pytest.mark.e2e


def test_bad_token_is_classified_as_auth_error() -> None:
    """A deliberately invalid token must produce a structured auth error."""
    server_url = os.environ.get("GLEAN_SERVER_URL")
    instance = os.environ.get("GLEAN_INSTANCE")

    if server_url:
        ctx = GleanContext(api_token="invalid-token-for-e2e-error-path", server_url=server_url)
    else:
        ctx = GleanContext(api_token="invalid-token-for-e2e-error-path", instance=instance)

    with ctx:
        result = search(ctx, query="glean", page_size=1)

    assert_tool_result_envelope(result)
    assert result["status"] == "error", (
        f"expected the live server to reject an invalid token, got: {result}"
    )
    assert result["error_type"] == "auth", result
    assert result["suggested_action"] == "check_credentials", result
