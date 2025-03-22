from kash.config.api_keys import print_api_key_setup, warn_if_missing_api_keys
from kash.config.logger import get_logger
from kash.docs.all_docs import all_docs
from kash.exec import kash_command
from kash.help.tldr_help import tldr_refresh_cache
from kash.shell.output.shell_output import PrintHooks, cprint, format_name_and_value, print_h2
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
