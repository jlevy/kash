"""ScoredCompletion must stay compatible with xonsh RichCompletion."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from xonsh.completers.tools import RichCompletion

from kash.shell.completions.completion_types import CompletionGroup, ScoredCompletion

# Classes that rebuild a third-party instance via **__dict__ (or an equivalent
# field copy). Add a row here if you introduce another wrapper of that form.
RECONSTRUCTION_WRAPPERS: tuple[tuple[type, type], ...] = ((ScoredCompletion, RichCompletion),)

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "kash"

# Call sites that unpack **obj.__dict__. New sites fail this inventory so they
# get classified (reconstruction wrapper vs harmless merge).
KNOWN_CALL_DICT_SPLATS: dict[str, set[str]] = {
    "config/colors.py": {"SimpleNamespace"},
    "docs/load_api_docs.py": {"template.format"},
    "shell/completions/completion_types.py": {"cls", "dict"},
}

KNOWN_LITERAL_DICT_SPLAT_FILES: set[str] = {
    "config/colors.py",
}


def _init_param_names(cls: type) -> set[str]:
    names: set[str] = set()
    for name, param in inspect.signature(cls.__init__).parameters.items():
        if name == "self" or param.kind is inspect.Parameter.VAR_KEYWORD:
            continue
        names.add(name)
    return names


def _instance_from_init_defaults(cls: type, value: str) -> object:
    kwargs: dict[str, object] = {}
    for name, param in inspect.signature(cls.__init__).parameters.items():
        if name in {"self", "value"}:
            continue
        if param.kind in {inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL}:
            continue
        if param.default is inspect.Parameter.empty:
            kwargs[name] = "x"
        else:
            kwargs[name] = param.default
    return cls(value, **kwargs)


def _rel(path: Path) -> str:
    return path.relative_to(SRC_ROOT).as_posix()


def test_reconstruction_wrappers_declare_all_parent_init_params():
    """from_unscored forwards RichCompletion.__dict__; extra keys crash Tab.

    basedpyright cannot check `**dict[str, Any]` against a constructor, so this
    signature comparison is the build-time guard when xonsh adds fields.
    """
    for child, parent in RECONSTRUCTION_WRAPPERS:
        missing = _init_param_names(parent) - _init_param_names(child)
        assert missing == set(), (
            f"{child.__name__} missing {parent.__name__} params: {sorted(missing)}"
        )


def test_from_unscored_accepts_live_rich_completion_signature():
    """Build a RichCompletion with every current init field, then wrap it."""
    rich = _instance_from_init_defaults(RichCompletion, "ls")
    assert isinstance(rich, RichCompletion)
    if "provider" in _init_param_names(RichCompletion):
        rich = rich.replace(provider="command")
    scored = ScoredCompletion.from_unscored(rich)
    for name in _init_param_names(RichCompletion) - {"value"}:
        assert getattr(scored, name) == getattr(rich, name)


def test_from_unscored_preserves_provider_and_rich_fields():
    rich = RichCompletion(
        "ls",
        prefix_len=1,
        display="ls",
        description="list files",
        style="bold",
        append_closing_quote=False,
        append_space=True,
        provider="command",
    )
    scored = ScoredCompletion.from_unscored(rich)
    assert scored == "ls"
    assert scored.prefix_len == 1
    assert scored.display == "ls"
    assert scored.description == "list files"
    assert scored.style == "bold"
    assert scored.append_closing_quote is False
    assert scored.append_space is True
    assert scored.provider == "command"
    assert scored.group == CompletionGroup.standard


def test_from_unscored_plain_string():
    scored = ScoredCompletion.from_unscored("echo")
    assert scored == "echo"
    assert scored.provider is None


def test_replace_matches_xonsh_format_completion_path():
    """xonsh Completer._format_completion calls RichCompletion.replace()."""
    scored = ScoredCompletion("ls", provider="command", append_space=True)
    after_quote = scored.replace(value=scored.value + '"')
    after_space = after_quote.replace(value=after_quote.value + " ")
    assert after_space == 'ls" '
    assert after_space.provider == "command"
    assert after_space.append_space is True


def test_dict_splat_call_sites_are_known():
    """Inventory `**obj.__dict__` unpacks so a new reconstruction hole is reviewed."""
    found: dict[str, set[str]] = {}
    literal_files: set[str] = set()
    for path in SRC_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text())
        rel = _rel(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg is not None:
                        continue
                    if isinstance(kw.value, ast.Attribute) and kw.value.attr == "__dict__":
                        found.setdefault(rel, set()).add(ast.unparse(node.func))
            elif isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=True):
                    if (
                        key is None
                        and isinstance(value, ast.Attribute)
                        and value.attr == "__dict__"
                    ):
                        literal_files.add(rel)

    assert found == KNOWN_CALL_DICT_SPLATS
    assert literal_files == KNOWN_LITERAL_DICT_SPLAT_FILES
