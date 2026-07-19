"""Injectable context object for Glean API client access."""

from __future__ import annotations

import os
import threading
from types import TracebackType

from glean.api_client import Glean
from glean.api_client.utils import BackoffStrategy, RetryConfig


def _parse_retry_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _build_retry_config() -> RetryConfig:
    initial = _parse_retry_env_float("GLEAN_RETRY_INITIAL", 1.0)
    maximum = _parse_retry_env_float("GLEAN_RETRY_MAX", 50.0)
    exponent = _parse_retry_env_float("GLEAN_RETRY_MULTIPLIER", 1.1)
    max_elapsed = _parse_retry_env_float("GLEAN_RETRY_MAX_ELAPSED", 60.0)

    initial_interval = round(initial)
    max_interval = round(maximum)
    max_elapsed_time = round(max_elapsed)

    return RetryConfig(
        strategy="backoff",
        backoff=BackoffStrategy(
            initial_interval=initial_interval,
            max_interval=max_interval,
            exponent=exponent,
            max_elapsed_time=max_elapsed_time,
        ),
        retry_connection_errors=True,
    )


class GleanContext:
    """Context object providing Glean client access to tools.

    Passed as the first parameter to every tool function. Adapters
    bind it via ``functools.partial`` so LLM frameworks never see it.

    The context owns the lifecycle of the underlying :class:`Glean`
    client: the client is created lazily, cached, and shared across
    tool calls. Call :meth:`close` (or use the context as a context
    manager) to release the client's HTTP resources when done.
    """

    def __init__(
        self,
        client: Glean | None = None,
        api_token: str | None = None,
        server_url: str | None = None,
        instance: str | None = None,
    ) -> None:
        """Initialize the context.

        Args:
            client: Pre-configured Glean client instance.
            api_token: Glean API token (falls back to ``GLEAN_API_TOKEN``).
            server_url: Glean server URL (falls back to ``GLEAN_SERVER_URL``).
            instance: Glean instance name (falls back to ``GLEAN_INSTANCE``).
        """
        self._client = client
        self._api_token = api_token
        self._server_url = server_url
        self._instance = instance
        self._lock = threading.Lock()

    def get_client(self) -> Glean:
        """Get a Glean client, creating one if needed.

        The client is created lazily on first use, cached, and reused
        for the lifetime of this context. Creation is thread-safe.
        """
        with self._lock:
            if self._client is not None:
                return self._client

            api_token = self._api_token or os.getenv("GLEAN_API_TOKEN")

            if self._server_url is not None or self._instance is not None:
                server_url = self._server_url
                instance = self._instance
            else:
                server_url = os.getenv("GLEAN_SERVER_URL")
                instance = os.getenv("GLEAN_INSTANCE")

            if not api_token:
                raise ValueError("GLEAN_API_TOKEN environment variable is required")

            if server_url:
                client = Glean(
                    api_token=api_token,
                    server_url=server_url,
                    retry_config=_build_retry_config(),
                )
                self._client = client
                return client
            elif instance:
                client = Glean(
                    api_token=api_token,
                    instance=instance,
                    retry_config=_build_retry_config(),
                )
                self._client = client
                return client
            else:
                raise ValueError(
                    "GLEAN_SERVER_URL or GLEAN_INSTANCE environment variable is required"
                )

    def close(self) -> None:
        """Close the underlying Glean client and release HTTP resources.

        Safe to call multiple times. After closing, the next
        :meth:`get_client` call creates a fresh client.
        """
        with self._lock:
            client = self._client
            self._client = None

        if client is None:
            return

        # Glean.__exit__ closes the underlying httpx client (when the
        # SDK owns it) and clears internal references.
        client.__exit__(None, None, None)

    def __enter__(self) -> GleanContext:
        """Enter the context manager, returning this context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, closing the underlying client."""
        self.close()
