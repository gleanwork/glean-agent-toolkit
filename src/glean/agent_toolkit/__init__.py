"""
Glean Agent Toolkit.

Universal Tool/Action Toolkit for Glean agent frameworks.
"""

from __future__ import annotations

import logging
import warnings
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from glean.agent_toolkit.context import GleanContext
from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.registry import Registry, get_registry
from glean.agent_toolkit.spec import ToolSpec

from . import adapters

__all__ = [
    "BUILTIN_TOOL_NAMES",
    "GleanContext",
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

_ADAPTER_CLASSES: dict[str, str] = {
    "openai": "glean.agent_toolkit.adapters.openai.OpenAIAdapter",
    "langchain": "glean.agent_toolkit.adapters.langchain.LangChainAdapter",
    "crewai": "glean.agent_toolkit.adapters.crewai.CrewAIAdapter",
    "adk": "glean.agent_toolkit.adapters.adk.ADKAdapter",
}

#: Names of the built-in Glean tools shipped with this package.
BUILTIN_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "glean_calendar_search",
        "glean_chat",
        "glean_code_search",
        "glean_employee_search",
        "glean_gmail_search",
        "glean_outlook_search",
        "glean_read_document",
        "glean_search",
        "glean_web_search",
    }
)


def get_tools(
    framework: str,
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    builtin: bool | None = None,
    client: Any | None = None,
    api_token: str | None = None,
    server_url: str | None = None,
    instance: str | None = None,
) -> list[Any]:
    """Return framework-adapted tools filtered by include/exclude.

    The tool registry is **global**: by default this returns every tool
    registered in the current process, which includes both the built-in
    ``glean_*`` tools and any user-defined tools registered via
    :func:`tool_spec`. Use *builtin* (or *include*/*exclude*) to scope
    the result.

    Args:
        framework: One of ``"openai"``, ``"langchain"``, ``"crewai"``, ``"adk"``.
        include: If given, only return tools whose names are in this list.
        exclude: If given, skip tools whose names are in this list.
        builtin: If ``True``, only return the built-in Glean tools (see
            :data:`BUILTIN_TOOL_NAMES`). If ``False``, only return
            user-registered tools. If ``None`` (default), return all
            registered tools. Applied in addition to *include*/*exclude*.
        client: Pre-configured :class:`~glean.api_client.Glean` instance.
        api_token: Glean API token (falls back to ``GLEAN_API_TOKEN``).
        server_url: Glean server URL (falls back to ``GLEAN_SERVER_URL``).
        instance: Glean instance name (falls back to ``GLEAN_INSTANCE``).

    Returns:
        List of framework-specific tool objects.

    Raises:
        ValueError: If *framework* is not recognised.
        ImportError: If the framework's adapter dependency is missing.
    """
    import glean.agent_toolkit.tools  # noqa: F811 – ensure all tools registered

    if framework not in _ADAPTER_CLASSES:
        raise ValueError(
            f"Unknown framework {framework!r}. Choose from: {', '.join(sorted(_ADAPTER_CLASSES))}"
        )

    ctx = GleanContext(client=client, api_token=api_token, server_url=server_url, instance=instance)

    adapter_path = _ADAPTER_CLASSES[framework]
    module_path, class_name = adapter_path.rsplit(".", 1)

    import importlib

    mod = importlib.import_module(module_path)
    adapter_cls = getattr(mod, class_name)

    include_set = set(include) if include else None
    exclude_set = set(exclude) if exclude else set()

    results: list[Any] = []
    for spec in get_registry().list():
        if include_set is not None and spec.name not in include_set:
            continue
        if spec.name in exclude_set:
            continue
        if builtin is True and spec.name not in BUILTIN_TOOL_NAMES:
            continue
        if builtin is False and spec.name in BUILTIN_TOOL_NAMES:
            continue

        adapter = adapter_cls(spec, ctx)
        try:
            results.append(adapter.to_tool())
        except Exception as exc:  # noqa: BLE001 - one bad tool must not sink the list
            warnings.warn(
                f"Skipping tool {spec.name!r}: failed to convert for framework "
                f"{framework!r}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )

    return results
