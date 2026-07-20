import glean.agent_toolkit

glean.agent_toolkit.configure(
    api_token="your-api-token",
    server_url="https://your-company-be.glean.com",  # or instance="your-company"
)

tools = glean.agent_toolkit.get_tools("langchain")
