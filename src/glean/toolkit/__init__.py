"""Universal Tool/Action SDK for agent frameworks."""

import logging
from importlib.metadata import PackageNotFoundError, version

from glean.toolkit.decorators import tool_spec
from glean.toolkit.registry import get_registry
from glean.toolkit.spec import ToolSpec

from . import adapters

__all__ = [
    "tool_spec",
    "get_registry",
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
