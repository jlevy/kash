from enum import Enum
from logging import getLogger

from rich.text import Text

from kash.config.dotenv_utils import env_var_is_set, find_load_dotenv
from kash.shell.output.shell_output import cprint, format_success_or_failure
from kash.utils.common.atomic_var import AtomicVar

log = getLogger(__name__)


class Api(str, Enum):
    openai = "OPENAI_API_KEY"
    anthropic = "ANTHROPIC_API_KEY"
    gemini = "GEMINI_API_KEY"
    xai = "XAI_API_KEY"
    deepseek = "DEEPSEEK_API_KEY"
    mistral = "MISTRAL_API_KEY"
    perplexityai = "PERPLEXITYAI_API_KEY"
    deepgram = "DEEPGRAM_API_KEY"
    groq = "GROQ_API_KEY"
    firecrawl = "FIRECRAWL_API_KEY"
    exa = "EXA_API_KEY"


RECOMMENDED_APIS = [
    Api.openai,
    Api.anthropic,
    Api.deepgram,
    Api.groq,
]


_log_api_setup_done = AtomicVar(False)


def warn_if_missing_api_keys(keys: list[Api] = RECOMMENDED_APIS) -> list[Api]:
    missing_keys = [api for api in keys if not env_var_is_set(api.value)]
    if missing_keys:
        log.warning(
            "Missing recommended API keys (%s). Check .env file or run `self_configure` to set them.",
            ", ".join(missing_keys),
        )

    return missing_keys


def print_api_key_setup(once: bool = False) -> None:
    if once and _log_api_setup_done:
        return

    dotenv_paths = find_load_dotenv()

    cprint(
        Text.assemble(
            format_success_or_failure(
                value=bool(dotenv_paths),
                true_str=f"Found .env files: {', '.join(dotenv_paths)}",
                false_str="No .env files found. Set up your API keys in a .env file.",
            ),
        )
    )

    texts = [format_success_or_failure(env_var_is_set(api.value), api.name) for api in Api]

    cprint(Text.assemble("API keys found: ", Text(" ").join(texts)))

    warn_if_missing_api_keys()

    _log_api_setup_done.set(True)
