## Kash Overview

Kash is an extensible command-line power tool for all kinds of technical and content
tasks. It integrates the models, APIs, and Python libraries with the flexibility and
extensibility of a modern command line interface.

### Command Line

The philosophy behind kash is similar to Unix shell tools: simple commands that can be
combined flexibly in powerful ways.
It operates on “items” such as URLs, files, or Markdown notes within a workspace
directory.

This command-line is also AI enabled.
Kash understands its own code can help you use and even extend it.
At any time you can ask a question and have the LLM-based assistant help you in how to
use kash. Anything you type that ends in a `?` is sent to the assistant.

Kash is built on top of xonsh, a Python-powered shell language.
This lets you run all kash commands, as well as have access to intelligent
auto-complete. In xonsh, you also have access to the full power of Python and the shell
when needed. Note xonsh is not strictly a POSIX shell, but it has a similar flavor.
Kash adapts xonsh in several ways, prioritizing ease of use in interactive settings.

You can always run regular shell commands like `ls`, but you may find you more typically
will want to use the variety of built-in commands and actions that are more powerful and
intuitive than old Unix commands.

### MCP Support

If the idea of having lots of commands runnable by an LLM sounds to you a little like
MCP, you’re right. Any action in kash can also be an MCP tool!

You can connect Claude Desktop or Cursor or other MCP clients to kash and use any kash
action as a tool. However, unlike the complexity of writing a new MCP server, the idea
here is to make it as simple as possible to create new actions, and for these actions to
be used by you or an agent.

Anyone, including kash itself, can write new actions.
(Yes, there is an action, `write_new_action`, that helps you write new actions.)
You write a simple Python function, add a decorator, and it becomes an action you can
use in your shell.

Finally, getting really useful things to work still takes effort, so I’ve also added a
number of little libraries to help with this.

### Supporting Complex Tasks

Because it’s really just a set of Python libraries, kash is more capable than a typical
shell. It is starting to become a sort of AI-friendly scripting framework as well.

Inputs and outputs of commands are stored as files, so you can easily chain commands
together and inspect intermediate results.

When possible, actions are nondestructive and idempotent—that is, they will either
create new files or simply skip an operation if it’s already complete.

So it can work a bit like a Makefile: suppose you run a command like `transcribe` on a
video. If you’ve already run that command on the same YouTube URL, kash knows it and can
recognize the downloaded video and transcribed text is already present in your current
workspace.

This is especially useful for slow actions (like downloading and transcribing videos).
(You can always add `--rerun` to an Action to force it to rerun.)

### Items and File Formats

Kash operates on **items**, which are URLs, files, text or Markdown notes, audio, video,
or media files, or other documents.
These are stored as simple files, in a single directory, called a **workspace**.
Typically, you want a workspace for a single topic or project.

Within a workspace, files can be organized into folders however you like, but typically
it would be by type, such as resources, docs, configs, and exports.
Most text items are stored in Markdown format with YAML front matter (the same format
used by Jekyll or other static site generators), optionally with some HTML for structure
if needed. But with kash you can process or export items in any other format you wish,
like a PDF or a webpage.

All items have a **source path**, which is simply the path of the file relative to the
workspace directory.
Item files are named in a simple and readable way, that reflects the title of the item,
its type, its format, and in some cases its provenance.
For example, `docs/day_1_workout_introduction_youtube_transcription_timestamps.doc.md`
might be an item that is a doc (a text file) that is transcription of a YouTube video,
including timestamps, in Markdown format.

The path (directory and filename) of each file is simply a convenient locator for the
item. The metadata on text items is in YAML metadata at the top of each file.
The metadata on items includes titles and item types, as you might expect, but also
provenance information, e.g. the URL where a page was downloaded from.
If an item is based on one or more other items (such as a summary that is based on an
original document), the sources are listed in a `derived_from` array within the
`relations` metadata.
This means actions can find citations or other data on the provenance of a given piece
of information.

This might sound a little complex, but it’s quite simple in practice.
All the metadata is in a standard format,
[Frontmatter Format](https://github.com/jlevy/frontmatter-format), and the information
is compatible with other apps and pretty self explanatory.

### Commands and Actions

Most things are done via kash **commands**, which are built-in operations (like listing
or selecting files to process), and kash **actions**, which are an extensible set of
capabilities, like downloading a file, summarizing a document using an LLM, transcribing
videos.

Kash actions operate on one or more items and produce one or more new items.
Actions can invoke APIs, use LLMs, or perform any other operation in Python.
You specify inputs to actions as URLs or source paths.

Commands and actions are just Python functions!
By decorating them with a kash decorator, they become commands in the shell.
But they can still be used from Python, as well.

Here is an example action:

```python
from kash.config.logger import get_logger
from kash.utils.errors import InvalidInput
from kash.exec import kash_action
from kash.exec.preconditions import has_html_body, has_text_body
from kash.model import Format, Item, ItemType
from kash.utils.common.format_utils import html_to_plaintext

log = get_logger(__name__)


@kash_action(precondition=has_html_body | has_text_body)
def strip_html(item: Item) -> Item:
    """
    Strip HTML tags from HTML or Markdown. This is a simple filter, simply searching
    for and removing tags by regex. This works well for basic HTML; use `markdownify`
    for complex HTML.
    """
    if not item.body:
        raise InvalidInput("Item must have a body")

    clean_body = html_to_plaintext(item.body)
    output_item = item.derived_copy(
        type=ItemType.doc,
        format=Format.markdown,
        body=clean_body,
    )

    return output_item
```

URLs that are provided as input and the output of actions are automatically stored as
new items in the workspace.
URLs or resources can be added manually, but this is normally not necessary.

### Interactive Exploration

The output of any command is always marked as the current **selection**, which is then
automatically available for input on a subsequent command.
This is sort of like Unix pipes, but is more convenient and incremental, and allows you
to sequence actions, multiple output items becoming the input of another action.

Actions also have **preconditions**, which reflect what kinds of content they can be run
on. For example, transcription only works on media URL resources, while summarization
works on readable text such as Markdown.
This catches errors and allows you to find actions that might apply to a given selected
set of items using `suggest_actions`.

### Programmatic Usage

Kash can be used entirely programmatically, so that actions are called just like
functions from Python, but the additional functionality of the items model, saving files
to a workspace, and so on, are all automatic.

This means you can use Kash to build your own CLI apps much more quickly.

For an example of this, see [textpress](https://github.com/jlevy/textpress), which wraps
quite a few kash actions to allow clean publishing of docx or PDF files on
[textpress.md](https://textpress.md/).

### Utilities and Supporting Libraries

Kash includes a number of utility libraries to help with common tasks, either in the
base `kash-shell` package or or smaller dependencies:

- See [frontmatter-format](https://github.com/jlevy/frontmatter-format) for the spec and
  implementation we use of frontmatter YAML format.

- See
  [utils/file_utils](https://github.com/jlevy/kash/tree/main/src/kash/utils/file_utils)
  for file format detection, conversion, filename handling, etc.

- See [chopdiff](https://github.com/jlevy/chopdiff) for a simple text doc data model
  that includes sentences and paragraphs and fairly advanced diffing, filtered diffing,
  and windowed transformations of text via LLM calls.

- See [clideps](https://github.com/jlevy/clideps) for utilities for helping with dot-env
  files, API key setup, and dependency checks.

- See [utils/common](https://github.com/jlevy/kash/tree/main/src/kash/utils/common) the
  rest of [utils/](https://github.com/jlevy/kash/tree/main/src/kash/utils) for a variety
  of other general utilities.
