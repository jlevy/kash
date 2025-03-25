from pathlib import Path
from shutil import copyfile

from dotenv.main import rewrite, with_warn_for_invalid_lines
from dotenv.parser import parse_stream

from kash.config.dotenv_utils import find_load_dotenv
from kash.shell.input.input_prompts import input_confirm, input_simple_string
from kash.shell.output.shell_output import cprint, print_status


def fill_missing_dotenv(keys_to_update: list[str]):
    """
    Interactively fill missing values in the active .env file.
    """
    dotenv_paths = find_load_dotenv()
    dotenv_path = dotenv_paths[0] if dotenv_paths else Path("~/.env").expanduser()

    if dotenv_paths:
        cprint(f"Found .env file: {dotenv_path}")
    else:
        cprint("No .env file found.")

    if input_confirm("Do you want to update your .env file?", default=True):
        dotenv_path_str = input_simple_string(
            "Path to the .env file to use: ", default=str(dotenv_path)
        )
        if not dotenv_path_str:
            print_status("Config changes cancelled.")
            raise KeyboardInterrupt()

        dotenv_path = Path(dotenv_path_str)

        cprint(
            "Enter values for each key, or press enter to leave unset for now. Values need not be quoted."
        )
        updates = {}
        for key in keys_to_update:
            cprint()
            value = input_simple_string(
                f"Enter value for {key}:",
                instruction='Leave empty to skip, use "" for a true empty string.',
            )
            if value and value.strip():
                updates[key] = value
            else:
                cprint(f"Skipping {key}.")

        # Actually save the collected variables to the .env file
        update_env_file(dotenv_path, updates, create_if_missing=True, keep_backup=True)
        print(f"API keys saved to {dotenv_path}")
    else:
        print_status("Config changes cancelled.")
        raise KeyboardInterrupt()


def update_env_file(
    dotenv_path: Path,
    updates: dict[str, str],
    create_if_missing: bool = False,
    keep_backup: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Updates values in a .env file (safely). Similar to what dotenv offers but allows multiple
    updates at once and keeps a backup. Values may be quoted or unquoted.
    """
    if not create_if_missing and not dotenv_path.exists():
        raise FileNotFoundError(f".env file does not exist: {dotenv_path}")

    # Create the .env file directory if it doesn't exist
    if create_if_missing and not dotenv_path.parent.exists():
        dotenv_path.parent.mkdir(parents=True, exist_ok=True)

    def format_line(key: str, value: str) -> str:
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            return f"{key}={value}"
        else:
            return f"{key}=" + '"' + value.replace('"', '\\"') + '"'

    if keep_backup and dotenv_path.exists():
        copyfile(dotenv_path, dotenv_path.with_suffix(".env.bak"))

    changed = []
    added = []
    with rewrite(dotenv_path, encoding="utf-8") as (source, dest):
        for mapping in with_warn_for_invalid_lines(parse_stream(source)):
            if mapping.key in updates:
                dest.write(format_line(mapping.key, updates[mapping.key]))
                dest.write("\n")
                changed.append(mapping.key)
            else:
                dest.write(mapping.original.string.rstrip("\n"))
                dest.write("\n")
        for key in set(updates.keys()) - set(changed):
            dest.write(format_line(key, updates[key]))
            dest.write("\n")
            added.append(key)

    return changed, added
