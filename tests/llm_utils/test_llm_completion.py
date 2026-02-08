"""Tests for llm_completion: LLM call wrappers with mocked API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kash.llm_utils.llm_completion import (
    CitationList,
    LLMCompletionResult,
    llm_completion,
    llm_template_completion,
)
from kash.llm_utils.llm_messages import Message, MessageTemplate
from kash.llm_utils.llm_names import LLMName
from kash.utils.errors import ApiResultError


def _mock_response(content: str | None = "mocked", citations=None, tool_calls=None):
    """Create a mock LiteLLM ModelResponse."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    response.get = MagicMock(return_value=citations)
    response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
    return response


class TestCitationList:
    def test_markdown_footnotes(self):
        cl = CitationList(citations=["Source A", "Source B"])
        md = cl.as_markdown_footnotes()
        assert "[^1]:" in md
        assert "[^2]:" in md
        assert "Source A" in md

    def test_url_citations(self):
        cl = CitationList(citations=["https://example.com", "Not a URL"])
        assert len(cl.url_citations) == 1
        assert len(cl.non_url_citations) == 1


class TestLLMCompletionResult:
    def test_content_with_citations(self):
        result = LLMCompletionResult(
            message=MagicMock(),
            content="Hello",
            citations=CitationList(citations=["Ref"]),
        )
        assert "Hello" in result.content_with_citations
        assert "[^1]:" in result.content_with_citations

    def test_content_without_citations(self):
        result = LLMCompletionResult(message=MagicMock(), content="Hello", citations=None)
        assert result.content_with_citations == "Hello"

    def test_has_tool_calls(self):
        result = LLMCompletionResult(
            message=MagicMock(),
            content="x",
            citations=None,
            tool_calls=[{"function": {"name": "search"}}],
        )
        assert result.has_tool_calls
        assert result.tool_call_names == ["search()"]

    def test_no_tool_calls(self):
        result = LLMCompletionResult(message=MagicMock(), content="x", citations=None)
        assert not result.has_tool_calls
        assert result.tool_call_names == []


class TestLlmCompletion:
    @patch("litellm.completion")
    @patch("kash.llm_utils.llm_completion.init_litellm")
    def test_basic_completion(self, _mock_init, mock_litellm_completion):
        """Basic completion returns content from mocked API."""
        mock_litellm_completion.return_value = _mock_response("test output")
        model = LLMName("openai/gpt-4")
        messages = [{"role": "user", "content": "hello"}]
        result = llm_completion(model, messages, save_objects=False)
        assert result.content == "test output"
        mock_litellm_completion.assert_called_once()

    @patch("litellm.completion")
    @patch("kash.llm_utils.llm_completion.init_litellm")
    def test_completion_with_citations(self, _mock_init, mock_litellm_completion):
        """Completion extracts citations from response."""
        mock_litellm_completion.return_value = _mock_response(
            "answer", citations=["https://example.com"]
        )
        result = llm_completion(
            LLMName("openai/gpt-4"),
            [{"role": "user", "content": "q"}],
            save_objects=False,
        )
        assert result.citations is not None
        assert len(result.citations.citations) == 1

    @patch("litellm.completion")
    @patch("kash.llm_utils.llm_completion.init_litellm")
    def test_empty_content_raises(self, _mock_init, mock_litellm_completion):
        """Raises ApiResultError when response has no content."""
        mock_litellm_completion.return_value = _mock_response(content=None)
        with pytest.raises(ApiResultError, match="LLM completion failed"):
            llm_completion(
                LLMName("openai/gpt-4"),
                [{"role": "user", "content": "q"}],
                save_objects=False,
            )


class TestLlmTemplateCompletion:
    @patch("kash.llm_utils.llm_completion.llm_completion")
    def test_formats_template(self, mock_completion):
        """Template completion formats the body into the template."""
        mock_completion.return_value = LLMCompletionResult(
            message=MagicMock(), content="result", citations=None
        )
        result = llm_template_completion(
            model=LLMName("openai/gpt-4"),
            system_message=Message("You are helpful"),
            input="test input",
            body_template=MessageTemplate("Process: {body}"),
            save_objects=False,
            check_no_results=False,
        )
        assert result.content == "result"
        call_args = mock_completion.call_args
        messages = call_args.kwargs.get("messages") or call_args[0][1]
        user_msg = messages[-1]["content"]
        assert "Process: test input" in user_msg

    @patch("kash.llm_utils.llm_completion.llm_completion")
    def test_no_results_cleared(self, mock_completion):
        """When check_no_results=True and result matches is_no_results, content is cleared."""
        mock_completion.return_value = LLMCompletionResult(
            message=MagicMock(), content="no results", citations=None
        )
        result = llm_template_completion(
            model=LLMName("openai/gpt-4"),
            system_message=Message("sys"),
            input="x",
            check_no_results=True,
            save_objects=False,
        )
        assert result.content == ""

    def test_missing_system_message_raises(self):
        with pytest.raises(ValueError, match="system_message is required"):
            llm_template_completion(
                model=LLMName("openai/gpt-4"),
                system_message=Message(""),
                input="x",
            )
