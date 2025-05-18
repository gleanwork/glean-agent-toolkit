# Contributing to Glean Agent Toolkit

This guide explains how to set up a local environment and submit changes to **Glean Agent Toolkit** (`glean-agent-toolkit`).

## Development environment

The repository relies on [uv](https://github.com/astral-sh/uv) and [go-task](https://taskfile.dev/) for reproducible workflows.

### Prerequisites

1. uv

    ```bash
    pip install uv
    ```

2. go-task

    ```bash
    brew install go-task
    ```

### One-time setup

```bash
task setup
```

The command creates `.venv/` and installs all dev/test dependencies via uv.

## Development Tasks

The project uses [go-task](https://taskfile.dev/) to manage development tasks. Here are the available tasks:

### Testing

| Task | Description |
|------|-------------|
| `task test` | Run unit tests |
| `task test:watch` | Run tests in watch mode |
| `task test:cov` | Run tests with coverage |
| `task test:all` | Run all tests and lint fixes |

### Linting and formatting

| Task | Description |
|------|-------------|
| `task lint` | Run Ruff, mypy and formatting checks |
| `task lint:diff` | Same as above but only on changed files |
| `task lint:package` | Lint only `glean/toolkit` |
| `task lint:tests` | Lint only `tests` |
| `task lint:fix` | Autofix style issues |
| `task format` | Apply Ruff formatter |
| `task format:diff` | Format only changed files |

### Examples and Utilities

| Task | Description |
|------|-------------|
| `task examples` | Run basic examples |
| `task run:search-example` | Run Glean search example |
| `task spell:check` | Check spelling |
| `task spell:fix` | Fix spelling |
| `task clean` | Clean build artifacts |
| `task build` | Build the package |
| `task release` | Create a new release (version bump + changelog) |

## Project structure

```text
glean-agent-toolkit/
├─ glean/
│  ├─ __init__.py        # exposes `glean.toolkit`
│  └─ toolkit/
│     ├─ __init__.py
│     ├─ decorators.py
│     ├─ registry.py
│     ├─ spec.py
│     ├─ adapters/
│     ├─ tools/
│     └─ cli.py
├─ tests/
├─ examples/
└─ docs/
```

## Pull Request Process

1. Fork the repository and create your branch from `main`.
2. Make your changes and ensure that all tests pass.
3. Update the documentation to reflect any changes.
4. Submit a pull request.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. 