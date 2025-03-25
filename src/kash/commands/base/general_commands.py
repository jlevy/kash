from kash.config.api_keys import (
    RECOMMENDED_APIS,
    Api,
    find_load_dotenv,
    print_api_key_setup,
    warn_if_missing_api_keys,
)
from kash.config.dotenv_utils import env_var_is_set
from kash.config.logger import get_logger
from kash.docs.all_docs import all_docs
from kash.errors import InvalidState
from kash.exec import kash_command
from kash.help.tldr_help import tldr_refresh_cache
from kash.shell.input.collect_dotenv import fill_missing_dotenv
from kash.shell.output.shell_output import (
    PrintHooks,
    cprint,
    format_name_and_value,
    format_success_or_failure,
    print_h2,
)
from kash.shell.utils.sys_tool_deps import sys_tool_check, terminal_feature_check

log = get_logger(__name__)


@kash_command
def version() -> None:
    """
    Show the version of kash.
    """
    from kash.shell_main import APP_VERSION

    cprint(APP_VERSION)


@kash_command
def self_check(brief: bool = False) -> None:
    """
    Self-check kash setup, including termal settings, tools, and API keys.
    """
    if brief:
        terminal_feature_check().print_term_info()
        print_api_key_setup(once=False)
        check_tools(brief=brief)
        tldr_refresh_cache()
        try:
            all_docs.load()
        except Exception as e:
            log.error("Could not index docs: %s", e)
            cprint("See `logs` for details.")
            log.info("Exception details", exc_info=True)
    else:
        version()
        cprint()
        terminal_feature_check().print_term_info()
        cprint()
        print_api_key_setup(once=False)
        cprint()
        check_tools(brief=brief)
        cprint()
        if tldr_refresh_cache():
            cprint("Updated tldr cache")
        else:
            cprint("tldr cache is up to date")
        try:
            all_docs.load()
        except Exception as e:
            log.error("Could not index docs: %s", e)
            cprint("See `logs` for details.")
            log.info("Exception details", exc_info=True)


@kash_command
def self_configure(all: bool = False, update: bool = True) -> None:
    """
    Interactively configure your .env file with recommended API keys.

    :param all: Configure all known API keys (instead of just recommended ones).
    :param update: Update values even if they are already set.
    """
    if all:
        needed_keys = [api.value for api in Api]
    else:
        needed_keys = [api.value for api in RECOMMENDED_APIS]
    if update:
        keys_to_update = needed_keys
    else:
        keys_to_update = [key for key in needed_keys if not env_var_is_set(key)]

    cprint(
        format_success_or_failure(
            len(keys_to_update) == 0,
            f"All requested API keys are set! Found: {', '.join(needed_keys)}",
            f"Need to update API keys: {', '.join(keys_to_update)}",
        )
    )
    if keys_to_update:
        fill_missing_dotenv(keys_to_update)
        reload_env()


@kash_command
def check_tools(warn_only: bool = False, brief: bool = False) -> None:
    """
    Check that all tools are installed.

    :param warn_only: Only warn if tools are missing.
    :param brief: Print summary as a single line.
    """
    if warn_only:
        sys_tool_check().warn_if_missing()
    else:
        if brief:
            cprint(sys_tool_check().status())
        else:
            cprint("Checking for required tools:")
            cprint()
            cprint(sys_tool_check().formatted())
            cprint()
            sys_tool_check().warn_if_missing()


@kash_command
def check_api_keys(warn_only: bool = False) -> None:
    """
    Check that all recommended API keys are set.
    """

    if warn_only:
        warn_if_missing_api_keys()
    else:
        print_api_key_setup()


@kash_command
def reload_env() -> None:
    """
    Reload the environment variables from the .env file.
    """

    env_paths = find_load_dotenv()
    if env_paths:
        cprint("Reloaded environment variables")
        print_api_key_setup()
    else:
        raise InvalidState("No .env file found")


@kash_command
def kits() -> None:
    """
    List all kits (modules within `kash.kits`).
    """
    from kash.actions import get_loaded_kits

    if not get_loaded_kits():
        cprint(
            "No kits currently imported (be sure the Python environment has `kash.kits` modules in the load path)"
        )
    else:
        cprint("Currently imported kits:")
        for kit in get_loaded_kits().values():
            cprint(format_name_and_value(f"{kit.name} kit", str(kit.path or "")))


@kash_command
def settings() -> None:
    """
    Show all global kash settings.
    """
    from kash.config.settings import global_settings

    settings = global_settings()
    print_h2("Global Settings")
    for field, value in settings.__dict__.items():
        cprint(format_name_and_value(field, str(value)))
    PrintHooks.spacer()
