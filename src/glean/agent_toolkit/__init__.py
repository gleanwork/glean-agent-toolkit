"""
Glean Agent Toolkit.

Universal Tool/Action Toolkit for Glean agent frameworks.
"""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.registry import Registry, get_registry
from glean.agent_toolkit.spec import ToolSpec
from glean.agent_toolkit.tools._common import configure

from . import adapters

__all__ = [
    "configure",
    "get_tools",
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

# Ensure all built-in tools are registered on import.
from glean.agent_toolkit import tools as _tools  # noqa: E402, F811


def get_tools(
    framework: Literal["openai", "langchain", "crewai", "adk"],
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    api_token: str | None = None,
    server_url: str | None = None,
) -> list[Any]:
    """Get all toolkit tools converted for a specific framework.

    Args:
        framework: Target framework ("openai", "langchain", "crewai", "adk").
        include: Only include these tools (by name). ``None`` means all.
        exclude: Exclude these tools (by name). ``None`` means none.
        api_token: Glean API token.  Falls back to ``GLEAN_API_TOKEN`` env var.
        server_url: Glean server URL.  Falls back to ``GLEAN_SERVER_URL`` env var.

    Returns:
        List of framework-specific tool objects.

    Raises:
        ValueError: If both *include* and *exclude* are provided, or if the
            *framework* value is not recognised.
    """
    if include is not None and exclude is not None:
        raise ValueError("Cannot specify both 'include' and 'exclude'")

    adapter_method = {
        "openai": "as_openai_tool",
        "langchain": "as_langchain_tool",
        "crewai": "as_crewai_tool",
        "adk": "as_adk_tool",
    }.get(framework)

    if adapter_method is None:
        raise ValueError(
            f"Unknown framework {framework!r}. " f"Choose from: openai, langchain, crewai, adk"
        )

    if api_token is not None or server_url is not None:
        configure(api_token=api_token, server_url=server_url)

    specs = get_registry().list()

    if include is not None:
        include_set = set(include)
        specs = [s for s in specs if s.name in include_set]
    elif exclude is not None:
        exclude_set = set(exclude)
        specs = [s for s in specs if s.name not in exclude_set]

    result: list[Any] = []
    for spec in specs:
        # Each ToolSpec is wrapped by the @tool_spec decorator which attaches
        # as_<framework>_tool() helpers.  The adapters are also accessible via
        # the adapter classes directly.
        from glean.agent_toolkit.adapters.adk import ADKAdapter
        from glean.agent_toolkit.adapters.crewai import CrewAIAdapter
        from glean.agent_toolkit.adapters.langchain import LangChainAdapter
        from glean.agent_toolkit.adapters.openai import OpenAIAdapter

        adapter_cls: type = {
            "openai": OpenAIAdapter,
            "langchain": LangChainAdapter,
            "crewai": CrewAIAdapter,
            "adk": ADKAdapter,
        }[framework]

        adapter = adapter_cls(spec)
        result.append(adapter.to_tool())

    return result
