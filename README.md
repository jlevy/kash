<div align="center">

<img width="392" alt="kash"
src="https://github.com/user-attachments/assets/a5d62ae4-17e6-46bb-a9cb-3b6ec8d8d3fe" />

</div>

</div>

## What is Kash?

> “*Simple should be simple.
> Complex should be possible.*” —Alan Kay

Kash (“Knowledge Agent SHell”) is an **interactive, AI-native command-line** shell for
practical knowledge tasks.

It's also **a Python library** that lets you convert a simple Python function into a
command and an MCP tool, so it integrates with other tools like Anthropic Desktop or
Cursor.

You can think of it a kind of power-tool for technical users who want to use Python and
APIs, a kind of hybrid between an AI assistant, a shell, and a developer tool like
Cursor or Claude Code.

It's my attempt at finding a way to remix, combine, and interactively explore and then
gradually automate complex tasks by composing AI tools, APIs, and libraries.

And of course, kash can read its own functionality and enhance itself by writing new
actions.

### Key Concepts

- **Actions:** The core of Kash are **Kash actions**. By decorating a Python function,
  you can turn it into an action, which makes it more flexible and powerful, able to
  work with file inputs stored and outputs in a given directory, also called a
  **workspace**.

- **Compositionality:** An action is composable with other actions simply as a Python
  function, so complex (like transcribing and annotating a video) actions can be built
  from simpler actions (like downloading and caching a YouTube video, identifying the
  speakers in a transcript, etc.). The goal is to reduce the "interstitial complexity"
  of combining tools, so it's easy for you (or an LLM!) to combine tools in flexible and
  powerful ways.

- **Command-line usage:** In addition to using the function in other libraries and
  tools, an action is also **a command-line tool** (with auto-complete, help, etc.)
  in the Kash shell. So you can simply run `transcribe` to download and transcribe a
  video. In kash you have **smart tab completions**, **Python expressions**, and an **LLM
  assistant** built into the shell.

- **MCP support:** Finally, an action is also an **MCP tool server** so you can use it
  in any MCP client, like Anthropic Desktop or Cursor.

- **Support for any API:** Kash is tool agnostic and runs locally, on file inputs in
  simple formats, so you own and manage your data and workspaces however you like.
  You can use it with any models or APIs you like, and is already set up to use the APIs
  of **OpenAI GPT-4o and o1**, **Anthropic Claude 3.7**, **Google Gemini**, **xAI
  Grok**, **Mistral**, **Groq (Llama, Qwen, Deepseek)** (via **LiteLLM**), **Deepgram**,
  **Perplexity**, **Firecrawl**, **Exa**, and any Python libraries.
  There is also some experimental support for **LlamaIndex** and **ChromaDB**.

### What Can Kash Do?

You can use kash actions to do deep research, transcribe videos, summarize and organize
transcripts and notes, write blog posts, extract or visualize concepts, check citations,
convert notes to PDFs or beautifully formatted HTML, or perform numerous other
content-related tasks possible by orchestrating AI tools in the right ways.

As I've been building kash over the past couple months, I found I've found it's not only
faster to do complex things, but that it has also become replacement for my usual shell.
It's the power-tool I want to use alongside Cursor and ChatGPT/Claude.
We all know and trust shells like bash, zsh, and fish, but now I find this is much more
powerful for everyday usage.
It has little niceties, like you can just type `files` for a better listing of files or
`show` and it will show you a file the right way, no matter what kind of file it is.
You can also type something like "? find md files" and press tab and it will list you I
find it is much more powerful for local usage than than bash/zsh/fish.
If you're a command-line nerd, you might like it a lot.

But my hope is that with these enhancements, the shell is also far more friendly and
usable by anyone reasonably technical, and does not feel so esoteric as a typical Unix
shell.

Finally, one more thing: Kash is also my way of experimenting with something else new: a
**terminal GUI support** that adds GUI features terminal like clickable text, buttons,
tooltips, and popovers in the terminal.
I've separately built a new desktop terminal app, Kerm, which adds support for a simple
"Kerm codes" protocol for such visual components, encoded as OSC codes then rendered in
the terminal. Because Kash supports these codes, as this develops you will get the
visuals of a web app layered on the flexibility of a text-based terminal.

### Is Kash Mature?

No. :) It's the result of a couple months of coding and experimentation, and it's very
much in progress. Please help me make it better by sharing your ideas and feedback!
It's easiest to DM me at [twitter.com/ojoshe](https://x.com/ojoshe).
My contact info is at [github.com/jlevy](https://github.com/jlevy).

[**Please follow or DM me**](https://x.com/ojoshe) for future updates or if you have
ideas, feedback, or use cases for Kash!

## Installation

### Running the Kash Shell

Kash offers a shell environment based on [xonsh](https://xon.sh/) augmented with an LLM
assistant and a variety of other enhanced commands and customizations.
If you've used a bash or Python shell before, xonsh is very intuitive.

Within the kash shell, you get a full environment with all actions and commands.
You also get intelligent auto-complete, a built-in assistant to help you perform tasks,
and enhanced tab completion.

The shell is an easy way to use Kash actions, simply calling them like other shell
commands from the command line.

But remember that's just one way to use actions; you can also use them directly in
Python or from an MCP client.

### Current Kash Packages

The base installation of kash is the `kash-shell` package.
However, some use cases require additional libraries, like video downloading tools, PDF
handling, etc.

To keep kash dependencies more manageable, these additional utilities and actions are
packaged additional "kits".

The examples below use video transcription from YouTube as an example.
To start with more full examples, I suggest starting with the `kash-media` kit.

### Installation Steps

These steps have mainly been tested on macOS but should work on other platforms.
These are for `kash-media` but you can use a `kash-shell` for a more basic setup.

1. **Install uv and Python:**

   Kash is easiest to use via [**uv**](https://docs.astral.sh/uv/), the new package
   manager for Python. `uv` replaces traditional use of `pyenv`, `pipx`, `poetry`, `pip`,
   etc. Installing `uv` also ensures you get a compatible version of Python.

   If you don't have `uv` installed, a quick way to install it is:

   ```shell
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   For macOS, you prefer [brew](https://brew.sh/) you can install or upgrade uv with:

   ```shell
   brew update
   brew install uv
   ```
   See [uv's docs](https://docs.astral.sh/uv/getting-started/installation/) for other
   installation methods and platforms.

2. **Install additional command-line tools:**

   In addition to Python, it's highly recommended to install a few other dependencies to
   make more tools and commands work: `ripgrep` (for search), `bat` (for prettier file
   display), `eza` (a much improved version of `ls`), `hexyl` (a much improved hex
   viewer), `imagemagick` (for image display in modern terminals), `libmagic` (for file
   type detection), `ffmpeg` (for audio and video conversions)

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

3. **Install kash or a kash kit:**

   ```shell
   uv tool install kash-media --python=3.13
   ```

   Other versions of Python should work but 3.13 is recommended.
   For a setup without the media tools, use `kash-shell` instead.

   If you've installed an older version and want to be sure you have the latest shell,
   you may want to add `--upgrade --force` to be sure you get the latest version of the
   kit.

   ```shell
   uv tool install kash-media --python=3.13 --upgrade --force 
   ```

4. **Set up API keys:**

   You will need API keys for all services you wish to use.
   Configuring OpenAI, Anthropic, Groq (for Llama 3), and Deepgram (if you wish to do
   transcriptions) are a good start.
   But kash supports dozens of models
   [via LiteLLM](https://docs.litellm.ai/docs/providers).

   You can set these up now, or after you run kash (below):

   ```shell
   # Set up API secrets:
   cp .env.template .env 
   # Now edit the .env file to add all desired API keys.
   # You can also put .env in ~/.env if you want it to be usable in any directory.
   ```

   These keys should go in the `.env` file in your current work directory or a parent or
   your home directory (recommended if you'll be working in several directories, as with
   a typical shell).

5. **Run kash:**

   ```shell
   kash
   ```

   You should see a welcome message with all info about APIs and tools.

   Use the `self_check` command to confirm which tools and API keys are working.

   Use the `self_configure` command as a quick way to fill in additional values in your
   .env file and to set workspace parameters on what LLMs to use by default.

### Running Kash as an MCP Server

You can use kash from your MCP client (such as Anthropic Desktop or Cursor).

You do this by running the the `kash_mcp` binary to make kash actions available as MCP
tools.

For Claude Desktop, my config looks like this:

```json
{
  "mcpServers": {
    "kash": {
      "command": "/Users/levy/.local/bin/kash_mcp",
      "args": ["--proxy"]
    }
  }
}
```

If you add the `--proxy` arg, it will run an MCP stdio server but connect to the MCP SSE
server you are running in the kash shell, by default at `localhost:4440`.

Then if you run `start_mcp_server` from the shell, your client will connect to your
shell, and you can actually use any "published" kash action as an MCP tool.

Then you can for example ask your MCP client "can you transcribe this video?"
and give it a URL, and it will be able to call the `transcribe` action as a tool.

What is even better is that all the inputs and outputs are saved in the current kash
workspace, just as if you'd been running these commands yourself in the shell.
This way, you don't lose context or any work, and can seamlessly switch between an MCP
client like Cursor, the shell, and any other tools to edit the inputs or outputs of
actions in your workspace directory.

### Running Kash From Source

See the `development.md` file in GitHub for building and using kash from source.

## Getting Started

### Use Tab Completion and Help!

Tab completion is your friend!
Just press tab to get lists of commands and guidance on help from the LLM-based
assistant.

You can also ask any question directly in the shell.

Type `help` for the full documentation.

### An Example: Transcribing Videos

The simplest way to illustrate how to use kash is by example.
You can go through the commands below a few at a time, trying each one.

This is a "real" example that uses a bunch of libraries.
So to get it to work you must install not just the main shell but the kash "media kit"
with extra dependencies.

You need the following tools:

```shell
# On MacOS:
brew install ripgrep bat eza hexyl imagemagick libmagic ffmpeg 
# On Linux:
apt install ripgrep bat eza hexyl imagemagick libmagic ffmpeg
```

Then install the `kash-media`, which includes kash-shell and many other libs like yt-dlp
for YouTube handling:

```shell
uv tool install kash-media
```

Then run `kash` to start.

For each command below you can use tab completion (which shows information about each
command or option) or run with `--help` to get more details.

```shell
# Check the help page for a full overview:
help

# Confirm kash is set up correctly with right tools:
check_system_tools

# The assistant is built into the shell, so you can just ask questions on the
# command line. Note you can just press Space twice and it will insert the question
# mark for you:
? how do I get started with a new workspace

# Set up a workspace to test things out (we'll use fitness as an example):
workspace fitness

# A short transcription (use this one or pick any video on YouTube):
transcribe https://www.youtube.com/watch?v=KLSRg2s3SSY

# Note there is a selection indicated.
# We can then look at the selected item easily, because commands often
# will just work on the selection automatically:
show

# Now let's manipulate that transcription. Note we are using the outputs
# of each previous command, which are auto-selected as input to each
# subsequent command. You can always run `show` to see the last result.

# Remove the speaker id <span> tags from the transcript.
strip_html
show

# Break the text into paragraphs. Note this is smart enough to "filter"
# the diff so even if the LLM modifies the text, we only let it insert
# newlines.
break_into_paragraphs
show

# Look at the paragraphs and (by following the `derived_from` relation
# this doc up to find the original source) then infer the timestamps
# and backfill them, inserting timestamped link to the YouTube video
# at the end of each paragraph.
backfill_timestamps
show

# How about we add some headings?
insert_section_headings

# How about we compare what we just did with what there was there
# previously? 
diff

# If you're wondering how that works, it is an example of a command
# that looks at the selection history.
select --history

# And add some summary bullets and a description:
add_summary_bullets
add_description

# Note we are just using Markdown still but inserting <div> tags to
# add needed structure.
show

# Render it as a PDF:
create_pdf

# See the PDF.
show

# Cool. But it would be nice to have some frame captures from the video.
? are there any actions to get screen captures from the video

# Oh yep, there is!
# But we're going to want to run it on the previous doc, not the PDF.
# Let's see what the files are so far.
files

# Note we could select the file like this before we run the next command
# with `select <some-file>.doc.md`. But actually we can see the history
# of items we've selected:
select --history

# And just back up to the previous one.
select --previous

# Look at it again. Yep, there should be timestamps in the text.
show

# As a side note, not all actions work on all items. So we also have
# a way to check preconditions to see what attributes a given item has.
# Note that for this doc `has_timestamps` is true.
preconditions

# And there is a way to see what commands are compatible with the current
# selection based on these preconditions.
suggest_actions

# Okay let's try it. (If you're using a shell that supports kash well,
# you can just click the command name!)
insert_frame_captures

# Note the screen capture images go to the assets folder as assets.
files

# Let's look at that as a web page.
show_webpage

# Note that works because unlike regular `show`, that command
# runs actions to convert a pretty HTML format.
show_webpage --help

# And you can actually how this works by looking at its source:
source_code show_webpage

# What if something isn't working right?
# Sometimes we may want to browse more detailed system logs:
logs

# Note transcription works with multiple speakers, thanks to Deepgram
# diarization. 
transcribe https://www.youtube.com/watch?v=_8djNYprRDI
show

# We can create more advanced commands that combine sequences of actions.
# This command does everything we just did above: transcribe, format,
# include timestamps for each paragraph, etc.
transcribe_format --help
transcribe_format https://www.youtube.com/watch?v=_8djNYprRDI

# Getting a little fancier, this one adds little paragraph annotations and
# a nicer summary at the top:
transcribe_annotate_summarize https://www.youtube.com/watch?v=_8djNYprRDI

show_webpage
```

This is only the beginning but should give a flavor for how you can use kash.
With more actions, you can then take a transcript like this and have actions to extract
concepts, look up more about them with Perplexity, and crawl and save all the resources.
You might then visualize all the concepts.
All of these steps are just actions.

### Creating a New Workspace

Although you don't always need one, a *workspace* is very helpful for any real work in
kash. It's just a directory of files, plus a `.kash/` directory with various logs and
metadata.

Note the `.kash/cache` directory contains all the downloaded videos and media you
download, so it can get large.
You can delete these files if they take up too much space.

Note the `.kash/cache` directory contains all the downloaded videos and media you
download, so it can get large.
You can delete these files if they take up too much space.
(See the `cache_list` and `clear_cache` commands.)

Pick a workspace that encompasses a project or topic, and it lets you keep things
organized.

Type `workspace` any time to see the current workspace.

By default, when you are not using the shell inside a workspace directory, or when you
run kash the first time, it uses the default *global workspace*.

Once you create a workspace, you can `cd` into that workspace and that will become the
current workspace. (If you're familiar with how the `git` command-line works in
conjunction with the `.git/` directory, this behavior is very similar.)

To start a new workspace, run a command like

```
workspace health
```

This will create a workspace directory called `health` in the current directory.
You can run `cd health` or `workspace health` to switch to that directory and begin
working.

### Essential Kash Commands

Kash has quite a few basic commands that are easier to use than usual shell commands.
You can always run `help` for a full list, or run any command with the `--help` option
to see more about the command.

A few of the most important commands for managing files and work are these:

- `self_check` to check existing .env file and installed tools (like bat and ffmpeg)

- `self_configure` to help you configure your .env files and LLM models

- `files` lists files in one or more paths, with sorting, filtering, and grouping.

- `show` lets you show any file you wish, or with no argument shows the first file in
  the current selection.
  It auto-detects whether to show the file in the console, the browser, or using a
  native app (like Excel for a .xls file), but you can customize this with options (see
  `--help`).

- `show_webpage` formats Markdown or HTML documents as a nice web page and opens your
  browser to view it.

- `workspace` shows or selects or creates a new workspace.
  Initially you work in the `global` workspace but for more real work you'll want to
  create a workspace, which is a directory to hold the files you are working with.

- `select` shows or sets selections, which are the set of files the next command will
  run on, within the current workspace.

- `edit` runs the currently configured editor (based on the `EDITOR` environment
  variable) on any file, or the current selection.

- `param` lets you set certain common parameters, such as what LLM to use (if you wish
  to use non-default model or language).

- `logs` to see full logs (typically more detailed than what you see in the console).

- `history` to see recent commands you've run.

- `import_item` to add a resource such as a URL or a file to your local workspace.

- `download` downloads a page from a URL, or video/audio media from any of several
  services like YouTube or Apple Podcasts (using yt-dlp).

- `chat` chat with any configured LLM, and save the chat as a chat document.

- `markdownify` fetches a webpage and converts it to markdown.

- `summarize_as_bullets` summarizes a text document as bulleted items.

If you use the `kash-media` kit and its dependencies, you get additional actions like:

- `transcribe` transcribes video or audio as text document, using Deepgram.

- `create_pdf` formats Markdown or HTML documents as a PDF.

All the above commands have help and the ability to see their own source code.
For example:

```shell
markdownify --help
markdownify --show_source 
```

## Elements of Kash

### What is Included?

I've tried to build independently useful pieces that fit together in a simple way:

- The kash **action framework**:

  - A [**data model**](https://github.com/jlevy/kash/tree/main/kash/model) where
    documents, resources like URLs, concepts, etc., are saved as files in known formats
    (Markdown, Markdown+HTML, HTML, YAML resource descriptions, etc.). These and used as
    `Item`s

  - An **execution model** for `Action`s that take input `Item` inputs and produce
    outputs, as well as `Parameters` for actions and `Preconditions` that specify what
    kinds of `Items` the `Action`s operate on (like whether a document is Markdown,
    HTML, or a transcript with timestamps, and so on), so you and the shell know what
    actions might apply to any selection

  - A **workspace** which is just a directory of files you are working on, such as a
    GitHub project or a directory of Markdown files, or anything else, with a `.kash`
    directory within it to hold cached content and media files, configuration settings

  - A **selection system** in the workspace for maintaining context between commands so
    you can pass outputs of one action into the inputs of another command (this is a bit
    like pipes but more flexible for sequences of tasks, possibly with many intermediate
    inputs and outputs)

  - A simple [**file format for metadata**](https://github.com/jlevy/frontmatter-format)
    in YAML at the top of text files, so metadata about items can be added to Markdown,
    HTML, Python, and YAML, as well as detection of file types and conventions for
    readable filenames based on file type

  - **Dependency tracking** among action operations (sort of like a Makefile) so that
    Kash can recognize if the output of an action already exists and, if it is
    cacheable, skip running the action

  - **Python decorators** for functions that let you register and add new commands and
    actions, which can be packaged into libraries, including libraries with new
    dependencies

- A **hybrid command-line/natural language/Python shell**, based on
  [xonsh](https://github.com/xonsh/xonsh)

  - About 100 simple **built-in commands** for listing, showing, and paging through
    files, etc. (use `commands` for the full list, with docs) plus all usual shell tools

  - Enhanced **tab completion** that includes all actions and commands and parameters,
    as well as some extras like help summaries populated from
    [tldr](https://github.com/tldr-pages/tldr)

  - An **LLM-based assistant** that wraps the docs and the kash source code into a tool
    that assists you in using or extending kash (this part is quite fun!)

- A supporting **library of utilities** to make these work more easily:

  - A library [**chopdiff**](https://github.com/jlevy/chopdiff) to tokenize and parse
    documents simply into paragraphs, sentences, and words, and do windowed
    transformations and filtered diffs (such as editing a large document but only
    inserting section headers or paragraph breaks)

  - A new Markdown auto-formatter, [**flowmark**](https://github.com/jlevy/flowmark), so
    that text documents (like LLM outputs) are saved in a normalized form that can be
    diffed consistently

  - A **content and media cache**, which for downloading saving cached versions of video
    or audio and **audio transcriptions** (using Whisper or Deepgram)

- An optional **enhanced terminal UI** some major enhancements to the terminal
  experience:

  - Sixel graphics support (see images right in the terminal)

  - A local server for serving information on files as web pages that can be accessed as
    OSC 8 links

  - Sadly, we may have mind-boggling AI tools, but Terminals are still incredibly
    archaic and don't support these features well (more on this below) but I have a new
    terminal, Kerm, that shows these as tooltips and makes every command clickable
    (please contact me if you'd like an early developer preview, as I'd love feedback)

## Tools Used by Kash

All of this is only possible by relying on a wide variety of powerful libraries,
especially [xonsh](https://github.com/xonsh/xonsh),
[Rich](https://github.com/Textualize/rich),
[LiteLLM](https://github.com/BerriAI/litellm),
[Pydantic](https://github.com/pydantic/pydantic),
[Marko](https://github.com/frostming/marko), [yt-dlp](https://github.com/yt-dlp/yt-dlp),
[Ripgrep](https://github.com/BurntSushi/ripgrep), [Bat](https://github.com/sharkdp/bat),
[jusText](https://github.com/miso-belica/jusText),
[WeasyPrint](https://github.com/Kozea/WeasyPrint).
.

## Tips for Use with Other Tools

While not required, these tools can make using kash easier or more fun.

### Choosing a Terminal

You can use any favorite terminal to run kash.

However, you can get a much better terminal experience if you use one with more advanced
additional features, such as [OSC 8 link](https://github.com/Alhadis/OSC8-Adoption)
support and [Sixel](https://www.arewesixelyet.com/) graphics.

I tried half a dozen different popular terminals on Mac
([Terminal](https://support.apple.com/guide/terminal/welcome/mac),
[Warp](https://www.warp.dev/), [iTerm2](https://iterm2.com/),
[Kitty](https://sw.kovidgoyal.net/kitty/), [WezTerm](https://wezfurlong.org/wezterm/),
[Hyper](https://hyper.is/)). Unfortunately, none offer really good support right out of
the box, but I encourage you to try

✨**Would you be willing to help test something new?** If you've made it this far and are
still reading, I have a request.
So alongside kash, I've begun to build a new terminal app, **Kerm**, that has the
features we would want in a modern command line, such as clickable links and commands,
tooltips, and image support.
Kash also takes advantage of this support by embedding OSC 8 links.
It is *so* much nicer to use.
I'd like feedback so please [message me](https://twitter.com/ojoshe) if you'd like to
try it out an early dev version!

### Choosing an Editor

Most any editor will work.
Kash respects the `EDITOR` environment variable if you use the `edit` command.

### Using on macOS

Kash calls `open` to open some files, so in general, it's convenient to make sure your
preferred editor is set up for `.yml` and `.md` files.

For convenience, a reminder on how to do this:

- In Finder, pick a `.md` or `.yml` file and hit Cmd-I (or right-click and select Get
  Info).

- Select the editor, such as Cursor or VSCode or Obsidian, and click the "Change All…"
  button to have it apply to all files with that extension.

- Repeat with each file type.

### Using with Cursor and VSCode

[Cursor](https://www.cursor.com/) and [VSCode](https://code.visualstudio.com/) work fine
out of the box to edit workspace files in Markdown, HTML, and YAML in kash workspaces.

### Using with Zed

[Zed](https://zed.dev/) is another, newer editor that works great out of the box.

### Using with Obsidian

Kash uses Markdown files with YAML frontmatter, which is fully compatible with
[Obsidian](https://obsidian.md/). Some notes:

- In Obsidian's preferences, under Editor, turn on "Strict line breaks".

- This makes the line breaks in kash's normalized Markdown output work well in Obsidian.

- Some kash files also contain HTML in Markdown.
  This works fine, but note that only the current line's HTML is shown in Obsidian.

- Install the [Front Matter Title
  plugin](https://github.com/snezhig/obsidian-front-matter-title):

  - Go to settings, enable community plugins, search for "Front Matter Title" and
    install.

  - Under "Installed Plugins," adjust the settings to enable "Replace shown title in
    file explorer," "Replace shown title in graph," etc.

  - You probably want to keep the "Replace titles in header of leaves" off so you can
    still see original filenames if needed.

  - Now titles are easy to read for all kash notes.

<br/>

<div align="center">

⛭

</div>

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
