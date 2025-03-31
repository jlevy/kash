from flowmark import Wrap, fill_text

from kash.actions.meta.write_instructions import write_instructions
from kash.config.logger import get_logger
from kash.docs.all_docs import DocSelection
from kash.exec import kash_action
from kash.exec.preconditions import is_instructions
from kash.help.assistant import assist_preamble, assistance_structured
from kash.help.assistant_output import print_assistant_response
from kash.llm_utils import LLM, LLMName, Message
from kash.model import (
    ONE_OR_NO_ARGS,
    ActionInput,
    ActionResult,
    Format,
    ItemType,
    TitleTemplate,
    common_params,
)
from kash.utils.common.lazyobject import lazyobject
from kash.utils.common.type_utils import not_none
from kash.utils.errors import ApiResultError, InvalidInput
from kash.utils.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole

log = get_logger(__name__)


@lazyobject
def write_action_instructions() -> str:
    from kash.docs.load_source_code import load_source_code

    return (
        """
        You are a senior software engineer who writes clean code exactly
        conforming with existing practice using the kash framework, which you understand
        clearly. You always want to write actions that are helpful and reusable
        as command-line operations or as Python libraries, since kash makes
        commands and actions available to use both ways.

        You need to write Python code to implement an action or a command in kash.
        
        Guidelines:

        - Provide Python code in the python_code field.

        - Choose a command implementation (with @kash_command decorating a function) if the
          operation is very simple and does not have files (Items) to output. To just read
          a file and show information, or print something, use a command. Choose an
          action implementation (with @kash_action decorating a class) if the operation
          has files (Items) to output.
        
        - Add non-code commentary in the response_text field explaining any issues or
          assumptions you made while writing the code.

        - If desired behavior of the code is not clear from the description, add
          comment placeholders in the code so it can be filled in later.

        - If the user gives other random context, like a previous conversation, consider
          how you would implement a command or action that would generalize the operation
          being discussed. Add parameters to the command or action if it makes sense
          a user would want them, and use defaults as appropriate.

        - Look at the example below. Commonly, you will subclass PerItemAction
          for simple actions that work on one item at a time. Subclass LLMAction
          if it is simply a transformation of the input using an LLM.
.
        To illustrate, here are a couple examples of the correct format for an action that
        strips HTML tags:
        """
        + load_source_code().example_action_src.replace("{", "{{").replace("}", "}}")
        + """

        And here are a couple simple command implementations:
        """
        + load_source_code().example_command_src.replace("{", "{{").replace("}", "}}")
        + """

        Next you will get context or a request from the user on a problem, or
        simply a previous discussion with an assistant describing a partial solution
        but from which you can understand what action or command would help solve
        the problem.
         
        After thinking about the context below, describe a useful command or action
        that is appropriate for the problem, and then give the Python code for it.
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
    Create a new kash action or command in Python, based some problem or context or
    a description of the features.

    If no input is provided, will start an interactive chat to get

    Or `write_instructions` to create a chat to use as input for this action.
    """
    if not input.items:
        # Start a chat to collect the action description.
        # FIXME: Consider generalizing this so an action can declare an input action to collect its input.
        chat_result = write_instructions(ActionInput.empty())
        if not chat_result.items:
            raise InvalidInput("No chat input provided")

        action_description_item = chat_result.items[0]
    else:
        action_description_item = input.items[0]

    # Manually check precondition since we might have created the item
    is_instructions.check(action_description_item, "action `write_new_action`")

    chat_history = ChatHistory()

    instructions_message = ChatHistory.from_yaml(not_none(action_description_item.body)).messages[0]

    # Give the LLM full context on kash APIs.
    # But we do this here lazily to prevent circular dependencies.
    system_message = Message(assist_preamble(is_structured=True, doc_selection=DocSelection.full))
    chat_history.extend(
        [
            ChatMessage(ChatRole.system, system_message),
            ChatMessage(ChatRole.user, str(write_action_instructions)),
            instructions_message,
        ]
    )

    assistant_response = assistance_structured(chat_history.as_chat_completion(), model)

    print_assistant_response(assistant_response, model, DocSelection.programming)

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
