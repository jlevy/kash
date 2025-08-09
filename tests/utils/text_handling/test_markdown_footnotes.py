"""
Tests for markdown footnote extraction and management utilities.
"""

from textwrap import dedent
from unittest.mock import Mock

from flowmark import flowmark_markdown, line_wrap_by_sentence

from kash.utils.text_handling.markdown_footnotes import (
    FootnoteInfo,
    MarkdownFootnotes,
    extract_footnote_references,
)


def test_basic_footnote_extraction():
    """Test extracting basic footnotes from markdown content."""
    content = dedent("""
        This is some text with a footnote[^1].
        
        Another paragraph with another footnote[^2].
        
        [^1]: This is the first footnote.
        [^2]: This is the second footnote with more content.
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    assert len(footnotes) == 2
    assert "^1" in footnotes
    assert "^2" in footnotes

    assert footnotes["^1"].content == "This is the first footnote."
    assert footnotes["^2"].content == "This is the second footnote with more content."

    assert footnotes["^1"].footnote_id == "^1"
    assert footnotes["^2"].footnote_id == "^2"


def test_named_footnotes():
    """Test extracting footnotes with named labels."""
    content = dedent("""
        Text with named footnote[^note].
        
        Another reference[^important].
        
        [^note]: A footnote with a name instead of number.
        [^important]: This is marked as important.
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    assert len(footnotes) == 2
    assert "^note" in footnotes
    assert "^important" in footnotes

    assert footnotes["^note"].footnote_id == "^note"
    assert footnotes["^important"].footnote_id == "^important"

    assert footnotes["^note"].content == "A footnote with a name instead of number."
    assert footnotes["^important"].content == "This is marked as important."


def test_multiline_footnotes():
    """Test extracting footnotes with multiple lines and paragraphs."""
    content = dedent("""
        Text with complex footnote[^multi].
        
        [^multi]: This is a footnote that spans
            multiple lines and continues here.
            
            It even has multiple paragraphs!
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    assert len(footnotes) == 1
    assert "^multi" in footnotes

    # The content should preserve paragraph structure (flowmark rewraps lines)
    actual_content = footnotes["^multi"].content
    # Check that both parts of the content are present
    assert "This is a footnote that spans" in actual_content
    assert "multiple lines and continues here" in actual_content
    assert "It even has multiple paragraphs!" in actual_content
    # Check paragraph break is preserved
    assert "\n\n" in actual_content


def test_footnotes_with_formatting():
    """Test footnotes containing markdown formatting."""
    content = dedent("""
        Reference to formatted footnote[^formatted].
        
        [^formatted]: This footnote has **bold**, *italic*, and `code`.
            It also has a [link](https://example.com).
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    assert "^formatted" in footnotes
    # Content should preserve markdown formatting
    assert "**bold**" in footnotes["^formatted"].content
    assert "*italic*" in footnotes["^formatted"].content
    assert "`code`" in footnotes["^formatted"].content
    assert "[link](https://example.com)" in footnotes["^formatted"].content


def test_footnote_access_methods():
    """Test various ways of accessing footnotes."""
    content = dedent("""
        Text[^1] with[^note] footnotes[^test].
        
        [^1]: Numeric footnote.
        [^note]: Named footnote.
        [^test]: Test footnote.
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    # Test dictionary-style access
    assert footnotes["^1"].content == "Numeric footnote."

    # Test get method with default
    info = footnotes.get("^1")
    assert info is not None
    assert info.content == "Numeric footnote."
    assert footnotes.get("^nonexistent") is None

    mock_element = Mock(spec=["label"])
    default_info = FootnoteInfo("^default", "Default content", mock_element)
    assert footnotes.get("^nonexistent", default_info) == default_info

    # Test containment check
    assert "^1" in footnotes
    assert "^note" in footnotes
    assert "^nonexistent" not in footnotes

    # Test iteration
    ids = list(footnotes)
    assert set(ids) == {"^1", "^note", "^test"}

    # Test keys(), values(), items()
    assert set(footnotes.keys()) == {"^1", "^note", "^test"}
    assert len(list(footnotes.values())) == 3
    items = dict(footnotes.items())
    assert items["^1"].content == "Numeric footnote."


def test_footnote_access_without_caret():
    """Test that accessing footnotes without caret automatically adds it."""
    content = dedent("""
        Text[^123].
        
        [^123]: A footnote.
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    # Can access with or without caret
    assert footnotes["123"].content == "A footnote."
    assert footnotes["^123"].content == "A footnote."

    # get method also handles missing caret
    info1 = footnotes.get("123")
    assert info1 is not None
    assert info1.content == "A footnote."
    info2 = footnotes.get("^123")
    assert info2 is not None
    assert info2.content == "A footnote."

    # Contains check works both ways
    assert "123" in footnotes
    assert "^123" in footnotes


def test_extract_footnote_references():
    """Test extracting footnote references (usage points) from content."""
    content = dedent("""
        This text references footnote one[^1] and footnote two[^2].
        
        It also references[^named] and[^1] again (duplicate).
        
        But footnote three is only defined, not referenced.
        
        [^1]: First footnote.
        [^2]: Second footnote.
        [^named]: Named footnote.
        [^3]: Third footnote (not referenced).
        """)

    references = extract_footnote_references(content)

    # Should get unique references in order of first appearance
    assert references == ["^1", "^2", "^named"]
    # Note: ^3 is not in the list because it's never referenced


def test_empty_document():
    """Test handling of documents with no footnotes."""
    content = "Just plain text with no footnotes."

    footnotes = MarkdownFootnotes.from_markdown(content)
    assert len(footnotes) == 0
    assert list(footnotes) == []

    references = extract_footnote_references(content)
    assert references == []


def test_footnote_only_definitions():
    """Test document with footnote definitions but no references."""
    content = dedent("""
        Regular text here.
        
        [^unused1]: This footnote is defined but never referenced.
        [^unused2]: Another unused footnote.
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)
    assert len(footnotes) == 2
    assert "^unused1" in footnotes
    assert "^unused2" in footnotes

    references = extract_footnote_references(content)
    assert references == []  # No references in the text


def test_footnote_only_references():
    """Test document with footnote references but no definitions."""
    content = "Text with undefined footnote[^undefined]."

    footnotes = MarkdownFootnotes.from_markdown(content)
    assert len(footnotes) == 0  # No definitions

    references = extract_footnote_references(content)
    # Note: Marko only parses footnote references when there's a matching definition
    # This prevents false positives where [^text] in regular content would be parsed
    assert references == []  # No reference without definition


def test_complex_real_world_footnotes():
    """Test with a realistic document containing various footnote patterns."""
    content = dedent("""
        # Research Article
        
        This study examines ketamine therapy[^109] and its applications in 
        modern medicine[^study2023]. The treatment shows promise[^109] for 
        various conditions.
        
        ## Methodology
        
        We reviewed multiple sources[^pubmed][^scholar] and conducted 
        meta-analysis[^meta].
        
        ## References
        
        [^109]: What Is The Future Of Ketamine Therapy For Mental Health Treatment?
            - The Ko-Op, accessed June 28, 2025,
              <https://psychedelictherapists.co/blog/the-future-of-ketamine-assisted-psychotherapy/>
        
        [^study2023]: Johnson et al. (2023). "Ketamine in Clinical Practice."
            *Journal of Psychedelic Medicine*, 15(3), 234-251.
            
            This groundbreaking study demonstrated efficacy in treatment-resistant
            depression cases.
        
        [^pubmed]: PubMed database search conducted May 2023.
        
        [^scholar]: Google Scholar search for "ketamine therapy" 2020-2023.
        
        [^meta]: Meta-analysis of 15 randomized controlled trials.
        
        [^unused]: This footnote is defined but not referenced in the text.
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    # Check all footnotes are found
    assert len(footnotes) == 6
    expected_ids = {"^109", "^study2023", "^pubmed", "^scholar", "^meta", "^unused"}
    assert set(footnotes.keys()) == expected_ids

    # Check complex footnote content is preserved
    footnote_109 = footnotes["^109"]
    assert "What Is The Future Of Ketamine Therapy" in footnote_109.content
    assert "https://psychedelictherapists.co" in footnote_109.content

    footnote_study = footnotes["^study2023"]
    assert "Johnson et al." in footnote_study.content
    assert "*Journal of Psychedelic Medicine*" in footnote_study.content
    assert "groundbreaking study" in footnote_study.content

    # Check references (should not include unused)
    references = extract_footnote_references(content)
    assert set(references) == {"^109", "^study2023", "^pubmed", "^scholar", "^meta"}
    # ^109 appears twice but should only be listed once


def test_from_document_method():
    """Test creating MarkdownFootnotes from a pre-parsed document."""
    content = dedent("""
        Text with footnote[^1].
        
        [^1]: The footnote content.
        """)

    # Parse document separately
    parser = flowmark_markdown(line_wrap_by_sentence(width=88, is_markdown=True))
    document = parser.parse(content)

    # Create footnotes from parsed document
    footnotes = MarkdownFootnotes.from_document(document, parser)

    assert len(footnotes) == 1
    assert "^1" in footnotes
    assert footnotes["^1"].content == "The footnote content."


def test_footnote_with_lists():
    """Test footnotes containing list content."""
    content = dedent("""
        See the list of items[^list].
        
        [^list]: This footnote contains a list:
            - First item
            - Second item
            - Third item with **bold**
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    assert "^list" in footnotes
    # List structure should be preserved in the content
    content_text = footnotes["^list"].content
    assert "- First item" in content_text
    assert "- Second item" in content_text
    assert "- Third item with **bold**" in content_text


def test_special_characters_in_footnote_ids():
    """Test footnotes with special characters in their IDs."""
    content = dedent("""
        Various footnote styles[^foo-bar][^foo_bar][^123abc].
        
        [^foo-bar]: Footnote with hyphen.
        [^foo_bar]: Footnote with underscore.
        [^123abc]: Alphanumeric footnote.
        """)

    footnotes = MarkdownFootnotes.from_markdown(content)

    assert len(footnotes) == 3
    assert "^foo-bar" in footnotes
    assert "^foo_bar" in footnotes
    assert "^123abc" in footnotes

    assert footnotes["^foo-bar"].content == "Footnote with hyphen."
    assert footnotes["^foo_bar"].content == "Footnote with underscore."
    assert footnotes["^123abc"].content == "Alphanumeric footnote."
