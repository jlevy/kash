from flowmark import Wrap, fill_text

from kash.actions.meta.write_instructions import write_instructions
from kash.config.logger import get_logger
from kash.errors import ApiResultError
from kash.exec import kash_action
from kash.exec.action_exec import run_action_with_shell_context
from kash.exec.preconditions import is_instructions
from kash.help.assistant import assist_preamble, assistance_structured
from kash.help.assistant_output import print_assistant_response
from kash.llm_utils.chat_format import ChatHistory, ChatMessage, ChatRole
from kash.model import (
    LLM,
    ONE_OR_NO_ARGS,
    ActionInput,
    ActionResult,
    Format,
    ItemType,
    Message,
    TitleTemplate,
    common_params,
)
from kash.model.language_models import LLMName
from kash.model.params_model import RawParamValues
from kash.utils.common.lazyobject import lazyobject
from kash.utils.common.type_utils import not_none

log = get_logger(__name__)


@lazyobject
def write_action_instructions() -> str:
    from kash.docs.load_source_code import load_source_code

    return (
        """
        Write a kash action according to the following description. Guidelines:

        - Provide Python code in the python_code field.
        
        - Add non-code commentary in the response_text field.

        - If desired behavior of the code is not clear from the description, add
            comment placeholders in the code so it can be filled in later.

        - Look at the example below. Commonly, you will subclass PerItemAction
          for simple actions that work on one item at a time. Subclass LLMAction
          if it is simply a transformation of the input using an LLM.
.
        To illustrate, here are a cuople examples of the correct format for an action that
        strips HTML tags:
        """
        + load_source_code().example_action_src.replace("{", "{{").replace("}", "}}")
        + """
        
        I'll give you a description of an action and possibly more refinements
        and you will write the Python code for the action.
        """
    )


@kash_action(
    expected_args=ONE_OR_NO_ARGS,
    precondition=is_instructions,
    cacheable=False,
    interactive_input=True,
    params=common_params("model"),
    title_template=TitleTemplate("Action: {title}"),
)
def write_new_action(input: ActionInput, model: LLMName = LLM.default_structured) -> ActionResult:
    """
    Create a new kash action in Python, based on a description of the features.
    If no input is provided, will start an interactive chat to collect the action
    description.

    Use `write_instructions` to create a chat to use as input for this action.
    """
    if not input.items:
        # Start a chat to collect the action description.
        # FIXME: Consider generalizing this so an action can declare an input action to collect its input.
        chat_result = run_action_with_shell_context(
            write_instructions.__name__, RawParamValues(), internal_call=True
        )
        if not chat_result.items:
            raise ApiResultError("No chat input provided")

        action_description_item = chat_result.items[0]
    else:
        action_description_item = input.items[0]

    # Manually check precondition since we might have created the item
    is_instructions.check(action_description_item, "action `write_new_action`")

    chat_history = ChatHistory()

    instructions_message = ChatHistory.from_yaml(not_none(action_description_item.body)).messages[0]

    # Give the LLM full context on kash APIs.
    # But we do this here lazily to prevent circular dependencies.
    system_message = Message(assist_preamble(is_structured=True, skip_api_docs=False))
    chat_history.extend(
        [
            ChatMessage(ChatRole.system, system_message),
            ChatMessage(ChatRole.user, str(write_action_instructions)),
            instructions_message,
        ]
    )

    assistant_response = assistance_structured(chat_history.as_chat_completion(), model)

    print_assistant_response(assistant_response, model)

    if not assistant_response.python_code:
        raise ApiResultError("No Python code provided in the response.")

    body = assistant_response.python_code
    # Put the instructions in an actual comment at the top of the file.
    action_comments = "(This action was written by kash `write_new_action`.)\n\n" + str(
        instructions_message.content
    )
    comment = fill_text(action_comments, text_wrap=Wrap.WRAP_FULL, extra_indent="# ")
    commented_body = "\n\n".join(filter(None, [comment, body]))

    result_item = action_description_item.derived_copy(
        type=ItemType.extension,
        format=Format.python,
        body=commented_body,
    )

    return ActionResult([result_item])
