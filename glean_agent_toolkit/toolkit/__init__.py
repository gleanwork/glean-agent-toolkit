"""Universal Tool/Action SDK for agent frameworks."""

from glean_agent_toolkit.toolkit.decorators import tool_spec
from glean_agent_toolkit.toolkit.registry import get_registry
from glean_agent_toolkit.toolkit.spec import ToolSpec

__all__ = ["tool_spec", "get_registry", "ToolSpec"]
__version__ = "0.1.0"
