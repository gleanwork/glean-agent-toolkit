"""Employee Search tool for finding people profiles in the company."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import convert_to_tool_params, run_tool

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext


@tool_spec(
    name="employee_search",
    description=(
        "Find people at the company based on their personal information.\n"
        "INSTRUCTIONS:\n"
        "- Only use this when the user explicitly wants to find people in the company (e.g.,"
        ' "who" questions) or for aggregation queries on people.\n'
        "- You can also use this tool to find personal information about employees (e.g., what is "
        "person X's phone number or email address).\n"
        "- Do not use this when the user wants to find people outside of the company, or people "
        "who are no longer at the company.\n"
        "- You can find people based on details such as name, email, title, department, and "
        "location.\n"
        "- The results returned are not exhaustive; we only return the top few most relevant "
        "people to a query.\n"
        '- For analytics questions such as "how many people..." use the "statistics" field '
        "in the output."
    ),
)
def employee_search(
    ctx: GleanContext | None = None,
    *,
    query: Annotated[
        str,
        Field(
            description=(
                "Employee search query with optional filters. Supports person names, roles, "
                "departments, plus filters like 'roletype:', 'startafter:', 'startbefore:', "
                "'reportsto:'"
            ),
            examples=[
                "John Smith engineering manager",
                "data scientist machine learning",
                "roletype:manager startafter:2023-01-01",
                "frontend developer React",
                'reportsto:"Jane Doe"',
            ],
        ),
    ],
) -> dict[str, Any]:
    """Search for employees based on the query.

    Args:
        ctx: Glean context for client access
        query: Employee search query with optional filters
        like 'roletype:manager startafter:2023-01-01'
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    parameters = convert_to_tool_params(query=query)
    client = ctx.get_client()
    return run_tool("Employee Search", parameters, client=client)
