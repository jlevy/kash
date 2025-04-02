## The Philosophy of Kash

> “*Civilization advances by extending the number of important operations which we can
> perform without thinking about them.*” —Alfred North Whitehead

Here is a bit more motivation for experimenting with kash, why I think it's potentially
so useful, and some design principles.
(You may skip ahead to the next section if you just want a more concrete overview!)

### Why Apps Can't Solve All Your Problems

AI has radically changed the way we use software.
With LLMs and other generative AI models, we've seen big improvements in two areas:

1. Powerful general-purpose new AI tools (ChatGPT, Perplexity, etc.)

2. AI-powered features within specific SaaS tools that are built for the problem you
   want to solve, like Notion, Figma, Descript, etc.

While we have these powerful cloud apps, we all know numerous situations where our
problems aren't easily solved or automated with single tool like ChatGPT, Notion, Google
Docs, Slack, Excel, and Zapier.

If you want to use any of the newest AI models and APIs for something not supported by
an existing tool, you generally have to design and build it yourself—in Python and/or a
full-stack web app.

It's true tools like GitHub Copilot, Claude Code, and Cursor can help anyone write code
much faster. But even if you have a tool like this, building polished apps that are good
enough people will pay them takes time, and many good product ideas never get built.
And the curse of [Conway's Law](https://en.wikipedia.org/wiki/Conway%27s_law) means many
companies won't add specific features you want, or at best are likely to do it slowly.

In short, in spite of AI tools accelerating software, certain things don't change: we
are waiting for developers, product managers, designers, and entrepreneurs to design and
ship solutions for us.

### Why Do We Need an AI-Native Command Line?

So what does all this have to do with the command line?

Well, the classic Unix-style command line has been the Swiss Army knife for savvy
developers for decades.
(The bash shell, still used widely, was released 35 years ago!)

Like many developers, I love the terminal (I even wrote a popular
[guide on it](https://github.com/jlevy/the-art-of-command-line), with millions of
readers).

A fraction of developers do a lot in a terminal because it is the most efficient way to
solve many problems.
But among most normal people, the command line has pretty bad reputation.
This is a fair criticism.
Command-line shells generally still suffer from three big issues:

- Old and arcane commands, full of obscure behaviors that relatively few people remember

- A text-based interface many find confusing or ugly

- No easy, “native” support for modern tools, apps, and APIs (especially LLMs—and using
  `curl` to call OpenAI APIs doesn't count!)

Even worse, command lines haven't gotten much better.
Few companies make money shipping new command-line tooling.
(In the last few years this has slowly starting to change with tools like nushell, fish,
and Warp.)

Nonetheless, for all its faults, there is a uniquely powerful thing about the command
line: With a command line, you can do complex things that were never planned by an app
developer, a designer, or an enterpreneur building a product.

*You* know your problems better than anyone else.
Any tool that lets you solve complex problems yourself, without waiting for engineers
and designers, can radically improve your productivity.

I think it's a good time to revisit this idea.

In a post-LLM world, it should be possible to do more things without so much time and
effort spent (even with the help of LLMs) on coding and UI/UX design.

If we have an idea for a script or a feature or a workflow, we should not have to spend
weeks or months to iterate on web or mobile app design and full-stack engineering just
to see how well it works.

### The Goals of Kash

Kash is an experimental attempt at building the tool I've wanted for a long time, using
a command line as a starting point, and with an initial focus on content-related tasks.

That brings us to the goals behind building a new, AI-native shell.

- **Make simple tasks simple:** Doing a simple thing (like transcribing a video or
  proofreading a document) should be as easy as running a single command (not clicking
  through a dozen menus).
  We should be able to tell someone how to do something simply by telling them the
  command, instead of sharing a complex prompt or a tutorial video on how to use several
  apps.

- **Make complex tasks possible:** Highly complex tasks and workflows should be easy to
  assemble (and rerun if they need to be automated) by adding new primitive actions and
  combining primitive actions into more complex workflows.
  You shouldn't need to be a programmer to use any task—but any task should be
  extensible with arbitrary code (written by you and an LLM) when needed.

- **Augment human skills and judgement:** Many AI agent efforts aim for pure automation.
  But even with powerful LLMs and tools, full automation is rare.
  Invariably, the best results come from human review wherever it's needed—experimenting
  with different models and prompts, looking at what works, focusing expert human
  attention in the right places.
  The most flexible tools augment, not replace, your ability to review and manipulate
  information. It should help both very technical users, like developers, as well as less
  technical but sophisticated users who aren't traditional programmers.

- **Accelerate discovery of the workflows that work best:** We have so many powerful
  APIs, models, libraries, and tools now—but the real bottleneck is in discovering and
  then orchestrating the right workflows with the right inputs, models, prompts, and
  human assistance. Anyone should be able to discover new steps and workflows without
  waiting on engineers or designers.

- **Understand and build on itself:** A truly AI-native programming environment should
  improve itself! Kash can read its own code and docs, assist you with its own commands,
  and write new kash actions.
  Better languages and scripting tools can in fact make LLMs smarter, because it allows
  them to solve problems in ways that are simpler and less error prone.

A better command line like a first step toward an item-based information operating
system—an alternate, more flexible UX and information architecture for knowledge
workflows. My hope is that kash becomes the tool you need when you don't know what tool
you need.

### Design Principles

Key design choices:

1. **Flexibility and power arise from simple tools that can be recombined in complex
   ways** (like the old Unix model)

2. **Data formats should be simple, local, and transparent** (text files, Markdown,
   YAML, filenames with intuitive names, not opaque formats, sprawling JSON, or only
   stored in the cloud)

3. **Play well with other tools and APIs** (including local and cloud-based LLMs; edit
   content with external tools whenever necessary; use any APIs or libraries)

4. **Keep content human reviewable and editable at any stage** (never just assume
   automation will work; use formats that make diffs as easy and clear as possible)

5. **Make prompts, context, models, and changes transparent** (use formats that make LLM
   context and edits, diffs, and history as clear as possible, let the user pick the
   models they want at any time)

6. **Make interactive exploration easy but support automation and scripting when
   desired** (prefer chat or command-line interactions over a formal codebase at first,
   but also support scripts and use as a Python library, and tools to smooth the
   transition)

7. **Maintain context in workspaces** (keep files organized by project or effort in a
   folder that can be persisted, won't get lost, and includes content, metadata,
   actions, settings, selections, caches, history, etc.)

8. **Maintain metadata on files** (so you always know where each piece of content comes
   from (and keep this close to the content, as YAML frontmatter)

9. **Make operations idempotent** (resuming a task or workflow or restarting after a
   failure should be as simple as running again)

10. **Cache slow or costly operations** (track dependencies and content hashes and know
    when things need to rerun, like a makefile)

11. **Docs, code, and examples should be self-explanatory to both LLMs and humans** (so
    it is easy to add new capabilities—an AI-native coding environment should enhance
    itself!)

12. **User interfaces should be data-driven and gradually improve** (visuals and
    workflows should not be designed up front, but emerge naturally as data is
    manipulated and use cases become clearer)
