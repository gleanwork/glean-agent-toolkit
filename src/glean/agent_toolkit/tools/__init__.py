"""
Each tool lives in its own module under :pymod:`glean.agent_toolkit.tools`.

Importing this package will load all available tools.
"""

from __future__ import annotations

import warnings
from importlib import import_module as _import_module
from typing import Any

_tool_modules: list[str] = [
    "search",
    "web_search",
    "calendar_search",
    "employee_search",
    "code_search",
    "gmail_search",
    "outlook_search",
    "read_document",
    "_chat",
]

for _mod in _tool_modules:
    _import_module(f"{__name__}.{_mod}")

from ._chat import chat  # noqa: E402
from ._common import ToolResult  # noqa: E402
from .calendar_search import calendar_search  # noqa: E402
from .code_search import code_search  # noqa: E402
from .employee_search import employee_search  # noqa: E402
from .gmail_search import gmail_search  # noqa: E402
from .outlook_search import outlook_search  # noqa: E402
from .read_document import read_document  # noqa: E402
from .search import search  # noqa: E402
from .web_search import web_search  # noqa: E402

__all__: list[str] = [
    "ToolResult",
    "search",
    "web_search",
    "calendar_search",
    "employee_search",
    "code_search",
    "gmail_search",
    "outlook_search",
    "read_document",
    "chat",
]


def __getattr__(name: str) -> Any:
    """Resolve deprecated attribute names (PEP 562).

    ``glean_chat`` is a deprecated alias for :func:`chat`; the tool ID
    remains ``"glean_chat"``.
    """
    if name == "glean_chat":
        warnings.warn(
            "'glean_chat' is deprecated; import 'chat' instead "
            "(from glean.agent_toolkit.tools import chat). "
            "The tool ID remains 'glean_chat'.",
            DeprecationWarning,
            stacklevel=2,
        )
        return chat
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
