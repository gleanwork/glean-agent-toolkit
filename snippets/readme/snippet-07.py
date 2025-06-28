from glean.agent_toolkit.tools import code_search

# Search company codebases
code_tool = code_search.as_langchain_tool()

# Example queries:
# "Find authentication middleware implementations"
# "Show me recent changes to the payment processing module"
# "Locate configuration files for the staging environment"
