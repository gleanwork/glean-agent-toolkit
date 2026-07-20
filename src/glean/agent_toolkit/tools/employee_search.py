"""Employee Search tool for finding people profiles in the company."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from glean.agent_toolkit.decorators import tool_spec
from glean.agent_toolkit.tools._common import ToolResult
from glean.agent_toolkit.tools._transport import (
    ToolsCallBackend,
    execute_tool,
    register_backend,
)

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

register_backend("glean_employee_search", ToolsCallBackend("Employee Search"))


@tool_spec(
    name="glean_employee_search",
    description=(
        "Find current employees and their contact info, role, department, and org structure. "
        'Use for "who" questions about people inside the company.\n'
        "INSTRUCTIONS:\n"
        "- Search by name, email, title, department, or location.\n"
        "- Only for current employees; not for external or former people.\n"
        "- Returns top results, not exhaustive.\n"
        '- For count queries ("how many people..."), use the "statistics" field in the output.'
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
) -> ToolResult:
    """Search for employees based on the query.

    Args:
        ctx: Optional Glean context for client injection.
        query: Employee search query with optional filters
        like 'roletype:manager startafter:2023-01-01'
    """
    from glean.agent_toolkit.context import GleanContext

    ctx = ctx or GleanContext()
    client = ctx.get_client()
    return execute_tool("glean_employee_search", {"query": query}, client=client)
