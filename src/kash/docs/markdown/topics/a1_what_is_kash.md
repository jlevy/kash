## Hello!

If you’re seeing this, you there’s a good chance I shared it with you for feedback.
Thank you for checking out Kash.

It’s new, the result of some experimentation over the past few months.
I like a lot of things about it but it isn’t mature and I’d love your help to make it
more usable. If you try it please **let me know** what works and what doesn’t work.
Or if you just don’t get it, where you lost interest or got stuck.
My contact info is at [github.com/jlevy](https://github.com/jlevy) or [follow or DM
me](https://x.com/ojoshe) (I’m fastest on Twitter DMs).
Thank you. :)

## What is Kash?

> “*Simple should be simple.
> Complex should be possible.*” —Alan Kay

Kash (“Knowledge Agent SHell”) is an experiment in making software tasks more modular,
exploratory, and flexible using Python and current AI tools.

The philosophy behind kash is similar to Unix shell tools: simple commands that can be
combined in flexible and powerful ways.
It operates on “items” such as URLs, files, or Markdown notes within a workspace
directory.

You can use Kash as an **interactive, AI-native command-line** shell for practical
knowledge tasks.

But it’s actually not just a shell, and you can skip the shell entirely.
It’s really simply **a Python library** that lets you convert a simple Python function
into “actions” that work in a clean way on plain files in a workspace.
An action is also an MCP tool, so it integrates with other tools like Anthropic Desktop
or Cursor.

So basically, it gives a unified way to use the shell, Python functions, and MCP tools.

It’s new and still has some rough edges, but it’s now working well enough it is feeling
quite powerful. It now serves as a replacement for my usual shell (previously bash or
zsh). I use it routinely to remix, combine, and interactively explore and then gradually
automate complex tasks by composing AI tools, APIs, and libraries.
And last but not least, the same framework lets me build other tools (like
[textpress](https://github.com/jlevy/textpress)).

And of course, kash can read its own functionality and enhance itself by writing new
actions.

### Kash Packages

The [kash-shell](https://github.com/jlevy/kash) package is the base package and includes
the Python framework, a few core utilities, and the Kash command-line shell.

Additional actions for handling more complex tasks like converting documents and
transcribing, researching, or annotating videos, are in the
[kash-docs](https://github.com/jlevy/kash-docs) and
[kash-media](https://github.com/jlevy/kash-media) packages, all available on PyPI and
quick to install via uv.

### Key Concepts

- **Actions:** The core of Kash are **actions**. By decorating a Python function with
  `@kash_action`, you can turn it into an action, which makes it more flexible and
  powerful. It can then be used like a command line command as well as a Python function
  or an MCP tool.

- **Workspaces:** A key element of Kash is that it does most nontrivial work in the
  context of a **workspace**. A workspace is just a directory of files that have a few
  conventions to make it easier to maintain context and perform actions.
  A bit like how Git repos work, it has a `.kash/` directory that holds metadata and
  cached content. The rest can be anything, but is typically directories of content and
  resources (often Markdown or HTML but also .docx or .pdf or links to web pages).
  All text files use [frontmatter-format](https://github.com/jlevy/frontmatter-format)
  so have YAML metadata that includes not just title or description, but also how it was
  created. All Markdown files are auto-formatted with
  [flowmark](https://github.com/jlevy/flowmark), which makes documents much easier to
  diff and version control (and prettier to read and edit).

- **Compositionality:** An action is composable with other actions simply as a Python
  function, so complex operations (for example, transcribing and annotating a video and
  publishing it on a website) actions can be built from simpler actions (say downloading
  and caching a YouTube video, identifying the speakers in a transcript, formatting it
  as pretty HTML, etc.). The goal is to reduce the “interstitial complexity” of
  combining tools, so it’s easy for you (or an LLM!) to combine tools in flexible and
  powerful ways.

- **Command-line usage:** In addition to using the function in other libraries and
  tools, an action is also **a command-line tool** (with auto-complete, help, etc.)
  in the Kash shell. So you can simply run `transcribe` to download and transcribe a
  video. In kash you have **smart tab completions**, **Python expressions**, and an **LLM
  assistant** built into the shell.

- **Support for any API:** Kash is tool agnostic and runs locally, on file inputs in
  simple formats, so you own and manage your data and workspaces however you like.
  You can use it with any models or APIs you like, and is already set up to use the APIs
  of **OpenAI** (GPT-5 is now the default model), **Anthropic Claude**, **Google
  Gemini**, **xAI Grok**, **Mistral**, **Groq (Llama, Qwen, Deepseek)** (via
  **LiteLLM**), **Deepgram**, **Perplexity**, **Firecrawl**, **Exa**, and any Python
  libraries. There is also some experimental support for **LlamaIndex** and **ChromaDB**.

- **MCP support:** Finally, an action is also an **MCP tool server** so you can use it
  in any MCP client, like Anthropic Desktop or Cursor.

### What Can Kash Do?

You can use kash actions to do deep research, transcribe videos, summarize and organize
transcripts and notes, write blog posts, extract or visualize concepts, check citations,
convert notes to PDFs or beautifully formatted HTML, or perform numerous other
content-related tasks possible by orchestrating AI tools in the right ways.

As I’ve been building kash over the past couple months, I found I’ve found it’s not only
faster to do complex things, but that it has also become replacement for my usual shell.
It’s the power-tool I want to use alongside Cursor and ChatGPT/Claude.
We all know and trust shells like bash, zsh, and fish, but now I find this is much more
powerful for everyday usage.
It has little niceties, like you can just type `files` for a better listing of files or
`show` and it will show you a file the right way, no matter what kind of file it is.
You can also type something like “? find md files” and press tab and it will list you I
find it is much more powerful for local usage than than bash/zsh/fish.
If you’re a command-line nerd, you might like it a lot.

But my hope is that with these enhancements, the shell is also far more friendly and
usable by anyone reasonably technical, and does not feel so esoteric as a typical Unix
shell.

Finally, one more thing: Kash is also my way of experimenting with something else new: a
**terminal GUI support** that adds GUI features terminal like clickable text, buttons,
tooltips, and popovers in the terminal.
I’ve separately built a new desktop terminal app, Kerm, which adds support for a simple
“Kerm codes” protocol for such visual components, encoded as OSC codes then rendered in
the terminal. Because Kash supports these codes, as this develops you will get the
visuals of a web app layered on the flexibility of a text-based terminal.
