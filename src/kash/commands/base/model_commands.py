from flowmark import Wrap

from kash.config.api_keys import Api
from kash.config.dotenv_utils import env_var_is_set
from kash.config.text_styles import EMOJI_TRUE
from kash.exec.command_registry import kash_command
from kash.llm_utils.language_models import LLM
from kash.shell.output.shell_output import cprint


@kash_command
def list_models() -> None:
    """
    List all models.
    """
    for model in LLM.all_names():
        api = Api.for_model(model)
        have_key = api and env_var_is_set(api.env_var)
        emoji = EMOJI_TRUE if have_key else " "
        if api and have_key:
            message = f"found API key {api.env_var} for provider {api.name}"
        elif not api:
            message = "provider not recognized"
        else:
            message = f"API key {api.env_var} not found"
        cprint(
            f"{emoji} `{model}`: {message}",
            text_wrap=Wrap.NONE,
        )


@kash_command
def list_apis() -> None:
    """
    List all APIs.
    """
    for api in Api:
        emoji = EMOJI_TRUE if env_var_is_set(api.env_var) else " "
        message = (
            f"API key {api.env_var} found"
            if env_var_is_set(api.env_var)
            else f"API key {api.env_var} not found"
        )
        cprint(f"{emoji} `{api.name}`: {message}")
