from glean.agent_toolkit.tools import calendar_search, gmail_search

# Search emails and meetings
gmail_tool = gmail_search.as_langchain_tool()
calendar_tool = calendar_search.as_langchain_tool()

# Example queries:
# "Find emails about the product launch from last month"
# "Show me my meetings with the design team this week"
# "Search for messages containing budget discussions"
