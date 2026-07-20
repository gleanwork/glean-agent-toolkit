import os

from agents import Agent, Runner

from glean.agent_toolkit.tools import search

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_SERVER_URL"), "GLEAN_SERVER_URL must be set"
assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY must be set"

# Create an agent with the Glean search tool
agent = Agent(
    name="KnowledgeAssistant",
    instructions="""You help users find information from the company knowledge base using
    Glean search.""",
    tools=[search.as_openai_tool()],  # Convert to an Agents SDK FunctionTool
)

# Run a search query
result = Runner.run_sync(agent, "Find our Q4 planning documents")
print(f"Search results: {result.final_output}")
