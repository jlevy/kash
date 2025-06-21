import re
from dataclasses import dataclass, field
from textwrap import dedent


@dataclass
class Docstring:
    """
    A parsed docstring.
    """

    body: str = ""
    param: dict[str, str] = field(default_factory=dict)
    type: dict[str, str] = field(default_factory=dict)
    returns: str = ""
    rtype: str = ""


def parse_docstring(docstring: str) -> Docstring:
    """
    Parse a docstring in either reStructuredText or Google style format.

    Supports two formats:
    - reStructuredText style: `:param name: description`, `:type name: type`, etc.
    - Google style: `Args:` section with `name (type): description` format

    The parser automatically detects which format is used based on the presence
    of `:param` directives or `Args:` sections.
    """
    docstring = dedent(docstring).strip()

    if not docstring:
        return Docstring()

    # Detect format based on content
    if ":param " in docstring or ":type " in docstring or ":return" in docstring:
        return _parse_rst_docstring(docstring)
    elif re.search(r"\b(Args|Arguments|Returns?):", docstring):
        return _parse_google_docstring(docstring)
    else:
        # No special formatting, just treat as body
        return Docstring(body=docstring)


def _parse_rst_docstring(docstring: str) -> Docstring:
    """
    Parse reStructuredText-style docstring with :param: and :type: directives.
    """
    lines = docstring.split("\n")

    result = Docstring()
    body_lines = []

    for line in lines:
        if line.strip().startswith(":"):
            break
        body_lines.append(line)

    result.body = "\n".join(body_lines).strip()
    _parse_rst_fields(lines[len(body_lines) :], result)
    return result


def _parse_google_docstring(docstring: str) -> Docstring:
    """
    Parse Google-style docstring with Args: and Returns: sections.
    """
    lines = docstring.split("\n")
    result = Docstring()

    # Find sections using regex
    sections = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^(Args|Arguments):\s*$", stripped, re.IGNORECASE):
            sections["args"] = i
        elif re.match(r"^Returns?:\s*$", stripped, re.IGNORECASE):
            sections["returns"] = i

    # Body is everything before the first section
    body_end = min(sections.values()) if sections else len(lines)
    result.body = "\n".join(lines[:body_end]).strip()

    # Parse each section
    if "args" in sections:
        _parse_google_args_section(lines, sections["args"] + 1, result, sections)
    if "returns" in sections:
        _parse_google_returns_section(lines, sections["returns"] + 1, result, sections)

    return result


def _parse_google_args_section(
    lines: list[str], start_idx: int, result: Docstring, sections: dict[str, int]
) -> None:
    """
    Parse the Args: section of a Google-style docstring.
    """
    # Find the end of this section
    end_idx = len(lines)
    for section_start in sections.values():
        if section_start > start_idx:
            end_idx = min(end_idx, section_start)

    # Determine base indentation from first non-empty line
    base_indent = None
    for i in range(start_idx, end_idx):
        line = lines[i]
        if line.strip():
            base_indent = len(line) - len(line.lstrip())
            break

    if base_indent is None:
        return

    i = start_idx
    while i < end_idx:
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Check if this line is at the base indentation level (parameter line)
        line_indent = len(line) - len(line.lstrip())
        if line_indent == base_indent:
            param_line = line.strip()

            # More robust regex that allows underscores and handles various formats
            # Match: name (type): description
            match = re.match(r"([a-zA-Z_]\w*)\s*\(([^)]+)\)\s*:\s*(.*)", param_line)
            if match:
                name, param_type, description = match.groups()
                result.param[name] = description.strip()
                result.type[name] = param_type.strip()
            else:
                # Match: name: description
                match = re.match(r"([a-zA-Z_]\w*)\s*:\s*(.*)", param_line)
                if match:
                    name, description = match.groups()
                    result.param[name] = description.strip()

            # Collect continuation lines (more indented than base)
            i += 1
            continuation_lines = []
            while i < end_idx:
                if not lines[i].strip():
                    i += 1
                    continue
                next_indent = len(lines[i]) - len(lines[i].lstrip())
                if next_indent > base_indent:
                    continuation_lines.append(lines[i].strip())
                    i += 1
                else:
                    break

            # Add continuation to the last parameter
            if continuation_lines and result.param:
                last_param = list(result.param.keys())[-1]
                result.param[last_param] += " " + " ".join(continuation_lines)
        else:
            i += 1


def _parse_google_returns_section(
    lines: list[str], start_idx: int, result: Docstring, sections: dict[str, int]
) -> None:
    """
    Parse the Returns: section of a Google-style docstring.
    """
    # Find the end of this section
    end_idx = len(lines)
    for section_start in sections.values():
        if section_start > start_idx:
            end_idx = min(end_idx, section_start)

    # Collect all content from this section
    content_lines = []
    for i in range(start_idx, end_idx):
        line = lines[i]
        if line.strip():
            content_lines.append(line.strip())

    if content_lines:
        content = " ".join(content_lines).strip()

        # Try to parse "type: description" format
        if ":" in content and not content.startswith(":"):
            parts = content.split(":", 1)
            if len(parts) == 2 and parts[0].strip():
                result.rtype = parts[0].strip()
                result.returns = parts[1].strip()
            else:
                result.returns = content
        else:
            result.returns = content


def _parse_rst_fields(lines: list[str], result: Docstring) -> None:
    """Parse reStructuredText-style field directives."""
    current_field = None
    current_content = []

    def save_current_field():
        if current_field and current_content:
            content = " ".join(current_content).strip()
            if current_field.startswith("param "):
                result.param[current_field[6:]] = content
            elif current_field.startswith("type "):
                result.type[current_field[5:]] = content
            elif current_field == "return":
                result.returns = content
            elif current_field == "rtype":
                result.rtype = content

    for line in lines:
        if line.strip().startswith(":"):
            save_current_field()
            current_field, _, content = line.strip()[1:].partition(":")
            current_content = [content.strip()]
        else:
            current_content.append(line.strip())

    save_current_field()


## Tests


def test_parse_rst_docstring():
    rst_docstring = """
    Search for a string in files at the given paths and return their store paths.
    Useful to find all docs or resources matching a string or regex.

    :param sort: How to sort results. Can be `path` or `score`.
    :param ignore_case: Ignore case when searching.
    :type sort: str
    :type ignore_case: bool
    :return: The search results.
    :rtype: CommandOutput
    """

    parsed = parse_docstring(rst_docstring)

    assert (
        parsed.body
        == "Search for a string in files at the given paths and return their store paths.\nUseful to find all docs or resources matching a string or regex."
    )
    assert parsed.param == {
        "sort": "How to sort results. Can be `path` or `score`.",
        "ignore_case": "Ignore case when searching.",
    }
    assert parsed.type == {"sort": "str", "ignore_case": "bool"}
    assert parsed.returns == "The search results."
    assert parsed.rtype == "CommandOutput"


def test_parse_google_docstring_with_types():
    google_docstring = """
    Search for a string in files at the given paths and return their store paths.
    Useful to find all docs or resources matching a string or regex.

    Args:
        sort (str): How to sort results. Can be `path` or `score`.
        ignore_case (bool): Ignore case when searching.
        
    Returns:
        CommandOutput: The search results.
    """

    parsed = parse_docstring(google_docstring)

    assert (
        parsed.body
        == "Search for a string in files at the given paths and return their store paths.\nUseful to find all docs or resources matching a string or regex."
    )
    assert parsed.param == {
        "sort": "How to sort results. Can be `path` or `score`.",
        "ignore_case": "Ignore case when searching.",
    }
    assert parsed.type == {"sort": "str", "ignore_case": "bool"}
    assert parsed.returns == "The search results."
    assert parsed.rtype == "CommandOutput"


def test_parse_google_docstring_without_types():
    google_no_types = """
    Process the data.

    Args:
        data: The input data to process.
        verbose: Whether to print verbose output.

    Returns:
        The processed result.
    """

    parsed = parse_docstring(google_no_types)

    assert parsed.body == "Process the data."
    assert parsed.param == {
        "data": "The input data to process.",
        "verbose": "Whether to print verbose output.",
    }
    assert parsed.type == {}
    assert parsed.returns == "The processed result."
    assert parsed.rtype == ""


def test_parse_simple_docstring():
    simple_docstring = """Some text."""
    parsed = parse_docstring(simple_docstring)

    assert parsed.body == "Some text."
    assert parsed.param == {}
    assert parsed.type == {}
    assert parsed.returns == ""
    assert parsed.rtype == ""


def test_parse_docstring_with_underscores():
    docstring = """
    Test function.

    Args:
        some_param (str): A parameter with underscores.
        another_param_name: Another parameter without type.
    """

    parsed = parse_docstring(docstring)

    assert parsed.param == {
        "some_param": "A parameter with underscores.",
        "another_param_name": "Another parameter without type.",
    }
    assert parsed.type == {"some_param": "str"}


def test_parse_empty_docstring():
    """Test empty docstring handling."""
    parsed = parse_docstring("")
    assert parsed.body == ""
    assert parsed.param == {}
    assert parsed.type == {}
    assert parsed.returns == ""
    assert parsed.rtype == ""
