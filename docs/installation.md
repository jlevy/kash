## Installing uv and Python

This project is set up to use [**uv**](https://docs.astral.sh/uv/), the new package
manager for Python. `uv` replaces traditional use of `pyenv`, `pipx`, `poetry`, `pip`,
etc. This is a quick cheat sheet on that:

On macOS or Linux, if you don’t have `uv` installed, a quick way to install it:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On macOS, if you prefer [brew](https://brew.sh/), you can install or upgrade uv with:

```shell
brew update
brew install uv
```

See [uv’s docs](https://docs.astral.sh/uv/getting-started/installation/) for more
installation methods and platforms.

Now you can use uv to install a current Python environment:

```shell
uv python install 3.13
```

kash-shell supports **GIL** CPython 3.11–3.14. Freethreaded 3.14t is
unsupported (cydifflib’s sdist fails there).

`uv python find 3.14` and a bare `uv tool install` / `uvx` may resolve
`cpython-3.14.7+freethreaded`. Pin the interpreter:

```shell
uv tool install kash-shell --upgrade --python 3.13
# Or a GIL 3.14, not 3.14t. `--python 3.14` / `uv venv -p 3.14` can still
# resolve freethreaded on this toolchain.
```

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
