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
