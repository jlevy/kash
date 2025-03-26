from flowmark import Wrap
from rich.text import Text

from kash.config.api_keys import Api
from kash.config.dotenv_utils import env_var_is_set
from kash.config.text_styles import format_success_emoji
from kash.exec.command_registry import kash_command
from kash.llm_utils import LLM
from kash.shell.output.shell_output import (
    cprint,
    format_failure,
    format_name_and_value,
    format_success,
    format_success_or_failure,
    print_h2,
)


@kash_command
def list_models() -> None:
    """
    List and check API configuration for all models.
    """
    print_h2("Models")
    for model in LLM.all_names():
        api = Api.for_model(model)
        have_key = bool(api and env_var_is_set(api.env_var))
        if api:
            provider_msg = format_success(f"provider {api.name}")
            key_message = format_success_or_failure(have_key, f"{api.env_var}")
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
    for api in Api:
        emoji = format_success_emoji(env_var_is_set(api.env_var))
        message = (
            f"API key {api.env_var} found"
            if env_var_is_set(api.env_var)
            else f"API key {api.env_var} not found"
        )
        cprint(Text.assemble(emoji, format_name_and_value(api.name, message)))
