from __future__ import annotations

from enum import Enum

from kash.llm_utils.llm_names import LLMName


class LLM(LLMName, Enum):
    """
    Convenience names for common LLMs. This isn't exhaustive, but just common
    ones for autocomplete, docs, etc. Values are all LiteLLM names. See:
    https://github.com/BerriAI/litellm/blob/main/litellm/model_prices_and_context_window_backup.json
    """

    # https://platform.openai.com/docs/models
    o4_mini = LLMName("o4-mini")
    o3 = LLMName("o3")
    o3_mini = LLMName("o3-mini")
    o1 = LLMName("o1")
    o1_mini = LLMName("o1-mini")
    o1_pro = LLMName("o1-pro")
    o1_preview = LLMName("o1-preview")
    gpt_4_1 = LLMName("gpt-4.1")
    gpt_4o = LLMName("gpt-4o")
    gpt_4o_mini = LLMName("gpt-4o-mini")
    gpt_4 = LLMName("gpt-4")

    gpt_4_1_mini = LLMName("gpt-4.1-mini")
    gpt_4_1_nano = LLMName("gpt-4.1-nano")

    # https://docs.anthropic.com/en/docs/about-claude/models/all-models
    claude_4_opus = LLMName("claude-opus-4-20250514")
    claude_4_sonnet = LLMName("claude-sonnet-4-20250514")
    claude_3_7_sonnet = LLMName("claude-3-7-sonnet-latest")
    claude_3_5_haiku = LLMName("claude-3-5-haiku-latest")

    # https://ai.google.dev/gemini-api/docs/models
    gemini_2_5_pro_preview_06_05 = LLMName("gemini/gemini-2.5-pro-preview-06-05")
    gemini_2_5_pro_preview_05_06 = LLMName("gemini/gemini-2.5-pro-preview-05-06")
    gemini_2_5_pro_preview_03_25 = LLMName("gemini/gemini-2.5-pro-preview-03-25")
    gemini_2_5_flash_preview = LLMName("gemini-2.5-flash-preview-05-20")
    gemini_2_0_flash = LLMName("gemini/gemini-2_0-flash")
    gemini_2_0_flash_lite = LLMName("gemini/gemini-2.0-flash-lite")
    gemini_2_0_pro_exp_02_05 = LLMName("gemini/gemini-2.0-pro-exp-02-05")

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
