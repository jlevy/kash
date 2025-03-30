import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from functools import cache
from io import BytesIO
from pathlib import Path
from typing import TextIO
from urllib.request import Request, urlopen
from zipfile import ZipFile

from strif import atomic_output_file
from tldr import (
    DOWNLOAD_CACHE_LOCATION,
    REQUEST_HEADERS,
    URLOPEN_CONTEXT,
    get_cache_dir,
    get_cache_file_path,
    get_language_list,
    get_platform_list,
    store_page_to_cache,
)

from kash.config.logger import get_logger
from kash.docs_base.load_recipe_snippets import RECIPES_DIR
from kash.exec_model.commands_model import CommentedCommand
from kash.exec_model.script_model import BareComment
from kash.help.help_types import CommandInfo, CommandType
from kash.help.recommended_commands import DROPPED_TLDR_COMMANDS, RECOMMENDED_TLDR_COMMANDS
from kash.xonsh_custom.shell_which import is_valid_command

log = get_logger(__name__)


def excluded_tldr_commands() -> set[str]:
    from kash.exec.action_registry import get_all_actions_defaults
    from kash.exec.command_registry import get_all_commands

    return {name for name in get_all_commands().keys()} | {
        name for name in get_all_actions_defaults().keys()
    }


"""
Avoid old tldr help pages like "help" and "chat" that conflict with
kash commands.
"""


CACHE_UPDATE_INTERVAL = timedelta(days=14)

_cache_dir = Path(get_cache_dir())
_timestamp_file = _cache_dir / ".tldr_cache_timestamp"


def _should_update_cache() -> bool:
    try:
        if not _timestamp_file.exists():
            return True
        last_update = datetime.fromtimestamp(_timestamp_file.stat().st_mtime)
        return last_update < datetime.now() - CACHE_UPDATE_INTERVAL
    except Exception:
        return True


def _cache_location(language: str) -> str:
    return f"{DOWNLOAD_CACHE_LOCATION[:-4]}-pages.{language}.zip"


# Copied from tldr.py with adjustments.
def _update_cache() -> None:
    languages = get_language_list()
    errors = 0
    for language in languages:
        cache_location = None
        try:
            cache_location = _cache_location(language)
            log.warning(
                f"Updating tldr cache for language {language}: {cache_location} -> {_cache_dir}"
            )
            req = urlopen(Request(cache_location, headers=REQUEST_HEADERS), context=URLOPEN_CONTEXT)
            zipfile = ZipFile(BytesIO(req.read()))
            pattern = re.compile(r"(.+)/(.+)\.md")
            cached = 0
            for entry in zipfile.namelist():
                match = pattern.match(entry)
                if match:
                    bytestring = zipfile.read(entry)
                    store_page_to_cache(
                        bytestring,  # pyright: ignore (tldr seems to have wrong type)
                        match.group(2),
                        match.group(1),
                        language,
                    )
                    cached += 1

        except Exception as e:
            log.error(
                f"Error: Unable to update tldr cache for language {language} from {cache_location}: {e}"
            )
            errors += 1

    if errors:
        log.error(f"Could not update tldr cache: {errors} errors")
    else:
        _timestamp_file.parent.mkdir(parents=True, exist_ok=True)
        _timestamp_file.touch()


def tldr_page_from_cache(command: str) -> str | None:
    command = command.strip()
    if command.lower() in DROPPED_TLDR_COMMANDS:
        return None

    if command.lower() in excluded_tldr_commands():
        return None

    platforms = get_platform_list()
    languages = get_language_list()

    for platform in platforms:
        for language in languages:
            cache_file_path = get_cache_file_path(command, platform, language)
            # Avoid case-insensitive match on macOS.
            really_matches = cache_file_path.name.startswith(command)
            if cache_file_path.exists() and really_matches:
                return cache_file_path.read_text()

    return None


def _clean_tldr_comment(text: str) -> str:
    """
    Clean tldr text that has extra brackets:
    "List [a]ll files:" -> "List all files"
    """
    text = text.replace("`", "")
    text = re.sub(r"\[([A-Za-z0-9])\]", r"\1", text)
    text = text.rstrip(" :.")
    return text


def _clean_tldr_command(text: str) -> str:
    """
    Clean tldr command text.
    """
    # TODO: Also remove {{}} metavars?
    # dust --ignore-directory {{file_or_directory_name}}
    text = text.strip(" `")
    return text


def tldr_refresh_cache() -> bool:
    """
    Refresh the full TLDR cache.
    """
    if _should_update_cache():
        _update_cache()
        return True
    return False


def tldr_help(command: str, drop_header: bool = False) -> str | None:
    """
    Get TLDR help for a command, if available. Pre-caches all pages with occasional refresh.
    This way it's fast and fails instantly for unknown commands.
    """
    if not command.strip():
        return None

    tldr_refresh_cache()

    page_str = tldr_page_from_cache(command)
    if not page_str:
        return None

    if drop_header:
        page_str = re.sub(r"^# (.*)$", "", page_str, count=1, flags=re.MULTILINE)
    else:
        # Leave in place but make it an h3 so it looks nicer in Markdown.
        page_str = re.sub(r"^# (.*)$", r"### \1", page_str, count=1, flags=re.MULTILINE)

    return page_str.strip()


@cache
def tldr_description(command: str) -> str | None:
    """
    Get just the description from tldr.
    Returns the short command description paragraph, which is always on a markdown block with
    lines starting with ">".
    """
    page_str = tldr_help(command)
    if not page_str:
        return None

    # Split into lines and find description paragraph
    lines = []
    in_description = False
    for line in page_str.splitlines():
        line = line.strip()
        if line.startswith(">"):
            # Stop at "More information" line
            if "More information:" in line:
                break
            # Add line without '>' prefix, stripped
            lines.append(line[1:].strip())
            in_description = True
        elif in_description:
            # Stop when we hit a non-'>' line after being in description
            break

    return _clean_tldr_comment(" ".join(lines)) if lines else None


def tldr_descriptions(commands: list[str] = RECOMMENDED_TLDR_COMMANDS) -> list[CommandInfo]:
    command_infos = [
        CommandInfo(
            command_type=CommandType.shell_recommended,
            command=command,
            description=tldr_description(command) or "",
            help_page=tldr_help(command),
        )
        for command in commands
    ]
    missing_descriptions = [info.command for info in command_infos if not info.description]
    if missing_descriptions:
        log.warning("No descriptions for commands: %s", missing_descriptions)
    return command_infos


def tldr_snippets(command: str) -> list[CommentedCommand]:
    """
    Parse TLDR help into a list of CommentedCommand objects, which can function as
    suggested command snippets.
    """
    command = command.strip()
    page_str = tldr_help(command)
    if page_str:
        commands = []
        current_comment = None

        for line in page_str.splitlines():
            # Skip empty lines and headers.
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("#") or stripped_line.startswith(">"):
                continue

            # Lines starting with dash are descriptions
            if stripped_line.startswith("- "):
                current_comment = _clean_tldr_comment(stripped_line[2:].strip())
            # Indented lines are commands
            elif stripped_line and current_comment:
                command_str = _clean_tldr_command(stripped_line)
                # Some heuristics to drop keyboard shortcuts and other oddities that aren't command lines.
                if command_str[0].isalpha() and (
                    len(command_str) >= 4 or command_str.startswith(command)
                ):
                    commands.append(
                        CommentedCommand(
                            comment=current_comment, command_line=command_str, uses=[command]
                        )
                    )
                current_comment = None

        return commands

    return []


def _write_tldr_snippets(commands: Iterable[str], file: TextIO) -> None:
    """
    Write TLDR snippets for a list of commands in the format of a script recipe.
    """
    for command in commands:
        snippets = tldr_snippets(command)
        print("\n", file=file)
        print(BareComment(text=command).script_str, file=file)
        for snippet in snippets:
            print("", file=file)
            print(snippet.script_str, file=file)


def dump_all_tldr_snippets(commands: list[str] = RECOMMENDED_TLDR_COMMANDS) -> None:
    """
    Dump TLDR snippets for all commands in the input.
    """
    for command in commands:
        if not is_valid_command(command):
            log.warning("Including command not in a local path: %s", command)
            continue

    with atomic_output_file(RECIPES_DIR / "tldr_standard_commands.ksh") as tmp:
        with open(tmp, "w") as f:
            print("# -- Generated by dump_tldr_snippets --", file=f)
            _write_tldr_snippets(commands, f)

    log.message(
        "Dumped %s TLDR snippets: %s", len(commands), RECIPES_DIR / "tldr_standard_commands.ksh"
    )
