from __future__ import annotations

import litellm
from litellm.litellm_core_utils.get_llm_provider_logic import get_llm_provider

from kash.llm_utils.llm_names import LLMName
from kash.llm_utils.llms import LLM
from kash.shell.clideps.api_keys import ApiEnvKey
from kash.shell.clideps.dotenv_utils import env_var_is_set


def api_for_model(model: LLMName) -> ApiEnvKey | None:
    """
    Get the API key name for a model or None if not found.
    """
    try:
        _model, custom_llm_provider, _dynamic_api_key, _api_base = get_llm_provider(model)
    except litellm.exceptions.BadRequestError:
        return None

    return ApiEnvKey.for_provider(custom_llm_provider)


def have_key_for_model(model: LLMName) -> bool:
    """
    Do we have an API key for this model?
    """
    try:
        api = api_for_model(model)
        return bool(api and env_var_is_set(api))
    except ValueError:
        return False


def get_all_configured_models() -> list[LLMName]:
    """
    Get all models that have an API key.
    """
    return [model for model in LLM if have_key_for_model(model)]
