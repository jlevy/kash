## Workspace and File Formats

A kash workspace is simply a directory of files.
The goal is for a workspace to be easy to use not just with kash but with other editors
or tools, so it's possible to edit, share, or commit files to version control.
It makes sense to devote a workspace to a single topic, project, or area of research.

File formats and conventions:

- A workspace holds items.
  Items are simply files.
  Files in a workspace are organized into folder by type, including resources, notes,
  configs, and exports.

- Files are named in the format
  `docs/day_1_workout_introduction_youtube_transcription_timestamps.doc.md`. The file
  suffix indicates the item type (note, resource, etc.)
  and format (.md, .yml, etc.).

- Many items have metadata attached, giving an item type (see `ItemType` in the kash
  item model), a format (see `Format`), a title, and other optional fields like a URL
  (if the item is or is derived from an online URL) and a description.

- Text items are stored in Markdown format with YAML front matter to hold the metadata,
  in the style of Jekyll or other static site generators.
  The front matter is separated from the body with a `---` separator.

- Markdown in these items optionally may be pure Markdown or optionally contain HTML. A
  common use case is to add `<span>` or `<div>` tags to wrap sections of the document
  with semantic meaning.
  Any HTML can be used but some conventions are helpful:

  - Timestamps from a transcription: `<span data-timestamp="12.34">Some trancribed
    text.</span>`

  - Citations: `<span class="citation">⟦<a href="https://example.com">…</a>⟧</span>`

  - Block for a description: `<div class="description">…</div>`

  - Block for full text: ``<div class="full-text">…</div>`

- Pure text Markdown is usually stored in an auto-formatted normalized form.
  This enforces strict Markdown syntax conventions and makes it easy to read in the
  console and to diff.
  One detail with the Markdown format is that bullet point items are always written with
  two newlines between them.
  This makes chunking in LLMs easier, so that each bullet point is a separate paragraph.

- Resource items are often simply links to online resources such as a URL or YouTube
  video. These are stored as YAML frontmatter only (no body), with a title, description,
  URL and other fields.

- Config items are items where the body of the item is YAML. These are used to configure
  webpages or documents.
  Note that config items are have both YAML frontmatter (the metadata) and the YAML body
  (the content).

- Additional settings and data are stored in hidden directories (beginning with a `.`).
  The `.archive` directory contains archived items.
  The `.settings` directory contains settings, such as the current selection.
  The `.logs` directory contains logs.
