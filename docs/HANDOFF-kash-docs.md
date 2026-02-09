# Agent Handoff: kash-docs Post-Merge Verification and Cleanup

## Task

Verify that kash-docs builds and works correctly against the updated kash-shell main branch (PR #6 merged), then apply the same code quality cleanups to the kash-docs codebase.

## Context

PR #6 on `jlevy/kash` (kash-shell) was a large architecture modernization PR that has been merged to main. It included dependency upgrades (openai 2.x, litellm 1.81), Python 3.14 support, ruff/codespell/basedpyright fixes, `from __future__ import annotations` across 184 files, `@override` decorators, dead code removal, lazy action/command registration, a public API surface (`__all__`), and ~174 new tests. All 301 tests pass on Python 3.11-3.14. CI is green.

kash-docs is a namespace package that extends the `kash` namespace — it provides `kash.kits.docs` and `kash.docs.concepts` on top of kash-shell's `kash.*` modules. It currently pins `kash-shell==0.3.37` and targets Python `>=3.11,<3.14`.

## Step 1: Point kash-docs at bleeding-edge kash-shell

In `pyproject.toml`, change the pinned version to a git dependency:

```toml
# Change this:
"kash-shell==0.3.37",

# To this:
"kash-shell @ git+https://github.com/jlevy/kash.git",
```

Also uncomment or add this in `[tool.uv.sources]`:

```toml
[tool.uv.sources]
kash-shell = { git = "https://github.com/jlevy/kash.git" }
```

Then run `uv lock --upgrade && uv sync --all-extras` to pull the latest kash-shell from main.

## Step 2: Verify kash-docs builds and tests pass

Run the full CI pipeline locally:

```bash
uv run python devtools/lint.py   # codespell + ruff + basedpyright
uv run pytest                     # all tests
```

**What to watch for:**
- Import errors from kash-shell API changes (the PR kept all changes backward-compatible, but verify)
- openai 2.x breaking changes — the openai SDK went from 1.x to 2.x (`openai>=2.15.0`). Check for any direct `openai` imports in kash-docs that may use removed APIs
- litellm 1.81 compatibility — verify any direct litellm usage still works
- `from __future__ import annotations` interactions — kash-shell added this to 184 files, which changes how type annotations are evaluated at runtime. If kash-docs uses `as_dataclass()` or similar runtime type introspection on kash types, watch for `TypeError` on nested dataclass deserialization (the fix is to remove the future import from that specific file — see `tabbed_webpage.py` as the precedent)

## Step 3: Add Python 3.14 support

In `pyproject.toml`:
```toml
# Change:
requires-python = ">=3.11,<3.14"
# To:
requires-python = ">=3.11,<4.0"
```

In `.github/workflows/ci.yml`:
```yaml
# Change:
python-version: ["3.11", "3.12", "3.13"]
# To:
python-version: ["3.11", "3.12", "3.13", "3.14"]
```

Also update the uv version in CI:
```yaml
# Change:
version: "0.9.5"
# To:
version: "0.9.26"
```

Run tests with Python 3.14: `uv run --python 3.14 pytest`

Python 3.14.3 is fully released and works with Pydantic 2.12+. If you hit Pydantic `_eval_type()` errors, make sure uv is up to date (`uv self update`) to get the latest 3.14.x (not an old RC).

## Step 4: Apply the same code quality cleanups

These are the cleanups applied to kash-shell that should be mirrored on kash-docs:

### 4a. Add `from __future__ import annotations` to all Python files

Add to every `.py` file in `src/` and `tests/` that has type annotations:

```python
from __future__ import annotations
```

**IMPORTANT CAVEAT**: Do NOT add it to any file that uses runtime type introspection like `as_dataclass()` for YAML round-trip deserialization of nested dataclasses. If a test breaks after adding the import, remove it from that specific file. The symptom is a `TypeError` during dataclass construction from YAML.

### 4b. Add `@override` to subclass method overrides

For any method that overrides a parent class method, add the `@override` decorator:

```python
from typing_extensions import override

class MySubclass(Base):
    @override
    def some_method(self) -> None:
        ...
```

Use `typing_extensions.override` (not `typing.override`) for Python 3.11 compatibility.

### 4c. Remove dead code

- Remove any commented-out import blocks
- Remove `if __name__ == "__main__":` testing blocks (these should be proper tests)
- Remove any unused imports flagged by ruff

### 4d. Run ruff auto-fix and format

```bash
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
```

This will auto-fix things like:
- `isinstance(x, (A, B))` → `isinstance(x, A | B)` (UP038)
- Import sorting (I rules)
- Various pyupgrade modernizations (UP rules)

### 4e. Fix codespell errors

```bash
uv run codespell src/ tests/ docs/
```

If any words are false positives (e.g., test data), add them to the `ignore-words-list` in `pyproject.toml`:

```toml
[tool.codespell]
ignore-words-list = "iTerm,Numbe,caf,hel"
```

### 4f. Fix basedpyright errors

```bash
uv run basedpyright
```

Target 0 errors. Common fixes:
- Wrap bare strings in `Url()` when the type expects `Url` (it's a `NewType(str)`)
- Add `# type: ignore` for dynamic mock constructions in tests
- Use `assert x is not None` before using Optional values
- Prefix unused callback parameters with `_`

### 4g. Upgrade dependencies

In `pyproject.toml`, make sure these match kash-shell:
- `openai>=2.15.0` (was pinned to 1.x)
- `litellm>=1.80.16` (was older)
- Any other shared dependencies should have compatible version ranges

Run `uv lock --upgrade` to get all transitive deps updated.

## Step 5: Run full CI and verify

After all changes:

```bash
uv run python devtools/lint.py   # 0 errors expected
uv run pytest                     # all tests pass
```

Verify on all Python versions (3.11, 3.12, 3.13, 3.14).

## Step 6: Before shipping

Once everything works against the git dependency, decide on the final dependency strategy:
- For CI/development: keep the git dependency to validate against latest kash-shell
- For release/publish: pin to a specific kash-shell version (once a new release is cut that includes PR #6 changes)

The publish workflow (`publish.yml`) builds and uploads to PyPI, so it needs a proper version pin for release. The git dependency is for validation only.

## Known Risks

1. **openai 2.x migration**: The biggest risk. openai 2.x has breaking API changes. If kash-docs makes direct openai SDK calls (not through kash-shell's abstractions), those may break.

2. **Namespace package interactions**: Both packages share the `kash` namespace via `pkgutil.extend_path`. The `from __future__ import annotations` change affects how types resolve at runtime within the shared namespace. Test thoroughly.

3. **`as_dataclass()` breakage**: If any kash-docs code uses `as_dataclass()` with nested dataclasses and you add `from __future__ import annotations`, it will break. The fix is to not add the future import to that specific file.

4. **Python 3.14 + audioop**: kash-shell already handles this with `audioop-lts>=0.2.1; python_version >= '3.13'`. If kash-docs has audio processing, make sure the same conditional dep is present.

## Reference

- **kash-shell PR #6**: https://github.com/jlevy/kash/pull/6 (merged)
- **kash-shell main branch**: https://github.com/jlevy/kash (all changes are on main)
- **Architecture spec**: `.tbd/docs/specs/plan-2026-02-06-code-review-architecture.md`
- **CI config reference**: `.github/workflows/ci.yml` in kash-shell (shows the 3.11-3.14 matrix)
