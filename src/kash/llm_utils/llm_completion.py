import time
from typing import cast

import litellm
from flowmark import Wrap, fill_text
from funlog import format_duration, log_calls
from litellm.types.utils import Choices, ModelResponse
from litellm.types.utils import Message as LiteLLMMessage
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from slugify import slugify

from kash.config.logger import get_logger
from kash.config.text_styles import EMOJI_TIMING
from kash.llm_utils.fuzzy_parsing import is_no_results
from kash.llm_utils.llm_messages import Message, MessageTemplate
from kash.llm_utils.llm_names import LLMName
from kash.utils.common.url import Url, is_url
from kash.utils.errors import ApiResultError
from kash.utils.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole

log = get_logger(__name__)


@dataclass(frozen=True)
class CitationList:
    citations: list[str]

    def as_markdown_footnotes(self) -> str:
        footnotes = []
        for i, citation in enumerate(self.citations, 1):
            footnotes.append(
                f"[^{i}]: {fill_text(citation, text_wrap=Wrap.MARKDOWN_ITEM, initial_column=8)}"
            )
        return "\n\n".join(footnotes)

    @property
    def url_citations(self) -> list[Url]:
        return [Url(citation) for citation in self.citations if is_url(citation)]

    @property
    def non_url_citations(self) -> list[str]:
        return [citation for citation in self.citations if not is_url(citation)]


@dataclass
class LLMCompletionResult:
    message: LiteLLMMessage
    content: str
    citations: CitationList | None

    @property
    def content_with_citations(self) -> str:
        content = self.content
        if self.citations:
            content = content + "\n\n" + self.citations.as_markdown_footnotes()
        return content


@log_calls(level="info")
def llm_completion(
    model: LLMName,
    messages: list[dict[str, str]],
    save_objects: bool = True,
    response_format: dict | type[BaseModel] | None = None,
    **kwargs,
) -> LLMCompletionResult:
    """
    Perform an LLM completion with LiteLLM.
    """

    chat_history = ChatHistory.from_dicts(messages)
    log.info(
        "Calling LLM completion from %s on %s, response_format=%s",
        model.litellm_name,
        chat_history.size_summary(),
        response_format,
    )

    start_time = time.time()
    llm_output = cast(
        ModelResponse,
        litellm.completion(
            model.litellm_name,
            messages=messages,
            response_format=response_format,
            **kwargs,
        ),  # pyright: ignore
    )
    elapsed = time.time() - start_time

    choices = cast(Choices, llm_output.choices[0])

    message = choices.message

    # Just sanity checking and logging.
    content = choices.message.content
    if not content or not isinstance(content, str):
        raise ApiResultError(f"LLM completion failed: {model.litellm_name}: {llm_output}")

    total_input_len = sum(len(m["content"]) for m in messages)
    speed = len(content) / elapsed
    log.message(
        f"{EMOJI_TIMING} LLM completion from {model.litellm_name} in {format_duration(elapsed)}: "
        f"input {total_input_len} chars in {len(messages)} messages, output {len(content)} chars "
        f"({speed:.0f} char/s)"
    )

    citations = llm_output.get("citations", None)

    if save_objects:
        metadata = {"citations": citations} if citations else {}
        chat_history.messages.append(
            ChatMessage(role=ChatRole.assistant, content=content, metadata=metadata)
        )
        model_slug = slugify(model.litellm_name, separator="_")
        log.save_object(
            "LLM response",
            f"llm.{model_slug}",
            chat_history.to_yaml(),
            file_ext="yml",
        )

    return LLMCompletionResult(
        message=message,
        content=content,
        citations=CitationList(citations=citations) if citations else None,
    )


def llm_template_completion(
    model: LLMName,
    system_message: Message,
    input: str,
    body_template: MessageTemplate | None = None,
    previous_messages: list[dict[str, str]] | None = None,
    save_objects: bool = True,
    check_no_results: bool = True,
    response_format: dict | type[BaseModel] | None = None,
    **kwargs,
) -> LLMCompletionResult:
    """
    Perform an LLM completion. Input is inserted into the template with a `body` parameter.
    Use this function to interact with the LLMs for consistent logging.
    """
    if not system_message:
        raise ValueError("system_message is required")
    if not body_template:
        body_template = MessageTemplate("{body}")

    user_message = body_template.format(body=input)

    if not previous_messages:
        previous_messages = []

    result = llm_completion(
        model,
        messages=[
            {"role": "system", "content": str(system_message)},
            *previous_messages,
            {"role": "user", "content": user_message},
        ],
        save_objects=save_objects,
        response_format=response_format,
        **kwargs,
    )

    if check_no_results and is_no_results(result.content):
        log.message("No results for LLM transform, will ignore: %r", result.content)
        result.content = ""

    return result
