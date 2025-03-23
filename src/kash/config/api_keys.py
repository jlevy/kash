import os
from enum import Enum

from dotenv import find_dotenv, load_dotenv
from rich.text import Text

from kash.shell.output.shell_output import cprint, format_success_or_failure
from kash.utils.common.atomic_var import AtomicVar


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


def api_setup() -> str:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)
    return dotenv_path


_log_api_setup_done = AtomicVar(False)


def warn_if_missing_api_keys(keys: list[Api] = RECOMMENDED_APIS) -> list[Api]:
    from kash.config.logger import get_logger

    log = get_logger(__name__)

    missing_keys = [api for api in keys if api.value not in os.environ]
    if missing_keys:
        log.warning(
            "Missing recommended API keys (check .env file or set them?): %s",
            ", ".join(missing_keys),
        )

    return missing_keys


def print_api_key_setup(once: bool = False) -> None:
    if once and _log_api_setup_done:
        return

    dotenv_path = api_setup()

    cprint(
        Text.assemble(
            format_success_or_failure(
                value=bool(dotenv_path),
                true_str=f"Found .env file: {dotenv_path}",
                false_str="No .env file found. Set up your API keys in a .env file.",
            ),
        )
    )

    # Heuristic to detect dummy or empty keys.
    def is_set(key: str) -> bool:
        value = os.environ.get(key, None)
        return bool(value and len(value.strip()) > 10 and "changeme" not in value)

    texts = [format_success_or_failure(is_set(api.value), api.name) for api in Api]

    cprint(Text.assemble("API keys found: ", Text(" ").join(texts)))

    warn_if_missing_api_keys()

    _log_api_setup_done.set(True)
