"""Compatibility helpers for glean-api-client version changes."""

from __future__ import annotations

import warnings
from importlib.metadata import PackageNotFoundError, version


def get_api_client_version() -> str | None:
    """Return the installed glean-api-client version, or None if not found."""
    try:
        return version("glean-api-client")
    except PackageNotFoundError:
        return None


def check_api_client_compatibility() -> None:
    """Emit deprecation warnings for glean-api-client versions with known breaking changes.

    Call this once at import time or on first use to alert users early.
    """
    ver = get_api_client_version()
    if ver is None:
        return

    # Add entries here as upstream breaking changes are discovered.
    # Each tuple: (version_prefix, message)
    _known_breaks: list[tuple[str, str]] = [
        # Example for a future break:
        # ("1.0", "glean-api-client>=1.0 renamed client.tools.run() to client.tools.execute()."),
    ]

    for prefix, msg in _known_breaks:
        if ver.startswith(prefix):
            warnings.warn(
                f"{msg} Installed version: {ver}. "
                "Please update glean-agent-toolkit or pin a compatible glean-api-client version.",
                DeprecationWarning,
                stacklevel=2,
            )


def resolve_method(obj: object, preferred: str, *fallbacks: str) -> object:
    """Look up a method by name with fallback alternatives.

    Tries *preferred* first, then each name in *fallbacks*.  If a fallback is
    used, a ``DeprecationWarning`` is emitted so callers know the upstream API
    has changed.

    Raises ``AttributeError`` with a descriptive message when none of the
    names exist.
    """
    if hasattr(obj, preferred):
        return getattr(obj, preferred)

    for name in fallbacks:
        if hasattr(obj, name):
            warnings.warn(
                f"glean-api-client method '{preferred}' not found; "
                f"falling back to '{name}'. This may indicate an API client "
                "version mismatch. Please update glean-agent-toolkit.",
                DeprecationWarning,
                stacklevel=2,
            )
            return getattr(obj, name)

    tried = ", ".join([preferred, *fallbacks])
    obj_type = type(obj).__name__
    ver = get_api_client_version() or "unknown"
    raise AttributeError(
        f"None of the expected methods ({tried}) exist on "
        f"'{obj_type}' (glean-api-client=={ver}). "
        "The upstream API client may have renamed this method. "
        "Please update glean-agent-toolkit to a version compatible "
        "with your installed glean-api-client."
    )
