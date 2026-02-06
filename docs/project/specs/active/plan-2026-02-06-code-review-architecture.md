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

#### 5A. Create test infrastructure

- Add `conftest.py` with shared fixtures:
  - Temporary workspace fixture
  - Mock LLM client fixture
  - Test item factories
- Keep simple tests inline per the guidelines

#### 5B. Add tests for critical untested paths

Priority order:
1. Action execution pipeline (action_exec.py)
2. Workspace operations (create, switch, save/load items)
3. Web content fetching and extraction (with mocked HTTP)
4. LLM integration (with mocked API calls)
5. MCP server tool registration and execution
6. Command execution and argument parsing

#### 5C. Add CLI output format tests

Once structured output is supported (Phase 6), add tests that verify
JSON output mode works correctly for key commands.

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

- [ ] Create conftest.py with shared fixtures
- [ ] Add action execution pipeline tests
- [ ] Add workspace operation tests
- [ ] Add web content tests (mocked HTTP)
- [ ] Add LLM integration tests (mocked API)
- [ ] Add MCP server tests
- [ ] Add command execution tests

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

- Unit tests for each subsystem with mocked external dependencies
- Integration tests for action execution pipeline
- CLI output tests (text and JSON modes)
- Workspace lifecycle tests with temporary directories
- No tests requiring live API keys in CI (use mocks)

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
