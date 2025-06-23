from glean.agent_toolkit.tools import employee_search

# Find engineering team members
engineering_team = employee_search.as_langchain_tool()

# Example usage in an agent:
# "Who are the senior engineers in the backend team?"
# "Find Sarah Johnson's contact information"
# "List all product managers in the San Francisco office"
