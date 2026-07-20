# Release Process

This document outlines the process for releasing new versions of the `glean_agent_toolkit` package.

## Release Steps

1. **Prepare for Release**

   Ensure all changes intended for the release are merged into the main branch.

   ```bash
   git checkout main
   git pull origin main
   ```

2. **Run Tests and Linters**

   Verify that all tests and linters pass successfully.

   ```bash
   mise run test:all
   ```

3. **Preview the Release**

   Generate a preview of the version bump and changelog to verify everything looks correct.

   ```bash
   DRY_RUN=true mise run release
   ```

4. **Create the Release**

   If the preview looks good, create the actual release.

   ```bash
   mise run release
   ```

   This will:

   - Update the version in `pyproject.toml` (the only version file, per `.cz.toml`)
   - Update the CHANGELOG.md file
   - Create a `bump:` commit and a git tag for the new version

5. **Push the Release**

   If the changelog regeneration (or `uv.lock`) left any uncommitted changes, commit them first, then push the branch and the new tag.

   ```bash
   git status              # commit any leftover CHANGELOG.md / uv.lock changes
   git push origin main --tags
   ```

6. **Publishing Happens Automatically**

   Pushing the version tag triggers the "Publish to PyPI" GitHub Actions workflow (`.github/workflows/publish.yml`), which:

   - Runs the test suite (`mise run test`)
   - Builds the package with `uv build`
   - Creates a GitHub Release with changelog notes
   - Publishes to PyPI via trusted publishing (`pypa/gh-action-pypi-publish`)

   Do **not** upload manually with `twine` — publishing is handled entirely by the workflow. Monitor the workflow run to confirm the release succeeds.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). Version numbers are in the format `MAJOR.MINOR.PATCH`:

- **MAJOR**: Incompatible API changes
- **MINOR**: Added functionality in a backward-compatible manner
- **PATCH**: Backward-compatible bug fixes

## Commitizen

This project uses [Commitizen](https://commitizen-tools.github.io/commitizen/) to standardize commit messages and automate versioning and changelog generation.

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Where `<type>` is one of:

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes to the build process or dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files

The `<scope>` is optional and can be used to specify the component affected by the change.

For example:

```
feat(adapters): add support for new LangChain version
```

## After Release

After a release is published, monitor the package to ensure it is working as expected and address any issues that arise promptly.
