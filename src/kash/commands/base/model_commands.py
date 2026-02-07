from __future__ import annotations

from clideps.env_vars.dotenv_utils import env_var_is_set
from flowmark import Wrap
from rich.text import Text

from kash.config.settings import get_all_common_api_env_vars
from kash.exec.command_registry import kash_command
from kash.llm_utils import LLM, api_for_model
from kash.shell.output.shell_formatting import (
    format_failure,
    format_name_and_value,
    format_success,
    format_success_emoji,
    format_success_or_failure,
)
from kash.shell.output.shell_output import (
    cprint,
    print_h2,
)


@kash_command
def list_models() -> None:
    """
    List and check API configuration for all models.
    """
    print_h2("Models")
    for model in LLM.all_names():
        api = api_for_model(model)
        have_key = bool(api and env_var_is_set(api.value))
        if api:
            provider_msg = format_success(f"provider {api.name}")
            key_message = format_success_or_failure(have_key, f"{api.value}")
        else:
            provider_msg = format_failure("provider not recognized")
            key_message = format_failure("unknown API key")

        message = Text.assemble(provider_msg, ", ", key_message, ", ", model.features_str)

        cprint(
            format_name_and_value(f"`{model}`", message, text_wrap=Wrap.NONE),
            text_wrap=Wrap.NONE,
        )


@kash_command
def list_apis() -> None:
    """
    List and check configuration for all APIs.
    """
    print_h2("API keys")
    for env_var in get_all_common_api_env_vars():
        emoji = format_success_emoji(env_var_is_set(env_var))
        message = (
            f"API key {env_var} found"
            if env_var_is_set(env_var)
            else f"API key {env_var} not found"
        )
        cprint(Text.assemble(emoji, format_name_and_value(env_var, message)))
