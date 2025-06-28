import os

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from glean.agent_toolkit.tools import glean_search

# Ensure environment variables are set
assert os.getenv("GLEAN_API_TOKEN"), "GLEAN_API_TOKEN must be set"
assert os.getenv("GLEAN_INSTANCE"), "GLEAN_INSTANCE must be set"

# Convert to LangChain tool format
langchain_tool = glean_search.as_langchain_tool()

llm = ChatOpenAI(model="gpt-4", temperature=0)
tools = [langchain_tool]

prompt_template = """You are a helpful assistant with access to company knowledge.
Use the glean_search tool to find relevant information when users ask questions.

Tools available:
{tools}

Use this format:
Question: {input}
Thought: I should search for information about this topic
Action: {tool_names}
Action Input: your search query
Observation: the search results
Thought: I can now provide a helpful response
Final Answer: your response based on the search results

Question: {input}
{agent_scratchpad}"""

prompt = ChatPromptTemplate.from_template(prompt_template)
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Search for company information
result = agent_executor.invoke({"input": "What is our vacation policy?"})
print(result["output"])
