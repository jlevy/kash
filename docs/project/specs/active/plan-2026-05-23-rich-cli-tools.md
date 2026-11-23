---
title: Plan Spec: rich-cli-tools
description: New standalone package for Python terminal UX — Rich enhancements, terminal detection, OSC links, live displays
---
# Feature: `rich-cli-tools` — A Focused Terminal UX Package for Python CLIs

**Date:** 2026-05-23 (last updated 2026-06-12)

**Author:** Joshua Levy

**Status:** Draft

## Overview

Create a new standalone open-source repo, **`rich-cli-tools`** (PyPI name
verified available), consolidating the generic terminal/CLI
user-experience utilities currently scattered across **kash**
(`utils/rich_custom/`, `config/unified_live.py`,
`shell/file_icons/nerd_icons.py`) and **clideps** (`terminal/`,
`ui/styles.py`, `ui/rich_output.py`).

The package covers everything a Python CLI needs for a polished terminal
experience: improved Rich Markdown rendering, OSC-8-aware cell-width
math, terminal capability detection, inline images (sixel/kitty), live
multi-task progress displays, Nerd Font file icons, and consistent
styled-output helpers.

**Internal structure documents the dependency split.** Rich is a hard
dependency of the installed package, but the source layout makes obvious
which modules need Rich and which don't. Two subpackages —
`terminal/` and `icons/` — use only the stdlib; one subpackage —
`display/` — uses Rich. This is for clarity and future flexibility,
not for an optional install: agents and humans reading the source can
see at a glance which utilities are about the terminal *emulator* (OSC
codes, capabilities, images) versus *Rich's rendering layer*.

The package depends on `rich`, `strif`, and `typing-extensions`; it
does **not** depend on clideps — the dependency will eventually flow
the other way (clideps becomes a *consumer* of this package and
refocuses on package/env management).

The repo also ships a **companion agent skill** (`SKILL.md`, Agent
Skills open standard) so that coding agents asked to "build a Python
CLI" can discover the package and follow a menu of high-quality UX
patterns.

This spec is written to be handed to an agent and implemented
end-to-end: scaffolding from the `simple-modern-uv` template,
module-by-module porting with decoupling notes, tests, docs, skill,
and publishing.

## Goals

- One focused package for terminal UX in Python CLIs, useful to humans
  and to agents driving CLIs
- **Explicit internal layering**: a clear, documented split between
  dep-free terminal/data modules and Rich-dependent display modules.
  Each module's path advertises which side it's on.
- Minimal external dependency surface: `rich`, `strif`,
  `typing-extensions` (see Dependency Policy)
- No dependency on clideps, kash, or flowmark; clideps later becomes a
  *consumer* of this package
- Scaffolded from `simple-modern-uv` (copier template) with the
  standard Makefile / uv / ruff / basedpyright / pytest / dynamic
  versioning setup
- Companion `SKILL.md` so agents can apply the package's patterns when
  building any Python CLI
- Golden/tryscript tests with ANSI-stripping for behavioral safety
  during the port, plus ported pytest suites
- kash and (later) clideps migrate to consume the published package via
  shims, then drop their internal copies

## Non-Goals

- Not a CLI framework (no argument parsing, no subcommand dispatch —
  argparse/typer remain the user's choice; the CLI introspection bundle
  is a separate future package per the utility-extraction spec)
- Not a kitchen-sink utility lib: file utils, async gather, chat
  formats, markdown *processing* (vs. rendering) are out of scope —
  they have their own phases in `plan-2026-05-23-utility-extraction.md`
- No dependency on `gather-limited` (doesn't exist yet); the progress
  display vendors the small task-state types it needs (see Design)
- Not porting kash-specific styling (`text_styles.py`'s 240-entry style
  dict, `KashHighlighter`, kash color palette) — only neutral defaults
- No Windows-specific terminal work in v0.1 beyond what the ported code
  already handles (sixel/kitty detection degrades gracefully)

## Background

kash accumulated a set of high-quality Rich/terminal utilities that fix
real gaps in Rich (OSC-8-aware cell width, arbitrary-prefix indent,
span-preserving case transforms, a better Markdown renderer, a
single-Live multiplexer, a uv/pnpm-style multitask progress display).
clideps accumulated terminal capability detection, OSC-8 link helpers,
and sixel/kitty image display — but clideps is really a
package-management/env-setup tool and those pieces don't belong there
long-term.

### Per-module maturity (read from current source, 2026-06-12)

Direct review of each candidate module — git history, in-kash usage
(production callers, excluding tests and the module itself), inline
tests, and coupling to kash internals:

| Module | LOC | Inline tests | kash coupling | Used by in kash | Maturity |
|---|---|---|---|---|---|
| `ansi_cell_len.py` | 74 | yes | none | 1 (doc normalization) | **Mature.** Fixes a real Rich bug (OSC-8 links break `cell_len`). Drop-in. |
| `rich_char_transform.py` | 91 | yes | none | 0 in production* | **Mature, niche.** *Only used in-tree by the markdown fork (heading uppercasing). |
| `rich_indent.py` (`Indent`) | 71 | none | none | 1 (shell_output) | **Mature** but lacks an inline test (trivial to add). Fills a real Rich gap (Padding is whitespace-only). |
| `rich_markdown_fork.py` | 771 | partial | 2 style consts | 3 (welcome, kmarkdown, shell_output) | **Usable, fork-risk.** Hard fork of Rich's `markdown.py` pinned to v13.9.4 internals; uses `rich._loop`, `rich._stack` private APIs; monkey-patches `rich.markdown.Markdown` at import. Single-commit history (no churn) — works but will need maintenance when Rich's internals shift. |
| `multitask_status.py` | 770 | yes | unified_live + progress types + text_styles | 1 (shell_output) | **Usable, moderately mature.** 3 commits; styles decoupled in commit `859424e`. Many moving parts. |
| `unified_live.py` | 249 | none | kash logger + text_styles | 4 (shell_callable_action, custom_shell, assistant_commands) | **Heavily exercised but "magic."** Singleton that patches Rich's one-Live-at-a-time limit; never refactored. Trickiest port; highest behavior risk. |
| `nerd_icons.py` | 946 | none | **none** | 2 (files_command, local_server_routes) | **Mature as data table.** Clean port of eza's icons with proper license attribution. Most of the LOC is icon-table data. Will slowly drift from eza upstream. |
| `color_for_format.py` | 72 | none | Format enum + kash colors | (kash internal) | **Stays in kash** — coupled to Format enum. Not extractable. |
| clideps `terminal/osc_utils.py` | 95 | (some) | rich only | (clideps internal) | **Mature.** Both string and Rich-Text OSC-8 variants — splits naturally between the package's two layers. |
| clideps `terminal/terminal_features.py` | 57 | none | clideps-only | (clideps `pkg-check`) | **Mature** detection logic; Rich-coupling is only in the report-printing helper, easy to split. |
| clideps `terminal/terminal_images.py` | 141 | none | NotSupportedError + STYLE_HINT | (clideps internal) | **Usable.** subprocess/termios-based detection + display; Rich only for an error fallback print — refactor to raise instead. |
| clideps `ui/styles.py` | 32 | none | rich only | (clideps-wide) | **Mature** small constants file. |
| clideps `ui/rich_output.py` | 147 | none | flowmark + clideps styles | (clideps-wide) | **Mature.** One `flowmark.fill_text` call to replace (stdlib `textwrap` or Rich's wrapping). |

PyPI name availability checked: `rich-cli-tools`, `richcli`, and
`rich-terminal-tools` are all unclaimed. Working name: `rich-cli-tools`.

### Ship-now vs. ship-careful (informs Phase ordering)

- **Ship-now** (safe, well-tested, low coupling): `ansi_cell_len`,
  `rich_char_transform`, `rich_indent`, `nerd_icons`, clideps's
  `osc_utils` / `styles` / `terminal_features` (detection half).
- **Ship-careful** (more complex; need careful test coverage):
  `multitask_status`, `rich_markdown_fork`, `unified_live`,
  `terminal_images`, clideps's `rich_output`.

This isn't a hard tier separation — all of these ship in v0.1 — but it
informs the implementation phase ordering and where to focus
tryscript golden tests.

### Prior related work in this repo

- `plan-2026-05-23-utility-extraction.md` — the full extraction menu;
  this spec implements its Phase C (terminal/Rich package) and the
  movement half of Phase D (clideps trim), with the explicit decision
  that the new package does NOT depend on gather-limited.
- Commit `859424e` (merged via PR #7) — decoupled progress symbols into
  injectable `ProgressSymbols`, preparing `multitask_status` for
  extraction.

## Design

### Repo layout

Scaffolded from `simple-modern-uv` (see Scaffolding below), with three
internal subpackages that document the dependency split:

- **`terminal/`** — pure stdlib. Anything about the terminal emulator
  itself (escape codes, capability detection, image subprocess).
- **`icons/`** — pure stdlib. Pure data tables and a lookup function.
- **`display/`** — Rich-required. Everything that builds on Rich's
  rendering layer.

Plus two top-level modules (`errors.py`, `progress_types.py`) that span
the layers — both stdlib-only.

```
rich-cli-tools/
├── pyproject.toml                  # from template; deps: rich (only)
├── README.md                       # with embedded demo screenshots/asciinema
├── src/rich_cli_tools/
│   ├── __init__.py                 # curated re-exports
│   ├── errors.py                   # NotSupportedError, package base (stdlib)
│   ├── progress_types.py           # TaskState/TaskInfo/TaskSummary/ProgressSymbols (stdlib)
│   │
│   ├── terminal/                   # ── pure stdlib ──
│   │   ├── __init__.py
│   │   ├── osc.py                  # OSC-8 hyperlink escape strings
│   │   ├── features.py             # TerminalInfo + capability detection (data)
│   │   └── images.py               # sixel/kitty inline image display (subprocess); raises NotSupportedError
│   │
│   ├── icons/                      # ── pure stdlib ──
│   │   ├── __init__.py
│   │   └── nerd_fonts.py           # Icons enum, lookup tables, icon_for_file()
│   │
│   └── display/                    # ── Rich-required ──
│       ├── __init__.py
│       ├── cells.py                # ansi_cell_len
│       ├── char_transform.py       # text_upper, text_lower (Text-preserving)
│       ├── indent.py               # Indent renderable
│       ├── osc_rich.py             # OSC-8 wrapper returning rich.Text
│       ├── markdown.py             # CustomMarkdown + explicit install()
│       ├── styles.py               # neutral Rich style constants
│       ├── output.py               # print_heading/error/warning/success + format_success_or_failure
│       ├── live.py                 # UnifiedLive multiplexer
│       ├── multitask.py            # MultitaskStatus live display
│       └── features_report.py      # pretty-print TerminalInfo (Rich consumer of terminal/features)
│
├── skills/
│   └── python-cli-ux/
│       └── SKILL.md                # companion agent skill (see Skill section)
├── examples/
│   ├── demo_markdown.py            # render a sample doc with the improved renderer
│   ├── demo_multitask.py           # synthetic multi-task progress run
│   ├── demo_features.py            # print terminal capability report
│   └── demo_icons.py               # icon listing for a directory
├── tests/                          # ported pytest suites
└── tryscript/                      # golden CLI-output tests (ANSI-stripped)
```

The user-facing API (re-exported from `rich_cli_tools.__init__`)
remains flat for ergonomics — the subpackage layout is for source-level
documentation, not for forcing long import paths on consumers.

### Module inventory (source → target)

Grouped by target subpackage so the dependency split is self-evident.

#### `terminal/` — pure stdlib, no Rich import

| Source | LOC | Target | Decoupling |
|---|---|---|---|
| clideps `terminal/osc_utils.py` (string-only half) | ~50 of 95 | `terminal/osc.py` | Split: keep the OSC-8 string builders here; move the `osc8_link_rich(...) -> rich.Text` wrapper to `display/osc_rich.py` |
| clideps `terminal/terminal_features.py` (detection half) | ~30 of 57 | `terminal/features.py` | Split: keep `TerminalInfo` dataclass + the capability-detection logic (env vars, TTY checks) here. Move the report-printing function to `display/features_report.py`. |
| clideps `terminal/terminal_images.py` | 141 | `terminal/images.py` | Drop the `STYLE_HINT` printing fallback — `display_image()` returns on success, raises `NotSupportedError` on failure with a useful message. Callers decide how to print errors. |

#### `icons/` — pure stdlib, no Rich import

| Source | LOC | Target | Decoupling |
|---|---|---|---|
| kash `shell/file_icons/nerd_icons.py` | 946 | `icons/nerd_fonts.py` | None — already zero-coupling stdlib. Add a basic test for `icon_for_file()` over a fixture set of common filenames (currently has no tests). |

#### Top-level (stdlib only, span both layers)

| Source | LOC | Target | Decoupling |
|---|---|---|---|
| clideps `errors.py` (`NotSupportedError`) | ~5 | `errors.py` | Move; add a package base class if useful |
| kash `utils/api_utils/progress_protocol.py` (types subset) | ~80 of 316 | `progress_types.py` | Vendor `TaskState`, `TaskInfo`, `TaskSummary`, `ProgressSymbols`. Do **not** vendor `ProgressTracker` Protocol / `SimpleProgressTracker` — they belong with the future gather-limited package (see interop note). |

#### `display/` — Rich-required

| Source | LOC | Target | Decoupling |
|---|---|---|---|
| kash `utils/rich_custom/ansi_cell_len.py` | 74 | `display/cells.py` | None — already self-contained |
| kash `utils/rich_custom/rich_char_transform.py` | 91 | `display/char_transform.py` | None — already self-contained |
| kash `utils/rich_custom/rich_indent.py` | 71 | `display/indent.py` | Add an inline test (currently none) |
| clideps `terminal/osc_utils.py` (Rich half) | ~45 of 95 | `display/osc_rich.py` | Just the `osc8_link_rich(...) -> rich.Text` wrapper; depends on `terminal/osc.py` for the escape string |
| clideps `ui/styles.py` | 32 | `display/styles.py` | Merge with neutral defaults needed by multitask/markdown |
| clideps `ui/rich_output.py` | 147 | `display/output.py` | **Replace `flowmark.fill_text` with stdlib `textwrap.fill` or Rich's own wrapping** (used in exactly one function). |
| clideps `terminal/terminal_features.py` (report half) | ~27 of 57 | `display/features_report.py` | Pretty-print a `TerminalInfo` (consumes the dataclass from `terminal/features.py`). |
| kash `utils/rich_custom/rich_markdown_fork.py` | 771 | `display/markdown.py` | Inline 2 style constants from `kash.config.text_styles`; make the `rich.markdown.Markdown` monkey-patch **opt-in** via an explicit `install()` call (today it patches at import time, line 771). Pin a minimum rich version and add a CI canary test that fails loudly when a new rich release breaks the fork (it uses `rich._loop`, `rich._stack` private APIs). |
| kash `config/unified_live.py` | 249 | `display/live.py` | Replace `kash.config.logger.get_console` with injectable console (default `rich.get_console()`); inline 2 spinner/color constants; **replace `strif.AtomicVar` with `threading.Lock` + plain variable** (small refactor) |
| kash `utils/rich_custom/multitask_status.py` | 770 | `display/multitask.py` | Take live-display via constructor instead of `kash.config.unified_live.get_unified_live()` (accept optional `UnifiedLive` or plain console). Emojis already injectable via `ProgressSymbols` (commit `859424e`). **Inline `strif.abbrev_str` and `strif.single_line`** (each ~5 lines) into a small `_internal.py` or directly into the module. |

#### Explicitly not ported

- kash `shell/file_icons/color_for_format.py` (72 LOC) — coupled to
  kash's `Format` enum; stays in kash
- kash `shell/output/kmarkdown.py` / `kerm_code_utils.py` /
  `kerm_codes.py` — Kerm protocol is its own future decision
- kash `config/text_styles.py` and `config/colors.py` — kash branding;
  only the handful of neutral constants used by ported modules are
  inlined into `display/styles.py`

### Dependency policy

**Only one runtime dependency: `rich`.**

Rich already brings `markdown-it-py` and `pygments` transitively, so
the markdown renderer costs nothing extra. Everything else uses the
stdlib. This means the package installs as cleanly as Rich itself does.

| Dep | Status | Notes |
|---|---|---|
| `rich` | required | The headline dep; used by every `display/*` module. `terminal/*` and `icons/*` never import it. |
| `markdown-it-py` | transitive (via rich) | Used by `display/markdown.py` |
| `pygments` | transitive (via rich) | Used by `display/markdown.py` for code fence highlighting |
| `strif` | **removed** | Replaced with stdlib: `AtomicVar` → `threading.Lock` + variable in `display/live.py`; `abbrev_str` / `single_line` → small inline helpers in `display/multitask.py` |
| `typing-extensions` | **removed** | Replaced with `try: from typing import override; except ImportError: def override(f): return f` (stdlib path on Python 3.12+, no-op shim on 3.11) |
| `flowmark` | **removed** | The single `fill_text` call in `display/output.py` is replaced by stdlib `textwrap.fill` or Rich's wrapping |
| `clideps` | excluded | Pieces move *into* this package |
| `gather-limited` (future) | excluded | See interop note |
| `prettyfmt` | excluded | Not currently needed by any ported module |

**Test-time deps** (`dev` group): pytest, ruff, basedpyright, codespell
per simple-modern-uv defaults; plus tryscript invoked via
`npx tryscript@latest` (no install needed).

### gather-limited interop note

`display/multitask.py` implements the `ProgressTracker` protocol that
the future `gather-limited` package will define. Because
`ProgressTracker` is a `typing.Protocol` (structural),
`MultitaskStatus` satisfies it without importing it — no dependency
needed in either direction. The one nominal type that crosses the
boundary is the `TaskState` enum: vendored here in `progress_types.py`
and (eventually) in gather-limited. To keep the two enums
interoperable, `display/multitask.py` MUST compare states by `.value`
(string), not by identity. Document this contract in both packages. If
it proves awkward, the fallback is a `rich-cli-tools[gather]` extra
plus a thin adapter — decide after gather-limited ships.

### Public API (`__init__.py`)

Curated re-exports keep import paths short for typical use:

```python
# Top-level (stdlib)
from rich_cli_tools.errors import NotSupportedError
from rich_cli_tools.progress_types import (
    TaskState, TaskInfo, TaskSummary, ProgressSymbols,
)

# terminal/ (stdlib)
from rich_cli_tools.terminal.osc import osc8_link, terminal_supports_osc8
from rich_cli_tools.terminal.features import TerminalInfo, detect_terminal_features
from rich_cli_tools.terminal.images import display_image, terminal_supports_sixel

# icons/ (stdlib)
from rich_cli_tools.icons.nerd_fonts import icon_for_file, Icons

# display/ (Rich)
from rich_cli_tools.display.cells import ansi_cell_len
from rich_cli_tools.display.char_transform import text_upper, text_lower
from rich_cli_tools.display.indent import Indent
from rich_cli_tools.display.osc_rich import osc8_link_rich
from rich_cli_tools.display.markdown import CustomMarkdown, install as install_markdown
from rich_cli_tools.display.output import (
    print_heading, print_error, print_warning, print_success,
    format_success_or_failure,
)
from rich_cli_tools.display.live import UnifiedLive
from rich_cli_tools.display.multitask import (
    MultitaskStatus, StatusSettings, StatusStyles,
)
from rich_cli_tools.display.features_report import print_terminal_features
```

The top-level `__init__.py` re-exports the most-used symbols so callers
can write `from rich_cli_tools import ansi_cell_len, Indent, ...` for
common cases. The subpackage paths remain the canonical home and are
the form shown in docs / the skill.

### Scaffolding from simple-modern-uv

The agent implementing this spec should:

1. Create the new repo `jlevy/rich-cli-tools` on GitHub (private until
   first publish, then public — or public from the start per owner
   preference).
2. Scaffold with copier:
   ```bash
   uvx copier copy gh:jlevy/simple-modern-uv rich-cli-tools
   # answers: package_name=rich-cli-tools, module_name=rich_cli_tools,
   # author=Joshua Levy, license=MIT, python >=3.11,<4.0
   ```
   (or `uvx uvtemplate` interactive equivalent)
3. Verify the template plumbing works before porting any code:
   `make install && make lint && make test` on the placeholder test.
4. Set up GitHub Actions per the template (the template ships CI for
   lint + test + publish).
5. Configure `uv-dynamic-versioning` (comes with template) — versions
   from git tags.
6. Run `tbd setup --auto --prefix=rct` (or chosen prefix) to set up
   issue tracking in the new repo.

### Companion agent skill

Per the agent-skills open standard (`SKILL.md` format, agentskills.io)
and the `cli-agent-skill-patterns` guideline:

- Ship `skills/python-cli-ux/SKILL.md` in the repo (≤500 lines,
  imperative).
- **Description** (drives activation): "High-quality terminal UX for
  Python CLIs using rich-cli-tools. Use when creating or improving a
  Python CLI's output: markdown rendering, progress displays, colors,
  hyperlinks, terminal detection, file icons."
- **Body is a menu**, mirroring how the user wants to consume it
  ("anytime you're writing a Python CLI, the skill gives a menu of a
  few options"):
  1. **Styled output basics** — print_heading/error/warning/success;
     when to use stderr vs stdout; NO_COLOR/CI respect
  2. **Markdown output** — render help text, docs, LLM output in the
     terminal with `CustomMarkdown`
  3. **Progress for long operations** — `MultitaskStatus` for parallel
     work, plain progress for serial; always `--no-progress` flag for
     agent/CI compatibility
  4. **Hyperlinks & terminal detection** — OSC-8 links with
     `terminal_supports_osc8()` fallback; capability report
  5. **File listings** — Nerd Font icons with graceful fallback
  6. **Agent-friendly CLI checklist** — `--json` on every command,
     non-interactive mode, exit codes (cross-reference
     `python-cli-patterns` guideline conventions)
- The skill **points**, the package's docs **document**: the skill
  names each capability + the import; it does not duplicate API docs.
- Installable via `npx skills add jlevy/rich-cli-tools` (skills.sh
  ecosystem reads `skills/` directories) and by copying into
  `.claude/skills/` or `.agents/skills/`.

### API changes in kash and clideps (follow-on, separate PRs)

- **kash:** replace `utils/rich_custom/*`, `config/unified_live.py`,
  `shell/file_icons/nerd_icons.py` with shim modules re-exporting from
  `rich_cli_tools`; add the dependency; one release with shims, then
  delete.
- **clideps:** same pattern for `terminal/*`, `ui/styles.py`,
  `ui/rich_output.py`; clideps gains a `rich-cli-tools` dependency and
  sheds its `flowmark` dependency (it was only used in rich_output).
  This completes clideps's refocus on package/env management.

## Implementation Plan

Single repo, ordered phases. Phase 1 is sequential prerequisite;
Phases 2–4 can be done in parallel by module; Phases 5–7 are
sequential.

### Phase 1: Scaffold and verify

- [ ] Create GitHub repo `jlevy/rich-cli-tools`
- [ ] Scaffold from simple-modern-uv via copier (answers below)
- [ ] Set `pyproject.toml` dependencies to `rich` only
- [ ] Create subpackage skeletons: `src/rich_cli_tools/{terminal,icons,display}/__init__.py`
- [ ] `make install && make lint && make test` passes on placeholder
- [ ] CI green on first push
- [ ] `tbd setup --auto --prefix=<chosen>` in the new repo

### Phase 2: Port the stdlib-only modules (no Rich needed)

These ship first because they have no decoupling work and no Rich-bug
surface area. Includes a CI rule that fails the build if any module
under `terminal/` or `icons/` imports `rich`.

- [ ] `terminal/osc.py` — string-only OSC-8 builders + capability check
- [ ] `terminal/features.py` — `TerminalInfo` dataclass + detection logic
- [ ] `terminal/images.py` — sixel/kitty subprocess display; refactor
      `STYLE_HINT` fallback into `raise NotSupportedError(...)`
- [ ] `icons/nerd_fonts.py` — direct copy of `nerd_icons.py`
- [ ] `errors.py` — `NotSupportedError` + package base
- [ ] `progress_types.py` — vendor `TaskState`, `TaskInfo`,
      `TaskSummary`, `ProgressSymbols`; document compare-by-value
      contract for `TaskState`
- [ ] Tests:
  - port existing inline tests where they exist
  - **add** `icon_for_file()` fixture test (no current coverage)
  - **add** `terminal/features.py` test with env-var fakes
- [ ] CI lint rule: `grep -r "import rich\|from rich" src/rich_cli_tools/{terminal,icons}/ && exit 1`

### Phase 3: Port the self-contained Rich modules

The "ship-now" tier from the Background maturity table. Direct copies,
import-path updates, minor inlining.

- [ ] `display/cells.py` from `ansi_cell_len.py` — direct copy
- [ ] `display/char_transform.py` from `rich_char_transform.py` — direct copy
- [ ] `display/indent.py` from `rich_indent.py` — direct copy + **add an inline test**
- [ ] `display/osc_rich.py` from clideps `osc_utils.py` Rich half — depends on `terminal/osc.py`
- [ ] `display/styles.py` — merge neutral constants from clideps `ui/styles.py` + the 2 from `kash.config.text_styles` needed by markdown + multitask defaults; keep under ~40 lines
- [ ] `display/features_report.py` from clideps `terminal_features.py` report half — consumes `terminal/features.py`
- [ ] `display/output.py` from clideps `rich_output.py` — **replace `flowmark.fill_text` with `textwrap.fill` or Rich's wrapping**; verify identical output on width-varied test strings

### Phase 4: Port the heavier Rich modules

The "ship-careful" tier. Each gets extra test coverage.

- [ ] `display/markdown.py` from `rich_markdown_fork.py`:
  - inline 2 style constants
  - convert import-time monkey-patch to explicit `install()` call
  - add a docstring explaining when to call `install()`
  - pin a minimum rich version in `pyproject.toml`
  - **canary test**: imports `rich.markdown` private internals
    (`rich._loop`, `rich._stack`); a missing or renamed symbol fails
    the build loudly (intentional CI signal when a new rich release
    breaks the fork)
- [ ] `display/live.py` from `unified_live.py`:
  - replace `kash.config.logger.get_console` with injectable console
    (default `rich.get_console()`)
  - inline 2 spinner/color constants
  - **replace `strif.AtomicVar` with `threading.Lock` + variable**
- [ ] `display/multitask.py` from `multitask_status.py`:
  - emojis already injectable via `ProgressSymbols` (commit `859424e`)
  - take live-display via constructor instead of
    `get_unified_live()` (accept optional `UnifiedLive` or plain console)
  - **replace `strif.abbrev_str` + `single_line` with small inline
    helpers** (each ~5 LOC)
  - port the inline test set; integration test driving a synthetic
    async batch (port relevant parts of kash's
    `test_multitask_status.py`, minus the gather-limited-coupled
    cases)

### Phase 5: Examples, golden tests, docs

- [ ] `examples/demo_markdown.py`, `demo_multitask.py`,
      `demo_features.py`, `demo_icons.py`
- [ ] **tryscript golden tests** under `tryscript/`:
  - each demo run under `COLUMNS=80 NO_COLOR=` and ANSI-stripped;
    output committed as golden
  - extra `NO_COLOR=1` variant per demo to verify graceful degradation
  - use `[..]` / `...` elisions for unstable spans (timings)
- [ ] **Byte-identical port verification** (one-time): for `cells`,
      `char_transform`, `indent`, `markdown`, `output`, run the same
      fixture inputs through kash's originals and the ported versions;
      diff must be empty
- [ ] README: what/why, install, 4 short usage snippets, asciinema
      of the multitask demo
- [ ] Internal architecture doc covering the three-subpackage split
      and the rule "no Rich imports in `terminal/` or `icons/`"

### Phase 6: Skill

- [ ] Write `skills/python-cli-ux/SKILL.md` per the design below
- [ ] Validate activation description against the
      `cli-agent-skill-patterns` checklist (what it does + when to use)
- [ ] Test: in a scratch project, install the skill and confirm an
      agent asked to "add progress output to this Python CLI" discovers
      and follows it

### Phase 7: Publish

- [ ] Publish to TestPyPI; `pip install` in clean venv; run examples
- [ ] Tag v0.1.0; publish to PyPI per template's publishing.md
- [ ] Announce in README of kash/clideps as the new home

### Phase 8: Consumer migration (separate PRs, can lag)

- [ ] kash: add dep, shim modules at the old paths, run full kash test
      suite; one release with shims; following release: remove shims
- [ ] clideps: add dep, shim modules, **drop flowmark dep**; tryscript
      golden of `clideps` CLI output before/after must be identical
- [ ] Update `plan-2026-05-23-utility-extraction.md` Phase C/D status

## Testing Strategy

Per the golden-testing guidelines (console-output capture strategy):

- **pytest**: all inline tests from kash/clideps move with their
  modules. Target: no module ships with fewer tests than it had in its
  source repo. New tests required: `icon_for_file()`,
  `terminal/features.py` env-var detection, `display/indent.py` inline test.
- **Layer-isolation CI check**: a grep step in CI that fails the build
  if any module under `terminal/` or `icons/` imports `rich`. This
  enforces the dep-free contract on those subpackages.
- **tryscript golden tests** (`tryscript/` dir): each `examples/demo_*`
  run under `COLUMNS=80 NO_COLOR=` and ANSI-stripped, output committed
  as golden. Catches structural drift (wrong columns, missing lines,
  changed markdown layout) through every future refactor. Use
  `[..]`/`...` elisions for unstable spans (timings). Plus a
  `NO_COLOR=1` variant per demo.
- **Byte-identical port verification** (one-time, Phase 5): fixture
  inputs through old (kash) and new implementations; diff must be
  empty. This is the core migration-safety check.
- **Markdown-fork canary** (Phase 4): an import-only test that touches
  the private Rich symbols the fork uses (`rich._loop.loop_first`,
  `rich._stack.Stack`); a CI failure here signals a Rich-internals
  break before any user-visible bug ships.
- **Visual smoke** (manual, documented in development.md): run
  `demo_multitask.py` in a real terminal, eyeball spinners/colors;
  not in CI.
- **CI matrix**: Python 3.11–3.14 per template defaults.

## Rollout Plan

1. v0.1.0 to PyPI after Phases 1–7
2. kash migrates first (it has the larger surface and its test suite is
   the best validation)
3. clideps migrates second and drops its flowmark dep
4. Skill published via the repo; optionally submitted to a skills
   marketplace later
5. Future: when `gather-limited` ships, revisit the `TaskState` interop
   contract; add `rich-cli-tools[gather]` extra only if the
   compare-by-value contract proves insufficient

## Open Questions

- **Final name**: `rich-cli-tools` (available, descriptive) vs
  `richcli` (shorter, available). Owner picks before Phase 1. The
  name slightly under-describes the `terminal/` and `icons/`
  subpackages (which don't require Rich) but signals the dominant
  use case.
- **Subpackage names**: `terminal/`, `icons/`, `display/` are the
  working names. `display/` is a deliberate choice over `rich/`
  (would shadow `import rich`). Other candidates: `ui/`, `ext/`.
  Owner sanity-check before Phase 1.
- **Public API surface in top-level `__init__.py`**: re-export
  everything, or only the most commonly-used symbols? Recommendation:
  re-export the common path (cell_len, Indent, CustomMarkdown,
  print_*, MultitaskStatus, icon_for_file) — the canonical home is
  the subpackage path.
- **Upstream contributions to Rich**: several pieces (cell-width fix,
  dashes-as-bullets option, arbitrary-prefix indent) could be PR'd
  to Rich itself over time; carrying them here is the pragmatic
  interim. Track as future beads in the new repo.
- **Python floor**: template default `>=3.11,<4.0` matches kash.
  Confirm 3.11. The `override` decorator shim makes 3.11 painless.

## References

- `plan-2026-05-23-utility-extraction.md` — parent extraction menu
  (this spec implements Phase C + movement half of Phase D)
- Template: `attic/simple-modern-uv/` —
  https://github.com/jlevy/simple-modern-uv (copier; `uvx uvtemplate`)
- Sources audited in attic/working tree:
  - kash: `src/kash/utils/rich_custom/`, `src/kash/config/unified_live.py`,
    `src/kash/shell/file_icons/nerd_icons.py`,
    `src/kash/utils/api_utils/progress_protocol.py`
  - clideps: `attic/clideps/src/clideps/terminal/`,
    `attic/clideps/src/clideps/ui/`
- Guidelines: `tbd guidelines cli-agent-skill-patterns`,
  `tbd guidelines python-cli-patterns`,
  `tbd guidelines golden-testing-guidelines`
- tryscript: https://github.com/jlevy/tryscript
- Agent Skills standard: https://agentskills.io
- Commit `859424e` — ProgressSymbols decoupling (already landed)
