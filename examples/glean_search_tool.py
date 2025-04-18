#!/usr/bin/env python3
"""Example of a Glean search tool using the Glean Agent Toolkit."""

import json

from pydantic import BaseModel

from glean_agent_toolkit.toolkit import tool_spec


class SearchResult(BaseModel):
    """A single search result from Glean."""

    title: str
    url: str
    snippet: str
    datasource: str
    score: float


class SearchResponse(BaseModel):
    """Response from a Glean search query."""

    results: list[SearchResult]
    total_results: int
    query: str
    execution_time_ms: float


@tool_spec(
    name="glean_search",
    description="Search Glean for documents matching a query",
    output_model=SearchResponse,
    version="1.0.0",
)
def glean_search(
    query: str,
    max_results: int = 5,
    datasource_filter: list[str] | None = None,
) -> SearchResponse:
    """Search Glean for documents matching a query.

    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        datasource_filter: Optional list of datasources to filter by

    Returns:
        A SearchResponse object containing the search results
    """
    # In a real implementation, this would call the Glean API
    # This is a mock implementation for demonstration purposes

    # Simulate API call latency and response
    results = [
        SearchResult(
            title="Glean Architecture Overview",
            url="https://docs.glean.com/architecture",
            snippet="Comprehensive architecture diagram and explanation of Glean's "
            "core components...",
            datasource="Confluence",
            score=0.95,
        ),
        SearchResult(
            title="Agent Toolkit Design Doc",
            url="https://docs.glean.com/agent-toolkit",
            snippet="The Agent Toolkit provides a universal interface for defining tools...",
            datasource="Google Docs",
            score=0.87,
        ),
        SearchResult(
            title="Implementing Custom Tools",
            url="https://docs.glean.com/custom-tools",
            snippet="Tutorial on implementing custom tools for Glean agents using the toolkit...",
            datasource="Notion",
            score=0.82,
        ),
    ]

    # Apply datasource filter if provided
    if datasource_filter:
        results = [r for r in results if r.datasource in datasource_filter]

    # Limit results
    results = results[:max_results]

    return SearchResponse(
        results=results,
        total_results=len(results),
        query=query,
        execution_time_ms=120.5,
    )


def main() -> None:
    """Run the example."""
    # Test the search function
    response = glean_search("agent toolkit", max_results=2)
    print("Search Results:")
    for idx, result in enumerate(response.results, 1):
        print(f"{idx}. {result.title} ({result.datasource}) - {result.score:.2f}")
        print(f"   {result.snippet}")
        print(f"   {result.url}")
        print()

    # Get OpenAI tool definition
    openai_tool = glean_search.as_openai_tool()
    print("\nOpenAI Tool Definition:")
    print(json.dumps(openai_tool, indent=2))

    # Get LangChain tool
    try:
        langchain_tool = glean_search.as_langchain_tool()
        print("\nLangChain Tool Name:", langchain_tool.name)
        print("LangChain Tool Description:", langchain_tool.description)
    except ImportError:
        print("\nLangChain not installed - skipping LangChain tool example")


if __name__ == "__main__":
    main()
