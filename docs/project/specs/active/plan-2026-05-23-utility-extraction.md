---
title: Plan Spec: Utility Extraction
description: Map kash's mature reusable utilities to standalone or existing open-source repos
---
# Feature: Extracting Reusable Utilities from kash (and Trimming clideps)

**Date:** 2026-05-23 (last updated 2026-05-23)

**Author:** Joshua Levy

**Status:** Draft

## Overview

A substantial set of utilities developed inside kash are domain-neutral and
useful to any Python CLI or LLM tool author. This document is a **menu** of
extraction candidates, each scoped as an independent phase that can be picked
up (or skipped) on its own schedule.

Two non-kash repos are in scope:

- **clideps** can be trimmed: its `terminal/`, `ui/styles.py`, and
  `ui/rich_output.py` subtrees fit better in a new terminal/Rich utilities
  package than in a library named "clideps" (which should focus on package
  and env-var setup).
- **practical-prose/tools/prose-eval** is the validation consumer for
  several extractions (notably `gather-limited`), so each phase that
  applies names it explicitly.

Each phase section includes its own coupling notes, dependencies, decoupling
work, and a concrete testing approach — emphasizing **golden tests via
tryscript** for CLI-shaped extractions so migrations are highly reliable.

## Goals

- Provide a menu of independent extraction phases, each with a clear
  scope, home, and testing plan, so phases can be picked up out of order
- Prefer new focused packages over diluting `strif`, `clideps`, or
  `flowmark` with items that don't fit their scope and maturity bar
- For each extraction, identify whether the utility is **CLI-shaped**
  (testable end-to-end via tryscript) or **library-shaped** (testable via
  pytest); add a tiny CLI wrapper where one would meaningfully improve
  migration reliability
- Use existing tests as baseline; add golden/tryscript tests at the new
  home for any module whose behavior could subtly drift during extraction
- Each new package ships with at least one external consumer validated
  end-to-end (kash itself, prose-eval, or both)

## Non-Goals

- Forcing items into `strif` or `flowmark` just because they are
  convenient hosts. Both libraries have clear scopes and maturity bars
  that should not be diluted.
- Touching `flowmark` aggressively. It is mature and has a Rust port; any
  additions must be universal enough to make sense on both sides.
- Mass refactor in a single change. Each phase is shippable on its own
  schedule.
- Extracting un-tested utilities. If a module currently has no tests, the
  phase includes adding them before extraction.
- Building a new CLI just to enable testing of a non-CLI utility — the
  CLI-wrapper-for-testing approach is used only where a thin wrapper is
  natural and useful on its own.

## Background

A code survey identified ~20 utility modules with zero or near-zero coupling
to kash internals. Key constraints surfaced:

- **`strif`** is small, zero-dependency, and mature. Even `mtime_cache.py`
  — one of the most-reused pieces — needs careful evaluation before being
  added (it brings `cachetools` as a transitive dep and encodes a cache
  invalidation policy).
- **`clideps`** has accumulated rougher per-platform package-management
  code under `pkgs/` plus terminal/Rich helpers under `terminal/` and
  `ui/`. The two halves don't naturally belong together. Trimming clideps
  to focus on package and env-var setup makes both sides cleaner.
- **`flowmark`** is mature and has a Rust port. Markdown utilities can be
  folded in only if they make sense in both ecosystems.
- **`prettyfmt`** is focused and small; new functions need to earn a
  place by matching its formatting-of-values niche.
- The kash `gather_limited` bundle has **zero production callers** inside
  `src/kash/` today (only tests + `multitask_status.py` for
  `progress_protocol` types). It is shelf-ready infrastructure, not
  load-bearing kash code, so extraction carries no in-place migration
  risk.
- `practical-prose/tools/prose-eval/src/prose_eval/_concurrency.py`
  reimplements a bare-bones rate-limited gather in 55 LOC and would
  benefit immediately from `gather-limited` (free 429/529 retries,
  optional progress display, multi-provider bucket limits later).
- The author's most-wanted utilities are: **mtime cache**, **custom Rich
  rendering**, and **display of custom Rich content** (multitask progress,
  unified live).

## Phase Menu

Each row is independent and can be picked up or skipped on its own
schedule. "Effort" is small / medium / large (qualitative, no timeframes).

| # | Phase | Proposed home | Effort | Risk | Depends on | External consumer | Testing |
|---|---|---|---|---|---|---|---|
| A | `gather-limited` standalone | New package | Medium | Low | — | prose-eval | pytest + tryscript demo CLI |
| B | File/system utilities | New package (name TBD) | Medium | Low | — | kash; future CLI demo | pytest + tryscript |
| C | Terminal/Rich utilities | New package (name TBD) | Medium | Medium | A (Protocol) | kash | pytest + visual smoke |
| D | Trim `clideps` | clideps repo | Small | Medium | C (target home) | kash | pytest + tryscript |
| E | mtime cache decision | strif **or** Phase B | Small | Low | B if not strif | kash | pytest |
| F | Markdown utilities | flowmark (selective) | Small per item | Medium | flowmark Rust review | kash; chopdiff | pytest |
| G | Targeted prettyfmt adds | prettyfmt | Small | Low | — | kash | pytest |
| H | CLI introspection bundle | New micro-package (TBD) | Medium | Medium | — | kash; prose-eval cli.py | pytest + tryscript |
| I | `chat-format` micro-package | New package | Small | Low | — | kash; future LLM tools | pytest + tryscript |
| J | Less-mature `utils/common/` pieces | Stay in kash | — | — | — | — | — |

## Per-Phase Sections

---

### Phase A: `gather-limited` standalone package

**Scope:** Async, rate-limited fan-out of I/O-bound tasks with HTTP-aware
retries and an optional progress-display protocol. Domain-neutral,
Rich-independent (the Rich UI lives in Phase C and implements the protocol
from this package).

**Contents (extracted from `kash/utils/api_utils/`):**

- `gather.py` — `gather_limited_async`, `Limit`, `FuncTask`,
  `bucket_limits` (per-bucket rate limits with `*` fallback), retry
  orchestration
- `retries.py` — `RetrySettings`, HTTP status classification
  (429/503/529/5xx), exponential backoff with jitter, `extract_retry_after`,
  `extract_http_status_code` (merge `http_utils.py` in)
- `progress.py` — `ProgressTracker` Protocol, `TaskState`, `TaskInfo`,
  `TaskSummary`, `ProgressSymbols`, `SimpleProgressTracker`,
  `SimpleProgressContext`

**Paring decisions vs. kash's current bundle (~1820 LOC):**

- **Drop `gather_limited_sync`** from v1 (threaded sync-callables with
  cooperative cancellation, ~280 LOC). Re-addable later if a real
  consumer needs it.
- **Drop `TaskResult[T]` cache-bypass wrapper** from v1 (~30 LOC). Niche;
  prose-eval doesn't need it.
- **Move inline `test_*` functions out of `api_retries.py`** into a real
  `tests/` directory (~250 LOC out of the published wheel).
- **Delete from kash entirely:** `multitask_gather.py` (134 LOC) and
  `cache_requests_limited.py` (84 LOC). Zero production callers; both
  drag `kash.config.settings` / `kash.shell.output` / `kash.web_content`
  into the otherwise-clean bundle.

Realistic v1: ~1100 LOC of production code in 3 files.

**Dependencies:** `aiolimiter`. No Rich, no console.

**Decoupling:** Already done in commit `859424e` — emoji constants moved
to injectable `ProgressSymbols`; kash sources its emojis from
`text_styles`.

**External consumer:** `practical-prose/tools/prose-eval`. Replace
`tools/prose-eval/src/prose_eval/_concurrency.py` (55 LOC) with
`gather_limited_async`. Net gain for prose-eval: free 429/529 retries on
Anthropic calls, optional progress display, path to multi-provider
bucket limits.

**Testing:**

- pytest: the existing kash tests
  (`tests/kash/utils/api_utils/test_gather_limited.py` plus the inline
  tests we externalize from `api_retries.py`) move to the new package
- **tryscript demo CLI**: ship a small `gather-limited-demo` console
  script that runs N synthetic tasks with configurable failure
  probability, rate, and retries; capture stdout. Golden file shows
  rate-limit pacing, retry events, completion summary. This gives us a
  *behavioral* baseline that survives refactors of the package internals.
- prose-eval end-to-end: after migration, run `prose-eval score` on a
  fixture YAML against a mock Anthropic endpoint (or recorded responses)
  and check exit code + stdout structure with tryscript.

**Open questions for this phase:**

- Should the `gather-limited-demo` ship in the package itself or stay in
  `tests/`? Shipping it makes the package self-documenting but adds the
  binary to the install footprint.
- Name choice: `gather-limited` reads naturally but the GitHub org may
  already have a similar handle — verify before publish.

---

### Phase B: File/system utilities package

**Scope:** Broader than `strif` (which stays low-level/zero-dep). Focused
on file-format detection, directory tallies, and gitignore-aware
traversal. The recurring "roll up all files in a directory and see counts
by type" use case sits here.

**Contents (extracted from `kash/utils/file_utils/`):**

- `file_ext.py` — `FileExt` enum with canonicalization (jpeg↔jpg,
  yaml↔yml)
- `file_formats.py` + `file_formats_model.py` — `Format` enum,
  `MediaType`, `FileFormatInfo`, mime↔format↔extension mapping,
  content-based detection via `python-magic`
- `dir_info.py` — recursive tally by format/size/count (the "roll-up"
  use case explicitly called out by the author)
- `ignore_files.py` + `file_walk.py` — gitignore-compatible filtering
  plus `walk_by_dir` generator (depth limits, file caps, ignore-filter
  integration)
- `path_utils.py` — `common_path` / `common_parent_dir`
- `csv_utils.py` — smart CSV header/metadata detection
- `filename_parsing.py` — `(dir, name, type, ext)` splitting with URL
  awareness

**Dependencies:** `pathspec`, `python-magic` (optional/feature-gated),
`strif` (for atomic writes / hashing), `prettyfmt` (for `fmt_loc`).

**Decoupling work needed:**

- Replace `kash.config.logger` calls with stdlib `logging`
- Replace kash-specific `FileNotFound` with stdlib `FileNotFoundError`
- Drop the `clideps.pkgs.pkg_check` call inside `file_formats.py` (used
  only to warn about missing `libmagic`); use `try/except ImportError`
- `filename_parsing.py` imports `kash.utils.common.url` — bring `url.py`
  along or inline the small piece used

**External consumer:** kash itself via shim. A future small CLI demo
shipped in the package (`dir-info <path>` / `detect-format <file>`) is
likely valuable on its own.

**Testing — heavily CLI-shaped:**

The "roll up files by type" use case is naturally CLI-tested. Plan:

- pytest: existing
  `tests/kash/utils/file_utils/test_csv_utils.py` and any inline tests
  move to the new package
- **tryscript golden tests** for the CLI wrappers:
  - `detect-format <fixture-tree>/*.{md,csv,yml,py,bin}` → expected
    format + mime for each. Diff against golden output. This is the
    *primary* extraction-safety test — if format detection drifts during
    extraction, the diff lights up immediately.
  - `dir-info <fixture-tree>` → expected tally table (count + size by
    format). Golden file is the human-readable rolled-up table.
  - `walk --respect-gitignore <fixture-tree>` → expected file list.
    Fixture tree includes a `.gitignore` plus matching/non-matching
    files; golden captures the visited paths.
- The fixture tree lives in the package's `tests/fixtures/` and is
  checked in.

**Open questions for this phase:**

- Package name. Candidates: `fileforms`, `pathmatter`, `dirroll`,
  `fileinfo`. Should not collide with prominent PyPI packages and should
  read clearly.
- Does `mtime_cache` belong here? See Phase E.
- Should `chat_format.py` join this package as `chat_format` sub-module
  or be its own micro-package? See Phase I.

---

### Phase C: Terminal/Rich utilities package

**Scope:** Rich rendering enhancements + the visual rendering of multitask
gather. The explicitly non-package-management half of what currently
lives in clideps but should not grow into clideps (see Phase D).

**Contents (extracted from kash):**

- `rich_custom/ansi_cell_len.py` — OSC-8-aware `cell_len` fix
- `rich_custom/rich_char_transform.py` — character-wise transforms
  preserving Rich text spans
- `rich_custom/rich_indent.py` — Rich renderable for arbitrary prefix
  indent
- `rich_custom/rich_markdown_fork.py` — improved Rich Markdown renderer
  (dashes-as-bullets, fenced code blocks, less-prominent h1)
- `config/unified_live.py` — singleton multiplexer over Rich Live
  (status + progress + content)
- `rich_custom/multitask_status.py` — uv/pnpm-style multitask progress
  display; implements `gather-limited`'s `ProgressTracker` Protocol
- `shell/file_icons/nerd_icons.py` — Nerd Font icon mappings (port of eza)

**Contents (from Phase D — moved out of clideps):**

- `clideps/terminal/terminal_features.py` — terminal capability detection
- `clideps/terminal/osc_utils.py` — OSC-8 hyperlinks
- `clideps/terminal/terminal_images.py` — sixel/kitty image display
- `clideps/ui/styles.py` — Rich style constants
- `clideps/ui/rich_output.py` — `print_heading`, `print_error`,
  `print_warning`, status-emoji helpers

**Dependencies:** `rich`, `gather-limited` (for the `ProgressTracker`
Protocol), optional Nerd Font / terminal-image extras.

**Decoupling work needed:**

- `rich_markdown_fork.py`: inline the 2 style constants currently
  imported from `kash.config.text_styles`
- `unified_live.py`: replace `kash.config.logger.get_console` with a
  passable console argument
- `multitask_status.py`: already accepts custom `StatusStyles`; just
  inline the kash defaults

**External consumer:** kash itself via shim. clideps becomes a consumer
of this package for its remaining Rich-based UI (`pkg_check` output etc.).

**Testing:**

- pytest: existing inline tests in `ansi_cell_len.py`,
  `rich_char_transform.py`, `markdown_fork.py`, `multitask_status.py`
  move to the new package's `tests/`
- **Visual smoke test** for `unified_live` and `multitask_status`:
  manual run of a demo script + screenshot capture committed in the
  package. Not part of CI; documented as the manual acceptance step.
- **tryscript** with ANSI-strip preprocessing: a wrapper script runs the
  demo, strips ANSI codes, captures the plain-text result. Golden file
  is the plain-text trace. Catches structural regressions (wrong column
  order, missing summary line) even though it doesn't catch styling
  regressions.
- For `nerd_icons`: pytest table-driven test over the eza icon mapping
  is sufficient; no CLI needed.

**Open questions for this phase:**

- Package name. Candidates: `richer`, `richtools`, `termpolish`,
  `richkit`. Should not be confused with `rich` itself.
- Does `unified_live` belong here or split into its own micro-package?
  It's the trickiest part because it patches Rich's Live behavior.

---

### Phase D: Trim clideps to focus it on package + env-var setup

**Scope:** Move clideps's `terminal/`, `ui/styles.py`, and
`ui/rich_output.py` into Phase C's new package. clideps then depends on
that package for its remaining Rich UI. Net effect: clideps's identity
becomes "package and env-var setup for CLI apps" — matching its name.

**What stays in clideps:**

- `pkgs/` — all of it (per-platform pkg detection, install suggestions,
  pkg manager check, pkg model, platform checks). This is clideps's
  reason for being.
- `env_vars/` — env name registry, dotenv setup, env-var enum,
  interactive `.env` configuration via questionary
- `run/run_commands.py` — `run_command_with_confirmation`,
  `run_commands_sequence`
- `utils/which_all.py` — `which`-like helper used by pkg checking
- `utils/readable_argparse.py` — used by kash and others; keep here for
  now (move to Phase H bundle if/when it ships)
- `ui/inputs.py` — questionary wrappers used by env_vars/dotenv_setup
- `cli/` — the `clideps` CLI itself
- `errors.py`

**What moves to Phase C's package:**

- `terminal/terminal_features.py`, `terminal/osc_utils.py`,
  `terminal/terminal_images.py`
- `ui/styles.py`, `ui/rich_output.py`

**Dependencies — clideps after trim:** strif, dotenv, pyyaml,
questionary, prettyfmt, flowmark, pydantic, rich-argparse, plus a
dependency on the Phase C package (for terminal + Rich output it still
uses internally).

**Backward compatibility:** clideps adds shim modules at
`clideps/terminal/__init__.py` and `clideps/ui/__init__.py` that
re-export from the new package for one release cycle, then deletes them.

**Testing:**

- pytest: existing clideps tests cover the surface; ensure they still
  pass after the move (with the shim layer in place)
- **tryscript** for clideps's actual CLI (`clideps pkg-check`,
  `clideps env-check`): capture stdout golden files before the move,
  re-run after, confirm zero diff. This is the highest-confidence proof
  that user-visible behavior is unchanged.
- kash integration: kash imports from clideps in several places; run
  kash's test suite against the trimmed clideps to confirm no breakage

**Open questions for this phase:**

- Should `utils/readable_argparse.py` move to Phase H (CLI introspection
  bundle) immediately, or wait? Argument for waiting: it's already used
  by kash and prose-eval via clideps; the import path matters.
- Does the env-var subsystem (`env_vars/`) belong in clideps long-term,
  or should it eventually split into its own `envconf` package? Out of
  scope for this round; flag for future.

---

### Phase E: mtime cache home decision

**Scope:** Decide where `mtime_cache.py` lives. The author called this
out as one of the most-wanted utilities, but is wary of bloating `strif`
with anything that isn't extremely mature.

**Options:**

1. **Goes into `strif`:** Adds `cachetools` as a transitive dep for
   strif (currently zero-dep). Highest reach for the utility but
   compromises strif's "small, zero-dep, mature" identity.
2. **Goes into the Phase B file-utilities package:** Natural fit (it is
   file-mtime-keyed). No new transitive deps for strif. Reach is
   slightly narrower since consumers need the file-utils package.
3. **Goes into its own micro-package `mtime-cache`:** Maximum reach,
   minimum dep footprint, but yet-another-package overhead.

**Recommendation:** Option 2 (Phase B). Strif stays clean; the utility
still ships with a reasonable home; option 3 is overkill for ~110 LOC.

**Testing:**

- pytest: file-creation/modification/cache-hit/cache-miss scenarios on
  a tmp tree. The existing kash usage in `item_file_format.py` provides
  one real-world example.
- **tryscript** is overkill for a library-shaped utility; pytest is
  sufficient.

**Open questions for this phase:**

- Confirm the decision before Phase B starts (or do Phase E
  concurrently with Phase B).

---

### Phase F: Markdown utilities — selective additions to flowmark

**Scope:** Move kash's `utils/text_handling/*` items into `flowmark`
only where they make sense in both ecosystems (Python + the Rust port).
The author wants careful, per-item review here.

**Candidates (each evaluated individually):**

| Module | Description | Rust-port fit |
|---|---|---|
| `markdown_utils.py` | URL/heading/bullet extraction, rewriting | High — pure Markdown structural ops |
| `markdown_footnotes.py` | Footnote indexing | High — pure Markdown ops |
| `markdown_render.py` | GFM-to-HTML with footnotes | Medium — depends on marko in Python; Rust port would use its own renderer |
| `escape_html_tags.py` | Whitelist HTML escaping | High — pure string ops |
| `markdownify_utils.py` | markdownify pre/post-processing | Low — markdownify is Python-specific |
| `unified_diffs.py` | String/file unified diff generator | Medium — diffs aren't Markdown-specific; could live elsewhere |
| `doc_normalization.py` | flowmark-based normalization | Already a flowmark consumer; trivial move |

**Recommendation:** Tackle one or two items at a time as flowmark PRs.
Start with the easiest universal pieces (`escape_html_tags`,
`markdown_footnotes`) to test the review process.

**Dependencies:** flowmark already pulls `marko`, `regex`, `strif`.

**External consumer:** kash, `chopdiff` (already a flowmark consumer).

**Testing:**

- pytest: each candidate already has inline tests in kash; move them
- **tryscript golden tests** for any module that becomes part of
  flowmark's CLI (`flowmark` currently has a `reformat` CLI; we could
  add subcommands like `flowmark extract-urls <file>`,
  `flowmark footnotes <file>`, etc.). Diffs catch regressions.

**Open questions for this phase:**

- Coordinate with flowmark's Rust port — what's the cadence and review
  process?
- Is `unified_diffs.py` a flowmark concern at all, or does it belong in
  Phase B (file utilities) or its own tiny package? Flag for decision.

---

### Phase G: Targeted prettyfmt additions

**Scope:** Add `format_utils.plaintext_to_html`, `html_to_plaintext`,
and `format_utils.fmt_loc` to prettyfmt. Small, focused, natural fit
for the "format values for display" niche.

**Contents:**

- `plaintext_to_html(text)` and `html_to_plaintext(html)` — utility
  conversions
- `fmt_loc(path | url)` — formatted location strings

**Dependencies:** None new — prettyfmt already does similar work.

**External consumer:** kash; possibly prose-eval's `eval_report.py` or
`eval_render.py` for path/URL display.

**Testing:** pytest is sufficient. These are pure functions with
deterministic outputs.

**Open questions for this phase:**

- None significant; this is the lowest-risk phase. Could ship before
  any of the larger extractions.

---

### Phase H: CLI introspection bundle

**Scope:** A coherent toolkit for "introspect Python function → expose
as CLI / parse args back". The pieces compose naturally:

- `parse_shell_args.py` — Python-style shell tokenizer, quoting,
  command parsing
- `parse_key_vals.py` — `key=value` parsing with type coercion
- `parse_docstring.py` — reST + Google-style docstring parser
- `function_inspect.py` — `inspect_function_params` returning structured
  `FuncParam` objects
- `type_utils.py` — `not_none`, `instantiate_as_type`, `as_dataclass`
  (the type coercion that `parse_key_vals` builds on)
- `obj_replace.py` — recursive dict/list replacement helper

**Home options:**

1. **New micro-package `cliarg` (or similar):** Cleanest. Lets the
   bundle stand on its own and be adopted independently.
2. **Fold into clideps:** clideps already has
   `utils/readable_argparse.py`; could grow this bundle. But this
   re-bloats clideps right after Phase D trims it. Not recommended.
3. **Stay in kash for now:** the bundle has external value but no
   urgency. Defer until a real second consumer appears.

**Recommendation:** Option 1 (new micro-package) when a second consumer
emerges. Prose-eval's `cli.py` (99 LOC, 5 entry-point mains with
argparse) is a plausible second consumer. Skip this round if no second
consumer is committed.

**Dependencies:** Stdlib only. ~1500 LOC across 6 files.

**External consumer:** prose-eval `cli.py` would be a natural validator.

**Testing:**

- pytest: existing inline tests across the 6 files are extensive
- **tryscript golden tests** for any CLI demos shipped with the package
  (e.g. `cliarg parse "cmd foo=1 --bar=baz"` → structured output as
  JSON or YAML). Captures any change in how shell args are tokenized
  or how docstrings are parsed.

**Open questions for this phase:**

- Name. `cliarg` collides with several PyPI packages — pick something
  unique.
- Is this worth doing without a second consumer lined up?

---

### Phase I: `chat-format` micro-package

**Scope:** Extract `kash/utils/file_formats/chat_format.py` (~400 LOC,
extensive inline tests, zero kash coupling) as a standalone
`yaml-chat-format` (or similar) package. Multi-document YAML chat
format with `role`/`content` fields, supporting system/user/assistant/
command/output/template roles, plus `OpenAI` chat-completion export.

**Dependencies:** `frontmatter_format`, `prettyfmt`, `sidematter_format`,
`pydantic`.

**External consumer:** kash (heavily uses chat_format in actions),
plus any future LLM tool needing a YAML-on-disk transcript format.
`prose-eval` does *not* use it today but is a plausible future consumer
(for capturing eval prompts as replayable transcripts).

**Testing:**

- pytest: existing inline round-trip tests (276–416 of current
  `chat_format.py`) move to the new package
- **tryscript golden tests** for a small CLI shipped with the package:
  - `yaml-chat-format validate <file>` → exit 0 / non-zero with
    diagnostic
  - `yaml-chat-format to-openai <file>` → OpenAI JSON output (diffable)
  - `yaml-chat-format from-openai <file>` → YAML output (diffable)
  This makes round-trip behavior robust against extraction changes.

**Open questions for this phase:**

- Name. `chat-format` is generic; consider `yaml-chat-format`,
  `chatdoc`, `chatscript`.
- Pure Python with no transitive deps beyond pydantic + YAML would be
  ideal — currently pulls frontmatter_format + sidematter_format +
  prettyfmt. Can we narrow the deps?

---

### Phase J: Less-mature `utils/common/` pieces — stay in kash for now

**Scope:** Items that have zero kash coupling but no obvious external
consumer or insufficient maturity for extraction. Explicitly *not*
extracted in this round.

- `lazyobject.py` — proxy with deferred init (based on xonsh)
- `import_utils.py` — `import_recursive`, `warm_import_library`,
  `recursive_reload`
- `obj_replace.py` — already in Phase H if that ships
- `uniquifier.py` — name deduplication
- `capitalization.py` — Chicago-style title capitalization
- `stack_traces.py` — thread stack-trace dumping

These are good candidates for a future round but not urgent. Re-evaluate
when (a) a second consumer surfaces or (b) the package home becomes
obvious.

---

## Areas We Might Want to Improve the Library

In addition to extraction, the survey surfaced areas where the underlying
libraries could be strengthened, regardless of which repo ships them:

1. **Rich Markdown fork upstream contribution.** Several of the
   improvements in `rich_markdown_fork.py` (dashes-as-bullets, less
   prominent h1, fenced code blocks with triple-backtick output) are
   broadly useful and could be proposed back to Rich as configurable
   options rather than carried as a fork.

2. **`flowmark` line-wrapping with OSC-8 awareness.** kash's
   `ansi_cell_len.py` exists because Rich's `cell_len` miscalculates
   width with OSC-8 hyperlinks. If flowmark needs to wrap text with
   hyperlinks, it would benefit from the same fix — worth contributing
   into flowmark directly.

3. **`prettyfmt` could grow a few path-formatting variants.** Currently
   has `fmt_path` (abbreviated paths); could grow `fmt_loc` (Phase G)
   plus possibly a unified `fmt_loc` that handles both paths and URLs
   for diagnostics.

4. **`chopdiff` / `flowmark` overlap.** Both deal with text
   transformation; would benefit from clear boundary documentation as
   utilities get added.

5. **`strif` `atomic_output_file` could grow a directory variant** for
   atomic-replace semantics on whole directories (used by sidematter +
   kash for workspace updates). Possibly worth proposing.

6. **Tryscript-style runnable docs.** Several of these packages have
   README examples that don't currently run as part of CI. Wiring them
   into tryscript would prevent README rot. (Strongest candidates:
   prettyfmt, strif, clideps after Phase D.)

These are not part of any phase above — they are documented here for
opportunistic improvement during the relevant extraction.

---

## Cross-Cutting Testing Strategy

Migrating utilities between packages is exactly the kind of change where
behavior can drift in subtle ways that unit tests miss. The strategy
emphasizes **golden tests via tryscript** for any extraction with a
plausible CLI shape, supplementing pytest.

### Principles (from the golden-testing guidelines)

- Capture full execution traces (stdout/stderr + exit code + files
  touched), not just narrow assertions
- Normalize unstable fields (timestamps, generated IDs, paths under
  tmp) at serialization time
- Keep scenarios end-to-end, few but representative, fast in CI
- Commit golden files alongside code; review diffs in PRs

### Per-phase testing matrix

| Phase | pytest | tryscript golden | Visual smoke | Live external |
|---|---|---|---|---|
| A `gather-limited` | ✓ (port existing) | ✓ (demo CLI) | — | prose-eval Anthropic batch |
| B file utilities | ✓ (port existing + add) | ✓ (`detect-format`, `dir-info`, `walk`) | — | — |
| C terminal/Rich | ✓ (port existing) | ✓ (ANSI-stripped trace) | ✓ (manual screenshot) | — |
| D clideps trim | ✓ (existing) | ✓ (`clideps pkg-check`, `clideps env-check`) | — | kash suite against trimmed clideps |
| E mtime cache | ✓ | — | — | — |
| F flowmark adds | ✓ (port existing) | ✓ (if added to `flowmark` CLI) | — | chopdiff suite |
| G prettyfmt adds | ✓ | — | — | — |
| H CLI introspection | ✓ (port existing) | ✓ (demo CLI for parser round-trip) | — | prose-eval cli.py |
| I `chat-format` | ✓ (port existing) | ✓ (validate / to-openai / from-openai round-trip) | — | — |

### Building CLI wrappers solely for testing

Not all utilities need a public CLI. But the user explicitly noted that
many can be CLI-shaped if done correctly, **even just for testing
purposes**, and that gives a clean format for golden tests.

Guidance per phase:

- **Phase A:** ship `gather-limited-demo` as a real demo CLI (it's
  useful documentation too).
- **Phase B:** the package's CLI (`detect-format`, `dir-info`, `walk`)
  is useful enough to be public. Ship it.
- **Phase H:** ship a small `cliarg` CLI as both documentation and test
  surface.
- **Phase I:** ship `yaml-chat-format` CLI subcommands; useful for any
  human inspecting / editing chat files.
- **Phase C:** demo scripts in `examples/` rather than installed
  entry-points. Run them under tryscript with ANSI stripping.
- **Phase F (flowmark adds):** add subcommands to flowmark's existing
  CLI where the addition is universal (URL extraction, footnote dump);
  test via tryscript.
- **Phases E, G:** library-shaped only; pytest is sufficient.

### Migration safety procedure (applies to every phase)

For each phase:

1. **Before extraction:** run the existing kash test suite (and any
   external consumer suite); record passing baseline.
2. **At the new package:** port tests verbatim; confirm pass at the new
   home with the same Python version pins.
3. **Add tryscript golden files** for any newly-CLI-shaped surface.
   Capture goldens from the kash-internal version first; the new
   package must reproduce them byte-for-byte (modulo normalized fields).
4. **Add shim re-exports in kash** that route to the new package; rerun
   kash's test suite to confirm zero diff in behavior.
5. **External consumer migration** (prose-eval, clideps, chopdiff as
   applicable): replace direct kash imports with the new package;
   rerun their test suites.
6. **Publish to TestPyPI, install in a clean venv, smoke-test.**
7. **Publish v0.1.0 to PyPI.**
8. **Following release:** delete the kash shim; the new package is the
   only path.

## Rollout Plan

Each phase rolls out independently:

1. Move the code into the new home; tests pass at the new home
2. Publish to TestPyPI; verify clean-venv install
3. Add kash shim re-exports for backward compatibility
4. Ship one kash release with the shims in place — downstream kash
   consumers see no breakage
5. Following release: remove the shims; the new package is the only
   path

For Phase D (clideps trim), the same pattern applies but with shims
inside clideps itself.

## Open Questions

- Naming for: Phase A (`gather-limited` likely OK), Phase B (file
  utilities — TBD), Phase C (terminal/Rich — TBD), Phase H (CLI
  introspection — TBD), Phase I (chat format — TBD).
- Should Phases A and C ship as a coordinated pair (since C consumes
  A's `ProgressTracker` Protocol), or should A ship first standalone
  and C add the dep later? Recommendation: A first; C adds the dep
  when it ships.
- Phase E (mtime cache) decision: confirm "goes into Phase B's
  package" before Phase B starts, or run Phase E concurrently.
- Phase F (flowmark): what is the coordination cadence with the Rust
  port maintainer (jlevy)? Items need Rust-side review.
- Phase H: skip this round unless a second consumer is committed (e.g.
  refactor prose-eval cli.py at the same time).
- Minimum Python version for each new package: match kash
  (`>=3.11, <4.0`) or relax to `>=3.10` for wider adoption?

## References

- Survey notes from utility audit (parallel agent reports on
  `rich/terminal/markdown utilities`, `file utils & format detection`,
  `clideps/strif/prettyfmt scope`, `decorators/annotations/CLI args`)
- `tbd guidelines golden-testing-guidelines` — golden testing principles
- tryscript: https://github.com/jlevy/tryscript — CLI golden test runner
- Consumer: `practical-prose/tools/prose-eval/src/prose_eval/_concurrency.py`
  (55 LOC bespoke gather that Phase A replaces)
- Consumer: `practical-prose/tools/prose-eval/src/prose_eval/eval_score.py:644`
  (`score_batch_async` call site for `gather_limited`)
- Existing libs in scope: `strif`, `prettyfmt`, `flowmark`, `clideps`,
  `frontmatter-format`, `sidematter-format`, `chopdiff`, `funlog`,
  `tminify`
- Commit `859424e` — initial `ProgressSymbols` refactor (already
  landed; prepares Phase A)
