# Development Setup

This file describes steps to set up your local Python development environment.

## Installation

### Prerequisites

- UNIX OS (e.g., macOS or Linux)
- git version 2.55+

### Installing Tools

1. Install `pyenv` as
   per [Getting Pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#a-getting-pyenv)

2. Install `python` 3.14+

- Get the latest `python` 3.14+ version using `pyenv` as follows:

    ```bash
    pyenv install --list | grep '^[[:space:]]*3.1[4-9]'
    ```

- Install the latest `python` 3.14 using `pyenv` as follows:

    ```bash
    # assuming 3.14.7 is the latest python 3.14 release.
    pyenv install "3.14.7"
    ```

- Configure the global `python` version:

    ```bash
    # assuming 3.14.7 is the latest python 3.14 release.
    pyenv global "3.14.7"
    ```

- Check the installed `python` version:

    ```bash
    python --version
    ```

3. Install `pipx`

- OS: `macOS`

    ```bash
    # macOS brew
    brew install pipx
    pipx ensurepath
    ```

- OS: `linux` (e.g., Ubuntu using `apt`)

    ```bash
    # Ubuntu Linux apt.
    sudo apt update
    sudo apt install pipx
    pipx ensurepath
    ```

4. Install `poetry`

```bash
pipx install poetry
```

5. Install `Claude Code`

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

### Cloning Git Repository

- Clone the Git repository

   ```bash
   git clone https://github.com/rubensgomes-org/math-ai-agent
   cd math-ai-agent
   ```

### Install Project Dependencies

- `poetry install` automatically creates a `poetry` virtual environment folder
  to install all the dependencies listed in `pyproject.toml`

    ```bash
    # change to project git local directory for this project
    cd $(git rev-parse --show-toplevel) || exit
    poetry install
    ```

- Show all the installed dependencies

    ```bash
    # change to project git local directory for this project
    cd $(git rev-parse --show-toplevel) || exit
    poetry show
    ```

- Show `poetry` virtual environment

    ```bash
    # change to project git local directory for this project
    cd $(git rev-parse --show-toplevel) || exit
    # complete information about poetry virtual environment
    poetry env info
    # below is the location of poetry virtual environment installation folder
    poetry env info --path
    ```

**NOTE:** since we are using `poetry` we do not need to activate a virtual
environment to run tests or the application. `poetry` automatically takes
care of running commands in its own virtual environment.

- Activate/deactivate virtual environment (for illustration only)

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    poetry env info
    eval $(poetry env activate)
    deactivate
    ```

- Clean up `poetry` virtual environment:

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    poetry env remove --all
    ```

## Common Development Commands

**NOTE:** we are using `poetry` to run all commands. That's because all the
tools below are defined in the `pyproject.toml` which `poetry install` installs
in its own virtual environment.

- Format, lint, type check, sort imports

    ```bash
    # Format code
    poetry run black src/ tests/ --target-version py314

    # Lint
    poetry run pylint src/

    # Type checking
    poetry run mypy src/

    # Sort imports
    poetry run isort src/ tests/
    ```

- Tests with coverage

    ```bash
    # Run all tests
    poetry run pytest

    # Run specific test module -- must disable coverage for single module
    poetry run pytest --no-cov tests/test_config.py
    ```

- Run `pip-audit` security scan to check vulnerabilities

    ```bash
    poetry run pip-audit --skip-editable
    ```

- Run `sonar` static analysis and quality gate check. **NOTE:**
  requires the `SONAR_TOKEN` environment variable with a valid API key.

    ```bash
    poetry run pytest
    poetry run pysonar --sonar-python-coverage-report-paths=coverage.xml
    ```

- Add project dependencies

    ```bash
    # Ensure at the top of the project root folder
    cd $(git rev-parse --show-toplevel) || exit
    # to add runtime dependencies to pyproject.toml
    poetry add <dependency>
    # to add "dev" dependencies to pyproject.toml
    poetry add --group dev <dependency>
    ```

- Update project dependencies in `pyproject.toml`

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    poetry update -vv
    poetry lock --regenerate -vv
    ```
