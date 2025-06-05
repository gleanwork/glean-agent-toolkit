"""
Each tool lives in its own module under :pymod:`glean.agent_toolkit.tools`.

Importing this package will load all available tools.
"""

from __future__ import annotations

from importlib import import_module as _import_module

_tool_modules: list[str] = [
    "glean_search",
    "web_search",
    "ai_web_search",
    "calendar_search",
    "employee_search",
    "code_search",
    "gmail_search",
    "outlook_search",
]

for _mod in _tool_modules:
    _import_module(f"{__name__}.{_mod}")

from .ai_web_search import ai_web_search  # noqa: E402
from .calendar_search import calendar_search  # noqa: E402
from .code_search import code_search  # noqa: E402
from .employee_search import employee_search  # noqa: E402
from .glean_search import glean_search  # noqa: E402
from .gmail_search import gmail_search  # noqa: E402
from .outlook_search import outlook_search  # noqa: E402
from .web_search import web_search  # noqa: E402

__all__: list[str] = [
    "glean_search",
    "web_search",
    "ai_web_search",
    "calendar_search",
    "employee_search",
    "code_search",
    "gmail_search",
    "outlook_search",
]
