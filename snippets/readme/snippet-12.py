from agents import Agent, Runner

from glean.agent_toolkit import get_tools

agent = Agent(
    name="KnowledgeAssistant",
    instructions="Answer questions using Glean enterprise search.",
    tools=get_tools("openai"),
)

result = Runner.run_sync(agent, "Find our Q4 planning documents")
print(result.final_output)
