from __future__ import annotations

from enum import Enum

from pydantic import ValidationInfo

from kash.utils.common.type_utils import not_none


class LLMName(str):
    """
    Name of an LLM, as a subclass of str for convenience. Also lets you
    resolve names like "default_careful" to the actual LLM name and accepts
    names from the LLM enum too.

    We are using LiteLLM for model names.
    For the current list of models see:
    https://docs.litellm.ai/docs/providers
    """

    # Pydantic support.
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str, _info: ValidationInfo) -> LLMName:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                # First try LLM enum names.
                return cls(LLM[value].value)
            except KeyError:
                # Otherwise this is the name.
                return cls(value)
        raise ValueError(f"Invalid LLM name: {value!r}")

    @property
    def litellm_name(self) -> str:
        """
        Get the LiteLLM name, resolving any `default_*` names to the actual name.
        """
        if self.startswith("default_"):
            llm_default = LLMDefault(self.removeprefix("default_"))
            name = llm_default.workspace_llm
        else:
            name = self

        # Shouldn't be necessary but just in case (e.g. an underscore name was saved),
        # use hyphens only, not Python enum names.
        return name.replace("_", "-")


class LLMDefault(Enum):
    """
    It's nice to have some "default types" of LLMs, so actions can default to a given
    type and the user can have a preference as a parameter in their workspace.
    """

    careful = "careful"
    structured = "structured"
    standard = "standard"
    fast = "fast"

    @property
    def param_name(self) -> str:
        if self == LLMDefault.careful:
            return "careful_llm"
        elif self == LLMDefault.structured:
            return "structured_llm"
        elif self == LLMDefault.standard:
            return "standard_llm"
        elif self == LLMDefault.fast:
            return "fast_llm"
        else:
            raise ValueError(f"Invalid assistance type: {self}")

    @property
    def workspace_llm(self) -> LLMName:
        from kash.workspaces.workspaces import ws_param_value

        return not_none(ws_param_value(self.param_name, type=LLMName))

    @property
    def is_structured(self) -> bool:
        return self == LLMDefault.structured

    def __str__(self):
        return f"LLMDefault.{self.value}"


class LLM(LLMName, Enum):
    """
    Convenience names for common LLMs. This isn't exhaustive, but just common
    ones for autocomplete, docs, etc. Values are all LiteLLM names.
    """

    # https://platform.openai.com/docs/models
    o3_mini = LLMName("o3-mini")
    o1_mini = LLMName("o1-mini")
    o1_preview = LLMName("o1-preview")
    gpt_4o_mini = LLMName("gpt-4o-mini")
    gpt_4o = LLMName("gpt-4o")
    gpt_4 = LLMName("gpt-4")
    gpt_3_5_turbo = LLMName("gpt-3.5-turbo")

    # https://docs.anthropic.com/en/docs/about-claude/models/all-models
    claude_3_7_sonnet = LLMName("claude-3-7-sonnet-latest")
    claude_3_5_sonnet = LLMName("claude-3-5-sonnet-latest")
    claude_3_5_haiku = LLMName("claude-3-5-haiku-latest")

    # https://ai.google.dev/gemini-api/docs/models
    gemini_2_0_flash = LLMName("gemini/gemini-2_0-flash")
    gemini_2_0_pro_exp_02_05 = LLMName("gemini/gemini-2.0-pro-exp-02-05")
    gemini_1_5_flash = LLMName("gemini/gemini-1.5-flash")
    gemini_1_5_flash_8b = LLMName("gemini/gemini-1.5-flash-8b")

    # https://docs.x.ai/docs/models
    xai_grok_2 = LLMName("xai/grok-2-latest")

    # https://docs.mistral.ai/getting-started/models/models_overview/
    mistral_small = LLMName("mistral/mistral-small-latest")
    mistral_large = LLMName("mistral/mistral-large-latest")
    mistral_codestral = LLMName("mistral/mistral-codestral-latest")

    # https://docs.perplexity.ai/guides/model-cards
    sonar = LLMName("perplexity/sonar")
    sonar_pro = LLMName("perplexity/sonar-pro")

    # https://api-docs.deepseek.com/quick_start/pricing
    deepseek_chat = LLMName("deepseek/deepseek-chat")
    deepseek_coder = LLMName("deepseek/deepseek-coder")
    deepseek_reasoner = LLMName("deepseek/deepseek-reasoner")

    # https://console.groq.com/docs/models
    groq_llama_3_3_7b_versatile = LLMName("groq/llama-3.3-70b-versatile")
    groq_llama_3_1_8b_instant = LLMName("groq/llama-3.1-8b-instant")
    groq_llama_3_1_70b_versatile = LLMName("groq/llama-3.1-70b-versatile")
    groq_llama_3_1_405b_reasoning = LLMName("groq/llama-3.1-405b-reasoning")
    groq_llama3_8b_8192 = LLMName("groq/llama3-8b-8192")
    groq_llama3_70b_8192 = LLMName("groq/llama3-70b-8192")
    groq_deepseek_r1_distill_llama_70b = LLMName("groq/deepseek-r1-distill-llama-70b")
    groq_deepseek_r1_distill_qwen_32b = LLMName("groq/deepseek-r1-distill-qwen-32b")

    # Allows use of "default_basic" etc as model names and have the
    # model be looked up from workspace parameter settings.
    default_basic = LLMName("default_basic")
    default_structured = LLMName("default_structured")
    default_careful = LLMName("default_careful")
    default_fast = LLMName("default_fast")

    @classmethod
    def all_names(cls) -> list[LLMName]:
        return [value for name, value in cls.__members__.items() if not name.startswith("default_")]

    def __str__(self):
        return f"{self.value}"


class EmbeddingModel(Enum):
    """
    LiteLLM embedding models.

    For current list of models see: https://docs.litellm.ai/docs/embedding/supported_embedding
    """

    text_embedding_3_large = "text-embedding-3-large"
    text_embedding_3_small = "text-embedding-3-small"

    @property
    def litellm_name(self) -> str:
        return self.value

    def __str__(self):
        return self.value


DEFAULT_EMBEDDING_MODEL = EmbeddingModel.text_embedding_3_large
