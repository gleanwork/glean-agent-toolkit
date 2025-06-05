"""AI Web Search tool for searching the internet with AI-powered results."""

from __future__ import annotations

from typing import Any

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import run_tool
from glean.api_client import models


@tool_spec(
    name="ai_web_search",
    description=(
        "Searches the web for up-to-date external information and generates a well structured "
        "response to the user query grounded in relevant webpages. Closely evaluate the "
        "instructions below for the user query to decide whether to use the web agent. If you "
        "think the scenarios are contradictory, do not use the web agent unless there is clear "
        "user intent. If you think the user query is ambiguous, use the Conversation history to "
        "infer the context.\n"
        "INSTRUCTIONS:\n"
        "Examples of when to use this tool:\n"
        "- User Intent: Use this tool if the user is asking you to search the web, look online, "
        "provide links/sources, or explicitly looking for current external information (outside "
        "of the company) like weather, news, or latest updates/plans.\n"
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
def ai_web_search(parameters: dict[str, models.ToolsCallParameter]) -> dict[str, Any]:
    """Search the web for up-to-date external information."""
    return run_tool("Gemini Web Search", parameters)
