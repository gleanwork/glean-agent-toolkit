"""Injectable context object for Glean API client access."""

from __future__ import annotations

import os
import threading
from types import TracebackType

from glean.api_client import Glean
from glean.api_client.utils import BackoffStrategy, RetryConfig


class GleanConfigurationError(ValueError):
    """The Glean client configuration is invalid (e.g. a malformed server URL).

    Subclasses :class:`ValueError` so existing callers that catch
    ``ValueError`` from :meth:`GleanContext.get_client` keep working.
    """


class GleanCredentialsError(GleanConfigurationError):
    """Required Glean credentials (API token or server location) are missing."""


_MISSING_TOKEN_MESSAGE = (
    "Glean API token is not configured. Set the GLEAN_API_TOKEN environment "
    "variable, or pass api_token=/client= to configure()/get_tools()/GleanContext."
)

_MISSING_SERVER_MESSAGE = (
    "Glean server location is not configured: GLEAN_SERVER_URL or GLEAN_INSTANCE "
    "environment variable is required. Set one of them, or pass "
    "server_url=/instance=/client= to configure()/get_tools()/GleanContext."
)


def _validate_server_url(server_url: str) -> str:
    """Fail fast on a server URL without an http(s) scheme.

    A missing scheme used to surface only after the SDK burned its full
    connection-retry budget (~60s by default). Validating up front turns
    that hang into an immediate, actionable error.
    """
    if not server_url.lower().startswith(("http://", "https://")):
        raise GleanConfigurationError(
            f"Invalid Glean server_url {server_url!r}: it must include an "
            "http:// or https:// scheme, e.g. 'https://your-company-be.glean.com'. "
            "Set GLEAN_SERVER_URL to the full URL, or pass server_url= to "
            "configure()/get_tools()/GleanContext (or use instance='your-company')."
        )
    return server_url


def _parse_retry_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _build_retry_config() -> RetryConfig:
    """Build a :class:`RetryConfig` from ``GLEAN_RETRY_*`` environment variables.

    The environment variables are expressed in **seconds** (e.g.
    ``GLEAN_RETRY_INITIAL=0.5`` means half a second), while the underlying
    Speakeasy-generated :class:`BackoffStrategy` expects integer
    **milliseconds** for ``initial_interval``, ``max_interval`` and
    ``max_elapsed_time`` (its retry loop divides the intervals by 1000
    before sleeping and compares elapsed wall-clock milliseconds against
    ``max_elapsed_time``). Values are converted here.
    """
    initial = _parse_retry_env_float("GLEAN_RETRY_INITIAL", 1.0)
    maximum = _parse_retry_env_float("GLEAN_RETRY_MAX", 50.0)
    exponent = _parse_retry_env_float("GLEAN_RETRY_MULTIPLIER", 1.1)
    max_elapsed = _parse_retry_env_float("GLEAN_RETRY_MAX_ELAPSED", 60.0)

    # Convert seconds (env var semantics) to integer milliseconds (SDK units).
    initial_interval = round(initial * 1000)
    max_interval = round(maximum * 1000)
    max_elapsed_time = round(max_elapsed * 1000)

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

        Raises:
            GleanConfigurationError: If *server_url* lacks an http(s) scheme.
        """
        if server_url is not None:
            _validate_server_url(server_url)
        self._client = client
        self._api_token = api_token
        self._server_url = server_url
        self._instance = instance
        self._lock = threading.Lock()

    def get_client(self) -> Glean:
        """Get a Glean client, creating one if needed.

        The client is created lazily on first use, cached, and reused
        for the lifetime of this context. Creation is thread-safe.

        Raises:
            GleanCredentialsError: If no API token or server location is
                configured (also a ``ValueError``).
            GleanConfigurationError: If the resolved server URL lacks an
                http(s) scheme (also a ``ValueError``).
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
                raise GleanCredentialsError(_MISSING_TOKEN_MESSAGE)

            if server_url:
                _validate_server_url(server_url)
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
                raise GleanCredentialsError(_MISSING_SERVER_MESSAGE)

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


_default_context: GleanContext | None = None
_default_context_lock = threading.Lock()


def configure(
    *,
    api_token: str | None = None,
    server_url: str | None = None,
    instance: str | None = None,
    client: Glean | None = None,
) -> None:
    """Set process-wide default Glean configuration.

    The configured defaults are used whenever a tool, adapter, or
    :func:`~glean.agent_toolkit.get_tools` call is made without an explicit
    context/client/credentials. Calling :func:`configure` again replaces the
    previous defaults (idempotent), and explicit per-call arguments always
    win over the configured defaults.

    Args:
        api_token: Glean API token (falls back to ``GLEAN_API_TOKEN``).
        server_url: Full Glean server URL including the http(s) scheme,
            e.g. ``https://your-company-be.glean.com`` (falls back to
            ``GLEAN_SERVER_URL``).
        instance: Glean instance name (falls back to ``GLEAN_INSTANCE``).
        client: Pre-configured :class:`~glean.api_client.Glean` client.

    Raises:
        GleanConfigurationError: If *server_url* lacks an http(s) scheme.
    """
    global _default_context
    ctx = GleanContext(
        client=client,
        api_token=api_token,
        server_url=server_url,
        instance=instance,
    )
    with _default_context_lock:
        _default_context = ctx


def get_default_context() -> GleanContext:
    """Return the process-default context for calls without an explicit one.

    When :func:`configure` has been called, its context (and cached client)
    is shared. Otherwise a fresh environment-driven :class:`GleanContext` is
    returned, preserving the pre-:func:`configure` behavior.
    """
    with _default_context_lock:
        ctx = _default_context
    return ctx if ctx is not None else GleanContext()
