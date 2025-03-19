import os
from functools import cache
from pathlib import Path

from prettyfmt import fmt_path
from pydantic.dataclasses import dataclass

from kash.config.logger import get_logger

log = get_logger(__name__)

kash_base_path = Path(os.path.dirname(__file__)).parent


_TESTS_COMMENT_STR = "\n## Tests"

_SOURCE_SEPARATOR = "\n---\n"


def _format_source_file(path: Path) -> str:
    with open(path) as file:
        file_content = file.read()

    # Don't include any pytests that happen to be in the files.
    file_content = file_content.split(_TESTS_COMMENT_STR)[0]
    file_content = file_content.rstrip("\n") + "\n"

    header = f"# File {path.relative_to(kash_base_path.parent)}:\n\n"

    return header + (file_content if file_content.strip() else "(empty)")


def _format_source_module(module_path: Path) -> str:
    source_files = [f for f in os.listdir(module_path) if f.endswith(".py")]
    output: list[str] = []

    for filename in source_files:
        if source_code := _format_source_file(module_path / filename):
            output.append(source_code)

    return _SOURCE_SEPARATOR.join(output)


def _format_file_or_module(path: Path) -> str:
    if path.is_file():
        return _format_source_file(path)
    elif path.is_dir():
        return _format_source_module(path)
    else:
        raise ValueError(f"Path for source not found (or not a file/directory): {fmt_path(path)}")


def read_source_code(*paths: Path) -> str:
    """
    Get the source code for the given paths, formatted in a format friendly for an LLM.
    """
    return _SOURCE_SEPARATOR.join(filter(None, (_format_file_or_module(path) for path in paths)))


@dataclass(frozen=True)
class SourceCode:
    model_src: str
    """The source code for the kash framework model."""

    assistant_response_model_src: str
    """The source code for the assistant response model."""

    core_action_defs_src: str
    """The source code for all the core action definitions."""

    text_tool_src: str
    """The source code for some generally useful text tools."""

    file_formats_src: str
    """Documentation and source for common file formats."""

    example_action_src: str
    """Source code for an example action."""

    example_command_src: str
    """Source code for an example command."""

    def self_check(self) -> bool:
        return (
            len(self.model_src.splitlines()) > 5
            and len(self.assistant_response_model_src.splitlines()) > 5
            and len(self.core_action_defs_src.splitlines()) > 5
            and len(self.text_tool_src.splitlines()) > 5
            and len(self.file_formats_src.splitlines()) > 5
            and len(self.example_action_src.splitlines()) > 5
            and len(self.example_command_src.splitlines()) > 5
        )

    def __str__(self) -> str:
        sizes = ", ".join(f"{k} {len(v.splitlines())} lines" for k, v in self.__dict__.items())
        return f"SourceCode({sizes})"


@cache
def load_source_code() -> SourceCode:
    code = SourceCode(
        model_src=read_source_code(kash_base_path / "model"),
        assistant_response_model_src=read_source_code(
            kash_base_path / "model" / "assistant_response_model.py",
        ),
        text_tool_src=read_source_code(
            kash_base_path / "text_handling",
            kash_base_path / "utils" / "lang_utils",
            # TODO: Include additional dep libs like chopdiff TextDoc too?
        ),
        file_formats_src=read_source_code(
            kash_base_path / "utils" / "file_utils" / "file_formats_model.py"
        ),
        core_action_defs_src=read_source_code(kash_base_path / "actions" / "core"),
        example_action_src=read_source_code(
            kash_base_path / "actions" / "core" / "strip_html.py",
            kash_base_path / "actions" / "core" / "summarize_as_bullets.py",
        ),
        example_command_src=read_source_code(
            kash_base_path / "commands" / "extras" / "utils_commands.py",
            kash_base_path / "commands" / "base" / "reformat_command.py",
        ),
    )
    log.info("Loaded sources: %s", str(code))
    return code
