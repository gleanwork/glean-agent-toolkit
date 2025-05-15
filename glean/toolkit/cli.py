"""Command-line interface for working with tools."""

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from glean.toolkit.registry import get_registry

app = typer.Typer(help="Agent Toolkit CLI")
console = Console()


@app.command("list")
def list_tools() -> None:
    """List all registered tools."""
    registry = get_registry()
    tools = registry.list()

    if not tools:
        console.print("No tools registered.")
        return

    table = Table(title="Registered Tools")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Version")

    for tool in tools:
        table.add_row(
            tool.name,
            tool.description,
            tool.version or "N/A",
        )

    console.print(table)


@app.command("export-schema")
def export_schema(
    name: str = typer.Argument(..., help="Name of the tool to export"),
    output: str | None = typer.Option(None, help="Output file path (default: stdout)"),
) -> None:
    """Export the JSON schema for a tool."""
    registry = get_registry()
    tool = registry.get(name)

    if tool is None:
        console.print(f"Tool '{name}' not found.")
        sys.exit(1)

    schema = {
        "name": tool.name,
        "description": tool.description,
        "version": tool.version,
        "input_schema": tool.input_schema,
        "output_schema": tool.output_schema,
    }

    json_str = json.dumps(schema, indent=2)

    if output:
        with open(output, "w") as f:
            f.write(json_str)
        console.print(f"Schema exported to {output}")
    else:
        console.print(json_str)


if __name__ == "__main__":
    app()
