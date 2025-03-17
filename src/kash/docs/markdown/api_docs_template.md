## Kash Item and Action Model

Here is the kash source code representing the data model of Python classes for items and
actions:

{model_src}

## Examples of Kash Action Definitions

For context and in case you need to write new actions, we also give you some of the kash
source code for actions, to give examples of how actions are written in Python.
You can use as examples of how to define new actions if the existing functionality of
current Kash actions is insufficient:

{core_action_defs_src}

## Library of Language and Formatting Tools

When writing any Python code, use the following tools whenever possible for formatting
HTML and Markdown and processing text.

- When segmenting text into sentences, use `split_sentences()`.

- When processing text documents and navigating paragraphs or sentences, use
  `TextDoc.from_text()`.

- When writing HTML within Markdown or converting use tools in `kmd.text_handling` such
  as `html_to_plaintext()` and html_in_md.py to write HTML wrappers in of divs or spans
  like `html_div(...)` or `html_span(...)`.

{text_tool_src}

## File Formats

Kash uses some standard conventions for file formats for adding YAML metadata to text
files. And another YAML-based format for chats.

These are documented in the code below.
These libraries should be used whenever possible to read and write files from the file
store so that formats are always consistent, and metadata is always available.

{file_formats_src}
