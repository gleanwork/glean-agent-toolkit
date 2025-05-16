"""Built-in stub tools delivered with Glean Toolkit.

Each tool lives in its own module under :pymod:`glean.toolkit.tools`. Importing this package
registers every stub via its ``@tool_spec`` decorator and re-exports the
callables for convenience::

    from glean.toolkit.tools import glean_search, web_browser

"""

from __future__ import annotations

from importlib import import_module as _import_module

_tool_modules: list[str] = [
    "glean_search",
    "web_browser",
    "gemini_web_search",
    "meeting_lookup",
    "expert_search",
    "employee_search",
    "code_search",
    "gmail_search",
    "outlook_search",
]

for _mod in _tool_modules:
    _import_module(f"{__name__}.{_mod}")

from .code_search import code_search  # noqa: E402
from .employee_search import employee_search  # noqa: E402
from .expert_search import expert_search  # noqa: E402
from .gemini_web_search import gemini_web_search  # noqa: E402
from .glean_search import glean_search  # noqa: E402  pylint: disable=wrong-import-position
from .gmail_search import gmail_search  # noqa: E402
from .meeting_lookup import meeting_lookup  # noqa: E402
from .outlook_search import outlook_search  # noqa: E402
from .web_browser import web_browser  # noqa: E402

__all__: list[str] = [
    "glean_search",
    "web_browser",
    "gemini_web_search",
    "meeting_lookup",
    "expert_search",
    "employee_search",
    "code_search",
    "gmail_search",
    "outlook_search",
]
