import logging
from pathlib import Path
from typing import Protocol

from strif import atomic_output_file

from kash.utils.common.format_utils import fmt_loc

log = logging.getLogger(__name__)


MINIMAL_IGNORE_PATTERNS = """
# Hidden files.
.*
.DS_Store

# Temporary and backup files
*.tmp
*.temp
*.bak
*.orig

# Partial files
*.partial
*.partial.*

# Editors/IDEs

*.swp
*.swo
*~

# Python
*.py[cod]
*.pyo
*.pyd
*.pyl
__pycache__/
"""

DEFAULT_IGNORE_PATTERNS = f"""
# Default ignore patterns for kash, in gitignore format.
# Idea is to avoid matching large files that aren't usually
# useful in file listings etc.
{MINIMAL_IGNORE_PATTERNS}

# Dev directories
.git/
.idea/
.vscode/

# Build and distribution directories
# dist/
# build/

# Node.js
node_modules/

# Python
*.venv/
*.env/
.Python
*.egg-info/

# Binaries and compiled files
*.out
*.exe
*.dll
*.so
*.o
*.a

# (end of defaults)

"""


class IgnoreFilter(Protocol):
    def __call__(self, path: str | Path, *, is_dir: bool = False) -> bool: ...


class IgnoreChecker(IgnoreFilter):
    def __init__(self, lines: list[str]):
        from pathspec.gitignore import GitIgnoreSpec

        self.lines = lines
        self.spec = GitIgnoreSpec.from_lines(lines)

    @classmethod
    def from_file(cls, path: Path) -> "IgnoreChecker":
        with open(path) as f:
            lines = f.readlines()

        log.info("Loading ignore file (%s lines): %s", len(lines), fmt_loc(path))
        return cls(lines)

    def matches(self, path: str | Path, *, is_dir: bool = False) -> bool:
        # Don't match "."!
        if Path(str(path)) == Path("."):
            return False

        # If it's a directory, make sure we check with a trailing slash to fit
        # gitignore rules.
        patterns = [str(path)]
        if is_dir and not str(path).endswith("/"):
            patterns.append(str(path) + "/")

        return any(self.spec.match_file(p) for p in patterns)

    def pattern_strs(self):
        lines = [line.strip() for line in self.lines]
        return [line for line in lines if line and not line.startswith("#")]

    def __call__(self, path: str | Path, *, is_dir: bool = False) -> bool:
        return self.matches(path, is_dir=is_dir)

    def __repr__(self) -> str:
        return f"IgnoreChecker({'; '.join(self.pattern_strs())})"


ignore_none: IgnoreFilter = lambda path, is_dir=False: False

is_ignored_minimal = IgnoreChecker(list(MINIMAL_IGNORE_PATTERNS.splitlines()))
"""
Basic check for whether a file is ignored.
"""

is_ignored_default = IgnoreChecker(list(DEFAULT_IGNORE_PATTERNS.splitlines()))
"""
Default check for whether a file is ignored.
"""


def write_ignore(path: Path, body: str = DEFAULT_IGNORE_PATTERNS, append: bool = False) -> None:
    """
    Write the default kash ignore file to the given path.
    """
    if append:
        with open(path, "a") as f:
            f.write(body)
    else:
        with atomic_output_file(path) as f:
            with f.open("w") as f:
                f.write(body)

    log.info("Wrote ignore file (%s lines): %s", len(body.splitlines()), fmt_loc(path))


def add_to_ignore(path: Path, pat_list: list[str]) -> None:
    """
    Add patterns to a .gitignore file for the given directory.
    Idempotent.
    """

    if path.exists():
        existing_lines = path.read_text().splitlines()
    else:
        existing_lines = []

    with path.open("a") as f:
        for pat in pat_list:
            pat = pat.strip()
            if pat and pat not in existing_lines:
                f.write(f"{pat}\n")
