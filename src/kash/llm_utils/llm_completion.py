from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from flowmark import Wrap, fill_text
from funlog import format_duration, log_calls
from prettyfmt import slugify_snake
from pydantic import BaseModel

from kash.config.logger import get_logger
from kash.config.text_styles import EMOJI_TIMING
from kash.llm_utils.fuzzy_parsing import is_no_results
from kash.llm_utils.init_litellm import init_litellm
from kash.llm_utils.llm_messages import Message, MessageTemplate
from kash.llm_utils.llm_names import LLMName
from kash.utils.common.url import Url, is_url
from kash.utils.errors import ApiResultError
from kash.utils.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole

if TYPE_CHECKING:
    from litellm.types.utils import Message as LiteLLMMessage

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
    tool_calls: list[dict[str, Any]] | None = None

    @property
    def content_with_citations(self) -> str:
        content = self.content
        if self.citations:
            content = content + "\n\n" + self.citations.as_markdown_footnotes()
        return content

    @property
    def has_tool_calls(self) -> bool:
        """Check if the response contains tool calls."""
        return bool(self.tool_calls)

    @property
    def tool_call_names(self) -> list[str]:
        """Get list of tool names that were called."""
        if not self.tool_calls:
            return []
        names = []
        for call in self.tool_calls:
            # Handle both LiteLLM objects and dict representations
            if hasattr(call, "function") and hasattr(getattr(call, "function", None), "name"):
                # LiteLLM object format
                names.append(f"{call.function.name}()")  # pyright: ignore[reportAttributeAccessIssue]
            elif isinstance(call, dict) and call.get("function", {}).get("name"):
                # Dict format
                names.append(f"{call['function']['name']}()")
            else:
                names.append(str(call))
        return names


@log_calls(level="info")
def llm_completion(
    model: LLMName,
    messages: list[dict[str, str]],
    save_objects: bool = True,
    response_format: dict[str, Any] | type[BaseModel] | None = None,
    tools: list[dict[str, Any]] | None = None,
    enable_web_search: bool = False,
    **kwargs,
) -> LLMCompletionResult:
    """
    Perform an LLM completion with LiteLLM.

    Args:
        model: The LLM model to use
        messages: Chat messages
        save_objects: Whether to save chat history
        response_format: Response format specification
        tools: List of tools available for function calling (e.g., web_search)
        enable_web_search: If True, automatically add web search tools for the model
        **kwargs: Additional LiteLLM parameters
    """
    from litellm.types.utils import Choices, ModelResponse

    init_litellm()

    # Prepare completion parameters
    completion_params = {
        "model": model.litellm_name,
        "messages": messages,
        **kwargs,
    }

    # Auto-enable web search if requested
    if enable_web_search:
        import litellm

        if litellm.supports_web_search(model=model.litellm_name):
            log.message("Enabling web search for model %s", model.litellm_name)
            completion_params["web_search_options"] = {"search_context_size": "medium"}
        else:
            log.warning("Web search requested but not supported by model %s", model.litellm_name)

    chat_history = ChatHistory.from_dicts(messages)

    # Enhanced logging to detect tool use
    tools_info = f", {len(tools)} tools" if tools else ", no tools"
    log.info(
        "Calling LLM completion from %s on %s, response_format=%s%s",
        model.litellm_name,
        chat_history.size_summary(),
        response_format,
        tools_info,
    )

    if tools:
        tool_names = []
        for tool in tools:
            if tool.get("type") == "function":
                tool_names.append(tool.get("function", {}).get("name", "unknown"))
            elif tool.get("type") == "native_web_search":
                tool_names.append("native_web_search")
            else:
                tool_names.append(tool.get("type", "unknown"))

        log.message("Tools enabled: %s", tool_names)

    start_time = time.time()

    if response_format:
        completion_params["response_format"] = response_format

    if tools:
        completion_params["tools"] = tools
        log.info("Enabling function calling with %d tools", len(tools))

    import litellm

    llm_output = cast(
        ModelResponse,
        litellm.completion(**completion_params),  # pyright: ignore
    )
    elapsed = time.time() - start_time

    choices = cast(Choices, llm_output.choices[0])

    message = choices.message

    # Extract tool calls from the response
    tool_calls = getattr(message, "tool_calls", None)
    tool_calls_list = list(tool_calls) if tool_calls else None

    # Just sanity checking and logging.
    content = choices.message.content
    if not content or not isinstance(content, str):
        raise ApiResultError(f"LLM completion failed: {model.litellm_name}: {llm_output}")

    # Create the result object with tool calls
    citations = llm_output.get("citations", None)
    result = LLMCompletionResult(
        message=message,
        content=content,
        citations=CitationList(citations=citations) if citations else None,
        tool_calls=tool_calls_list,
    )

    # Log tool calls if present
    if result.has_tool_calls:
        tool_count = len(result.tool_calls or [])
        log.message("LLM executed %d function calls: %s", tool_count, result.tool_call_names)
        log.message(
            "⚠️  Function calls require implementation - LLM requested tools but no handlers are implemented"
        )

    # Performance logging
    total_input_len = sum(len(m["content"]) for m in messages)
    speed = len(content) / elapsed
    tool_count = len(result.tool_calls or []) if result.has_tool_calls else 0
    tool_info = f", {tool_count} tool calls" if result.has_tool_calls else ""
    log.info(
        f"{EMOJI_TIMING} LLM completion from {model.litellm_name} in {format_duration(elapsed)}: "
        f"input {total_input_len} chars in {len(messages)} messages, output {len(content)} chars "
        f"({speed:.0f} char/s){tool_info}"
    )

    if save_objects:
        metadata = {"citations": citations} if citations else {}
        if result.has_tool_calls:
            metadata["tool_calls"] = len(result.tool_calls or [])
        chat_history.messages.append(
            ChatMessage(role=ChatRole.assistant, content=content, metadata=metadata)
        )
        model_slug = slugify_snake(model.litellm_name)
        log.save_object(
            "LLM response",
            f"llm.{model_slug}",
            chat_history.to_yaml(),
            file_ext="yml",
        )

    return result


def llm_template_completion(
    model: LLMName,
    system_message: Message,
    input: str,
    body_template: MessageTemplate | None = None,
    previous_messages: list[dict[str, str]] | None = None,
    save_objects: bool = True,
    check_no_results: bool = True,
    response_format: dict[str, Any] | type[BaseModel] | None = None,
    tools: list[dict[str, Any]] | None = None,
    enable_web_search: bool = False,
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
        tools=tools,
        enable_web_search=enable_web_search,
        **kwargs,
    )

    if check_no_results and is_no_results(result.content):
        log.info("No results for LLM transform, will ignore: %r", result.content)
        result.content = ""

    return result
