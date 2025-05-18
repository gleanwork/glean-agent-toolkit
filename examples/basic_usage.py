#!/usr/bin/env python3
"""Basic usage example for the Glean Agent Toolkit."""

from pydantic import BaseModel

from glean.toolkit import tool_spec


# Simple tool example
@tool_spec(name="add", description="Add two integers")
def add(a: int, b: int) -> int:
    """Add two integers and return the result.

    Args:
        a: First integer
        b: Second integer

    Returns:
        The sum of a and b
    """
    return a + b


# Tool with custom output model
class MultiplyResult(BaseModel):
    """Result of multiplying two numbers."""

    result: int
    explanation: str


@tool_spec(
    name="multiply",
    description="Multiply two integers with detailed explanation",
    output_model=MultiplyResult,
    version="1.0.0",
)
def multiply(a: int, b: int) -> MultiplyResult:
    """Multiply two integers and return the result with an explanation.

    Args:
        a: First integer
        b: Second integer

    Returns:
        A MultiplyResult containing the product and an explanation
    """
    product = a * b
    return MultiplyResult(
        result=product,
        explanation=f"The product of {a} and {b} is {product}",
    )


def main() -> None:
    """Run the example."""
    # Test the add function
    result = add(3, 5)
    print(f"Add result: {result}")

    # Test the multiply function
    result = multiply(4, 7)
    print(f"Multiply result: {result}")

    # Print OpenAI tool definition
    print("\nOpenAI Tool Definition:")
    print(add.as_openai_tool())

    # Print MultiplyResult schema
    print("\nMultiply Result Schema:")
    print(MultiplyResult.model_json_schema())

    # Print all registered tools
    from glean.toolkit import get_registry

    registry = get_registry()
    print("\nRegistered Tools:")
    for tool in registry.list():
        print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    main()
