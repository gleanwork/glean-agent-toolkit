# Agent Guidelines

This project contains the **Glean Agent Toolkit**, a Python package used to integrate Glean's search and discovery tools with various agent frameworks.

## Setup

1. Install the prerequisites:
   - [uv](https://github.com/astral-sh/uv)
   - [mise](https://mise.jdx.dev/)
 2. Run `mise run setup` to create the `.venv` and install all development, test, lint and typing dependencies via `uv`.

Environment variables `GLEAN_API_TOKEN` and `GLEAN_INSTANCE` must be set to interact with Glean or regenerate VCR cassettes.

## Development Tasks

The repository uses **mise**. Key commands include:

| Task | Description |
|------|-------------|
| `mise run test` | Run unit tests |
| `mise run test:watch` | Run tests in watch mode |
| `mise run test:cov` | Run tests with coverage |
| `mise run test:all` | Run tests, apply lint fixes, and run pyright |
| `mise run lint` | Run Ruff, formatting checks and pyright |
| `mise run lint:diff` | Lint only changed files |
| `mise run lint:fix` | Apply Ruff fixes and formatting |
| `mise run format` | Format code using Ruff formatter |
| `mise run spell:check` | Check spelling |
| `mise run clean` | Remove build artifacts |
| `mise run build` | Build the package |
| `mise run release` | Bump version and generate the changelog |

Special tasks exist to manage VCR cassettes used in tests:

- `mise run test:vcr:regenerate` – Re-record all HTTP interactions (requires `GLEAN_API_TOKEN` and `GLEAN_INSTANCE`).
- `mise run test:vcr:clean` – Delete cassettes so the next test run regenerates them.

## Coding Guidelines

- Python **>=3.10** is required. The project enforces formatting with Ruff. Line length is limited to **100** characters and double quotes are used by default.
- Docstrings follow the **Google** style as configured in `pyproject.toml`.
- Type checking is performed with **pyright**.
- Tools should be implemented using the `@tool_spec` decorator found in `glean.agent_toolkit.decorators`. See existing tools under `src/glean/agent_toolkit/tools` for examples.

## Contribution Process

1. Fork the repository and create a branch from `main`.
2. Make your changes and ensure all tasks run cleanly (`mise run test` and `mise run lint`).
3. Update or add documentation when necessary.
4. Submit a pull request.
5. Be respectful and follow the project's code of conduct.

## Additional Notes

Check the [README](README.md) for feature descriptions and basic usage. The package is released under the [MIT License](LICENSE).
