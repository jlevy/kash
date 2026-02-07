# Feature: Kash Architecture Review and Modernization

**Date:** 2026-02-06

**Author:** Code review by Claude (requested by Joshua Levy)

**Status:** Draft

## Overview

Comprehensive senior engineering review of the kash codebase (~274 Python files,
~42,000 lines) covering architecture, code quality, modern Python conformance,
library reusability, and actionable improvement areas. The goal is to make kash
highly flexible, reusable across different environments, following modern Python
best practices, and simplified where possible.

## Goals

- Systematically review the entire codebase architecture
- Identify strengths, weaknesses, and areas for improvement
- Ensure conformance with tbd Python guidelines (python-rules, python-modern-guidelines,
  python-cli-patterns, error-handling-rules, general-coding-rules, etc.)
- Map out work to make kash components reusable as standalone libraries, CLI tools,
  and agent skills
- Design approaches to make kash's powerful features available outside the interactive
  shell (in testing loops, Claude Code skills, CI pipelines, etc.)

## Non-Goals

- Complete rewrite of the codebase
- Breaking backward compatibility of the existing shell experience
- Removing xonsh as the shell backend (though decoupling from it is a goal)

## Background

Kash is an AI-native command-line shell framework and Python library. It combines
Python, LLMs, and Unix shell philosophy to make knowledge work more modular. The
codebase has grown organically and would benefit from a systematic review to:

1. Clean up technical debt
2. Improve library reusability (so kash components can be imported and used
   independently)
3. Make actions and commands accessible as standalone CLI tools and agent skills
4. Conform to modern Python best practices as defined in the tbd guidelines

---

## Part 1: Architecture Assessment

### Current Architecture Summary

```
SHELL INTERFACE (xonsh_custom/, shell/, xontrib/)
    |
COMMAND/ACTION EXECUTION (exec/, commands/, actions/)
    |
DATA MODELS & WORKSPACE (model/, workspaces/, file_storage/)
    |
INTEGRATION LAYERS (llm_utils/, web_content/, media_base/, mcp/, local_server/)
    |
UTILITIES (utils/, config/, help/, embeddings/, docs/)
```

### Strengths

1. **Well-designed action system**: The `@kash_action` decorator pattern is elegant.
   Actions are composable, cacheable, and self-describing with preconditions, parameter
   declarations, and output type metadata. The precondition algebra (`&`, `|`, `~`) is
   particularly clean.

2. **Item as universal data model**: The `Item` class provides a unified abstraction
   for documents, URLs, resources, and data. Derivation tracking, identity-based
   deduplication, and operation fingerprinting are well-thought-out.

3. **Thread-safe global state**: Consistent use of `AtomicVar` from strif for all
   mutable registries and settings. `@synchronized` decorator on FileStore methods.
   ContextVar for per-thread console overrides.

4. **Modern Python practices**: Already good adoption of `X | None` over `Optional`,
   `pathlib.Path` over strings, absolute imports throughout, StrEnum where appropriate,
   Pydantic v2 dataclasses for models.

5. **Clean registry pattern**: Actions, commands, and preconditions all use a consistent
   registry pattern with lazy initialization and cache invalidation.

6. **Flexible parameter system**: `Param` objects carry validation, defaults, JSON
   schema, and documentation. Parameters can come from explicit args, workspace defaults,
   or global defaults with clear precedence.

7. **MCP integration**: Actions can be exposed as MCP tools via a single `mcp_tool=True`
   flag, enabling IDE integration.

8. **Good logging**: Structured logging with funlog, Rich console integration,
   per-workspace log directories.

### Weaknesses

1. **Tight xonsh coupling**: The shell layer completely subclasses xonsh's Shell and
   reimplements core execution logic. Commands are registered as xonsh aliases.
   `CustomAssistantShell.default()` reimplements command dispatch. This makes it
   impossible to use kash commands outside xonsh without significant workarounds.

2. **No clear public library API**: There's no canonical `from kash import ...` pattern.
   Users must know internal paths (`from kash.config.logger import get_logger`). Only
   3 of 25+ `__init__.py` files declare `__all__`. Root `__init__.py` exports nothing.

3. **Heavy dependency footprint**: 65 direct dependencies for the core package. Several
   appear unused (dunamai, prompt-toolkit, inquirerpy, questionary, patch-ng). No
   optional dependency groups for heavy subsystems (media, LLM, web scraping).

4. **Low test coverage**: Only 9 test files (~3,169 lines) for ~42,000 lines of source
   (~7% ratio). No pytest fixtures, no conftest.py, no shared test utilities. Entire
   subsystems untested: LLM, web content, media, MCP, most commands.

5. **Import side effects**: Importing `kash.actions` triggers `load_kits()` which
   imports all action modules. Importing `kash.commands` registers all commands. This
   makes it impossible to selectively import parts of kash without triggering the
   full registration system.

6. **Scattered configuration**: Settings live in `config/settings.py`,
   `config/env_settings.py`, `config/logger.py`, `config/setup.py`,
   `config/init.py`. Initialization order is implicit and undocumented.

7. **Utils sprawl**: 72 files across 7 subdirectories in `utils/`. Some could be
   standalone packages (e.g., `api_utils/`, `text_handling/`, `rich_custom/`). Others
   are small enough to fold into their consumers.

8. **MCP tightly coupled to full kash**: The MCP server requires full kash
   initialization including all registries, workspace system, and configuration.
   Cannot expose a single action as an MCP tool without loading everything.

9. **Circular import workarounds**: Item has an optional `context` field that references
   ActionContext, resolved via TYPE_CHECKING guards and `rebuild_dataclass()`. The
   local_server has circular imports handled via late imports in methods.

10. **Magic numbers in scoring/completion**: `completion_scoring.py` has hardcoded
    weights and thresholds without named constants.

### Missing from Guidelines Conformance

Based on the tbd guidelines (python-rules, python-modern-guidelines, python-cli-patterns,
error-handling-rules, general-coding-rules, general-comment-rules, general-testing-rules,
backward-compatibility-rules):

| Guideline | Status | Issues |
|-----------|--------|--------|
| `from __future__ import annotations` | Partial | ~215 of 274 files missing it |
| `@override` on subclass methods | Partial | Only 14 files use it; many overrides lack it |
| Atomic file writes (strif) | Partial | Some files use Path.write_text() directly |
| No magic numbers | Partial | Scoring weights, port ranges, timing constants |
| Concise explanatory comments | Good | Some obvious/redundant comments remain |
| No `if __name__ == "__main__"` for testing | Mostly good | 7 files still have it |
| Inline tests close to code | Partial | Most tests are in separate files, not inline |
| No trivial tests | Good | Tests are non-trivial |
| No pytest fixtures unless necessary | Good | No fixtures used at all (could use some) |
| Error handling as feature | Partial | Some debug-only error logging |
| CLI agent compatibility (--format json, --non-interactive) | Missing | Shell has no structured output mode |

---

## Part 2: Architectural Improvements

### Phase 1: Core Library Extraction and API Cleanup

The highest-impact change is making kash's core usable as a Python library without
requiring the shell.

#### 1A. Define a clean public API surface

Create a well-organized root `__init__.py` and per-module `__all__` exports:

```python
# kash/__init__.py - The public API
from kash.model import Item, ItemType, Format, Action, ActionInput, ActionResult
from kash.model import Param, Precondition, StorePath
from kash.exec import kash_action, kash_command, kash_precondition
from kash.exec import run_action, prepare_action_input
from kash.workspaces import current_ws, get_ws, Workspace
from kash.llm_utils import llm_completion, LLM, LLMName
from kash.config import kash_setup
```

#### 1B. Eliminate import side effects

- Remove `load_kits()` call from `kash/__init__.py` module level
- Make action/command registration explicit via `kash.init()` or lazy on first use
- Allow importing `kash.model`, `kash.llm_utils`, `kash.web_content` without
  triggering full initialization

#### 1C. Create a standalone action runner

A function that can execute any kash action without the shell:

```python
from kash import kash_setup, run_action

kash_setup()
result = run_action("strip_html", inputs=["https://example.com"])
# Returns ActionResult with items
```

#### 1D. Add `__all__` to all public modules

Every `__init__.py` should declare what it exports. Internal modules should
use `_` prefix conventions.

### Phase 2: Dependency Cleanup and Optional Extras

#### 2A. Remove unused dependencies

Remove from pyproject.toml: dunamai (if truly unused), and audit prompt-toolkit,
inquirerpy, questionary, patch-ng, tiktoken for actual usage.

#### 2B. Create optional dependency groups

```toml
[project.optional-dependencies]
llm = ["litellm>=1.74", "openai>=1.99", "tiktoken>=0.9"]
media = ["pydub>=0.25", "deepgram-sdk>=3.10"]
web = ["curl-cffi>=0.11", "selectolax>=0.3", "justext>=3.0", "readabilipy>=0.3"]
server = ["fastapi>=0.115", "uvicorn>=0.34", "mcp>=1.6"]
shell = ["xonsh>=0.19"]
all = ["kash-shell[llm,media,web,server,shell]"]
```

This would allow `pip install kash-shell` for the core library and
`pip install kash-shell[all]` for the full interactive shell.

#### 2C. Fix the openai version pinning

Resolve the FIXME at pyproject.toml line 88 regarding `openai==1.99.9` pinning
due to ResponseTextConfig import error.

### Phase 3: Shell Decoupling

#### 3A. Create a ShellContext abstraction

```python
class ShellContext(Protocol):
    def set_env(self, name: str, value: Any) -> None: ...
    def print_output(self, content: str) -> None: ...
    def get_workspace(self) -> Workspace: ...
    def record_history(self, command: str) -> None: ...
```

Implementations:
- `XonshShellContext` - Current shell (wraps xonsh environment)
- `StandaloneContext` - For library/script use
- `CLIContext` - For standalone CLI commands

#### 3B. Decouple command execution from xonsh aliases

Currently `shell_load_commands.py` wraps every command with xonsh-specific
wrappers. Instead, commands should be executable via a context-neutral runner,
with xonsh registration as one possible integration.

#### 3C. Make actions callable as standalone CLI commands

Each action registered with `@kash_action` could automatically generate a CLI
entry point:

```bash
# Instead of: kash> strip_html my_file.html
# Allow: kash-action strip_html my_file.html
# Or:    python -m kash.actions.core.strip_html my_file.html
```

### Phase 4: Python Modernization and Code Cleanup

#### 4A. Add `from __future__ import annotations` to all files

~215 files need this added. Can be automated.

#### 4B. Add `@override` to all subclass method overrides

Audit all classes for overridden methods and add the decorator.

#### 4C. Use atomic file writes consistently

Replace direct `Path.write_text()` calls with `atomic_output_file` from strif
where appropriate (anywhere data loss on interruption would be problematic).

#### 4D. Extract named constants

Replace magic numbers in `completion_scoring.py`, port configurations, timing
constants, etc. with named constants with docstrings.

#### 4E. Clean up dead code and comments

- Remove commented-out lazyasd code in `lazy_imports.py`
- Remove unused imports with `# noqa` that are no longer needed
- Audit TODO/FIXME comments (17 found) and create beads for unresolved ones

### Phase 5: Test Coverage Expansion

See Part 5 below for the comprehensive testability map.

#### 5A. Create test infrastructure

- Add `tests/conftest.py` with shared fixtures:
  - `temp_workspace` - Temporary kash workspace via tmp_path
  - `mock_current_ws` - Patches `current_ws()` to return temp workspace
  - `mock_llm` - Patches litellm.completion with canned responses
  - `test_item_factory` - Helper to create Items with minimal boilerplate
- Add pytest markers: `@pytest.mark.slow`, `@pytest.mark.online`
- Keep simple tests inline per the guidelines

#### 5B. Phase 1 tests: Quick wins (pure functions, no mocks needed)

These require zero infrastructure and can be written immediately:

1. `tests/model/test_items_model.py` - ItemType properties, Item construction,
   validation, serialization round-trips
2. `tests/model/test_params_model.py` - Param validation, type checking,
   JSON schema generation
3. `tests/model/test_preconditions_model.py` - Precondition `&`, `|`, `~` operators
4. `tests/model/test_paths_model.py` - StorePath parsing, normalization edge cases
5. `tests/llm_utils/test_fuzzy_parsing.py` - JSON extraction, markdown fence
   stripping, no-results detection
6. `tests/llm_utils/test_llm_names.py` - Model name parsing and validation
7. `tests/shell/test_completion_scoring.py` - Pure scoring/fuzzy matching algorithms
8. `tests/utils/test_url.py` - URL parsing and canonicalization
9. `tests/utils/test_markdown_utils.py` - Markdown parsing helpers
10. `tests/web_content/test_canon_url.py` - URL normalization

#### 5C. Phase 2 tests: Mocked dependencies (medium effort)

These require the conftest.py fixtures from 5A:

1. `tests/exec/test_action_registry.py` - Action lookup, cache invalidation
2. `tests/exec/test_resolve_args.py` - URL/path resolution with mocked workspace
3. `tests/exec/test_precondition_checks.py` - Precondition matching with mocked FileStore
4. `tests/workspaces/test_selections.py` - Selection history with temp workspace
5. `tests/workspaces/test_param_state.py` - Parameter state management
6. `tests/file_storage/test_item_id_index.py` - Index operations
7. `tests/llm_utils/test_llm_completion.py` - Prompt assembly, mock litellm
8. `tests/llm_utils/test_sliding_transforms.py` - Text chunking logic

#### 5D. Phase 3 tests: Integration tests (higher effort)

These test larger subsystem interactions:

1. `tests/exec/test_action_exec.py` - Full action pipeline with mocked workspace + LLM
2. `tests/web_content/test_web_fetch.py` - HTTP fetching with mocked httpx
3. `tests/web_content/test_local_file_cache.py` - Cache lifecycle with tmp_path
4. `tests/mcp/test_mcp_routes.py` - MCP message routing with mocked action execution
5. `tests/commands/test_workspace_commands.py` - Workspace CRUD with temp dirs

#### 5E. What NOT to test (diminishing returns)

- xonsh shell integration (too tightly coupled, test manually)
- Rich terminal rendering (UI-specific, snapshot test if needed)
- Interactive user input prompts (parameterized inputs instead)
- Individual action `apply()` methods that just call LLMs (test the LLM mock layer)
- Third-party library wrappers (justext, readabilipy) - trust their tests

---

## Part 3: Making Kash Available Outside the Shell

### The Problem

Kash's powerful features (action system, web content extraction, LLM integration,
item management) are currently only easily accessible through the interactive xonsh
shell. In principle everything is a Python function, but in practice:

1. Importing kash triggers heavy initialization
2. Running an action requires setting up workspace context
3. Output goes to Rich console, not structured data
4. No CLI interface for individual actions
5. No structured output format for agent consumption

### Approach A: Kash as a Python Library

**Target users**: Python scripts, notebooks, testing loops

```python
import kash

kash.init()  # Explicit initialization, no shell needed

# Use actions directly
result = kash.run("summarize_as_bullets", "https://example.com/article")
print(result.items[0].body)

# Use LLM utilities
response = kash.llm_completion("claude-sonnet-4-20250514", messages=[...])

# Use web content extraction
page = kash.fetch_page("https://example.com")
print(page.clean_text)
```

**Requirements**:
- Lazy initialization (don't load everything on import)
- No xonsh dependency for library use
- Structured return types (not console output)
- Minimal required configuration

### Approach B: Standalone CLI Commands

**Target users**: Shell scripts, CI pipelines, agent tools

```bash
# Run any action as a CLI command
kash run strip_html --input my_file.html --output clean.md --format json

# Use specific utilities
kash fetch https://example.com --format json
kash llm "Summarize this" --model claude-sonnet-4-20250514 --input doc.md
kash workspace create my_project
kash workspace import *.md
```

**Requirements**:
- Typer or argparse-based CLI (not xonsh)
- JSON output mode for machine consumption
- `--non-interactive` flag for CI/agent use
- Minimal startup time (lazy imports)

### Approach C: Claude Code Skills / MCP Tools

**Target users**: AI agents in Claude Code, Cursor, other IDEs

The MCP server already exposes actions as tools, but it requires a running server.
For Claude Code skills, we could:

1. **Direct skill integration**: Wrap key kash actions as Claude Code skills that
   can be invoked without a running MCP server
2. **Lightweight MCP mode**: An MCP server that only loads requested actions
   (not the full registry)
3. **Skill templates**: Generate Claude Code skill definitions from
   `@kash_action` metadata

Example skill usage:
```
User: "Summarize this webpage: https://example.com"
Claude Code: [invokes kash skill: summarize_as_bullets with URL]
```

### Approach D: Testing Loop Integration

**Target users**: Developers running kash in automated test/eval loops

```python
# In a pytest test or eval script
from kash.testing import KashTestRunner

runner = KashTestRunner(workspace=tmp_path)

# Run action and assert on output
result = runner.run_action("strip_html", item_with_html)
assert "clean text" in result.body
assert result.format == Format.markdown

# Run action pipeline
result = runner.run_pipeline([
    ("fetch_url", {"url": "https://example.com"}),
    ("strip_html", {}),
    ("summarize_as_bullets", {"model": "gpt-4o"}),
])
```

**Requirements**:
- No console output during test runs
- Deterministic behavior (mock LLM calls)
- Easy workspace setup/teardown
- Assert-friendly return types

### Recommendation

Implement in this order:
1. **Approach A** (library API) - Foundation for everything else
2. **Approach B** (standalone CLI) - Built on top of library API
3. **Approach D** (testing integration) - Built on top of library API
4. **Approach C** (skills/MCP) - Already partially done, extend with lightweight mode

---

## Part 4: Subsystem-Specific Notes

### Utils Reorganization

The `utils/` directory has 72 files. Consider:
- `api_utils/` - Could be its own package (retry logic, rate limiting, concurrent gathering)
- `text_handling/` - Could merge with web content extraction
- `rich_custom/` - Could be contributed upstream to Rich or made a separate package
- `file_utils/` - Core enough to stay, but audit for dead code
- `common/` - Audit each file; some may be unused

### Web Content as Standalone Package

`web_content/` is already highly independent (9/10 independence score). It could
be published as a separate package (`kash-scraper` or similar) with zero kash
dependencies. This would:
- Reduce kash core dependency count
- Make web scraping available to non-kash users
- Allow independent versioning and testing

### LLM Utils as Standalone Package

`llm_utils/` is also highly independent (8/10). Could be published as `kash-llm`
or similar. Already a clean LiteLLM wrapper with:
- Multi-model support
- Structured output via Pydantic
- Citation tracking
- Web search integration

### Config Simplification

The initialization flow (`kash_setup()` -> `kash_reload_all()` -> various registries)
should be documented with a clear diagram and ideally simplified to a single
entry point that handles all initialization lazily.

---

## Part 5: Comprehensive Testability Map

### Current State

8 existing test files (~2,500 lines) covering ~7% of the codebase. Well-tested
areas: gather_limited, markdown_footnotes, item serialization, file_store, CSV.
**Entire subsystems untested**: execution layer, shell/completions, web_content,
workspaces, LLM utils, commands, actions, MCP.

### Testability by Subsystem

#### Model Layer (3,890 lines) — Testability: EXCELLENT

**Existing tests**: test_item_serialization.py (113 lines)

| File | Lines | Key Functions | Testability | Notes |
|------|-------|---------------|-------------|-------|
| items_model.py | 1,094 | ItemType.for_format(), Item construction, validation, metadata(), to_dict/from_dict | Easy | Pure data class, enums, validation |
| params_model.py | 479 | Param.validate_value(), ParamDeclarations, JSON schema gen | Easy | Generic frozen dataclass, pure validation |
| preconditions_model.py | 90 | Precondition.__and__/or__/invert__() | Easy | Pure callable wrapper, logic composition |
| paths_model.py | 464 | StorePath parsing, normalization, workspace resolution | Easy | Pure string parsing, some path logic |
| operations_model.py | 213 | Operation, Source, Input construction | Easy | Frozen dataclasses |
| actions_model.py | 668 | Action abstract base, ActionInput, ActionResult | Medium | Abstract base needs subclass for testing |
| media_model.py | 132 | MediaMetadata construction | Easy | Simple dataclass |
| commands_model.py | ~200 | Command, Script models | Easy | Data models |

**Pure functions to test (no mocks needed)**:
- `ItemType.for_format(format)` - enum mapping
- `Param[T].validate_value(value)` - type validation
- `Precondition.__and__()`, `__or__()`, `__invert__()` - logic algebra
- `StorePath.parse()`, `StorePath.normalize()` - string parsing
- `Item.from_dict()`, `Item.to_dict()` - serialization
- `Item.fingerprint()` - identity hashing

**What needs mocks**: `Item.sidematter()` (workspace paths), `Action.create()` (subclass)

#### Execution Layer (2,459 lines) — Testability: MEDIUM

**Existing tests**: None

| File | Lines | Key Functions | Testability | Notes |
|------|-------|---------------|-------------|-------|
| resolve_args.py | 80 | resolve_locator_arg(), assemble_path_args() | Easy/Medium | Pure parsing + workspace mock |
| precondition_checks.py | 72 | actions_matching_paths(), items_matching_precondition() | Medium | Needs FileStore mock |
| action_registry.py | 93 | get_all_action_classes(), look_up_action_class() | Medium | Global registry state |
| action_validation.py | ~150 | validate_action_input() | Medium | Needs ExecContext mock |
| action_cache.py | ~100 | Cache lookup/storage | Medium | Needs workspace mock |
| combiners.py | ~200 | Item combining logic | Medium | Pure-ish with model deps |
| action_exec.py | 621 | prepare_action_input(), execute_action() | Hard | Orchestrates everything |
| action_decorators.py | 540 | @action decorator | Hard | Side effects (registration) |
| shell_callable_action.py | 140 | Shell command wrapping | Hard | xonsh coupling |

**What's easily testable**:
- `resolve_locator_arg()` - pure URL/path pattern matching
- Registry lookup (clear cache between tests)
- Precondition filtering (mock FileStore)

**What needs significant mocking**:
- `prepare_action_input()` - calls `current_ws()`, `fetch_url_item_content()`
- `execute_action()` - full orchestration, multiple dependencies
- `@action` decorator - global registry side effects

#### Shell Layer (~2,000 lines) — Testability: LOW

**Existing tests**: test_shell.py (7 lines, smoke test only)

| File | Lines | Key Functions | Testability | Notes |
|------|-------|---------------|-------------|-------|
| completion_scoring.py | 323 | score_completions(), normalize(), score_exact_prefix() | Easy | Pure algorithms |
| shell_completions.py | 287 | Completion generation | Hard | xonsh environment deps |
| shell_output.py | 500+ | Rich terminal UI | Hard | Terminal rendering |
| shell_results.py | 400+ | Result formatting | Hard | Rich formatting |
| param_inputs.py | 300+ | Interactive prompts | Hard | User input required |
| command_wrappers.py | ~200 | xonsh alias wrapping | Hard | Shell coupling |

**Only testable without mocks**: `completion_scoring.py` (pure fuzzy matching algorithms)

**Everything else** requires xonsh environment or terminal - skip for unit tests,
test manually or via integration tests only.

#### LLM Utilities (~3,000 lines) — Testability: MEDIUM-HIGH

**Existing tests**: None

| File | Lines | Key Functions | Testability | Notes |
|------|-------|---------------|-------------|-------|
| fuzzy_parsing.py | 80 | is_no_results(), fuzzy_match(), strip_markdown_fence(), fuzzy_parse_json() | Easy | All pure functions |
| llm_names.py | 118 | Model name parsing, validation | Easy | Pure string handling |
| llm_messages.py | 44 | Message template rendering | Easy | Mostly pure |
| clean_headings.py | 79 | Heading cleanup transforms | Easy | Pure text transforms |
| custom_sliding_transforms.py | 309 | Text sliding window, chunk management | Easy | Pure algorithms |
| llm_completion.py | 295 | llm_completion(), llm_template_completion() | Medium | Mock litellm.completion |
| llm_api_keys.py | 43 | have_key_for_model() | Medium | Mock env vars |

**Easy wins**: fuzzy_parsing, llm_names, clean_headings, sliding_transforms are
all pure functions with zero external dependencies.

#### Web Content (~1,400 lines) — Testability: MIXED

**Existing tests**: None

| File | Lines | Key Functions | Testability | Notes |
|------|-------|---------------|-------------|-------|
| canon_url.py | 25 | URL canonicalization | Easy | Pure function |
| web_page_model.py | 44 | WebPageData dataclass | Easy | Data model |
| web_extract.py | 94 | Content extraction orchestration | Medium | Library deps |
| web_extract_justext.py | 81 | JusText extraction | Medium | External lib |
| web_fetch.py | 545 | HTTP client, retries, S3 fallback | Hard | Network I/O |
| local_file_cache.py | 378 | File caching with TTL | Medium | File I/O (use tmp_path) |
| file_cache_utils.py | 176 | High-level cache API | Medium | File I/O |

**Easy wins**: canon_url (pure), web_page_model (data model).
**Medium effort**: local_file_cache (use tmp_path), web_extract (mock HTML input).
**Hard**: web_fetch (mock httpx, but many code paths including SSL, S3, retries).

#### Workspaces (~800 lines) — Testability: MEDIUM

**Existing tests**: None

| File | Lines | Key Functions | Testability | Notes |
|------|-------|---------------|-------------|-------|
| selections.py | 200 | Selection history management | Medium | Needs workspace mock |
| param_state.py | 100 | Parameter state management | Easy/Medium | Mostly pure |
| workspace_registry.py | 100 | Workspace lookup | Medium | Global state |
| workspaces.py | 300 | Workspace operations | Medium | Singleton pattern |

**Strategy**: Create temp workspace fixture, mock `current_ws()` at module level.

#### File Storage (~1,000 lines) — Testability: GOOD

**Existing tests**: test_file_store.py (559 lines) - already decent coverage

**Gaps**:
- `item_id_index.py` - Pure index structure, easy to test
- `metadata_dirs.py` - Path handling, easy to test
- Edge cases: permissions, symlinks, concurrent access

#### Utils (~11,500 lines) — Testability: EXCELLENT

**Existing tests**: 4 test files (gather_limited, markdown_footnotes, csv, social_metadata)

**Untested pure utilities** (highest ROI):
- `common/url.py` - URL parsing and validation
- `common/format_utils.py` - Text formatting
- `file_utils/file_formats.py` - Format detection
- `file_utils/ignore_files.py` - Gitignore matching
- `text_handling/markdown_utils.py` - Markdown parsing
- `text_handling/text_normalization.py` - Text transforms

All of these are pure functions with no external dependencies.

#### Config (~600 lines) — Testability: MEDIUM

**Existing tests**: None

**Strategy**: Use monkeypatch for env vars, reset global settings between tests.

#### Commands (~2,000+ lines) — Testability: LOW

**Existing tests**: None

**Strategy**: Integration tests only. Mock FileStore and Workspace entirely.
Focus on testing the command logic (argument parsing, validation) not the
I/O effects.

#### Actions (~5,000+ lines) — Testability: LOW-MEDIUM

**Existing tests**: None

**Strategy**: Don't test individual action `apply()` methods directly.
Instead:
1. Extract pure transformation logic into utility functions
2. Test those utility functions
3. Use integration tests for full action pipelines

#### MCP (~943 lines) — Testability: MEDIUM

**Existing tests**: None

**Strategy**: Mock action execution, test tool registration and message routing.

### Summary: Test Priority Matrix

```
                    EASY                    HARD
              ┌─────────────────────┬─────────────────────┐
   HIGH       │ model/              │ exec/action_exec    │
   VALUE      │ llm_utils/fuzzy*    │ exec/decorators     │
              │ utils/common/url    │ workspaces/         │
              │ utils/text_handling │                     │
              ├─────────────────────┼─────────────────────┤
   MEDIUM     │ llm_utils/names     │ web_content/fetch   │
   VALUE      │ web_content/canon   │ commands/           │
              │ file_storage/index  │ mcp/routes          │
              │ shell/scoring       │ actions/            │
              ├─────────────────────┼─────────────────────┤
   LOW        │ config/settings     │ shell/completions   │
   VALUE      │ media_model         │ shell/output        │
              │                     │ xonsh_custom/       │
              └─────────────────────┴─────────────────────┘
```

**Top-left quadrant (easy + high value) should be done first.**

### Estimated Test Counts by Phase

| Phase | New Test Files | Approx. Tests | Effort |
|-------|---------------|---------------|--------|
| Phase 1: Pure functions | 10 files | ~150 tests | Low |
| Phase 2: Mocked deps | 8 files | ~100 tests | Medium |
| Phase 3: Integration | 5 files | ~50 tests | High |
| **Total** | **23 files** | **~300 tests** | — |

### conftest.py Design

```python
# tests/conftest.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary kash workspace for testing."""
    ws_dir = tmp_path / "test_workspace"
    ws_dir.mkdir()
    from kash.file_storage.file_store import FileStore
    return FileStore(ws_dir, is_global_ws=False, auto_init=True)

@pytest.fixture
def mock_current_ws(temp_workspace):
    """Patch current_ws() to return the temp workspace."""
    with patch('kash.workspaces.current_ws', return_value=temp_workspace):
        yield temp_workspace

@pytest.fixture
def mock_llm():
    """Mock LLM API calls for deterministic testing."""
    with patch('kash.llm_utils.llm_completion.litellm.completion') as mock:
        mock.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="mocked response"))],
            usage=MagicMock(prompt_tokens=10, completion_tokens=20)
        )
        yield mock

@pytest.fixture
def sample_item():
    """Create a minimal Item for testing."""
    from kash.model import Item, ItemType, Format
    return Item(
        title="Test Item",
        type=ItemType.doc,
        format=Format.markdown,
        body="# Test\n\nThis is test content.",
    )
```

---

## Implementation Plan

### Phase 1: Core Library API and Cleanup

- [ ] Define and implement clean public API surface in `__init__.py`
- [ ] Eliminate import side effects (lazy registration)
- [ ] Create standalone action runner (`kash.run()`)
- [ ] Add `__all__` to all public modules
- [ ] Remove unused dependencies
- [ ] Create optional dependency groups in pyproject.toml
- [ ] Fix openai version pinning

### Phase 2: Python Modernization

- [ ] Add `from __future__ import annotations` to all files
- [ ] Add `@override` to subclass method overrides
- [ ] Extract named constants from magic numbers
- [ ] Clean up dead code, TODO/FIXME comments
- [ ] Review and fix atomic file write usage
- [ ] Ensure all public APIs have concise docstrings

### Phase 3: Test Infrastructure and Coverage

- [ ] Create tests/conftest.py with workspace, LLM, and item fixtures
- [ ] **Quick wins (pure functions)**: model tests, fuzzy_parsing, llm_names,
      completion_scoring, url parsing, canon_url, markdown_utils (~10 files)
- [ ] **Mocked dependencies**: action_registry, resolve_args, precondition_checks,
      selections, param_state, item_id_index, llm_completion (~8 files)
- [ ] **Integration**: action_exec pipeline, web_fetch (mock httpx),
      local_file_cache, MCP routes, workspace commands (~5 files)

### Phase 4: Shell Decoupling and Standalone Access

- [ ] Design and implement ShellContext protocol
- [ ] Decouple command execution from xonsh aliases
- [ ] Create standalone CLI for individual actions
- [ ] Add `--format json` output mode
- [ ] Add `--non-interactive` flag support
- [ ] Create KashTestRunner for testing loops

### Phase 5: Packaging and Publishing (if desired)

- [ ] Extract web_content as standalone package
- [ ] Extract llm_utils as standalone package
- [ ] Create skill templates for Claude Code integration
- [ ] Implement lightweight MCP mode (selective action loading)

## Testing Strategy

- **Unit tests** for pure functions (models, parsing, scoring, URLs) - no mocks
- **Mocked tests** for functions with external deps (LLM, filesystem, workspace)
- **Integration tests** for action execution pipeline, web fetch, MCP routing
- **Not tested**: xonsh shell integration, Rich rendering, interactive prompts
- **CI rules**: No tests requiring live API keys; use `@pytest.mark.online` for optional
- **Speed target**: <1 second for all unit tests; integration tests marked `@pytest.mark.slow`

## Part 6: Guidelines Conformance Review

The following tbd guidelines should be reviewed against the kash codebase.
Each guideline review should verify conformance and create beads for gaps.

### Guidelines to Apply

| Guideline | Key Checks | Status |
|-----------|-----------|--------|
| python-rules | Type hints, naming, imports, error handling | Partial |
| python-modern-guidelines | `from __future__`, `@override`, uv, modern patterns | Partial |
| python-cli-patterns | CLI structure, agent compat, output modes, error codes | Not applied |
| error-handling-rules | Custom exceptions, exit codes, no silent failures | Partial |
| general-coding-rules | Constants, magic numbers, DRY, YAGNI | Partial |
| general-comment-rules | Concise comments, no obvious comments, why not what | Good |
| general-testing-rules | Minimal effective tests, no trivial tests, coverage | Low coverage |
| backward-compatibility-rules | API stability, file format compat, migration | Needs clarification |
| general-style-rules | Formatting, consistency | Good (ruff enforced) |
| general-tdd-guidelines | Test-first for new features | Not practiced |
| commit-conventions | Conventional commits | Partial |
| release-notes-guidelines | Changelog and release notes | Not present |

### Key Gaps Identified

1. **python-modern-guidelines**: ~215 files missing `from __future__ import annotations`;
   limited `@override` usage (14 files); no `__slots__` on performance-critical classes

2. **python-cli-patterns**: No `--format json` output mode; no `--non-interactive` flag;
   no `--no-progress` flag; errors go to stdout not stderr; no exit codes beyond 0/1

3. **error-handling-rules**: No custom exception hierarchy (uses generic Exception in
   many places); some bare `except:` clauses; error logging without re-raise in places

4. **general-coding-rules**: Magic numbers in completion_scoring.py, port ranges,
   timing constants; some constants defined as module-level variables without docstrings

5. **general-testing-rules**: Test coverage at ~7%; no conftest.py; no test markers;
   no coverage measurement configured

6. **backward-compatibility-rules**: No documented compatibility policy for Item
   file format, workspace directory structure, or action parameter signatures

## Open Questions

1. Should web_content and llm_utils be extracted to separate packages, or kept
   in-tree with optional dependency groups? (Separate packages add maintenance
   overhead but improve reusability.)

2. What's the minimum viable library API? Should `kash.run()` handle workspace
   creation automatically, or require explicit setup?

3. For standalone CLI commands, should we use Typer (modern, rich integration)
   or stick with argparse + rich_argparse (lighter weight)?

4. How much of the xonsh integration can we preserve while making the core
   shell-independent? Is there a clean separation boundary?

5. Should the action registry be fully lazy (import on first use) or use a
   manifest/metadata approach (scan decorators without importing)?

6. What backward compatibility requirements exist for the Item file format
   (frontmatter YAML), workspace directory structure, and action parameter
   signatures?

## References

- tbd guidelines: python-rules, python-modern-guidelines, python-cli-patterns
- tbd guidelines: error-handling-rules, general-coding-rules, general-comment-rules
- tbd guidelines: general-testing-rules, backward-compatibility-rules
- Kash README.md and development.md
