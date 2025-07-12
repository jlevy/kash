from __future__ import annotations

import csv
from pathlib import Path
from typing import NamedTuple


class CsvMetadata(NamedTuple):
    """
    Result of CSV analysis, containing skip rows, metadata, and dialect.
    """

    skip_rows: int
    metadata: dict[str, str]
    dialect: type[csv.Dialect]


def sniff_csv_metadata(
    file_path: Path,
    *,
    max_scan_lines: int = 500,
    threshold_ratio: float = 0.8,
    min_columns: int = 3,
    sample_size: int = 32768,
) -> CsvMetadata:
    """
    Detect CSV metadata and where the table data starts by finding the first row that looks
    like proper headers.

    This function handles various CSV formats:
    - Normal CSV files: returns skip_rows=0 (no rows to skip)
    - Files with metadata: detects the first row with multiple columns that looks like headers
    - Survey exports: handles key-value metadata followed by proper CSV structure

    Args:
        file_path: Path to the CSV file to analyze
        max_scan_lines: Maximum number of lines to scan before giving up
        threshold_ratio: Minimum ratio of max columns a row must have to be considered headers
        min_columns: Minimum number of columns required to be considered headers
        sample_size: Number of bytes to read for dialect detection

    Returns:
        CsvMetadata with skip_rows, metadata dict, and detected dialect
    """
    # Read sample for dialect detection
    sample_text = file_path.read_text(encoding="utf-8", errors="replace")[:sample_size]

    # Detect CSV dialect
    try:
        dialect = csv.Sniffer().sniff(sample_text)
    except csv.Error:
        # Fall back to default dialect if detection fails
        dialect = csv.excel

    # Analyze file structure
    with open(file_path, encoding="utf-8", errors="replace") as file:
        reader = csv.reader(file, dialect=dialect)

        max_columns = 0
        header_candidates = []
        metadata = {}

        for line_num, row in enumerate(reader):
            # Stop scanning if we've looked at too many lines
            if line_num >= max_scan_lines:
                break

            # Skip completely empty rows
            non_empty_cells = [cell.strip() for cell in row if cell.strip()]
            if not non_empty_cells:
                continue

            column_count = len(non_empty_cells)

            # Track the maximum number of columns seen
            if column_count > max_columns:
                max_columns = column_count

            # Collect potential key-value metadata (exactly 2 columns)
            # Only collect metadata before we find any header candidates with min_columns
            if column_count == 2 and not any(hc[1] >= min_columns for hc in header_candidates):
                key, value = non_empty_cells[0], non_empty_cells[1]
                # Simple heuristic: if it looks like a key-value pair, store it
                if not key.isdigit() and not value.replace(".", "").replace(",", "").isdigit():
                    metadata[key] = value

            # Consider this a potential header if it has minimum required columns
            if column_count >= min_columns:
                header_candidates.append((line_num, column_count, row))

    # If no multi-column rows found, assume it's a normal CSV starting at line 0
    if not header_candidates:
        return CsvMetadata(skip_rows=0, metadata=metadata, dialect=dialect)

    # Look for the first row that has close to the maximum number of columns
    # This helps distinguish metadata (usually fewer columns) from real headers (many columns)
    threshold = max(min_columns, max_columns * threshold_ratio)

    for line_num, column_count, _row in header_candidates:
        if column_count >= threshold:
            return CsvMetadata(skip_rows=line_num, metadata=metadata, dialect=dialect)

    # If no clear header found but we have candidates, return the first multi-column row
    first_candidate_line = header_candidates[0][0]
    return CsvMetadata(skip_rows=first_candidate_line, metadata=metadata, dialect=dialect)
