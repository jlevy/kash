"""Tests for completion scoring pure functions."""

from __future__ import annotations

import math

from kash.shell.completions.completion_scoring import (
    ONE_HOUR,
    ONE_YEAR,
    Score,
    decaying_recency,
    linear_boost,
    normalize,
    score_exact_prefix,
    score_subphrase,
)


def test_normalize():
    assert normalize("Hello, World!") == "hello  world"
    assert normalize("foo_bar-baz") == "foo_bar baz"
    assert normalize("  spaces  ") == "spaces"
    assert normalize("") == ""


def test_score_exact_prefix_match():
    assert score_exact_prefix("hel", "hello") > Score(70)
    assert score_exact_prefix("hello", "hello") > Score(90)
    assert score_exact_prefix("x", "hello") == Score(0)
    # Very short prefix gets a lower base score
    assert score_exact_prefix("h", "hello") == Score(50)


def test_score_exact_prefix_full_match():
    """Full prefix match should score highest."""
    full = score_exact_prefix("hello", "hello")
    partial = score_exact_prefix("hel", "hello")
    assert full > partial


def test_linear_boost():
    assert linear_boost(Score(100), Score(50)) == Score(100)
    assert linear_boost(Score(0), Score(50)) == Score(50)
    # Midpoint should be scaled linearly
    boosted = linear_boost(Score(50), Score(50))
    assert Score(70) <= boosted <= Score(80)


def test_decaying_recency_bounds():
    assert decaying_recency(0) == Score(100.0)
    assert decaying_recency(ONE_HOUR / 2) == Score(100.0)  # below min_age
    assert decaying_recency(ONE_YEAR * 2) == Score(0.0)  # above max_age


def test_decaying_recency_decay():
    """Score should decrease monotonically with age."""
    scores = [decaying_recency(age) for age in [ONE_HOUR, ONE_HOUR * 24, ONE_HOUR * 24 * 30, ONE_HOUR * 24 * 180]]
    for i in range(len(scores) - 1):
        assert scores[i] > scores[i + 1]


def test_score_subphrase():
    assert score_subphrase("hello", "hello world how are you") > Score(50)
    assert score_subphrase("xyz", "hello world") < Score(50)
