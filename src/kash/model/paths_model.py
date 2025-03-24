from __future__ import annotations

import sys
from os import PathLike
from pathlib import Path, PosixPath, WindowsPath
from typing import Any

import regex
from frontmatter_format import add_default_yaml_representer
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from kash.utils.common.parse_shell_args import shell_quote
from kash.utils.common.url import is_url


class StorePathError(ValueError):
    """
    An error related to a StorePath.
    """


class InvalidStorePath(StorePathError):
    """
    Input was not a valid StorePath.
    """


_valid_store_name_re = regex.compile(r"^[\p{L}\p{N}_\.]+$", regex.UNICODE)

AT_PREFIX = "@"
"""
Any store path can be @-mentioned, and it's fine to include this prefix
when the store path is parsed.
"""

# Determine the base class for StorePath based on the operating system
if sys.platform == "win32":
    BasePath = WindowsPath
else:
    BasePath = PosixPath


class StorePath(BasePath):  # pyright: ignore
    """
    A StorePath is a relative Path within a given scope (a directory we call a
    store) with the addition of some additional syntactic conveniences for parsing
    and displaying.

    Standard formats for StorePaths:
    - `~store_name/folder1/folder2/filename.ext`: A file with the path
      `folder1/folder2/filename.ext` within the `store_name` store.
    - `folder1/folder2/filename.ext`: A path within the current store.

    Store names must be alphanumeric (letters, digits, `_`, `.`).

    Alternative forms:
    - A path may contain an `@` prefix: `@folder1/folder2/filename.ext` and
      `@/folder1/folder2/filename.ext` both refer to `folder1/folder2/filename.ext`.

    Paths containing spaces can be enclosed in single quotes:
    - `'folder 1/folder 2/filename.ext'`
    - `@'~store_name/file with spaces.txt'`

    Restrictions:
    - Bare absolute paths like `/home/user/file.ext` are not allowed.
    - Empty or "." paths are not allowed.
    - `~store_name/` and `~store_name` are not valid StorePaths.
    """

    store_name: str | None = None

    def __new__(
        cls,
        value: str | Path,
        *more_parts: str | Path,
        store_name: str | None = None,
    ) -> StorePath:
        """
        Create a new `StorePath` instance from a string representation as a relative path or in
        a standard format like `@folder/filename` or `@~store_name/folder/filename`.
        """

        # Parse a non-StorePath value
        # Pull out the store name from the first value.
        parsed_path: Path
        if isinstance(value, StorePath):
            parsed_path = value
            if not store_name:
                store_name = value.store_name
        else:
            parsed_path, parsed_store_name = cls.parse(value)
            if not store_name:
                store_name = parsed_store_name

        # Construct the path from all parts. This is important because this __new__ may
        # be called with same args as Path, e.g. from deepcopy, with several parts.
        path = Path(parsed_path, *more_parts)

        self = super().__new__(cls, *path.parts)
        self.store_name = store_name

        # XXX Ugly but not sure of a simpler way to initialize ourselves
        # exactly like a Path in __new__.
        if hasattr(path, "_raw_paths"):  # Needed for Python 3.12 and 3.13
            self._raw_paths = path._raw_paths  # pyright: ignore
        if hasattr(self, "_load_parts"):  # Needed for Python 3.12 but not 3.13
            self._load_parts()  # pyright: ignore

        return self

    def __init__(  # pyright: ignore
        self,
        value: str | Path,
        *rest: str | Path,
        store_name: str | None = None,
    ):
        pass  # not calling super().__init__

    @staticmethod
    def parse(value: str | Path) -> tuple[Path, str | None]:
        """
        Parse a string representation of the store path into a Path and store name
        (if any). The input should be a relative Path or a string representation
        that is a valid store path.
        """
        if not isinstance(value, (str, Path)):
            raise InvalidStorePath(f"Unexpected type for store path: {type(value)}: {value!r}")
        if isinstance(value, str) and is_url(value):
            raise InvalidStorePath(f"Expected a store path but got a URL: {value!r}")

        path = Path(value)
        if path.is_absolute():
            raise InvalidStorePath(f"Absolute store paths are not allowed: {value!r}")
        if path == Path("."):
            raise InvalidStorePath(f"Invalid store path: {value!r}")
        rest = str(value)

        # Ignore any @ prefix.
        if rest.startswith(AT_PREFIX):
            rest = rest[1:]

        # Handle single quotes.
        if rest.startswith("'"):
            # Path is enclosed in single quotes
            if rest.endswith("'"):
                quoted_path = rest[1:-1]
                rest = quoted_path
            else:
                raise InvalidStorePath(f"Unclosed single quote in store path: {value!r}")

        # Handle store name of form ~store_name/some/path.
        if rest.startswith("~"):
            # Store name is specified.
            rest = rest[1:]
            # Split rest into store_name and path.
            if "/" in rest:
                store_name, path_str = rest.split("/", 1)
            else:
                raise InvalidStorePath(f"Invalid store path: {value!r}")
            if (
                not store_name.strip()
                or not path_str.strip()
                or path_str.strip().startswith("/")
                or not _valid_store_name_re.match(store_name)
            ):
                raise InvalidStorePath(f"Invalid store path: {value!r}")
        else:
            store_name = None
            path_str = rest
            if path_str.startswith("/"):
                path_str = path_str[1:]

        return Path(path_str), store_name

    def __truediv__(self, key: str | PathLike[str]) -> StorePath:
        if isinstance(key, Path):
            if key.is_absolute():
                raise StorePathError(f"Cannot join a StorePath with an absolute Path: {str(key)!r}")
            if isinstance(key, StorePath) and self.store_name != key.store_name:
                raise StorePathError(
                    f"Cannot join paths from different stores: {self!r} and {str(key)!r}"
                )
            key_parts = key.parts
        else:
            key_parts = (str(key),)
        new_parts = self.parts + key_parts
        return self.__class__(Path(*new_parts), store_name=self.store_name)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Use the handler to get the schema for the base Path type.
        path_schema = handler(BasePath)
        return core_schema.no_info_after_validator_function(
            cls.validate,
            path_schema,
        )

    @classmethod
    def validate(cls, value: str | Path | StorePath) -> StorePath:
        if isinstance(value, StorePath):
            return value
        return cls(value)

    def resolve(self) -> Path:  # pyright: ignore
        """
        If we resolve a StorePath, it must be a plain Path again, since StorePaths are relative.
        """
        return Path(self).resolve()

    @property
    def parent(self) -> Path:  # pyright: ignore
        """
        The parent of a StorePath is a Path, for simplicity.
        """
        return Path(self).parent

    def display_str(self, with_at: bool = True) -> str:
        """
        String representation of the path, quoting appropriately and
        optionally with the `@` prefix and store name (if any).
        """
        path_str = str(self)
        if self.store_name:
            display = shell_quote(f"~{self.store_name}/{path_str}")
        else:
            display = shell_quote(path_str)
        if with_at:
            display = AT_PREFIX + display
        return display

    def __str__(self) -> str:
        """
        The default str representation remains compatible with Path.
        """
        return super().__str__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)!r})"

    def __eq__(self, other):
        if isinstance(other, StorePath):
            return super().__eq__(other) and self.store_name == other.store_name
        else:
            return False

    def __hash__(self):
        return hash((super().__str__(), self.store_name))


UnresolvedPath = str | Path | StorePath
"""
"Resolved" means that the argument has been converted to a known argument
type, like Path, StorePath, or Url.
"Unresolved" means it is a string or a resolved type.
Resolving an unresolved argument of a string or any argument-compatible type
is idempotent.
"""


def fmt_store_path(store_path: str | Path | StorePath) -> str:
    """
    Format a store path as a string.
    """
    return StorePath(store_path).display_str()


def parse_path_spec(path: str | Path | StorePath) -> Path | StorePath:
    """
    Resolve any string into a path, ensuring that a path that includes an @ prefix
    becomes a StorePath. Leaves already-resolved StorePaths and Paths unchanged.
    """
    if "*" in str(path):
        # Would be nice to have resolution here instead of only at the shell level?
        raise NotImplementedError("Glob resolution not yet implemented for StorePaths")
    if isinstance(path, StorePath):
        return path
    elif isinstance(path, Path):
        return path
    elif path.startswith(AT_PREFIX):
        return StorePath(path)
    else:
        return Path(path)


def _represent_store_path(dumper: Any, data: StorePath) -> Any:
    return dumper.represent_str(str(data))


add_default_yaml_representer(StorePath, _represent_store_path)


## Tests


def test_store_path():
    # Test creation with relative path
    sp1 = StorePath("some/relative/path")
    sp2 = StorePath("@some/relative/path")
    sp3 = StorePath("@/some/relative/path")
    assert isinstance(sp1, StorePath)
    assert isinstance(sp1, Path)
    assert sp1.store_name is None
    assert str(sp1) == "some/relative/path"
    assert sp1.display_str() == "@some/relative/path"
    assert sp1 == sp2
    assert sp1 == sp3

    # Test equality
    sp1 = StorePath("@path/to/file")
    sp2 = StorePath("path/to/file")
    sp3 = StorePath("path/to/file", store_name="store1")
    sp4 = StorePath("path/to/file", store_name="store1")
    assert sp1 == sp2
    assert sp3 == sp4
    assert sp1 != sp3

    # Test hash
    s = set()
    s.add(sp1)
    s.add(sp3)
    assert len(s) == 2
    s.add(sp2)
    assert len(s) == 2  # sp1 and sp2 are equal

    # Test that __str__, __repr__, and fmt_path don't raise an exception
    print([str(sp1), str(sp2), str(sp3), str(sp4)])
    print([repr(sp1), repr(sp2), repr(sp3), repr(sp4)])
    print(fmt_store_path(StorePath("store/path1")))
    print(repr(Path(StorePath("store/path1"))))

    # Test some invalid store paths
    try:
        StorePath("/absolute/path")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Absolute store paths are not allowed: '/absolute/path'"
    try:
        StorePath(".")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '.'"
    try:
        StorePath("")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: ''"

    try:
        StorePath("https://example.com")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Expected a store path but got a URL: 'https://example.com'"

    # Test with store name
    sp_with_store = StorePath("@~mystore/folder/file.txt")
    assert isinstance(sp_with_store, StorePath)
    assert sp_with_store.store_name == "mystore"
    assert str(sp_with_store) == "folder/file.txt"
    assert sp_with_store.display_str() == "@~mystore/folder/file.txt"

    # Test parsing '@folder/file.txt'
    sp2 = StorePath("@folder/file.txt")
    assert sp2.store_name is None
    assert str(sp2) == "folder/file.txt"
    assert sp2.display_str() == "@folder/file.txt"

    # Test parsing '@/folder/file.txt'
    sp3 = StorePath("@/folder/file.txt")
    assert sp3.store_name is None
    assert str(sp3) == "folder/file.txt"  # Leading '/' is removed
    assert sp3.display_str() == "@folder/file.txt"

    # Test parsing '@~/folder/file.txt' (invalid, missing store name)
    try:
        StorePath("@~/folder/file.txt")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '@~/folder/file.txt'"

    # Test invalid store name
    try:
        StorePath("@~store-name/folder/file.txt")  # 'store-name' with hyphen is invalid
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '@~store-name/folder/file.txt'"

    # Test that '~store_name/' and '~store_name' are invalid
    try:
        StorePath("~store_name/")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '~store_name/'"

    try:
        StorePath("~store_name")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '~store_name'"

    # Test that '@~store_name' is invalid
    try:
        StorePath("@~store_name")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Invalid store path: '@~store_name'"

    # Test paths with spaces enclosed in single quotes
    sp_spaces = StorePath("@'folder 1/folder 2/filename.ext'")
    assert isinstance(sp_spaces, StorePath)
    assert sp_spaces.store_name is None
    assert str(sp_spaces) == "folder 1/folder 2/filename.ext"
    assert sp_spaces.display_str() == "@'folder 1/folder 2/filename.ext'"

    sp_spaces2 = StorePath("@'/folder 1/folder 2/filename.ext'")
    assert sp_spaces == sp_spaces2

    sp_spaces3 = StorePath("@'~store_name/file with spaces.txt'")
    assert sp_spaces3.store_name == "store_name"
    assert str(sp_spaces3) == "file with spaces.txt"
    assert sp_spaces3.display_str() == "@'~store_name/file with spaces.txt'"

    # Test unclosed single quote
    try:
        StorePath("@'folder/filename.ext")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == 'Unclosed single quote in store path: "@\'folder/filename.ext"'
    try:
        StorePath("@'folder/filename.ext' extra")
        raise AssertionError()
    except InvalidStorePath as e:
        assert str(e) == "Unclosed single quote in store path: \"@'folder/filename.ext' extra\""

    # Path / StorePath
    combined = Path("base/path") / StorePath("@some/relative/path")
    assert isinstance(combined, Path)
    assert combined == Path("base/path/some/relative/path")

    # StorePath / relative Path
    combined = StorePath("base/store/path") / Path("some/relative/path")
    assert isinstance(combined, StorePath)
    assert combined == StorePath("base/store/path/some/relative/path")
    assert combined.store_name is None

    # StorePath / absolute Path
    try:
        combined = sp1 / Path("/absolute/path")
        raise AssertionError()
    except StorePathError as e:
        assert str(e) == "Cannot join a StorePath with an absolute Path: '/absolute/path'"

    # StorePath / StorePath
    combined = StorePath("store/path1") / StorePath("store/path2")
    assert isinstance(combined, StorePath)
    assert combined == StorePath("store/path1/store/path2")
    assert combined.store_name is None

    # Instantiating Paths
    assert Path(StorePath("store/path1")).resolve() == Path("store/path1").resolve()
