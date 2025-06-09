from __future__ import annotations

import re
from dataclasses import dataclass

from kash.utils.common.url import Url


@dataclass(frozen=True)
class Slice:
    """
    A start and end time range, in seconds.
    """

    start_time: float
    end_time: float

    def __post_init__(self):
        if self.start_time >= self.end_time or self.start_time < 0 or self.end_time <= 0:
            raise ValueError(
                f"Not a valid time slice: got start={self.start_time}, end={self.end_time}"
            )

    @classmethod
    def parse(cls, slice_str: str) -> Slice:
        """
        Parse a slice string in format SSS-SSS or HH:MM:SS-HH:MM:SS.
        """
        if "-" not in slice_str:
            raise ValueError(f"Not a valid time slice: {slice_str!r}")

        start_str, end_str = slice_str.split("-", 1)

        try:
            # Try to parse as HH:MM:SS format first
            start_time = _parse_time_format(start_str)
            end_time = _parse_time_format(end_str)
        except ValueError:
            # Fall back to seconds format
            try:
                start_time = float(start_str)
                end_time = float(end_str)
            except ValueError:
                raise ValueError(f"Not a valid time slice: {slice_str!r}")

        return cls(start_time, end_time)

    def __str__(self) -> str:
        return f"{_format_seconds(self.start_time)}-{_format_seconds(self.end_time)}"


def _parse_time_format(time_str: str) -> float:
    """
    Parse time string in HH:MM:SS format and return seconds.
    Supports formats like: HH:MM:SS, MM:SS, or just SS
    """
    # Match HH:MM:SS, MM:SS, or SS format
    time_pattern = r"^(?:(\d{1,2}):)?(?:(\d{1,2}):)?(\d{1,2}(?:\.\d+)?)$"
    match = re.match(time_pattern, time_str.strip())

    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    hours_str, minutes_str, seconds_str = match.groups()

    # Default values
    hours = int(hours_str) if hours_str else 0
    minutes = int(minutes_str) if minutes_str else 0
    seconds = float(seconds_str) if seconds_str else 0

    # Handle case where we have MM:SS (2 components)
    if hours_str and not minutes_str:
        # This means we actually have MM:SS, not HH:MM
        minutes = hours
        hours = 0

    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds


def _format_seconds(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS, MM:SS, or SS depending on the value.
    Uses the most compact and natural representation.
    """
    total_seconds = int(seconds)
    fractional_part = seconds - total_seconds

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    # Add fractional seconds if present
    if fractional_part > 0:
        secs += fractional_part

    if hours > 0:
        # HH:MM:SS format
        if fractional_part > 0:
            return f"{hours}:{minutes:02d}:{secs:04.1f}"
        else:
            return f"{hours}:{minutes:02d}:{secs:02d}"
    elif minutes > 0:
        # MM:SS format
        if fractional_part > 0:
            return f"{minutes}:{secs:04.1f}"
        else:
            return f"{minutes}:{secs:02d}"
    else:
        # Just seconds
        if fractional_part > 0:
            return f"{secs:.1f}"
        else:
            return str(int(secs))


def is_url_slice(url: Url) -> bool:
    """
    Check if a URL contains valid slice information in its fragment.
    """
    return parse_url_slice(url)[1] is not None


def parse_url_slice(url: Url) -> tuple[Url, Slice | None]:
    """
    Parse slice information from a URL and return the base URL and slice.

    Looks for #~slice=START-END pattern at the end of the URL and validates
    that START-END is a valid time slice format.

    Returns:
        Tuple of (base_url_without_slice, slice_or_none)
    """
    slice_marker = "#~slice="
    slice_index = url.find(slice_marker)

    if slice_index == -1:
        return url, None

    # Extract the slice string after #~slice= (must be at end of URL)
    slice_str = url[slice_index + len(slice_marker) :]

    # Validate slice is at the end (no additional content)
    if not slice_str:
        return url, None

    try:
        slice_obj = Slice.parse(slice_str)
        base_url = Url(url[:slice_index])  # Everything before #~slice=
        return base_url, slice_obj
    except ValueError:
        # Invalid slice format, treat as regular URL
        return url, None


def add_slice_to_url(url: Url, slice_obj: Slice) -> Url:
    """Add slice information to a URL as a fragment."""
    # Remove any existing fragment and add the slice
    fragment_index = url.find("#")
    if fragment_index != -1:
        base_url = Url(url[:fragment_index])
    else:
        base_url = url
    return Url(f"{base_url}#~slice={slice_obj}")


## Tests


def test_url_slice_functionality():
    """Test URL slice functionality with fragment-based encoding."""

    # Basic slice creation and validation
    slice_obj = Slice(10.0, 20.0)
    assert slice_obj.start_time == 10.0
    assert slice_obj.end_time == 20.0
    assert str(slice_obj) == "10-20"

    # Invalid slice creation should raise ValueError
    for start, end in [(20.0, 10.0), (10.0, 10.0), (-5.0, 10.0), (0.0, 0.0)]:
        try:
            Slice(start, end)
            raise AssertionError(f"Should have raised ValueError for start={start}, end={end}")
        except ValueError as e:
            assert "Not a valid time slice" in str(e)

    # Test time format parsing - both seconds and HH:MM:SS formats
    parse_cases = [
        # Format: (input_string, expected_start, expected_end)
        ("10.5-25.7", 10.5, 25.7),  # decimal seconds
        ("30-60", 30.0, 60.0),  # integer seconds
        ("1:30-2:45", 90.0, 165.0),  # MM:SS format
        ("01:23:45-02:30:15", 5025.0, 9015.0),  # HH:MM:SS format
        ("00:01:30.5-00:02:45.25", 90.5, 165.25),  # HH:MM:SS with decimals
    ]

    for slice_str, expected_start, expected_end in parse_cases:
        parsed = Slice.parse(slice_str)
        assert parsed.start_time == expected_start
        assert parsed.end_time == expected_end

    # Test invalid parsing
    for invalid_input in ["invalid", "10_20", "1:2:3:4-5:6:7"]:
        try:
            Slice.parse(invalid_input)
            raise AssertionError(f"Should have raised ValueError for {invalid_input}")
        except ValueError as e:
            assert "Not a valid time slice" in str(e)

    # Run all sub-tests
    test_url_slice_detection()
    test_url_slice_manipulation()
    test_parse_url_slice()


def test_url_slice_detection():
    """Test URL slice detection and extraction."""

    # Test slice detection
    regular_url = Url("https://example.com/video.mp4")
    slice_url = Url("https://example.com/video.mp4#~slice=10-30")
    other_fragment_url = Url("https://example.com/video.mp4#chapter1")

    assert not is_url_slice(regular_url)
    assert is_url_slice(slice_url)
    assert not is_url_slice(other_fragment_url)

    # Test slice extraction
    base_url, slice_obj = parse_url_slice(regular_url)
    assert base_url == regular_url
    assert slice_obj is None

    base_url, slice_obj = parse_url_slice(slice_url)
    assert base_url == "https://example.com/video.mp4"
    assert slice_obj is not None
    if slice_obj:  # Help type checker understand slice_obj is not None
        assert slice_obj.start_time == 10.0
        assert slice_obj.end_time == 30.0

    # Test with HH:MM:SS format
    hms_url = Url("https://example.com/video.mp4#~slice=01:30-02:45")
    base_url, slice_obj = parse_url_slice(hms_url)
    assert base_url == "https://example.com/video.mp4"
    assert slice_obj is not None
    if slice_obj:  # Help type checker understand slice_obj is not None
        assert slice_obj.start_time == 90.0  # 1:30 in seconds
        assert slice_obj.end_time == 165.0  # 2:45 in seconds

    # Test slice at end of URL
    slice_at_end_url = Url("https://example.com/video.mp4#~slice=30-60")
    assert is_url_slice(slice_at_end_url)
    base_url, slice_obj = parse_url_slice(slice_at_end_url)
    assert base_url == "https://example.com/video.mp4"
    assert slice_obj is not None
    if slice_obj:
        assert slice_obj.start_time == 30.0
        assert slice_obj.end_time == 60.0

    # Test invalid slice in fragment
    invalid_slice_url = Url("https://example.com/video.mp4#~slice=invalid-format")
    assert not is_url_slice(invalid_slice_url)
    base_url, slice_obj = parse_url_slice(invalid_slice_url)
    assert base_url == invalid_slice_url
    assert slice_obj is None

    # Test partial slice marker
    partial_slice_url = Url("https://example.com/video.mp4#~slic=10-30")
    assert not is_url_slice(partial_slice_url)


def test_url_slice_manipulation():
    """Test adding slices to URLs."""

    base_url = Url("https://example.com/video.mp4")
    slice_obj = Slice(10.0, 30.0)

    # Add slice to URL
    sliced_url = add_slice_to_url(base_url, slice_obj)
    assert sliced_url == "https://example.com/video.mp4#~slice=10-30"
    assert is_url_slice(sliced_url)

    # Extract it back
    extracted_base, extracted_slice = parse_url_slice(sliced_url)
    assert extracted_base == base_url
    assert extracted_slice is not None
    if extracted_slice:  # Help type checker understand extracted_slice is not None
        assert extracted_slice.start_time == 10.0
        assert extracted_slice.end_time == 30.0

    # Replace existing slice
    new_slice = Slice(20.0, 40.0)
    new_sliced_url = add_slice_to_url(sliced_url, new_slice)
    assert new_sliced_url == "https://example.com/video.mp4#~slice=20-40"

    # URL with existing non-slice fragment
    fragment_url = Url("https://example.com/video.mp4#chapter1")
    sliced_fragment_url = add_slice_to_url(fragment_url, slice_obj)
    assert sliced_fragment_url == "https://example.com/video.mp4#~slice=10-30"


def test_parse_url_slice():
    """Test the parse_url_slice function directly."""

    # Test valid slice formats
    valid_cases = [
        ("https://example.com/video.mp4#~slice=10-30", 10.0, 30.0),
        ("https://example.com/video.mp4#~slice=1:30-2:45", 90.0, 165.0),
    ]

    for url_str, expected_start, expected_end in valid_cases:
        _, slice_obj = parse_url_slice(Url(url_str))
        assert slice_obj is not None
        if slice_obj:
            assert slice_obj.start_time == expected_start
            assert slice_obj.end_time == expected_end

    # Test invalid or missing slices
    invalid_cases = [
        "https://example.com/video.mp4",  # No fragment
        "https://example.com/video.mp4#chapter1",  # Fragment but no slice
        "https://example.com/video.mp4#~slice=",  # Empty slice
        "https://example.com/video.mp4#~slice=invalid",  # Invalid format
        "https://example.com/video.mp4#~slice=10",  # Missing end time
        "https://example.com/video.mp4#~slic=10-30",  # Wrong marker
    ]

    for url_str in invalid_cases:
        _, slice_obj = parse_url_slice(Url(url_str))
        assert slice_obj is None
