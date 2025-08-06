from clideps.env_vars.dotenv_setup import interactive_dotenv_setup
from clideps.env_vars.dotenv_utils import load_dotenv_paths
from clideps.env_vars.env_check import format_dotenv_check, format_env_var_check, print_env_check
from clideps.env_vars.env_names import get_all_common_env_names
from clideps.pkgs.pkg_check import pkg_check
from clideps.terminal.terminal_features import terminal_check
from flowmark import Wrap
from rich.text import Text

from kash.commands.base.model_commands import list_apis, list_models
from kash.config.logger import get_logger
from kash.config.settings import RECOMMENDED_API_KEYS, global_settings
from kash.docs.all_docs import all_docs
from kash.exec import kash_command
from kash.help.tldr_help import tldr_refresh_cache
from kash.llm_utils.llm_api_keys import get_all_configured_models
from kash.model.params_model import (
    DEFAULT_CAREFUL_LLM,
    DEFAULT_FAST_LLM,
    DEFAULT_STANDARD_LLM,
    DEFAULT_STRUCTURED_LLM,
)
from kash.shell.input.input_prompts import input_choice
from kash.shell.output.shell_formatting import format_name_and_value
from kash.shell.output.shell_output import (
    PrintHooks,
    cprint,
    print_h2,
)
from kash.shell.version import get_full_version_name
from kash.utils.errors import InvalidState
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


@kash_command
def version() -> None:
    """
    Show the version of kash.
    """
    cprint(get_full_version_name(with_kits=True))


@kash_command
def self_check(brief: bool = False) -> None:
    """
    Self-check kash setup, including termal settings, tools, and API keys.
    """
    if brief:
        cprint(terminal_check().formatted())
        cprint(Text.assemble("Dotenv files: ", format_dotenv_check()))
        cprint(
            Text.assemble(
                "Env vars: ", format_env_var_check(env_vars=RECOMMENDED_API_KEYS, one_line=True)
            )
        )
        check_system_tools(brief=brief)
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
        cprint(terminal_check().formatted())
        cprint()
        list_apis()
        cprint()
        list_models()
        cprint()
        check_system_tools(brief=brief)
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
def self_configure(all: bool = False, update: bool = False) -> None:
    """
    Interactively configure API keys and preferred models.
    """
    from kash.commands.workspace.workspace_commands import params as list_params

    if all:
        api_keys = list(set(get_all_common_env_names() + RECOMMENDED_API_KEYS))
    else:
        api_keys = RECOMMENDED_API_KEYS
    # Show APIs before starting.
    list_apis()

    interactive_dotenv_setup(api_keys, update=update)
    reload_env()

    cprint()
    ws = current_ws()
    print_h2(f"Configuring workspace parameters ({ws.name})")
    avail_models = get_all_configured_models()
    avail_structured_models = [model for model in avail_models if model.supports_structured]

    if avail_models:
        cprint(
            "Available models with configured API keys: %s",
            ", ".join(f"`{model}`" for model in avail_models),
        )
        standard_llm = input_choice(
            "Select a standard model",
            choices=[str(model) for model in avail_models],
            default=DEFAULT_STANDARD_LLM,
        )
        careful_llm = input_choice(
            "Select a careful model",
            choices=[str(model) for model in avail_models],
            default=DEFAULT_CAREFUL_LLM,
        )
        fast_llm = input_choice(
            "Select a fast model",
            choices=[str(model) for model in avail_models],
            default=DEFAULT_FAST_LLM,
        )
        if avail_structured_models:
            structured_llm = input_choice(
                "Select a structured model",
                choices=[str(model) for model in avail_structured_models],
                default=DEFAULT_STRUCTURED_LLM,
            )
        else:
            log.error("No structured models available, so not setting default structured LLM.")
            structured_llm = None
        params = {
            "standard_llm": standard_llm,
            "careful_llm": careful_llm,
            "fast_llm": fast_llm,
        }
        if structured_llm:
            params["structured_llm"] = structured_llm
        ws.params.set(params)
    else:
        log.warning(
            "Hm, still didn't find any models with configured API keys. Check your .env file?"
        )

    cprint()
    list_params()


@kash_command
def check_system_tools(warn_only: bool = False, brief: bool = False) -> None:
    """
    Check that all tools are installed.

    Args:
        warn_only: Only warn if tools are missing.
        brief: Print summary as a single line.
    """
    if warn_only:
        pkg_check().warn_if_missing()
    else:
        if brief:
            cprint(pkg_check().status())
        else:
            print_h2("Installed System Tools")
            cprint(pkg_check().formatted())
            cprint()
            pkg_check().warn_if_missing()


@kash_command
def reload_env() -> None:
    """
    Reload the environment variables from the .env file.
    """

    env_paths = load_dotenv_paths(True, True, global_settings().system_config_dir)
    if env_paths:
        cprint("Reloaded environment variables")

        print_env_check(RECOMMENDED_API_KEYS)
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
            cprint(
                format_name_and_value(
                    f"{kit.distribution_name} kit", str(kit.path or ""), text_wrap=Wrap.NONE
                )
            )


@kash_command
def settings() -> None:
    """
    Show all global kash settings.
    """
    from kash.config.settings import global_settings

    settings = global_settings()
    print_h2("Global Settings")
    for field, value in settings.__dict__.items():
        cprint(format_name_and_value(field, str(value), text_wrap=Wrap.NONE))
    PrintHooks.spacer()
