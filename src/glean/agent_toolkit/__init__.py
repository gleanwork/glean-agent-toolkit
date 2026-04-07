"""
Glean Agent Toolkit.

Universal Tool/Action Toolkit for Glean agent frameworks.
"""

import logging
from importlib.metadata import PackageNotFoundError, version

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.registry import Registry, get_registry
from glean.agent_toolkit.spec import ToolSpec

from . import adapters

__all__ = [
    "GleanContext",
    "tool_spec",
    "get_registry",
    "Registry",
    "ToolSpec",
    "adapters",
    "__version__",
]

try:
    __version__ = version("glean-agent-toolkit")
except PackageNotFoundError:  # pragma: no cover – package not installed
    __version__ = "0.0.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
