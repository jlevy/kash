<div align="center">

<p style="max-width: 400px;">

<br/>

<b>⎮Kash⎮</b>

<b><i>An AI-native command line for modern workflows.</i></b>

⛭

</p>

</div>

## What is Kash?

> “*Civilization advances by extending the number of important operations which we can
> perform without thinking about them.*” —Alfred North Whitehead

Kash (“Knowledge Agent SHell”) is a Python framework and an interactive, command-line
power tool for practical knowledge tasks.

It’s an exploration of a better way to remix, combine, and interactively explore how to
build tools and workflows by composing the myriad of AI tools, APIs, and libraries.

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
  video.

- **MCP support:** Finally, an action is also an **MCP tool** you can use it in any MCP
  client (like Anthropic Desktop).

- **Full extensibility:** Kash is tool agnostic and runs locally, on file inputs in
  simple formats, so you own and manage your data and workspaces however you like.
  You can use it with **OpenAI GPT-4o and o1**, **Anthropic Claude 3.5/3.7**, **Groq
  Llama, Qwen, and Deepseek models** (and any others via **LiteLLM**), **Deepgram**,
  **Perplexity**, **Firecrawl**, **Exa**, **LlamaIndex**, **ChromaDB**, and any Python
  libraries.

Use Kash actions to do deep research, transcribe videos, summarize and organize
transcripts and notes, write blog posts, extract or visualize concepts, check citations,
convert notes to PDFs or beautifully formatted HTML, or perform numerous other
content-related tasks possible by orchestrating AI tools in the right ways.

As I've been building Kash over the past couple months, I found I've found it's not only
faster to do complex things, but that it has also become replacement for my usual shell.
It's the power-tool I want to use alongside Cursor and ChatGPT/Claude.
I find it is much more powerful for local usage than than bash/zsh/fish.
If you're a command-line nerd, you might like it a lot.

But my hope is that with these enhancements, the shell is also far more friendly and
usable by anyone reasonably technical, and does not feel so esoteric as a typical Unix
shell.

Finally, one more thing: Kash is also my way of experimenting with something else new: a
**rich, web-enhanced terminal UI** that lets you seamlessly add graphics to the
terminal. I've separately built a new desktop terminal app, Kerm, which adds support for
a simple "Kerm codes" protocol for UX components like clickable text, buttons, tooltips,
and popovers in the terminal, encoded as OSC codes.
Because Kash supports these codes, as this develops you will get the visuals of a web
app layered on the flexibility of a text-based terminal.

## Is Kash Mature?

No. :) It's the result of a couple months of coding and experimentation, and it's very
much in progress. Please help me make it better by sharing your ideas and feedback!
It's easiest to DM me at [twitter.com/ojoshe](https://x.com/ojoshe).
My contact info is at [github.com/jlevy](https://github.com/jlevy).

[**Please follow or DM me**](https://x.com/ojoshe) for future updates or if you have
ideas, feedback, or use cases for Kash!

## What is Included?

- An **action framework** that includes:

  - A [**data model**](https://github.com/jlevy/kash/tree/main/kash/model) based on
    `Item`s, which are documents, resources like URLs, concepts, etc., stored simply as
    files in known any of several formats (Markdown, Markdown+HTML, HTML, YAML resource
    descriptions, etc.)

  - An **execution model** for `Action`s that take input `Item` inputs and produce
    outputs, as well as `Parameters` for acions and `Preconditions` that specify what
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
    HTML, Python, and YAML, as well as deteciton of file types and conventions for
    readable filenames based on file type

  - **Dependency tracking** among action operations (sort of like a Makefile) so that
    Kash can recognize if the output of an action already exists and, if it is
    cacheable, skip running the action

  - **Python decorators** that let you register and add new commands and actions, which
    can be packaged into libraries, including libraries with new dependencies

- A **hybrid command-line/natual language/Python shell**, based on
  [xonsh](https://github.com/xonsh/xonsh)

  - About 100 simple **built-in commands** for listing, showing, and paging through
    files, etc. (use `commands` for the full list, with docs) plus all usual shell tools

  - Enhanced **tab completion** that includes all actions and commands and parameters,
    as well as some extras like help summaries populated from
    [tldr](https://github.com/tldr-pages/tldr)

  - An **LLM-based assistant** that wraps the docs and the kash source code into a tool
    that assists you in using or extending kash (this part is quite fun!)

- A supporting **library of tools** to make these work more easily:

  - A **content and media cache**, which for downloading saving cached versions of video
    or audio and **audio transcriptions** (using Whisper or Deepgram)

  - A set of tools [**chopdiff**](https://github.com/jlevy/chopdiff) to tokenize and
    parse documents simply into paragraphs, sentences, and words, and do windowed
    transformations and filtered diffs (such as editing a large document but only
    inserting section headers or paragraph breaks)

  - A new Markdown auto-formatter, [**Flowmark**](https://github.com/jlevy/flowmark), so
    that text documents (like LLM outputs) are saved in a normalized form that can be
    diffed consistently

- An optional **enhanced terminal UI** some major enhancements to the terminal
  experience:

  - Sixel graphics support (see images right in the terminal)

  - A local server for serving information on files as web pages that can be accessed as
    OSC 8 links

  - Sadly, we may have mind-boggling AI tools, but Terminals are still incredibly
    archaic and don't support these features well (more on this below) but I have a new
    terminal, Kerm, that shows these as tooltips and makes every command clickable
    (please contact me if you'd like an early developer preview, as I'd love feedback)

All of this is only possible by relying on a wide variety of powerful libraries,
especially [LiteLLM](https://github.com/BerriAI/litellm),
[yt-dlp](https://github.com/yt-dlp/yt-dlp),
[Pydantic](https://github.com/pydantic/pydantic),
[Rich](https://github.com/Textualize/rich),
[Ripgrep](https://github.com/BurntSushi/ripgrep), [Bat](https://github.com/sharkdp/bat),
[jusText](https://github.com/miso-belica/jusText),
[WeasyPrint](https://github.com/Kozea/WeasyPrint),
[Marko](https://github.com/frostming/marko), and
[Xonsh](https://github.com/xonsh/xonsh).

## Installation

### Running the Kash Shell

Kash offers a shell environment based on [xonsh](https://xon.sh/) augmented with an LLM
assistant and a few other inhancements.
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

For macOS, if you have [brew](https://brew.sh/) installed, it's easy to install uv:

```shell
brew update
brew install uv
```

For Ubuntu:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See [uv's docs](https://docs.astral.sh/uv/getting-started/installation/) for other
platforms and installation methods.

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
# Install pyenv and other tools:
curl https://pyenv.run | bash
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

For each command below you can use tab completion (which shows information about each
command or option) or run with `--help` to get more details.

```shell
# Check the help page for a full overview:
help

# Confirm kash is set up correctly with right tools:
check_tools

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

# A few more possibilities...

# Note it's fine to rerun commands on the same arguments and whenever
# possible intermediate results are cached. The philosophy is actions
# should be cached and idempotent when possible (a bit like a makefile).

# Let's now look at the concepts discussed in that video (adjust the filename
# if needed):
transcribe_format https://www.youtube.com/watch?v=_8djNYprRDI
find_concepts

# This is the list of concepts:
show

# But we can actually save them as items:
save_concepts

# We now have about 40 concepts. But maybe some are near duplicates (like
# "high intensity interval training" vs "high intensity intervals").
# Let's embed them and find near duplicates:
find_near_duplicates

# In my case I see one near duplicate, which I'll archive:
archive

# And for fun now let's visualize them in 3d (proof of concept, this could
# get a lot better):
graph_view --concepts_only

# We can also list all videos on a channel, saving links to each one as
# a resource .yml file:
list_channel https://www.youtube.com/@Kboges

# Look at what we have and transcribe a couple more:
files resources
transcribe resources/quality_first.resource.yml resources/why_we_train.resource.yml

# Another interesting note: you can process a really long document.
# This one is a 3-hour interview. Kash uses sliding windows that process a
# group of paragraphs at a time, then stitches the results back together:
transcribe_format https://www.youtube.com/watch?v=juD99_sPWGU

show_webpage
```

### Creating a New Workspace

Although you don't always need one, a *workspace* is very helpful for any real work in
Kash. It's just a directory of files, plus a `.kash/` directory with various logs and
metadata.

Note the `.kash/cache` directory contains all the downloaded videos and media you
download, so it can get large.
You can delete these files if they take up too much space.

Typically, we name them like `health.kb` or `personal.kb`, because that makes it clear
they are in a certain format and may have other data.

Pick a workspace that encompasses a project or topic, and it lets you keep things
organized.

Type `workspace` any time to see the current workspace.

By default, when you are not using the shell inside a workspace directory, or when you
run Kash the first time, it uses the default *sandbox workspace*.

Once you create a workspace, you can `cd` into that workspace and that will become the
current workspace. (If you're familiar with how the `git` command-line works in
conjunction with the `.git/` directory, this behavior is very similar.)

To start a new workspace, run a command like

```
workspace health
```

This will create a workspace directory called `health.kb` in the current directory.
You can run `cd health.kb` or `workspace health` to switch to that directory and begin
working.

### Essential Kash Commands

Kash has quite a few basic commands that are easier to use than usual shell commands.
You can always run `help` for a full list, or run any command with the `--help` option
to see more about the command.

A few of the most important commands for managing files and work are these:

- `check_tools` to confirm your kash setup has necessary tools (like bat and ffmpeg).

- `files` lists files in one or more paths, with sorting, filtering, and grouping.

- `workspace` to show or select or create a new workspace.
  Initially you work in the "sandbox" workspace but for more real work you'll want to
  create a workspace, which is a directory to hold the files you are working with.

- `select` shows or sets selections, which are the set of files the next command will
  run on, within the current workspace.

- `edit` runs the currently configured editor (based on the `EDITOR` environment
  variable) on any file, or the current selection.

- `show` lets you show the first file in the current selection or any file you wish.
  It auto-detects whether to show the file in the console, the browser, or using a
  native app (like Excel for a .xls file).

- `param` lets you set certain common parameters, such as what LLM to use (if you wish
  to use non-default model or language).

- `logs` to see full logs (typically more detailed than what you see in the console).

- `history` to see recent commands you've run.

- `import_item` to add a resource such as a URL or a file to your local workspace.

The set of actions that do specific useful things is much longer, but a few to be aware
of include:

- `chat` chat with any configured LLM, and save the chat as a chat document.

- `web_search_topic` searches the web using Exa.

- `crawl_webpage` fetches a webpage and scrapes the content as text, using Firecrawl.

- `download_media` downloads video or audio media from any of several services like
  YouTube or Apple Podcasts, using yt-dlp.

- `transcribe` transcribes video or audio as text document, using Deepgram.

- `proofread` proofreads a document, editing it for typos and errors only.

- `describe_briefly` describes the contents of a document in about a paragraph.

- `summarize_as_bullets` summarizes a text document as a bulleted item.

- `break_into_paragraphs` breaks a long block of text into paragraphs.

- `insert_section_headings` inserts section headings into a document, assuming it is a
  document (like a transcript after you've run `break_into_paragraphs`) that has
  paragraphs but no section headers.

- `show_webpage` formats Markdown or HTML documents as a nice web page and opens your
  browser to view it.

- `create_pdf` formats Markdown or HTML documents as a PDF.

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
