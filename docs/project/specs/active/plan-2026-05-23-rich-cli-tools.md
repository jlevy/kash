---
title: Plan Spec: rich-cli-tools
description: New standalone package for Python terminal UX — Rich enhancements, terminal detection, OSC links, live displays
---
# Feature: `rich-cli-tools` — A Focused Terminal UX Package for Python CLIs

**Date:** 2026-05-23 (last updated 2026-05-23)

**Author:** Joshua Levy

**Status:** Draft

## Overview

Create a new standalone open-source repo, **`rich-cli-tools`** (PyPI name
verified available as of this writing), consolidating all the generic
terminal/CLI user-experience utilities currently scattered across
**kash** (`utils/rich_custom/`, `config/unified_live.py`,
`shell/file_icons/nerd_icons.py`) and **clideps** (`terminal/`,
`ui/styles.py`, `ui/rich_output.py`).

The package covers everything a Python CLI needs for a polished terminal
experience: improved Rich Markdown rendering, correct cell-width math
with OSC-8 hyperlinks, terminal capability detection, inline images
(sixel/kitty), live multi-task progress displays, Nerd Font file icons,
and consistent styled output helpers.

It is deliberately **dependency-minimal**: `rich` (which already brings
`markdown-it-py` and `pygments`) plus at most `strif` and
`typing-extensions`. It does **not** depend on clideps — the dependency
will eventually flow the other way (clideps depends on rich-cli-tools
for its terminal/UI needs, and refocuses on package/env management).

The repo also ships a **companion agent skill** (`SKILL.md`, Agent
Skills open standard) so that coding agents asked to "build a Python
CLI" can discover the package and follow a menu of high-quality UX
patterns.

This spec is written to be handed to an agent and implemented
end-to-end: repo scaffolding from the `simple-modern-uv` template,
module-by-module porting with decoupling notes, tests, docs, skill,
and publishing.

## Goals

- One focused package for terminal UX in Python CLIs, useful to humans
  and to agents driving CLIs
- Near-minimal dependency surface: `rich` + `strif` +
  `typing-extensions` only (see Dependency Policy)
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

A dependency scan confirms feasibility of the minimal-deps goal:

- kash's `rich_custom/*` modules import only `rich`, `markdown_it`
  (ships with rich), `strif`, `typing_extensions`, plus 2–3 small kash
  config imports that are easy to inline.
- clideps's `terminal/*` modules import only `rich` plus three tiny
  clideps-internal helpers (`NotSupportedError`, `STYLE_HINT`,
  `format_success_or_failure`) that move into this package alongside
  them.
- clideps's `ui/rich_output.py` imports `flowmark.fill_text` — the one
  dependency to eliminate (see Dependency Policy).

PyPI name availability checked: `rich-cli-tools`, `richcli`, and
`rich-terminal-tools` are all unclaimed. Working name: `rich-cli-tools`.

Prior related work in this repo:

- `plan-2026-05-23-utility-extraction.md` — the full extraction menu;
  this spec implements its Phase C (terminal/Rich package) and the
  movement half of Phase D (clideps trim), with the explicit decision
  that the new package does NOT depend on gather-limited.
- Commit `859424e` — decoupled progress symbols into injectable
  `ProgressSymbols`, preparing `multitask_status` for extraction.

## Design

### Repo layout

Scaffolded from `simple-modern-uv` (see Scaffolding below), with this
package structure:

```
rich-cli-tools/
├── pyproject.toml              # from template; deps: rich, strif, typing-extensions
├── README.md                   # with embedded demo screenshots
├── src/rich_cli_tools/
│   ├── __init__.py             # curated public API re-exports
│   ├── cells.py                # ansi_cell_len: OSC-8-aware cell-width fix
│   ├── char_transform.py       # span-preserving case transforms for rich.Text
│   ├── indent.py               # Indent renderable (arbitrary string prefix)
│   ├── markdown.py             # improved Markdown renderer (opt-in patch, see below)
│   ├── osc.py                  # OSC-8 hyperlinks (from clideps osc_utils)
│   ├── term_features.py        # terminal capability detection (from clideps)
│   ├── term_images.py          # sixel/kitty inline images (from clideps)
│   ├── styles.py               # neutral style constants (merged kash+clideps defaults)
│   ├── output.py               # print_heading/print_error/print_warning/
│   │                           #   format_success_or_failure (from clideps rich_output)
│   ├── progress_types.py       # TaskState/TaskInfo/TaskSummary/ProgressSymbols
│   │                           #   (vendored from kash progress_protocol; stdlib-only)
│   ├── multitask.py            # MultitaskStatus live display (from kash)
│   ├── live.py                 # UnifiedLive multiplexer (from kash unified_live)
│   ├── icons.py                # Nerd Font file icons (from kash nerd_icons)
│   └── errors.py               # NotSupportedError + package error base
├── skills/
│   └── python-cli-ux/
│       └── SKILL.md            # companion agent skill (see Skill section)
├── examples/
│   ├── demo_markdown.py        # render README.md with the improved renderer
│   ├── demo_multitask.py       # synthetic multi-task progress run
│   ├── demo_features.py        # print terminal capability report
│   └── demo_icons.py           # icon listing for a directory
├── tests/                      # ported pytest suites
└── tryscript/                  # golden CLI-output tests (ANSI-stripped)
```

### Module inventory (source → target)

| Source | LOC | Target module | Decoupling work |
|---|---|---|---|
| kash `utils/rich_custom/ansi_cell_len.py` | 74 | `cells.py` | None — self-contained |
| kash `utils/rich_custom/rich_char_transform.py` | 91 | `char_transform.py` | None — self-contained |
| kash `utils/rich_custom/rich_indent.py` | 71 | `indent.py` | None — self-contained |
| kash `utils/rich_custom/rich_markdown_fork.py` | 771 | `markdown.py` | Inline 2 style constants from `kash.config.text_styles`; make the `rich.markdown.Markdown` monkey-patch **opt-in** via explicit `install()` (today it patches at import time, line 771) |
| kash `utils/rich_custom/multitask_status.py` | 770 | `multitask.py` | Import emojis from own `styles.py` instead of `kash.config.text_styles`; take live-display via constructor instead of `kash.config.unified_live.get_unified_live()` (accept an optional `UnifiedLive` or plain console) |
| kash `config/unified_live.py` | 249 | `live.py` | Replace `kash.config.logger.get_console` with injectable console (default `rich.get_console()`); inline 2 spinner/color constants |
| kash `shell/file_icons/nerd_icons.py` | 946 | `icons.py` | None — self-contained (stdlib only) |
| kash `utils/api_utils/progress_protocol.py` (types only) | ~150 of 316 | `progress_types.py` | Vendor `TaskState`, `TaskInfo`, `TaskSummary`, `ProgressSymbols`. Do NOT vendor `ProgressTracker` Protocol / `SimpleProgressTracker` (they stay with the future gather-limited package; see interop note) |
| clideps `terminal/osc_utils.py` | 95 | `osc.py` | None — imports only rich |
| clideps `terminal/terminal_features.py` | 57 | `term_features.py` | Update imports to this package's `output.py` |
| clideps `terminal/terminal_images.py` | 141 | `term_images.py` | `NotSupportedError` moves to `errors.py`; `STYLE_HINT` from own `styles.py` |
| clideps `ui/styles.py` | 32 | `styles.py` | Merge with neutral defaults needed by multitask/markdown |
| clideps `ui/rich_output.py` | 147 | `output.py` | **Remove `flowmark.fill_text` dependency** — replace with a local simple fill using Rich's own `Text.wrap`/`console.width`, or stdlib `textwrap` (fill_text is used in exactly one function) |

**Explicitly not ported:**

- kash `shell/file_icons/color_for_format.py` (72 LOC) — coupled to
  kash's `Format` enum; stays in kash
- kash `shell/output/kmarkdown.py` / `kerm_code_utils.py` /
  `kerm_codes.py` — Kerm protocol is its own future decision
- kash `config/text_styles.py` and `config/colors.py` — kash branding;
  only the handful of neutral constants used by ported modules are
  inlined into `styles.py`

### Dependency policy

**Allowed:** `rich` (brings `markdown-it-py` + `pygments` transitively —
so the markdown renderer costs nothing extra), `strif` (used by
`multitask.py` for `abbrev_str`/`single_line` and `live.py` for
`AtomicVar`; small, zero-dep, author-owned), `typing-extensions`
(for `override` on Python 3.11).

**Excluded, with the replacement strategy:**

- `flowmark` → replace the single `fill_text` call in `output.py` with
  stdlib/Rich wrapping
- `clideps` → the needed pieces move *into* this package
- `gather-limited` (future) → see interop note below
- `prettyfmt` → not currently needed by any ported module; allowed
  later if a real need appears, but v0.1 ships without it

**gather-limited interop note:** `multitask.py` implements the
`ProgressTracker` protocol that the future `gather-limited` package
will define. Because `ProgressTracker` is a `typing.Protocol`
(structural), `MultitaskStatus` satisfies it without importing it —
no dependency needed in either direction. The one nominal type that
crosses the boundary is the `TaskState` enum: vendored here in
`progress_types.py` and (eventually) in gather-limited. To keep the two
enums interoperable, `multitask.py` MUST compare states by `.value`
(string), not by identity. Document this contract in both packages.
If this proves awkward in practice, the fallback is a
`rich-cli-tools[gather]` extra plus a thin adapter — decide after
gather-limited ships.

### Public API (`__init__.py`)

Curate a small, documented surface (everything else importable from
submodules but not re-exported):

```python
from rich_cli_tools.cells import ansi_cell_len
from rich_cli_tools.char_transform import text_upper, text_lower  # (actual names per port)
from rich_cli_tools.indent import Indent
from rich_cli_tools.markdown import CustomMarkdown, install as install_markdown
from rich_cli_tools.osc import osc8_link, osc8_link_rich, terminal_supports_osc8
from rich_cli_tools.term_features import TerminalInfo, detect_terminal_features
from rich_cli_tools.term_images import display_image, terminal_supports_sixel
from rich_cli_tools.output import (
    print_heading, print_error, print_warning, print_success,
    format_success_or_failure,
)
from rich_cli_tools.progress_types import TaskState, TaskInfo, TaskSummary, ProgressSymbols
from rich_cli_tools.multitask import MultitaskStatus, StatusSettings, StatusStyles
from rich_cli_tools.live import UnifiedLive
from rich_cli_tools.icons import icon_for_file, Icons
```

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

Single repo, ordered checklist. Steps 1–3 are sequential; 4–8 can be
done module-by-module in any order; 9–12 are sequential.

### Phase 1: Scaffold and verify

- [ ] Create GitHub repo `jlevy/rich-cli-tools`
- [ ] Scaffold from simple-modern-uv via copier (answers above)
- [ ] `make install && make lint && make test` passes on placeholder
- [ ] CI green on first push
- [ ] `tbd setup --auto --prefix=<chosen>` in the new repo

### Phase 2: Port the self-contained leaf modules

- [ ] `cells.py`, `char_transform.py`, `indent.py`, `icons.py`,
      `osc.py` — direct copies with import-path updates only
- [ ] Port their inline tests into `tests/`
- [ ] `errors.py` with `NotSupportedError`
- [ ] `styles.py` — merged neutral constants (audit exactly which
      constants the other modules need; keep it under ~40 lines)

### Phase 3: Port modules with light decoupling

- [ ] `output.py` from clideps `rich_output.py` — replace
      `flowmark.fill_text` with stdlib/Rich wrapping; verify identical
      output on test strings of varied width
- [ ] `term_features.py`, `term_images.py` — re-point internal imports
- [ ] `markdown.py` — inline style constants; convert import-time
      monkey-patch to explicit `install()`; add docstring explaining
      when to call it
- [ ] `progress_types.py` — vendor the four types; document the
      compare-by-value contract for `TaskState`

### Phase 4: Port the live-display modules

- [ ] `live.py` from kash `unified_live.py` — injectable console
- [ ] `multitask.py` from kash `multitask_status.py` — emojis from own
      `styles.py`; live-display injection; port the 4 inline tests
- [ ] Integration test: `MultitaskStatus` driving a synthetic batch of
      async tasks (port relevant parts of kash's
      `test_multitask_status.py`, minus the gather-limited-coupled
      cases, which stay in kash until gather-limited ships)

### Phase 5: Examples, golden tests, docs

- [ ] `examples/demo_*.py` (markdown, multitask, features, icons)
- [ ] tryscript golden tests: run each demo, strip ANSI, compare to
      checked-in golden output (normalize terminal width via
      `COLUMNS=80`); `NO_COLOR=1` variants
- [ ] README: what/why, install, 4 short usage snippets, screenshot or
      asciinema of the multitask demo
- [ ] Verify against kash baseline: for `cells`, `char_transform`,
      `markdown`, run the same fixture inputs through kash's originals
      and the ported versions; outputs must be byte-identical

### Phase 6: Skill

- [ ] Write `skills/python-cli-ux/SKILL.md` per the design above
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

- [ ] kash: add dep, shim modules, run full kash test suite, one
      release with shims, then remove shims
- [ ] clideps: add dep, shim modules, drop flowmark dep, tryscript
      golden of `clideps` CLI output before/after must be identical
- [ ] Update `plan-2026-05-23-utility-extraction.md` Phase C/D status

## Testing Strategy

Per the golden-testing guidelines (console-output capture strategy):

- **pytest**: all inline tests from kash/clideps move with their
  modules. Target: no module ships with fewer tests than it had in its
  source repo.
- **tryscript golden tests** (`tryscript/` dir): each `examples/demo_*`
  run under `COLUMNS=80 NO_COLOR=` and ANSI-stripped, output committed
  as golden. Catches structural drift (wrong columns, missing lines,
  changed markdown layout) through every future refactor. Use
  `[..]`/`...` elisions for unstable spans (timings).
- **Byte-identical port verification** (one-time, Phase 5): fixture
  inputs through old (kash) and new implementations; diff must be
  empty. This is the core migration-safety check.
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
  `richcli` (shorter, available). Owner picks before Phase 1.
- **`icons.py` placement**: 946 LOC of Nerd Font tables is ~40% of the
  package by volume. Ship in core (it's stdlib-only, costs nothing at
  import if not used) or as `rich-cli-tools[icons]` extra? Recommend
  core for simplicity.
- **`markdown.py` fork maintenance**: the fork tracks Rich's Markdown
  internals. Pin a minimum rich version and add a CI canary test that
  fails loudly when a new rich release breaks the fork? Recommended.
- **Upstream contributions**: several pieces (cell-width fix,
  dashes-as-bullets option) could be PR'd to Rich itself over time;
  carrying them here is the pragmatic interim. Track as future beads
  in the new repo.
- **Python floor**: template default `>=3.11,<4.0` matches kash;
  lowering to 3.10 would require reworking `typing.TypeAlias` usage —
  not worth it. Confirm 3.11.

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
