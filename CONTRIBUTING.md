# Contributing to Glean Agent Toolkit

Thank you for your interest in contributing to the Glean Agent Toolkit! This guide will help you understand the project structure, development workflow, and how to add new tools.

## Project Structure

```sh
src/
├─ glean/
│  ├─ __init__.py
│  └─ agent_toolkit/     # exposes `glean.agent_toolkit`
│     ├─ __init__.py
│     ├─ decorators.py
│     ├─ registry.py
│     ├─ spec.py
│     ├─ adapters/
│     ├─ tools/
│     └─ cli.py
├─ tests/
└─ docs/
```

## Development environment

The repository relies on [uv](https://github.com/astral-sh/uv) and [mise](https://mise.jdx.dev/) for reproducible workflows and task orchestration.

### Prerequisites

1. uv

   ```bash
   pip install uv
   ```

2. mise

   ```bash
   brew install mise
   ```

### One-time setup

```bash
mise run setup
```

The command creates `.venv/` and installs all dev/test dependencies via uv.

## Development Tasks

The project uses `mise` to manage development tasks. Here are the available tasks:

### Testing

| Task                  | Description                  |
| --------------------- | ---------------------------- |
| `mise run test`       | Run unit tests               |
| `mise run test:watch` | Run tests in watch mode      |
| `mise run test:cov`   | Run tests with coverage      |
| `mise run test:all`   | Run all tests and lint fixes |

### Linting and formatting

| Task                    | Description                             |
| ----------------------- | --------------------------------------- |
| `mise run lint`         | Run Ruff, pyright and formatting checks |
| `mise run lint:diff`    | Same as above but only on changed files |
| `mise run lint:package` | Lint only `glean/toolkit`               |
| `mise run lint:tests`   | Lint only `tests`                       |
| `mise run lint:fix`     | Autofix style issues                    |
| `mise run format`       | Apply Ruff formatter                    |
| `mise run format:diff`  | Format only changed files               |

### Examples and Utilities

| Task                   | Description                                     |
| ---------------------- | ----------------------------------------------- |
| `mise run spell:check` | Check spelling                                  |
| `mise run spell:fix`   | Fix spelling                                    |
| `mise run clean`       | Clean build artifacts                           |
| `mise run build`       | Build the package                               |
| `mise run release`     | Create a new release (version bump + changelog) |
| `mise run security:audit` | Run dependency vulnerability audit (pip-audit) |

## Pull Request Process

1. Fork the repository and create your branch from `main`.
2. Make your changes and ensure that all tests pass.
3. Update the documentation to reflect any changes.
4. Submit a pull request.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project.
