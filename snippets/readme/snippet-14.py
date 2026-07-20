import asyncio

from glean.agent_toolkit import get_tools


async def main() -> None:
    """Run glean_search through LangChain's native async path."""
    (search_tool,) = get_tools("langchain", include=["glean_search"])
    output = await search_tool.ainvoke({"query": "quarterly results", "page_size": 5})
    print(output)


asyncio.run(main())
