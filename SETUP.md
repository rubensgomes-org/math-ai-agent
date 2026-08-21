# Setup

This file describes steps to set up your local Python development environment.

## Prerequisites

As of March 01, 2026, the following tools and versions are required in Linux
Ubuntu:

- Ubuntu Linux 24.04.3 LTS
- Claude Code 2.1.62+
- cookiecutter 2.6.0+
- gh version 2.45.0+ (GitHub CLI tool)
- git version 2.43.0+
- isort 8.0.1+
- pip 25.3+
- pipx 1.4.3+
- poe 0.42.1+
- poetry 2.3.2+
- pyenv 2.6.23-5-g43e83b52+
- pylint 4.0.5+
- pytest 9.0.2+
- python 3.14.3+
- uv 0.10.7+

## Installing Tools

### `pyenv`

- Install `pyenv` as follows:
- Refer
  to [Getting Pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#a-getting-pyenv):

    ```bash
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    ```

- Set up `pyenv` as follows:
- Refer
  to [Set up shell environment for Pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#b-set-up-your-shell-environment-for-pyenv)

    ```bash
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
    echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init - bash)"' >> ~/.bash_profile
    ```

### `python`

- Get the latest `python` 3.14+ version as follows:

    ```bash
    pyenv install --list | grep '^[[:space:]]*3.1[4-9]'
    ```

- Install `python` 3.14 as follows:

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

### `pipx`

- Install python3 and pipx (macOS):

    ```bash
    # macOS brew
    brew install pipx
    pipx ensurepath
    ```

- Install python3 and pipx (Linux Ubuntu using `apt`):

    ```bash
    # Ubuntu Linux apt.
    sudo apt update
    sudo apt install pipx
    pipx ensurepath
    ```

- Check the installed `pipx` version:

    ```bash
    pipx --version
    ```

### `poetry` `pylint` `pytest` ...

- Install several required utilities:

    ```bash
    pipx install isort
    pipx install poethepoet
    pipx install poetry
    pipx install pylint
    pipx install pytest
    pipx install uv
    uv tool install cookiecutter
    ```

- Upgrade the packages installed using `pipx`:

    ```bash
    pipx upgrade isort
    pipx upgrade poethepoet
    pipx upgrade poetry
    pipx upgrade pylint
    pipx upgrade pytest
    pipx upgrade uv
    uv tool upgrade cookiecutter
    ```

- Check the installed `poetry` version:

    ```bash
    poetry --version
    ```

- Check the installed `pylint` version:

    ```bash
    pylint --version
    ```

- Check the installed `pytest` version:

    ```bash
    pytest --version
    ```

### `Claude Code`

- Install `Claude Code`:

    ```bash
    curl -fsSL https://claude.ai/install.sh | bash
    ```

- Clear the cache of any previous stale `Claude Code` installation:

    ```bash
    hash -d claude   # clears cached location for 'claude' only
    # if it says 'not found', just run:
    hash -r          # clears the whole cache
    ```

- Display the `Claude Code` version and help:

    ```bash
    claude --version
    claude --help
    ```

- Update `Claude Code`:

    ```bash
    claude update
    ```

- Run `Claude Code` using the latest `opus` LLM:

    ```bash
    # open project from IDE (e.g., PyCharm)
    # switch to the project folder, and type:
    claude --verbose --debug --model "opus" --ide
    ```

## Clone an Existing Python Poetry-Based Git Repository

**Clone the repository:**

   ```bash
   git clone https://github.com/rubensgomes/<proj-name>
   cd <proj-name>
   ```

## Add Dependencies

- Add Dependencies to the project

    ```bash
    # example: key_value
    poetry add key_value
    ```

- Add Dev Dependencies

    ```bash
    poetry add --dev black
    poetry add --dev coverage
    poetry add --dev mypy
    poetry add --dev pytest-asyncio
    poetry add --dev pytest-cov
    poetry add --dev types-pyyaml
    ```

## Python Virtual Environment

- Remove old virtual environment:

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    poetry env remove --all
    ```

- Create new virtual environment:

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    # poetry automatically uses the existing virtual environment to install packages
    poetry install
    # display information about virtual environment
    poetry env info
    poetry show
    ```

- Update virtual environment:

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    # poetry automatically uses the existing virtual environment to
    # install/update packages
    poetry update
    # display information about virtual environment
    poetry env info
    poetry show
    ```

- Activate virtual environment:

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    eval $(poetry env activate)
    ```

- De-activate the virtual environment:

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    deactivate
    ```

## Common Commands

**NOTE** You must have previously created and configured a clean virtual
environment to successfully run the following commands.

- Format, lint, type check, sort imports:

    ```bash
    # Format code
    poetry run black src/ tests/

    # Lint
    poetry run pylint src/

    # Type checking
    poetry run mypy src/

    # Sort imports
    poetry run isort src/ tests/
    ```

- Different commands to run tests:

    ```bash
    # Run all tests
    poetry run pytest

    # Run with coverage
    poetry run pytest --cov=src/ --cov-report=term-missing

    # Run specific test module
    poetry run pytest tests/<module-name>
    ```

- Miscellaneous `poetry` commands:

    ```bash
    # Ensure at the top of the project root folder
    cd $(git rev-parse --show-toplevel) || exit
    # to add runtime dependencies to pyproject.toml
    poetry add <dependency>
    # to add development dependencies to pyproject.toml
    poetry add --dev <dependency>
    ```

- Command to upgrade the packages in the `pyproject.toml`:

    ```bash
    cd $(git rev-parse --show-toplevel) || exit
    poetry update -vv
    poetry lock --regenerate -vv
    ```

## PyCharm IDE Development Environment

- First, ensure to follow all the previous steps to "Setting Up Shell
  Development Environment"

1. Open the project `<proj-name>` folder using `PyCharm`
2. Follow instructions
   to [Create a Poetry environment](https://www.jetbrains.com/help/pycharm/poetry.html#poetry-env)
    - Click on the Python Interpreter Selector to "Add New Interpreter"
    - Select "Add Local Interpreter..."
    - Select "Poetry Environment"
    - Ensure "Poetry executable" (e.g., ${HOME}/.local/bin/poetry)
    - Ensure "Base interpreter" is `poetry` and the right Python executable.
    - Enter `Python Integrated Tools`
    - Under `Testing` > `Default test runner` select `pytest`
3. Open `PyCharm` > `Terminal` to go to venv prompt
    - Ensure .venv correct settings:

    ```shell
    poetry env info
    ```

### Edit Configurations in PyCharm

1. Menu: Run -> Edit Configurations...
2. Ensure The "Run" drop-down menu shows "poetry (<proj-name>) Python 3.14.3 ~
   /.cache/pypoetry/virtualenvs/<proj-name>-...".
   See [PyCharm Edit Configurations Image](docs/img/pycharm_edit_configurations.jpg)
3. Click: "+" -> Python
4. Select: "module" from the script/module drop-down menu
5. Type: "<proj-name>" in the module

### Run `<proj-name>` in DEBUG mode from within PyCharm:

Once the above "Edit Configurations in PyCharm" are configure:

1. Menu: Run -> Debug...
2. Select `<proj-name>` and debug

## PyPi Configuration

- Generate PyPi tokens from account and configure below environment variables:

    ```bash
    ######################################################################
    ## PyPi PERSONAL API TOKEN
    export PYPI_API_TOKEN="<SECRET>"
    export TESTPYPI_API_TOKEN="<SECRET>"
    ```

- Store `pypi` credentials

    ```bash
    poetry config -v pypi-token.pypi "${PYPI_API_TOKEN}"
    poetry config -v pypi-token.testpypi "${TESTPYPI_API_TOKEN}"
    ```

- Publish `wheel` package to `PyPi` repository:

    ```bash
    # publish to TestPyPi
    poetry publish -vvv -r testpypi --build --dry-run
    # publish to PyPi
    poetry publish -vvv --build --dry-run
    ```

## Create Remote GitHub Public Git Repository

- This is how Rubens initialized this projects:

    - PROJ_NAME=<proj-name>
    - git init -b main
    - git add .
    - git commit -m "initial commit" -a
    - gh repo create --homepage "https://github.com/rubensgomes" --public "$
      {PROJ_NAME}"
    - git remote add origin "https://github.com/rubensgomes/${PROJ_NAME}"
    - git push -u origin main

After previous steps go to GitHub remote repo and create a "release" branch.

## Deploy MCP Server

- For more information: <https://docs.prefect.io/v3/get-started>

1. Login to <https://www.prefect.io/horizon> using GitHub credentials.
