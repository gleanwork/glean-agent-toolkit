"""Backward-compatibility helpers for Glean API client changes."""

from __future__ import annotations

import warnings
from importlib.metadata import PackageNotFoundError, version
from typing import Any


def resolve_method(obj: Any, preferred: str, *fallbacks: str) -> Any:
    """Return the first available method, warning on fallback usage.

    Args:
        obj: The object to search for the method on.
        preferred: The preferred method name.
        *fallbacks: Alternative method names to try in order.

    Returns:
        The bound method.

    Raises:
        AttributeError: If neither *preferred* nor any fallback exists.
    """
    method = getattr(obj, preferred, None)
    if method is not None:
        return method

    for name in fallbacks:
        method = getattr(obj, name, None)
        if method is not None:
            warnings.warn(
                f"{type(obj).__name__}.{preferred}() not found; "
                f"falling back to .{name}(). "
                f"This fallback will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            return method

    tried = ", ".join([preferred, *fallbacks])
    raise AttributeError(f"{type(obj).__name__} has none of the expected methods: {tried}")


def get_api_client_version() -> str | None:
    """Return the installed ``glean-api-client`` version, or ``None``."""
    try:
        return version("glean-api-client")
    except PackageNotFoundError:
        return None


def check_api_client_compatibility() -> None:
    """Warn if the installed API client version has known incompatibilities.

    Currently no versions are flagged, but this function provides the
    hook for future compatibility checks.
    """
    _breaking_versions: list[str] = []

    installed = get_api_client_version()
    if installed is None:
        return

    if installed in _breaking_versions:
        warnings.warn(
            f"glean-api-client {installed} has known compatibility issues "
            f"with glean-agent-toolkit. Consider upgrading.",
            UserWarning,
            stacklevel=2,
        )
