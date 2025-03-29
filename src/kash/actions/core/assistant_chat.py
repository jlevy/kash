from kash.docs.all_docs import DocSelection
from kash.exec import kash_action
from kash.exec.preconditions import is_chat
from kash.help.assistant import assistant_chat_history, shell_context_assistance
from kash.help.assistant_output import print_assistant_heading
from kash.llm_utils import LLM, LLMName
from kash.model import NO_ARGS, ActionInput, ActionResult, common_params
from kash.shell.input.input_prompts import input_simple_string
from kash.shell.output.shell_output import PrintHooks, Wrap, print_response


@kash_action(
    expected_args=NO_ARGS,
    interactive_input=True,
    cacheable=False,
    precondition=is_chat,
    params=common_params("model", "doc_selection"),
)
def assistant_chat(
    _input: ActionInput,
    model: LLMName = LLM.default_careful,
    doc_selection: DocSelection = DocSelection.full,
) -> ActionResult:
    """
    Chat with the kash assistant. This is just the same as typing on the command line,
    but with a chat session.
    """
    chat_history = assistant_chat_history(
        include_system_message=True,
        is_structured=False,
        doc_selection=doc_selection,
    )
    PrintHooks.spacer()
    print_assistant_heading(model, doc_selection)
    print_response(
        f"History of {chat_history.size_summary()}.\nPress enter (or type `exit`) to end chat.",
        text_wrap=Wrap.NONE,
    )

    while True:
        try:
            user_message = input_simple_string(f"assistant/{model.litellm_name}")
        except KeyboardInterrupt:
            break
        if user_message is None:
            break

        user_message = user_message.strip()
        if not user_message or user_message.lower() == "exit" or user_message.lower() == "quit":
            break

        shell_context_assistance(user_message, silent=True, model=model)

    return ActionResult([])
