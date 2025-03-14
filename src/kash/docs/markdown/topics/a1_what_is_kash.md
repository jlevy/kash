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
  in the Kash shell. So you can simply run `transcribe` to downlaod and transcribe a
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
