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
