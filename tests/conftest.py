"""Global fixtures for tests."""

import os
import pathlib
import re
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
import vcr
from vcr.cassette import Cassette
from vcr.record_mode import RecordMode

CASSETTES_DIR = pathlib.Path(__file__).parent / "cassettes"


def filter_request(request: Any) -> Any:
    """Scrub sensitive data from VCR requests."""
    if hasattr(request, 'uri'):
        request.uri = re.sub(
            r'https://[^/]*-be\.glean\.com',
            'https://test-instance-be.glean.com',
            request.uri
        )

    if hasattr(request, 'headers') and 'host' in request.headers:
        request.headers['host'] = ['test-instance-be.glean.com']

    return request


def filter_response(response: Any) -> Any:
    """Scrub sensitive data from VCR responses."""
    if hasattr(response, 'body') and hasattr(response.body, 'string'):
        body_str = response.body.string
        if isinstance(body_str, str):
            body_str = re.sub(
                r'https://[^/]*-be\.[^/]+\.com',
                'https://test-instance-be.example.com',
                body_str)
            body_str = re.sub(r'[^/]*-be\.[^/]+\.com', 'test-instance-be.example.com', body_str)

            body_str = re.sub(r'\b[a-zA-Z0-9_-]+-prod\b', 'test-instance', body_str)
            body_str = re.sub(r'instance=[a-zA-Z0-9_-]+-prod', 'instance=test-instance', body_str)
            body_str = re.sub(r'instance=[a-zA-Z0-9_-]+', 'instance=test-instance', body_str)

            body_str = re.sub(
                r'https://docs\.google\.com/[^"]+',
                'https://docs.google.com/document/d/REDACTED',
                body_str
            )
            body_str = re.sub(
                r'https://[^/]+\.slack\.com/[^"]+',
                'https://test-company.slack.com/REDACTED',
                body_str
            )

            body_str = re.sub(r'@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '@company.com', body_str)

            body_str = re.sub(
                r'"[A-Z][a-z]+ [A-Z][a-z]+"',
                '"Test User"',
                body_str
            )

            body_str = re.sub(
                r'("name"\s*:\s*")[A-Z][a-z]+ [A-Z][a-z]+(")',
                r'\1Test User\2',
                body_str
            )
            body_str = re.sub(
                r'("displayName"\s*:\s*")[A-Z][a-z]+ [A-Z][a-z]+(")',
                r'\1Test User\2',
                body_str
            )
            body_str = re.sub(
                r'("author"\s*:\s*")[A-Z][a-z]+ [A-Z][a-z]+(")',
                r'\1Test User\2',
                body_str
            )

            body_str = re.sub(
                r'"[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+"',
                '"Test User"',
                body_str
            )
            body_str = re.sub(
                r'("name"\s*:\s*")[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+(")',
                r'\1Test User\2',
                body_str
            )

            body_str = re.sub(
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b(?=\s+(said|wrote|authored|created|updated))',
                'Test User',
                body_str
            )

            body_str = re.sub(
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b(?=\s*<[^>]*@)',
                'Test User',
                body_str
            )

            body_str = re.sub(
                r'"obfuscatedId":"[A-F0-9]{32}"',
                '"obfuscatedId":"REDACTED_ID"',
                body_str
            )
            body_str = re.sub(
                r'"loggingId":"[A-F0-9]{32}"',
                '"loggingId":"REDACTED_LOGGING_ID"',
                body_str
            )

            body_str = re.sub(r'[A-Z]+_[A-Za-z0-9_-]+', 'DOC_REDACTED', body_str)

            body_str = re.sub(
                r'https://dev\.[^/]+\.com[^"]*',
                'https://dev.example.com/REDACTED',
                body_str
            )

            response.body.string = body_str

    return response


@pytest.fixture(autouse=True)
def mock_glean_env_vars() -> Generator[None, None, None]:
    """Mock Glean environment variables for all tests except when regenerating cassettes."""
    # Skip mocking when regenerating cassettes - use real credentials
    if should_regenerate_cassettes():
        yield
        return

    # Use environment variables that match the VCR cassette format
    # This ensures the API client can be created properly while VCR handles the HTTP calls
    with patch.dict(os.environ, {
        "GLEAN_API_TOKEN": "fake_token_for_vcr_testing",
        "GLEAN_INSTANCE": "test-instance"  # Matches the cassette hostname format
    }):
        yield


def should_regenerate_cassettes() -> bool:
    """Check if cassettes should be regenerated from environment variables."""
    return os.getenv("VCR_REGENERATE", "").lower() in ("1", "true", "yes")


def get_vcr_config() -> vcr.VCR:
    """Get configured VCR instance for recording/replaying HTTP interactions."""
    if should_regenerate_cassettes():
        record_mode = RecordMode.NEW_EPISODES
    else:
        record_mode = RecordMode.ONCE

    return vcr.VCR(
        cassette_library_dir=str(CASSETTES_DIR),
        record_mode=record_mode,
        match_on=["uri", "method", "body"],
        filter_headers=["authorization", "user-agent", "cookie", "set-cookie"],
        filter_query_parameters=["api_key", "token", "auth"],
        decode_compressed_response=True,
        serializer="yaml",
        before_record_request=filter_request,
        before_record_response=filter_response,
    )


@pytest.fixture
def vcr_cassette(request) -> Generator[Cassette, None, None]:
    """
    VCR fixture for recording/replaying HTTP interactions.

    Usage in tests:
        def test_something(vcr_cassette):
            # HTTP calls will be recorded/replayed automatically
            result = some_api_call()
    """
    test_name = request.node.name
    cassette_name = f"{test_name}.yaml"

    if should_regenerate_cassettes():
        cassette_path = CASSETTES_DIR / cassette_name
        if cassette_path.exists():
            cassette_path.unlink()
            print(f"Regenerating cassette: {cassette_name}")

    my_vcr = get_vcr_config()

    with my_vcr.use_cassette(cassette_name) as cassette:
        yield cassette
