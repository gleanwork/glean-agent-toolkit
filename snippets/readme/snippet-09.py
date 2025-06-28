from glean.agent_toolkit.tools import ai_web_search, web_search

# External information gathering
web_tool = web_search.as_langchain_tool()
ai_web_tool = ai_web_search.as_langchain_tool()

# Example queries:
# "Latest industry trends in machine learning"
# "Current market analysis for SaaS companies"
# "Recent news about our competitors"
