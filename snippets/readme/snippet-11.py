from glean.agent_toolkit import get_tools

# The nine built-in Glean tools, converted to LangChain StructuredTools.
# Credentials are read from GLEAN_API_TOKEN and GLEAN_SERVER_URL.
tools = get_tools("langchain")

# Bind them to any LangChain / LangGraph agent, e.g.:
#   from langgraph.prebuilt import create_react_agent
#   agent = create_react_agent(llm, tools)
print([tool.name for tool in tools])
