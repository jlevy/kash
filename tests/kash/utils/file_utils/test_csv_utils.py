from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent

from kash.utils.file_utils.csv_utils import sniff_csv_metadata


def test_sniff_csv_metadata_normal_csv():
    """Test CSV detection with a normal CSV file (no metadata)."""
    normal_csv = dedent("""
        Name,Age,City
        Alice,25,New York
        Bob,30,London
    """).strip()

    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(normal_csv)
        f.flush()

        result = sniff_csv_metadata(Path(f.name))
        assert result.skip_rows == 0
        assert result.metadata == {}
        assert result.dialect is not None


def test_sniff_csv_metadata_with_simple_metadata():
    """Test CSV detection with key-value metadata."""
    metadata_csv = dedent("""
        "Survey Name","Global AI Dialogues"
        "Date","2024-09-04"
        "Participants","1294"
        
        "Participant Id","Age","Gender","Country"
        "123","25","Female","USA"
        "456","30","Male","UK"
    """).strip()

    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(metadata_csv)
        f.flush()

        result = sniff_csv_metadata(Path(f.name))
        assert result.skip_rows == 4  # Skip metadata and empty line
        assert "Survey Name" in result.metadata
        assert result.metadata["Survey Name"] == "Global AI Dialogues"
        assert result.metadata["Date"] == "2024-09-04"
        # "Participants" is not collected because it stops when it finds the first header candidate
        assert len(result.metadata) == 2


def test_sniff_csv_metadata_complex_format():
    """Test CSV detection with complex metadata format like the example."""
    complex_csv = dedent("""
        "Name","Elicitation Questions Final"
        "Title","What future do you want?"
        "Date","September 04, 2024 at 05:15 PM (GMT)"
        "Duration","283:46:13"
        "Participants","1294"
        
        ""
        ""
        "","","Participant Id","Sample Provider Id","Please select your preferred language:"
        "","","f18ba393-1b2f-47a9-9387-7d90306e3b56","66d89e108ec7ec41c2401121","English"
    """).strip()

    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(complex_csv)
        f.flush()

        result = sniff_csv_metadata(Path(f.name))
        assert result.skip_rows == 8  # Should find the first row with 5 columns
        assert "Name" in result.metadata
        assert result.metadata["Name"] == "Elicitation Questions Final"
        # Check that we collected some metadata before finding the header
        assert len(result.metadata) >= 2


def test_sniff_csv_metadata_with_custom_parameters():
    """Test CSV detection with custom parameters."""
    csv_data = dedent("""
        "Key1","Value1"
        "Key2","Value2"
        
        "Col1","Col2","Col3","Col4","Col5"
        "A","B","C","D","E"
    """).strip()

    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_data)
        f.flush()

        # Test with higher min_columns threshold
        result = sniff_csv_metadata(Path(f.name), min_columns=5)
        assert result.skip_rows == 3
        assert len(result.metadata) == 2

        # Test with lower threshold_ratio
        result = sniff_csv_metadata(Path(f.name), threshold_ratio=0.5, min_columns=3)
        assert result.skip_rows == 3


def test_sniff_csv_metadata_empty_file():
    """Test behavior with empty file."""
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("")
        f.flush()

        result = sniff_csv_metadata(Path(f.name))
        assert result.skip_rows == 0
        assert result.metadata == {}


def test_sniff_csv_metadata_only_metadata():
    """Test file with only metadata rows, no table."""
    metadata_only = dedent("""
        "Key1","Value1"
        "Key2","Value2"
    """).strip()

    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(metadata_only)
        f.flush()

        result = sniff_csv_metadata(Path(f.name))
        assert result.skip_rows == 0  # No table found, start at beginning
        assert len(result.metadata) == 2
        assert result.metadata["Key1"] == "Value1"
