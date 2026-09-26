# PyCharm

This file contains handy information about working with the `pycharm` IDE.

## PyCharm IDE Development Environment

- First, ensure you have completed the steps in
  [DEVELOPMENT_SETUP.md](./DEVELOPMENT_SETUP.md).

1. Open the project `math-ai-agent` folder using `PyCharm`
2. Follow instructions
   to [Create a Poetry environment](https://www.jetbrains.com/help/pycharm/poetry.html#poetry-env)
    - Click on the Python Interpreter Selector to "Add New Interpreter"
    - Select "Add Local Interpreter..."
    - Select "Poetry Environment"
    - Ensure "Poetry executable" is set (e.g., ${HOME}/.local/bin/poetry)
    - Ensure "Base interpreter" is `poetry` and the right Python executable.
    - Enter `Python Integrated Tools`
    - Under `Testing` > `Default test runner` select `pytest`
3. Open `PyCharm` > `Terminal` to go to venv prompt
    - Verify the virtual environment settings:

    ```shell
    poetry env info
    ```

### Edit Configurations in PyCharm

1. Menu: Run -> Edit Configurations...
2. Ensure "Run" drop-down menu shows "poetry (math-ai-agent) Python 3.14.7"
3. Click: "+" -> Python
4. Select: "module" from the script/module drop-down menu
5. Type: "<proj-name>" in the module

### Run `math-ai-agent` in DEBUG mode from within PyCharm

Once the above "Edit Configurations in PyCharm" steps are complete:

1. Menu: Run -> Debug...
2. Select `math-ai-agent` and debug
