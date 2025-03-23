## Installation

### Running the Kash Shell

Kash offers a shell environment based on [xonsh](https://xon.sh/) augmented with an LLM
assistant and a few other enhancements.
If you've used a bash or Python shell before, xonsh is very intuitive.

Within the kash shell, you get a full environment with all actions and commands.
You also get intelligent auto-complete, a built-in assistant to help you perform tasks,
and enhanced tab completion.

The shell is an easy way to use Kash actions, simply calling them like other shell
commands from the command line.

But remember that's just one way to use actions; you can also use them directly in
Python or from an MCP client.

## Installing uv and Python

This project is set up to use [**uv**](https://docs.astral.sh/uv/), the new package
manager for Python. `uv` replaces traditional use of `pyenv`, `pipx`, `poetry`, `pip`,
etc. This is a quick cheat sheet on that:

If you don't have `uv` installed, a quick way to install it is:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For macOS, you prefer [brew](https://brew.sh/) you can install or upgrade uv with:

```shell
brew update
brew install uv
```
See [uv's docs](https://docs.astral.sh/uv/getting-started/installation/) for
installation methods and platforms.

Now you can use uv to install a current Python environment:

```shell
uv python install 3.13 # Or pick another version.
```

### Installing Additional Dependencies

In addition to Python, it's highly recommended to install a few other dependencies to
make more tools and commands work:

- `ripgrep` (for search), `bat` (for prettier file display), `eza` (a much improved
  version of `ls`), `hexyl` (a much improved hex viewer), `imagemagick` (for image
  display in modern terminals), `libmagic` (for file type detection), `ffmpeg` (for
  audio and video conversions)

For macOS, you can again use brew:

```shell
# Install pyenv, pipx, and other tools:
brew update
brew install ripgrep bat eza hexyl imagemagick libmagic ffmpeg 
```

For Ubuntu:

```shell
apt install ripgrep bat eza hexyl imagemagick libmagic ffmpeg 
```

For Windows or other platforms, see the uv instructions.

### Building Kash

1. [Fork](https://github.com/jlevy/kash/fork) this repo (having your own fork will make
   it easier to contribute actions, add models, etc.).

2. [Check out](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
   the code.

3. Install the package dependencies:

   ```shell
   make
   ```

### API Key Setup

You will need API keys for all services you wish to use.
Configuring OpenAI, Anthropic, Groq (for Llama 3), Deepgram (for transcriptions),
Firecrawl (for web crawling and scraping), and Exa (for web search) are recommended.

These keys should go in the `.env` file in your current directory.

```shell
# Set up API secrets:
cp .env.template .env 
# Now edit the .env file to add all desired API keys.
# You can also put .env in ~/.env if you want it to be usable in any directory.
```

### Running

To run:

```shell
uv run kash
```

Use the `self_check` command to confirm tools like `bat` and `ffmpeg` are found and
confirm API keys are set up.

Optionally, to install kash globally in the current user's Python virtual environment so
you can conveniently use `kash` anywhere,

```shell
uv tool install .
```
