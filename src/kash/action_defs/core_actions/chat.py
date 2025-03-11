from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.precondition_defs import is_chat
from kash.form_input.prompt_input import prompt_simple_string
from kash.llm_tools.chat_format import ChatHistory, ChatMessage, ChatRole
from kash.llm_tools.llm_completion import llm_completion
from kash.model import (
    ActionInput,
    ActionResult,
    common_params,
    Format,
    Item,
    ItemType,
    LLM,
    ONE_OR_NO_ARGS,
    ShellResult,
)
from kash.model.language_models import LLMName
from kash.shell_output.shell_output import (
    PadStyle,
    print_markdown,
    print_response,
    print_style,
    Wrap,
)

log = get_logger(__name__)


@kash_action(
    expected_args=ONE_OR_NO_ARGS,
    precondition=is_chat,
    uses_selection=False,
    interactive_input=True,
    cacheable=False,
    params=common_params("model"),
)
def chat(input: ActionInput, model: LLMName = LLM.default_careful) -> ActionResult:
    """
    Chat with an LLM. By default, starts a new chat session. If provided a chat
    history item, will continue an existing chat.
    """
    if input.items:
        chat_history = input.items[0].as_chat_history()
        size_desc = f"{chat_history.size_summary()} in chat history"
    else:
        chat_history = ChatHistory()
        size_desc = "empty chat history"

    print_response(
        f"Beginning chat with {size_desc}. Press enter (or type `exit`) to end chat.",
        text_wrap=Wrap.WRAP_FULL,
    )

    while True:
        try:
            user_message = prompt_simple_string(model.litellm_name)
        except KeyboardInterrupt:
            break

        user_message = user_message.strip()
        if not user_message or user_message.lower() == "exit" or user_message.lower() == "quit":
            break

        chat_history.append(ChatMessage(ChatRole.user, user_message))

        llm_response = llm_completion(
            model,
            messages=chat_history.as_chat_completion(),
        )

        with print_style(PadStyle.PAD):
            print_markdown(llm_response.content)

        # XXX: Why does the response have trailing whitespace on lines? Makes the YAML ugly.
        stripped_response = "\n".join(line.rstrip() for line in llm_response.content.splitlines())

        chat_history.append(ChatMessage(ChatRole.assistant, stripped_response))

    if chat_history.messages:
        item = Item(
            ItemType.chat,
            body=chat_history.to_yaml(),
            format=Format.yaml,
        )

        return ActionResult([item])
    else:
        log.warning("Empty chat! Not saving anything.")
        return ActionResult([], shell_result=ShellResult(show_selection=False))
