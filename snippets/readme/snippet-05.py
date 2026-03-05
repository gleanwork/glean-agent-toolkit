import os

from crewai import Agent, Crew, Task

from glean.agent_toolkit.tools import search

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_SERVER_URL"), "GLEAN_SERVER_URL must be set"

# Convert to CrewAI tool format
crewai_tool = search.as_crewai_tool()

# Create a research agent
researcher = Agent(
    role="Corporate Knowledge Researcher",
    goal="Find and summarize relevant company information",
    backstory="""You are an expert at navigating company knowledge bases to find accurate,
    up-to-date information.""",
    tools=[crewai_tool],
    verbose=True,
)

# Create a research task
research_task = Task(
    description="""Find information about our company's remote work policy and summarize the key
    points.""",
    expected_output="""A clear summary of the remote work policy including eligibility,
    expectations, and guidelines.""",
    agent=researcher,
)

# Execute the research
crew = Crew(agents=[researcher], tasks=[research_task])
result = crew.kickoff()
print(result)
