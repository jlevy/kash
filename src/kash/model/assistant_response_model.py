from enum import Enum

from pydantic import BaseModel

from kash.exec_model.commands_model import CommentedCommand


class Confidence(str, Enum):
    """
    How confident the assistant is that the answer is correct.
    """

    direct_answer = "direct_answer"
    """
    This response is a direct answer to the user's question.
    """

    partial_answer = "partial_answer"
    """
    This response is a partial answer to the user's question.
    """

    conversation = "conversation"
    """
    This response is conversational, not a direct answer to a user's question.
    """

    info_request = "info_request"
    """
    This response is a request from the assistant for more information from the user.
    """

    unsure = "unsure"
    """
    This assistant is unsure of how to respond or answer the question.
    """


class AssistantResponse(BaseModel):
    response_text: str
    """
    Put the answer to the user's question or response to their last message here.
    """

    confidence: Confidence
    """
    What is the nature of this response? Is it a direct answer, a partial answer,
    a conversational response, or a request for more information?

    If the user's last message was a question, and there is a clear answer,
    `response_text` should be a direct answer to the question and confidence
    should be `direct_answer`.
    
    If the answer is likely incomplete, confidence should be
    `partial_answer`.

    If answering the last message would would require more information,
    this response text should be one or more questions to get the information
    needed and the confidence should be `info_request`.

    If the user is being conversational, this response text should be a
    response to the user's message and the confidence should be `conversation`.

    If the assistant is unsure of how to respond, confidence should be `unsure`.
    """

    suggested_commands: list[CommentedCommand]
    """
    Commands that the assistant suggests to solve the user's request.
    These should be in the order the user could execute them.
    Only list these if the intent is relatively clear.
    If the answer is Python, use `python_code` instead.
    """

    python_code: str | None
    """
    If the assistant is suggesting a Python code snippet, put it here.
    Only use this for Python code!
    """

    see_also: list[str]
    """
    Other commands that may be relevant but were not suggested as a solution.
    This should not include commands that were already suggested.
    This usually should not be empty since the assistant can also suggest
    related commands and help pages.
    """
