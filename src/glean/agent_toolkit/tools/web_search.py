"""Web Search tool for searching the internet."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult, convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


@tool_spec(
    name="web_search",
    description=(
        "Can search for up-to-date external information from the web. Closely evaluate the "
        "instructions below for the user query to decide whether to use web search. If you think "
        "the scenarios are contradictory, do not use web search unless there is clear user intent."
        "\n"
        "INSTRUCTIONS:\n"
        "Examples of when to use this tool:\n"
        "- User Intent: Use this tool if the user is asking you to search the web, look online, "
        "provide links/sources, or explicitly looking for current external information (outside "
        "of the company) like weather, news, latest updates/plans, or financial data.\n"
        "- Freshness: Use this tool if you need up-to-date information on time-dependent topics "
        "or any time you would otherwise refuse to answer a question because your knowledge might "
        "be out of date.\n"
        "- Niche Information: If the answer would likely change based on detailed information not "
        "widely known or understood (which might be found on the internet), use web sources "
        "directly rather than relying on the distilled knowledge from pretraining.\n"
        "- Do NOT use this tool for programming related queries. You already know enough about "
        "those.\n"
        "- Do NOT use this tool for queries seeking general ideas, which may not benefit from "
        "specific information."
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
