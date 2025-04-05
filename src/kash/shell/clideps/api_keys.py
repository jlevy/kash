from __future__ import annotations

from enum import Enum
from logging import getLogger

from rich.text import Text

from kash.shell.clideps.dotenv_utils import env_var_is_set, load_dotenv_paths
from kash.shell.output.shell_formatting import format_success_or_failure
from kash.shell.output.shell_output import cprint
from kash.utils.common.atomic_var import AtomicVar

log = getLogger(__name__)


class ApiEnvKey(str, Enum):
    """
    Convenience names for common API env vars. Any other env key is allowed too.
    """

    OPENAI_API_KEY = "OPENAI_API_KEY"
    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
    GEMINI_API_KEY = "GEMINI_API_KEY"
    AZURE_API_KEY = "AZURE_API_KEY"
    XAI_API_KEY = "XAI_API_KEY"
    DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY"
    MISTRAL_API_KEY = "MISTRAL_API_KEY"
    PERPLEXITYAI_API_KEY = "PERPLEXITYAI_API_KEY"
    DEEPGRAM_API_KEY = "DEEPGRAM_API_KEY"
    GROQ_API_KEY = "GROQ_API_KEY"
    FIRECRAWL_API_KEY = "FIRECRAWL_API_KEY"
    EXA_API_KEY = "EXA_API_KEY"

    @classmethod
    def for_provider(cls, provider_name: str) -> ApiEnvKey | None:
        """
        Get the ApiKey for a provider name, if known.
        """
        return getattr(cls, provider_name.upper() + "_API_KEY", None)

    @property
    def provider_name(self) -> str:
        """
        Get the lowercase provider name for an API ("openai", "azure", etc.).
        This matches LiteLLM's provider names.
        """
        return self.value.removesuffix("_API_KEY").lower()


_log_api_setup_done = AtomicVar(False)


def warn_if_missing_api_keys(env_keys: list[str]) -> list[str]:
    missing_apis = [key for key in env_keys if not env_var_is_set(key)]
    if missing_apis:
        log.warning(
            "Missing recommended API keys (%s):\nCheck .env file or run `self_configure` to set them.",
            ", ".join(missing_apis),
        )

    return missing_apis


def print_api_key_setup(
    recommended_keys: list[str], all_keys: list[str] | None = None, once: bool = False
) -> None:
    if not all_keys:
        all_keys = [key.value for key in ApiEnvKey]
    if once and _log_api_setup_done:
        return

    dotenv_paths = load_dotenv_paths()

    cprint(
        Text.assemble(
            format_success_or_failure(
                value=bool(dotenv_paths),
                true_str=f"Found .env files: {', '.join(dotenv_paths)}",
                false_str="No .env files found. Set up your API keys in a .env file.",
            ),
        )
    )

    texts = [
        format_success_or_failure(env_var_is_set(key), ApiEnvKey(key).provider_name)
        for key in all_keys
    ]

    cprint(Text.assemble("API keys found: ", Text(" ").join(texts)))

    warn_if_missing_api_keys(recommended_keys)

    _log_api_setup_done.set(True)
