from kash.exec import kash_action
from kash.model import NO_ARGS, ActionInput, ActionResult, Format, Item, ItemType
from kash.shell.input.input_prompts import input_simple_string
from kash.utils.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole


@kash_action(
    expected_args=NO_ARGS,
    interactive_input=True,
    cacheable=False,
)
def write_instructions(_input: ActionInput) -> ActionResult:
    """
    Write a chat item with system and user instructions.
    """
    chat_history = ChatHistory()

    system_instructions = input_simple_string("Enter the system instructions (or enter for none): ")
    system_instructions = (system_instructions or "").strip()
    if system_instructions:
        chat_history.append(ChatMessage(ChatRole.system, system_instructions))

    user_instructions = input_simple_string("Enter the user instructions: ")
    user_instructions = (user_instructions or "").strip()
    if user_instructions:
        chat_history.append(ChatMessage(ChatRole.user, user_instructions))

    if chat_history.messages:
        item = Item(
            type=ItemType.chat,
            body=chat_history.to_yaml(),
            format=Format.yaml,
        )

        return ActionResult([item])
    else:
        return ActionResult([])
