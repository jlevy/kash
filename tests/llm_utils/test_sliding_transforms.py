"""Tests for custom_sliding_transforms: filtered and windowed transforms."""

from __future__ import annotations

from chopdiff.docs import TextDoc, TextUnit
from chopdiff.transforms import WindowSettings

from kash.llm_utils.custom_sliding_transforms import (
    filtered_transform,
    sliding_para_window_transform,
)


def _identity_transform(doc: TextDoc) -> TextDoc:
    """Transform that returns input unchanged."""
    return doc


def _uppercase_transform(doc: TextDoc) -> TextDoc:
    """Transform that uppercases all text."""
    return TextDoc.from_text(doc.reassemble().upper())


def _prefix_transform(doc: TextDoc) -> TextDoc:
    """Transform that adds a prefix."""
    return TextDoc.from_text("PREFIX " + doc.reassemble())


class TestFilteredTransform:
    def test_no_windowing_applies_transform(self):
        """Without windowing, applies transform to the whole document."""
        doc = TextDoc.from_text("Hello world.")
        result = filtered_transform(doc, _uppercase_transform, windowing=None)
        assert result.reassemble().strip() == "HELLO WORLD."

    def test_identity_preserves_content(self):
        """Identity transform preserves the document content."""
        doc = TextDoc.from_text("Keep this text.")
        result = filtered_transform(doc, _identity_transform, windowing=None)
        assert result.reassemble().strip() == "Keep this text."

    def test_no_windowing_no_filter(self):
        """Without windowing and without diff filter, transform is applied directly."""
        doc = TextDoc.from_text("Some input text.")
        result = filtered_transform(doc, _prefix_transform, windowing=None, diff_filter=None)
        assert "PREFIX" in result.reassemble()


class TestSlidingParaWindowTransform:
    def test_single_paragraph(self):
        """Single paragraph processed as one window."""
        doc = TextDoc.from_text("A single paragraph of text.")
        settings = WindowSettings(unit=TextUnit.paragraphs, size=10, shift=10)
        result = sliding_para_window_transform(doc, _identity_transform, settings)
        assert "single paragraph" in result.reassemble()

    def test_multiple_paragraphs(self):
        """Multiple paragraphs are windowed and reassembled."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        doc = TextDoc.from_text(text)
        settings = WindowSettings(unit=TextUnit.paragraphs, size=2, shift=2)
        result = sliding_para_window_transform(doc, _identity_transform, settings)
        reassembled = result.reassemble()
        assert "First" in reassembled
        assert "Third" in reassembled

    def test_size_must_equal_shift(self):
        """Raises ValueError if size != shift."""
        doc = TextDoc.from_text("text")
        settings = WindowSettings(unit=TextUnit.paragraphs, size=3, shift=2)
        import pytest

        with pytest.raises(ValueError, match="equal size and shift"):
            sliding_para_window_transform(doc, _identity_transform, settings)

    def test_wrong_unit_raises(self):
        """Raises ValueError for non-paragraph unit."""
        doc = TextDoc.from_text("text")
        settings = WindowSettings(unit=TextUnit.wordtoks, size=10, shift=10)
        import pytest

        with pytest.raises(ValueError, match="expects paragraphs"):
            sliding_para_window_transform(doc, _identity_transform, settings)
