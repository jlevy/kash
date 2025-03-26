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
