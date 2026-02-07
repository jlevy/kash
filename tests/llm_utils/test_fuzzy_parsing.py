"""Tests for fuzzy parsing edge cases beyond the inline tests."""

from __future__ import annotations

from kash.llm_utils.fuzzy_parsing import (
    fuzzy_match,
    fuzzy_parse_json,
    is_no_results,
    strip_markdown_fence,
)


def test_is_no_results_empty_and_sentinel():
    assert is_no_results("(No results)")
    assert is_no_results("(no results)")
    assert is_no_results(" (No Results) ")
    assert not is_no_results("Here are some results")
    assert not is_no_results("No results were found for your query")


def test_fuzzy_match_threshold():
    assert fuzzy_match("hello world", "hello world")
    assert fuzzy_match("helo world", "hello world")  # close enough at default 80
    assert not fuzzy_match("completely different", "hello world")
    assert not fuzzy_match("", "hello world")


def test_strip_markdown_fence_language_tags():
    assert strip_markdown_fence("```python\nprint('hi')\n```") == "print('hi')"
    assert strip_markdown_fence("```json\n{}\n```") == "{}"
    assert strip_markdown_fence("no fence here") == "no fence here"


def test_fuzzy_parse_json_array():
    result = fuzzy_parse_json('Here is the data: [1, 2, 3]')
    assert result == [1, 2, 3]


def test_fuzzy_parse_json_nested():
    result = fuzzy_parse_json('```json\n{"nested": {"key": [1, 2]}}\n```')
    assert result == {"nested": {"key": [1, 2]}}


def test_fuzzy_parse_json_invalid():
    assert fuzzy_parse_json("not json at all") is None
    assert fuzzy_parse_json("") is None
