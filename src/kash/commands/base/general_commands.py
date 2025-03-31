from kash.commands.base.model_commands import list_apis, list_models
from kash.commands.workspace.workspace_commands import list_params
from kash.config.api_keys import (
    RECOMMENDED_APIS,
    Api,
    get_all_configured_models,
    load_dotenv_paths,
    print_api_key_setup,
)
from kash.config.dotenv_utils import env_var_is_set
from kash.config.logger import get_logger
from kash.docs.all_docs import all_docs
from kash.exec import kash_command
from kash.help.tldr_help import tldr_refresh_cache
from kash.model.params_model import (
    DEFAULT_CAREFUL_LLM,
    DEFAULT_FAST_LLM,
    DEFAULT_STANDARD_LLM,
    DEFAULT_STRUCTURED_LLM,
)
from kash.shell.input.collect_dotenv import fill_missing_dotenv
from kash.shell.input.input_prompts import input_choice
from kash.shell.output.shell_output import (
    PrintHooks,
    cprint,
    format_failure,
    format_name_and_value,
    format_success,
    print_h2,
)
from kash.shell.utils.sys_tool_deps import sys_tool_check, terminal_feature_check
from kash.shell.version import get_full_version_name
from kash.utils.errors import InvalidState
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


@kash_command
def version() -> None:
    """
    Show the version of kash.
    """
    cprint(get_full_version_name())


@kash_command
def self_check(brief: bool = False) -> None:
    """
    Self-check kash setup, including termal settings, tools, and API keys.
    """
    if brief:
        terminal_feature_check().print_term_info()
        print_api_key_setup(once=False)
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
        terminal_feature_check().print_term_info()
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
    Interactively configure your .env file with recommended API keys.

    :param all: Configure all known API keys (instead of just recommended ones).
    :param update: Update values even if they are already set.
    """

    # Show APIs before starting.
    list_apis()

    apis = Api if all else RECOMMENDED_APIS
    keys = [api.value for api in apis]
    if not update:
        keys = [key for key in keys if not env_var_is_set(key)]

    cprint()
    print_h2("Configuring .env file")
    if keys:
        cprint(format_failure(f"API keys needed: {', '.join(keys)}"))
        fill_missing_dotenv(keys)
        reload_env()
    else:
        cprint(format_success("All requested API keys are set!"))

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

    :param warn_only: Only warn if tools are missing.
    :param brief: Print summary as a single line.
    """
    if warn_only:
        sys_tool_check().warn_if_missing()
    else:
        if brief:
            cprint(sys_tool_check().status())
        else:
            print_h2("Installed System Tools")
            cprint(sys_tool_check().formatted())
            cprint()
            sys_tool_check().warn_if_missing()


@kash_command
def reload_env() -> None:
    """
    Reload the environment variables from the .env file.
    """

    env_paths = load_dotenv_paths()
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
