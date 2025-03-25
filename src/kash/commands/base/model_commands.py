from flowmark import Wrap
from rich.text import Text

from kash.config.api_keys import Api
from kash.config.dotenv_utils import env_var_is_set
from kash.config.text_styles import format_success_emoji
from kash.exec.command_registry import kash_command
from kash.llm_utils.language_models import LLM
from kash.shell.output.shell_output import cprint, print_h2


@kash_command
def list_models() -> None:
    """
    List all models.
    """
    print_h2("Models")
    for model in LLM.all_names():
        api = Api.for_model(model)
        have_key = bool(api and env_var_is_set(api.env_var))
        emoji = format_success_emoji(have_key)
        if api and have_key:
            message = f"found API key {api.env_var} for provider {api.name}"
        elif not api:
            message = "provider not recognized"
        else:
            message = f"API key {api.env_var} not found"
        cprint(
            Text.assemble(emoji, " ", f"`{model}`", ": ", message),
            text_wrap=Wrap.NONE,
        )


@kash_command
def list_apis() -> None:
    """
    List all APIs.
    """
    print_h2("API keys")
    for api in Api:
        emoji = format_success_emoji(env_var_is_set(api.env_var), success_only=True)
        message = (
            f"API key {api.env_var} found"
            if env_var_is_set(api.env_var)
            else f"API key {api.env_var} not found"
        )
        cprint(Text.assemble(emoji, " ", f"`{api.name}`", ": ", message), text_wrap=Wrap.NONE)
