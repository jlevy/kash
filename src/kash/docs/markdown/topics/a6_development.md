## Development

Developer workflows:

```shell
# Run poetry install, lint, and test:
make

# Build wheel:
make build

# Linting and testing individually:
make lint
make test

# Delete all the build artifacts:
make clean

# To run a shell within the Python environment:
poetry shell
# Thereafter you can run tests.

# To run tests:
pytest   # all tests
pytest -s src/module/some_file.py  # one test, showing outputs

# Poetry dependency management commands:
# Upgrade all dependencies:
poetry up
# Update poetry itself: 
poetry self update
```

Developer setup:

```shell
# If needed (note we use newer Poetry 2.0):
poetry self update

# Or within the poetry shell:
pytest   # all tests
pytest -s src/kash/file_tools/filename_parsing.py  # one test, with outputs

# Build wheel:
poetry build

# Before committing, be sure to check formatting/linting issues:
poetry run lint

# Poetry dep management commands.
# Update poetry:
poetry self update
# The poetry-dynamic-versioning plugin is now automatically installed. Docs:
# https://github.com/mtkennerly/poetry-dynamic-versioning
# Poetry up plugin is useful upgrade deps.
# https://github.com/MousaZeidBaker/poetry-plugin-up
poetry self add poetry-plugin-up
poetry up --latest

# Update key packages:
source devtools/update_common_deps.xsh

# Update this README:
source devtools/generate_readme.xsh
```

A few debugging tips when finding issues:

```shell
# To see tracebacks if xonsh does not show them:
$XONSH_SHOW_TRACEBACK=1

# To dump Python stack traces of all threads (from another terminal):
pkill -USR1 kash
```
