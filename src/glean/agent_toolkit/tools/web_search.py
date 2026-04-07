"""Web Search tool for searching the internet."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


@tool_spec(
    name="glean_web_search",
    description=(
        "Search the public internet for external, up-to-date information. "
        "Use this instead of glean_search when the user needs current information "
        "outside the company (news, weather, public data, external docs).\n"
        "INSTRUCTIONS:\n"
        "- Use when: user asks to search the web, needs current external info "
        "(news, weather, financial data), or your training data may be outdated.\n"
        "- Use for niche topics where web sources are more reliable than pretraining.\n"
        "- Do NOT use for programming queries or general ideas.\n"
        "- Do NOT use for internal company information (use glean_search instead)."
    ),
)
def web_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description="Web search query containing keywords to search for external information",
            examples=[
                "current stock price Apple",
                "latest news artificial intelligence",
                "weather forecast San Francisco",
                "cryptocurrency market trends 2024",
                "Python 3.13 release notes",
            ],
        ),
    ],
) -> ToolResult:
    """Search the web for up-to-date external information.

    Args:
        ctx: Optional Glean context for client injection.
        query: Web search query containing keywords to search for
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    parameters = convert_to_tool_params(query=query)
    return run_tool("Web Browser", parameters, client=client)
