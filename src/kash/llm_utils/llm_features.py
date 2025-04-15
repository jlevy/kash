from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from prettyfmt import custom_key_sort

from kash.llm_utils.llm_names import LLMName
from kash.llm_utils.llms import LLM

Speed: TypeAlias = Literal["fast", "medium", "slow"]

ContextSize: TypeAlias = Literal["small", "medium", "large"]

ModelSize: TypeAlias = Literal["small", "medium", "large"]


@dataclass(frozen=True)
class LLMFeatures:
    speed: Speed | None = None
    context_size: ContextSize | None = None
    model_size: ModelSize | None = None
    structured_output: bool | None = None
    thinking: bool = False

    def satisfies(self, features: LLMFeatures) -> bool:
        return all(
            getattr(self, attr) == getattr(features, attr)
            for attr in features.__dataclass_fields__
            if getattr(self, attr) is not None
        )


def pick_llm(desired_features: LLMFeatures) -> LLMName:
    """
    Pick the preferred model that satisfies the desired features.
    """
    satisfied_models: list[LLMName] = [
        llm for llm, features in FEATURES.items() if features.satisfies(desired_features)
    ]
    satisfied_models.sort(key=custom_key_sort(preferred_llms))
    if not satisfied_models:
        raise ValueError(f"No model found for features: {desired_features}")
    return satisfied_models[0]


FEATURES = {
    LLM.o3_mini: LLMFeatures(
        speed="fast",
        context_size="small",
        model_size="small",
        structured_output=True,
        thinking=True,
    ),
    # FIXME
}

preferred_llms: list[LLMName] = [
    LLM.o3_mini,
    LLM.o1_mini,
    LLM.o1,
    LLM.gpt_4o_mini,
    LLM.gpt_4o,
    LLM.gpt_4,
    LLM.claude_3_7_sonnet,
    LLM.claude_3_5_sonnet,
    LLM.claude_3_5_haiku,
]
