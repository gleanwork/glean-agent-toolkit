# Commit Linting Setup

This project uses conventional commits with pre-commit hooks to ensure all commits follow the proper format.

## What is Conventional Commits?

Conventional Commits is a specification for commit messages that provides a standardized way to write commit messages. This makes it easier to:

- Automatically generate changelogs
- Determine semantic version bumps
- Communicate the nature of changes to teammates

Format: `<type>(<scope>): <description>`

Examples:

- `feat: add new search functionality`
- `fix(auth): resolve login issue`
- `docs: update README with new examples`
- `refactor(api): simplify response handling`

## Setup

### 1. Install Dependencies

```bash
# Install all dependencies including pre-commit
mise run setup
```

This will:

- Install Python dependencies with `uv`
- Install pre-commit hooks automatically

### 2. Manual Pre-commit Setup (if needed)

```bash
# Install pre-commit hooks
mise run pre-commit:install
```

## Available Tools

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit and will:

- Validate commit message format using Commitizen
- Run code formatting and linting with Ruff
- Check for common issues (trailing whitespace, merge conflicts, etc.)

**Commands:**

```bash
# Run pre-commit hooks on all files
mise run pre-commit:run

# Run pre-commit hooks on changed files only
mise run pre-commit:run:diff

# Update pre-commit hooks to latest versions
mise run pre-commit:update
```

## Making Commits

### Option 1: Use Commitizen (Recommended)

```bash
# Interactive commit creation
uv run python -m commitizen commit

# Or use the shorthand
uv run cz commit
```

This will guide you through creating a conventional commit interactively.

### Option 2: Manual Commits

You can write commits manually, but they must follow the conventional commit format:

```bash
git commit -m "feat: add new feature"
git commit -m "fix(auth): resolve login issue"
git commit -m "docs: update API documentation"
```

### Option 3: Use Pre-commit with Conventional Commits

```bash
# Write your commit message
git add .
git commit -m "your message here"

# Pre-commit will validate and potentially fix issues
```

**Note:** Pre-commit hooks will automatically run and validate your commit message format.

## Commit Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

## Troubleshooting

### Pre-commit Hook Not Running

```bash
# Reinstall pre-commit hooks
task pre-commit:install
```

### Commit Message Validation Failing

1. Use Commitizen for interactive commit creation:

   ```bash
   uv run python -m commitizen commit
   ```

2. Check the conventional commit format:

   - Must start with a type: `feat`, `fix`, `docs`, etc.
   - Optional scope in parentheses: `(auth)`, `(api)`, etc.
   - Colon and space: `: `
   - Description: `add new feature`

3. Examples of valid commits:
   ```bash
   git commit -m "feat: add new search functionality"
   git commit -m "fix(auth): resolve login timeout issue"
   git commit -m "docs: update installation instructions"
   ```

### Skipping Validation (Emergency Only)

```bash
# Skip pre-commit hooks (not recommended)
git commit -m "your message" --no-verify
```

## Configuration Files

- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `.cz.toml`: Commitizen configuration
- `pyproject.toml`: Project dependencies including pre-commit

## Benefits

1. **Consistent History**: All commits follow the same format
2. **Automated Changelogs**: Commitizen can generate changelogs automatically
3. **Semantic Versioning**: Automatic version bumping based on commit types
4. **Better Collaboration**: Clear communication about what each commit does
5. **Local Validation**: Immediate feedback before commits are made
