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
   task test:all
   ```

3. **Preview the Release**

   Generate a preview of the version bump and changelog to verify everything looks correct.

   ```bash
   task release DRY_RUN=true
   ```

4. **Create the Release**

   If the preview looks good, create the actual release.

   ```bash
   task release
   ```

   This will:
   - Update the version in `pyproject.toml` and `src/toolkit/__init__.py`
   - Update the CHANGELOG.md file
   - Create a git tag for the new version

5. **Push Changes**

   Push the changes and the new tag to the remote repository.

   ```bash
   git push origin main --tags
   ```

6. **Build and Publish the Package**

   Build the package and publish it to PyPI.

   ```bash
   task clean
   task build
   python -m twine upload dist/*
   ```

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