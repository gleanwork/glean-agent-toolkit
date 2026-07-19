"""Global fixtures for tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_glean_env_vars() -> Generator[None, None, None]:
    """Mock Glean environment variables for all tests.

    This ensures the API client can be created properly while the HTTP
    layer is mocked (e.g. via pytest-httpx) in transport-level tests.
    """
    with patch.dict(os.environ, {
        "GLEAN_API_TOKEN": "fake_token_for_vcr_testing",
        "GLEAN_SERVER_URL": "https://test-instance-be.glean.com",
    }):
        yield
