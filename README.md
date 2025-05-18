# Glean Agent Toolkit

The Glean Agent Toolkit makes it easy to integrate Glean's powerful search and knowledge discovery capabilities into your AI agents. Use our pre-built tools with popular agent frameworks like OpenAI Assistants, LangChain, CrewAI, and Google's Agent Development Kit (ADK), or adapt your own custom tools for cross-framework use.

## Key Features

* **Pre-built Glean Tools:** Instantly add capabilities like enterprise search, employee lookup, calendar search, and more to your agents.
* **Framework Adapters:** Seamlessly convert Glean tools into formats compatible with major agent SDKs.
* **Custom Tool Creation:** Define your own tools once using the `@tool_spec` decorator and use them across any supported framework.

## Installation

Install the base toolkit:

```bash
pip install glean-agent-toolkit
```

To include support for specific agent frameworks, install the relevant extras:

```bash
pip install glean-agent-toolkit[openai]
pip install glean-agent-toolkit[adk]
pip install glean-agent-toolkit[langchain]
pip install glean-agent-toolkit[crewai]
```

You can also install all extras:

```bash
pip install glean-agent-toolkit[all]
```

Note: The `[openai]` extra installs the standard `openai` Python library, used for direct API interactions like Chat Completions or the Assistants API. The example below for the "OpenAI Agents SDK" uses a separate library, `openai-agents`, which you'll need to install independently: `pip install openai-agents`.

## Glean's LLM-ready Tools

The toolkit comes with a suite of pre-defined tools that connect to various Glean functionalities. You can import these tools from `glean.toolkit.tools` and adapt them for your chosen agent framework.

**Available Built-in Tools (Stubs):**

* `glean_search`: Search Glean for relevant documents.
* `web_browser`: Fetch content from a public URL.
* `gemini_web_search`: Query Google Gemini for web information.
* `meeting_lookup`: Retrieve meeting details from calendar services.
* `expert_search`: Find internal experts on a given subject.
* `employee_search`: Search for employees by name, team, or expertise.
* `code_search`: Search company source code.
* `gmail_search`: Search Gmail messages.
* `outlook_search`: Search Outlook mail messages.

### Example: Using `glean_search`

Below are examples of how to use the `glean_search` tool with different agent frameworks.

#### OpenAI Agents SDK

The OpenAI Agents SDK (`openai-agents`) is a lightweight, Python-first library for building agentic applications. You'll need to install it separately: `pip install openai-agents`

Ensure your `OPENAI_API_KEY` environment variable is set to use this SDK.

```python
from glean.toolkit.tools import glean_search
from agents import Agent, Runner # From the openai-agents SDK
import os

# Ensure OPENAI_API_KEY is set for the Agent to make LLM calls
if not os.getenv("OPENAI_API_KEY"):
    print("Error: The OPENAI_API_KEY environment variable is not set.")
    # In a real application, you might exit or raise an error here.
    # For this example, we'll print a message and proceed,
    # but the Agent will likely fail to initialize or run.
    
# 'glean_search' is a ToolSpec instance from glean-agent-toolkit.
# 'glean_search.func' is the underlying Python function.
# 'glean_search.name' is the tool name defined in @tool_spec.
# 'glean_search.description' is the tool description from @tool_spec.

# The 'openai-agents' SDK typically expects a raw Python function for its tools.
# It will use the function's __name__, __doc__ (docstring), and signature
# to define the tool for the LLM.
agent_tool_function = glean_search.func

# Note: For the LLM to see the intended tool name (e.g., "glean_search") and description,
# ensure that agent_tool_function.__name__ and agent_tool_function.__doc__
# are aligned with what's defined in the @tool_spec for 'glean_search'.
# For built-in tools from `glean.toolkit.tools`, this alignment is generally expected.
# If they differ significantly (e.g., if @tool_spec's 'name' overrides a different function name),
# the LLM might see the original function's metadata.

print(f"Preparing agent with tool: {getattr(agent_tool_function, '__name__', 'unknown_function_name')}")

try:
    agent = Agent(
        name="GleanSearchAgent", # An arbitrary name for this agent instance, useful for tracing
        instructions="You are a helpful assistant. Use the provided search tool to find documents based on the user's query.",
        tools=[agent_tool_function]
        # The 'tools' parameter expects a list of callable Python functions.
        # The SDK automatically generates the necessary schema for the LLM.
    )

    user_query = "Search Glean for 'Q3 sales report'"
    print(f"Running agent with query: \"{user_query}\"")

    # Runner.run_sync executes the agent loop.
    # If the LLM decides to use 'agent_tool_function', the SDK will attempt to call it.
    # Since glean_search.func is a stub, it's expected to raise NotImplementedError.
    result = Runner.run_sync(agent, user_query)

    if result.is_success():
        print("\nAgent run successful.")
        print(f"Final output: {result.final_output}")
    else:
        print("\nAgent run failed.")
        print(f"Failure reason: {result.failure_reason}")
        if result.error:
            # If the tool raised NotImplementedError, it should be caught by the runner
            # and reflected in result.error.
            if isinstance(result.error, NotImplementedError):
                print(f"Tool '{glean_search.name}' is a stub and not implemented: {result.error}")
            else:
                # Display other errors that might have occurred during the run.
                print(f"Error details: {result.error}")
        
        # For debugging, you might want to inspect the history of events:
        # print("\nAgent history:")
        # for event in result.history:
        #     print(f"- {event.type}: {getattr(event, 'content', '')}")


except openai.APIError as e: # More specific catch for OpenAI API key issues
    print(f"OpenAI API Error: {e}. Please check your OPENAI_API_KEY and API access.")
except Exception as e:
    # Catch any other unexpected errors during agent setup or run execution.
    print(f"An unexpected error occurred: {e}")

```

#### LangChain

```python
from glean.toolkit.tools import glean_search
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate # Or your preferred prompt

# Adapt for LangChain
langchain_glean_search_tool = glean_search.as_langchain_tool()

llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
tools = [langchain_glean_search_tool]

# A simple ReAct prompt (replace with your actual prompt)
prompt_template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

prompt = ChatPromptTemplate.from_template(prompt_template)


try:
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    result = agent_executor.invoke({"input": "Search Glean for 'Q3 sales report'"})
    print(result)
except NotImplementedError as e:
    print(f"Tool '{glean_search.name}' is a stub: {e}")
except Exception as e:
    print(f"An error occurred: {e}")

```

#### CrewAI

```python
from glean.toolkit.tools import glean_search
from crewai import Agent, Task, Crew

# Adapt for CrewAI
crewai_glean_search_tool = glean_search.as_crewai_tool()

researcher = Agent(
    role="Corporate Researcher",
    goal="Find internal company documents based on queries",
    backstory="An AI assistant skilled in navigating Glean to find relevant documents.",
    tools=[crewai_glean_search_tool],
    verbose=True,
)

search_task = Task(
    description="Search Glean for the 'Q3 sales report'.",
    expected_output="A summary of the findings or an indication if the report was found.",
    agent=researcher,
)

company_crew = Crew(agents=[researcher], tasks=[search_task])

try:
    result = company_crew.kickoff()
    print(result)
except NotImplementedError as e:
    print(f"Tool '{glean_search.name}' is a stub: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
```

#### Google ADK (Agent Development Kit)

```python
from glean.toolkit.tools import glean_search
# Assuming Google ADK's Agent and other necessary imports are available
# from google.adk import Agent 

# Adapt for ADK
adk_glean_search_tool = glean_search.as_adk_tool()

# Example (conceptual, actual ADK usage may vary):
# try:
#     agent = Agent(tools=[adk_glean_search_tool])
#     response = agent.generate_content("Search Glean for 'Q3 sales report'")
#     print(response)
# except ImportError:
#     print("Google ADK not installed or Agent class not found.")
# except NotImplementedError as e:
#     print(f"Tool '{glean_search.name}' is a stub: {e}")
# except Exception as e:
#     print(f"An error occurred: {e}")

print("Note: Google ADK example is conceptual as ADK usage can vary.")
print(f"To use ADK, ensure it's installed and integrate '{adk_glean_search_tool.name}' as per ADK documentation.")

```

## Creating Custom Tools with `@tool_spec`

If you have your own functions that you'd like to use as tools across different agent frameworks, the `glean.toolkit.tool_spec` decorator provides a simple way to define them once.

```python
from glean.toolkit import tool_spec
from pydantic import BaseModel

# 1. Define your function
def get_weather(city: str, unit: str = "celsius") -> str:
    # Replace with actual weather fetching logic
    if city == "London":
        return f"The weather in London is 15 degrees {unit} and cloudy."
    return f"Weather data for {city} not found."

# 2. Define an optional output model (for more complex responses)
class WeatherResponse(BaseModel):
    temperature: int
    unit: str
    description: str
    city: str

def get_structured_weather(city: str, unit: str = "celsius") -> WeatherResponse:
    # Replace with actual weather fetching logic
    if city == "London":
        return WeatherResponse(temperature=15, unit=unit, description="cloudy", city=city)
    raise ValueError(f"Weather data for {city} not found.")

# 3. Decorate your function with @tool_spec
@tool_spec(name="get_current_weather", description="Fetches the current weather for a given city.")
def decorated_get_weather(city: str, unit: str = "celsius") -> str:
    return get_weather(city, unit)

@tool_spec(
    name="get_structured_weather_forecast",
    description="Fetches a structured weather forecast for a city.",
    output_model=WeatherResponse # Specify your Pydantic model here
)
def decorated_get_structured_weather(city: str, unit: str = "celsius") -> WeatherResponse:
    return get_structured_weather(city, unit)

# 4. Adapt and use your custom tool like the built-in ones
# openai_weather_tool = decorated_get_weather.as_openai_tool()
# langchain_weather_tool = decorated_get_structured_weather.as_langchain_tool()
# ...and so on for other frameworks.
```
The `@tool_spec` decorator inspects your function's signature, docstring, and type hints (including an optional Pydantic model for the return type via `output_model`) to create a standardized specification. This specification is then used by the `as_<framework>_tool()` methods to convert it into the format expected by each agent SDK.

### Why Use `@tool_spec` for Custom Tools?

You might notice that some agent SDKs, like the `openai-agents` SDK, can directly consume Python functions and attempt to derive tool schemas from their names, docstrings, and type hints. So, why use `@tool_spec`?

The `glean-agent-toolkit` and its `@tool_spec` decorator offer several advantages, particularly in a multi-framework environment or when aiming for more explicit and robust tool definitions:

1.  **Define Once, Use Anywhere**: This is the core benefit. Decorate your Python function with `@tool_spec` once.
    *   The toolkit then allows you to adapt this single definition for various agent frameworks (LangChain, CrewAI, OpenAI Assistants API, etc.) using methods like `your_tool.as_langchain_tool()`.
    *   Even for SDKs like `openai-agents` that consume raw functions, using `your_tool.func` ensures you're providing a function whose name, docstring, and signature have been thoughtfully defined and are consistent with the metadata you provided to `@tool_spec`.

2.  **Explicit and Standardized Specification**: `@tool_spec` allows for a more deliberate and detailed definition of your tool's interface than relying purely on function metadata:
    *   **Clear Naming and Description**: You explicitly set the `name` and `description` the LLM will see, which can be more detailed or user-friendly than a raw function name or a potentially long docstring.
    *   **Pydantic for Complex Data**: Crucially, you can define complex input and output structures using Pydantic models (`output_model` argument in `@tool_spec`). This provides strong typing, validation, and clear schema generation for the LLM, which is often more robust than relying on type hint inference alone for complex objects.

3.  **Ecosystem Benefits**:
    *   **Consistency with Pre-built Tools**: If you use the toolkit's pre-built Glean tools, defining your custom tools with `@tool_spec` maintains a consistent approach.
    *   **CLI Integration**: Tools defined with `@tool_spec` can be discovered and inspected by the `glean-toolkit` CLI (e.g., `glean-toolkit list`, `glean-toolkit export-schema`).
    *   **Maintainability**: Adapters can be updated within the toolkit to accommodate changes in framework APIs, often without requiring changes to your `@tool_spec` definitions.

In essence, while you *can* use raw functions with certain SDKs, `@tool_spec` promotes a more structured, reusable, and explicit way of defining tools, making your agent development more robust and scalable across different platforms. It acts as a central source of truth for your tool's contract.

## CLI

The toolkit includes a CLI for listing and exporting tool schemas (both built-in and any custom tools you register by importing them):

```bash
# List all registered tools
glean-toolkit list

# Export JSON schema for a specific tool's input
glean-toolkit export-schema get_current_weather
```

## Contributing

Interested in contributing? Check out our [Contributing Guide](CONTRIBUTING.MD) for instructions on setting up the development environment and submitting changes.

## License

This project is licensed under the [MIT License](LICENSE). 