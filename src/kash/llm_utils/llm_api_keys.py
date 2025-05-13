from __future__ import annotations

from clideps.env_vars.dotenv_utils import env_var_is_set
from clideps.env_vars.env_names import EnvName

from kash.llm_utils.init_litellm import init_litellm
from kash.llm_utils.llm_names import LLMName
from kash.llm_utils.llms import LLM


def api_for_model(model: LLMName) -> EnvName | None:
    """
    Get the API key name for a model or None if not found.
    """
    import litellm
    from litellm.litellm_core_utils.get_llm_provider_logic import get_llm_provider

    init_litellm()

    try:
        _model, custom_llm_provider, _dynamic_api_key, _api_base = get_llm_provider(model)
    except litellm.exceptions.BadRequestError:
        return None

    return EnvName.api_env_name(custom_llm_provider)


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
