from __future__ import annotations

from enum import Enum

from kash.llm_utils.llm_names import LLMName


class LLM(LLMName, Enum):
    """
    Convenience names for common LLMs. This isn't exhaustive, but just common
    ones for autocomplete, docs, etc. Values are all LiteLLM names. See:
    https://github.com/BerriAI/litellm/blob/main/litellm/model_prices_and_context_window_backup.json
    """

    # https://developers.openai.com/api/docs/guides/latest-model
    gpt_5_6_sol = LLMName("gpt-5.6-sol")
    gpt_5_6_terra = LLMName("gpt-5.6-terra")
    gpt_5_6_luna = LLMName("gpt-5.6-luna")

    # https://platform.claude.com/docs/en/about-claude/models/overview
    claude_fable_5 = LLMName("claude-fable-5")
    claude_opus_4_8 = LLMName("claude-opus-4-8")
    claude_sonnet_5 = LLMName("claude-sonnet-5")
    claude_haiku_4_5 = LLMName("claude-haiku-4-5-20251001")

    # https://ai.google.dev/gemini-api/docs/models
    gemini_2_5_pro = LLMName("gemini/gemini-2.5-pro")
    gemini_2_5_flash = LLMName("gemini/gemini-2.5-flash")
    gemini_2_5_flash_lite = LLMName("gemini/gemini-2.5-flash-lite")

    # https://docs.x.ai/docs/models
    xai_grok_3 = LLMName("xai/grok-3")
    xai_grok_3_fast = LLMName("xai/grok-3-fast")
    xai_grok_3_mini = LLMName("xai/grok-3-mini")
    xai_grok_3_mini_fast = LLMName("xai/grok-3-mini-fast")
    xai_grok_2 = LLMName("xai/grok-2")

    # https://api-docs.deepseek.com/quick_start/pricing
    deepseek_chat = LLMName("deepseek/deepseek-chat")
    deepseek_coder = LLMName("deepseek/deepseek-coder")
    deepseek_reasoner = LLMName("deepseek/deepseek-reasoner")

    # https://console.groq.com/docs/models
    groq_gemma2_9b_it = LLMName("groq/gemma2-9b-it")
    groq_llama_3_1_8b_instant = LLMName("groq/llama-3.1-8b-instant")
    groq_llama_3_3_70b_versatile = LLMName("groq/llama-3.3-70b-versatile")
    groq_deepseek_r1_distill_llama_70b = LLMName("groq/deepseek-r1-distill-llama-70b")
    groq_deepseek_r1_distill_qwen_32b = LLMName("groq/deepseek-r1-distill-qwen-32b")

    # https://docs.perplexity.ai/guides/model-cards
    sonar = LLMName("perplexity/sonar")
    sonar_pro = LLMName("perplexity/sonar-pro")

    # https://docs.mistral.ai/getting-started/models/models_overview/
    mistral_small = LLMName("mistral/mistral-small-latest")
    mistral_large = LLMName("mistral/mistral-large-latest")
    mistral_codestral = LLMName("mistral/mistral-codestral-latest")

    # Allows use of "default_standard" etc as model names and have the
    # model be looked up from workspace parameter settings.
    default_standard = LLMName("default_standard")
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
