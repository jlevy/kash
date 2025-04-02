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
