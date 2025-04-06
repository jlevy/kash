from pathlib import Path

from flowmark import Wrap
from prettyfmt import fmt_lines
from strif import abbrev_str

from kash.config.settings import get_system_config_dir, get_system_env_path
from kash.shell.clideps.dotenv_utils import (
    env_var_is_set,
    find_dotenv_paths,
    read_dotenv_file,
    update_env_file,
)
from kash.shell.input.input_prompts import input_confirm, input_simple_string
from kash.shell.output.shell_formatting import format_failure, format_success
from kash.shell.output.shell_output import (
    cprint,
    print_h2,
    print_status,
)


def interactive_dotenv_setup(
    api_keys: list[str],
    update: bool = False,
) -> None:
    """
    Interactively configure your .env file with the requested API key
    environment variables.

    :param all: Configure all known API keys (instead of just recommended ones).
    :param update: Update values even if they are already set.
    """

    if not update:
        api_keys = [key for key in api_keys if not env_var_is_set(key)]

    cprint()
    print_h2("Configuring .env file")
    if api_keys:
        cprint(format_failure(f"API keys needed: {', '.join(api_keys)}"))
        interactive_update_dotenv(api_keys)
    else:
        cprint(format_success("All requested API keys are set!"))


def interactive_update_dotenv(keys: list[str]) -> bool:
    """
    Interactively fill missing values in the active .env file.
    Returns True if the user made changes, False otherwise.
    """
    dotenv_paths = find_dotenv_paths(True, get_system_config_dir())
    dotenv_path = dotenv_paths[0] if dotenv_paths else get_system_env_path()

    if dotenv_paths:
        print_status(f"Found .env file you will update: {dotenv_path}")
        old_dotenv = read_dotenv_file(dotenv_path)
        if old_dotenv:
            cprint("Current values:")
            summary = fmt_lines(
                [f"{k} = {repr(abbrev_str(v or '', 12))}" for k, v in old_dotenv.items()]
            )
            cprint(f"File has {len(old_dotenv)} keys:\n{summary}", text_wrap=Wrap.NONE)
    else:
        print_status("No .env file found.")

    if input_confirm(
        "Do you want make updates to your .env file?",
        instruction="This will leave existing keys intact unless you choose to update them.",
        default=True,
    ):
        dotenv_path_str = input_simple_string("Path to the .env file: ", default=str(dotenv_path))
        if not dotenv_path_str:
            print_status("Config changes cancelled.")
            return False

        dotenv_path = Path(dotenv_path_str)

        cprint()
        cprint(
            "We will update the following keys from %s:\n%s",
            dotenv_path,
            fmt_lines(keys),
            text_wrap=Wrap.NONE,
        )
        cprint()
        cprint(
            "Enter values for each key, or press enter to skip changes for that key. Values need not be quoted."
        )

        updates = {}
        for key in keys:
            value = input_simple_string(
                f"Enter value for {key}:",
                instruction='Leave empty to skip, use "" for a true empty string.',
            )
            if value and value.strip():
                updates[key] = value
            else:
                cprint(f"Skipping {key}. Will not change this key.")

        # Actually save the collected variables to the .env file
        update_env_file(dotenv_path, updates, create_if_missing=True)
        cprint()
        cprint(format_success(f"{len(updates)} API keys saved to {dotenv_path}"))
        cprint()
        cprint(
            "You can always edit the .env file directly if you need to, or "
            "rerun `self_configure` to update your configs again."
        )
    else:
        print_status("Config changes cancelled.")
        return False

    return True
