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
        from kash.llm_utils import LLM

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
