import os

from google.adk.agents import Agent

from glean.agent_toolkit.tools import calendar_search, employee_search, glean_search, gmail_search

# Ensure environment variables are set
required_env_vars = ["GLEAN_API_TOKEN", "GLEAN_INSTANCE"]
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable must be set")

# For Google ADK, you also need authentication
# Either set GOOGLE_API_KEY for Google AI Studio, or use gcloud auth for Vertex AI
if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"):
    raise ValueError("Either GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT must be set for ADK")

# Convert Glean tools to Google ADK format
company_search = glean_search.as_adk_tool()
people_finder = employee_search.as_adk_tool()
meeting_search = calendar_search.as_adk_tool()
email_search = gmail_search.as_adk_tool()

# Create a Company Assistant agent
root_agent = Agent(
    name="company_assistant",
    model="gemini-2.0-flash",
    description="""Company Assistant that helps employees find information, people, and resources
    within the organization.""",
    instruction="""You are a helpful company assistant that helps employees find information,
    people, and resources within the organization. You have access to:

    - Company knowledge base and documents (use glean_search)
    - Employee directory and contact information (use employee_search)
    - Calendar and meeting information (use calendar_search)
    - Email search capabilities (use gmail_search)

    Always be helpful, professional, and respect privacy. When searching for people,
    only share appropriate business contact information.""",
    tools=[company_search, people_finder, meeting_search, email_search],
)
