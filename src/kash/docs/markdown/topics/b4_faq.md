## Frequently Asked Questions

### What is kash?

Kash is an extensible command-line power tool for all kinds of technical and content
tasks. It integrates the models, APIs, and Python libraries with the flexibility and
extensibility of a modern command line interface.

In addition, it is built on a simple set of Python tools and libraries to make it easier
and more powerful to performing tasks with the help LLM tools and agents.

Finally, kash is compatible with MCP. Any actions in kash are MCP tools!
The general idea is that any work you or an agent need to do should be broken into known
tasks, called actions, and these can then be used by you or an agent.
Anyone, including kash itself, can write new actions easily.
(Yes, there is an action, `write_new_action`, that helps you write new actions.)

The philosophy behind kash is similar to Unix shell tools: simple commands that can be
combined in flexible and powerful ways.
It operates on "items" such as URLs, files, or Markdown notes within a workspace
directory.

For more detailed information, you can run `help` to get background and a list of
commands and actions.

### How do I get started using kash?

Run `help` to get an overview.

Or use the kash assistant to get help.
Just ask natural language questions on the command line.
(These are auto-detected or you can start them with `?` to be sure they go to the
assistant.) The kash assistant knows the docs and can answer many questions!

Remember there are tab completions on many commands and actions, and that can help you
get started.
Press **tab** on a blank line to see more help commands and frequently asked
questions.

*See also:* `What are the most important kash commands?`

### How does kash accept both shell and assistant requests to the LLM with natural language?

By default, if a command is valid shell or Python, kash will treat it as a shell
command, using xonsh's conventions.

Commands that begin with a `?` are automatically considered assistant requests.

As a convenience, if you begin to type more than one word that is not a valid command,
it will auto-detect and type the `?` for you.
You can also press <space> at the beginning of the line, and this will also type the `?`
for you.

By default the assistant uses a fast LLM (see `param` to check which one is set) but you
can use `assist` do make an assistant request using a different LLM if you want more
careful answers or to try a different model.

### Do you need to know Bash to use kash?

Right now, it certainly helps, as it is focusing on basic functionality.
But one goal of kash is to make it *far* easier for less technical people to explore and
learn a command-line interface.
Give it a try and let me know!

### What models are available?

You can use kash with any APIs or models you like!
By default it uses APIs from OpenAI, Deepgram, and Anthropic.

### How can I transcribe a YouTube video or podcast?

Here is an example of how to transcribe a YouTube video or podcast, then do some
summarization and editing of it.
(Click or copy/paste these commands.)

```shell
# Set up a workspace to test things out:
workspace fitness

# A short transcription:
transcribe 'https://www.youtube.com/watch?v=XRQnWomofIY'

# Take a look at the output:
show

# Now manipulate that transcription (note we are using the outputs of each previous command,
# which are auto-selected as input to each next command):
strip_html
break_into_paragraphs
summarize_as_bullets
create_pdf

# Note transcription works with multiple speakers:
transcribe 'https://www.youtube.com/watch?v=uUd7LleJuqM'

# Or all videos on a channel and then download and transcribe them all:
list_channel 'https://www.youtube.com/@Kboges'
transcribe

# Process a really long document (this one is a 3 hour interview) with sliding windows,
# and a sequence action that transcribes, formats, and includes timestamps for each
# paragraph:
transcribe_format 'https://www.youtube.com/watch?v=juD99_sPWGU'

# Now look at these as a web page:
webpage_config
# Edit the config if desired:
edit
# Now generate the webpage:
webpage_generate
# And look at it in the browser:
show

# Combine more actions in a more complex combo action, adding paragraph annotations and headings:
transcribe_annotate_summarize 'https://www.youtube.com/watch?v=XRQnWomofIY'
show_webpage
```

### How is kash different from other shells like bash (or fish or xonsh)?

Kash is built directly on top of xonsh, so it is very much like a regular shell, but has
extra compatibility with Python, like xonsh.

But it is intended to be used quite differently from a regular shell.

Although nothing stops you from using traditional commands like `df` or `grep`, most
commands you will want to use are kash commands that are more powerful.
For example, `files` is usually easier to use than `ls` and `show` is easier to use than
`less` or `open`.

Kash also wraps the shell to natively supports natural language so you can ask questions
by pressing space before typing a new command (or starting the line with `?`).

There are other customizations kash needs to make to xonsh, including tab completion to
fit kash commands and actions, reading metadata on items, etc.

### Can kash replace my regular shell?

While kash doesn't aim to completely replace all uses of the shell—for example, that's
hard to do in general for remote use, and people have many constraints, customizations,
and preferences—I've found it's highly useful for a lot of situations.
It is starting to replace bash or zsh for day-to-day local use on my laptop.

Kash basically wraps xonsh, so you have almost all the functionality of xonsh and Python
for any purpose.

The [official xonsh tutorial](https://xon.sh/tutorial.html) has a good overview of using
xonsh, including the many ways it differs from bash and other shells like fish.

### What are commands and actions in kash?

Any command you type on the command-line in kash is a command.

Some commands are basic, built-in commands.
The idea is there are relatively few of these, and they do important primitive things
like `select` (select or show selections), `show` (show an item), `files` (list
files—kash's better version of `ls`), `workspace` (shows information about the current
workspace), or `logs` (shows the detailed logs for the current workspace).
In Python, built-in commands are defined by simple functions.

But most commands are defined as an *action*. Actions are invoked just like any other
command but have a standard structure: they are assumed to perform an "action" on a set
of items (files of known types) and then save those items, all within an existing
workspace. Actions are defined as a subclass of `Action` in Python.

### Does nvm (Node version manager) work in kash?

It's hard to get nvm to work well in xonsh, but try [fnm](https://github.com/Schniz/fnm)
instead! It works just as well and kash supports `fnm` automatically so it auto-detects
and uses fnm to switch or install Node versions for directories with Node projects (i.e.
there is an `.nvmrc`, `.node-version`, or `package.json` file).
