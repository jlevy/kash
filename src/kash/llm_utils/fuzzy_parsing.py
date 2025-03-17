import json
import re
from textwrap import dedent

from thefuzz import fuzz


def is_no_results(response: str, sentinel: str = "(No results)") -> bool:
    """
    Check if the response approximately is empty or is the sentinel value.
    """
    return fuzzy_match(response, "") or fuzzy_match(response, sentinel)


def fuzzy_match(response: str, sentinel: str, threshold: int = 80) -> bool:
    """
    Check if the response approximately the same as a sentinel value.
    """
    response = response.lower().strip()
    sentinel = sentinel.lower().strip()
    return bool(response and fuzz.ratio(response, sentinel) > threshold)


def strip_markdown_fence(
    content: str, max_lines_to_strip: int = 15, max_fraction_to_strip: float = 0.2
) -> str:
    """
    This is a useful filter if you ask an LLM to write code and tell it to just
    give you the code, but it still sometimes includes a silly "Here is the code"
    followed by the fence block. Removes the fence block if most of the response
    is in the fenced block.
    """
    content = content.strip()
    code_block_pattern = r"(?:^|\n)```(?:\w+)?\s*\n(.*?)\n```"
    match = re.search(code_block_pattern, content, re.DOTALL)
    if match:
        stripped = match.group(1).strip()
    else:
        stripped = content.strip()

    if (
        len(stripped) - len(content) <= max(2, len(content) * max_fraction_to_strip)
        or len(stripped.splitlines()) < max_lines_to_strip
    ):
        return stripped
    else:
        return stripped


def fuzzy_parse_json(content: str):
    """
    Attempt to parse JSON data from a string, after removing any markdown code blocks.
    """
    json_str = strip_markdown_fence(content)

    # Try to find the first '{' or '[' and the corresponding closing '}' or ']'
    try:
        # Check for JSON object.
        start = json_str.find("{")
        end = json_str.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_substring = json_str[start : end + 1]
            return json.loads(json_substring)
        else:
            # Check for JSON array.
            start = json_str.find("[")
            end = json_str.rfind("]")
            if start != -1 and end != -1 and end > start:
                json_substring = json_str[start : end + 1]
                return json.loads(json_substring)
        # If no JSON structure found, try parsing the entire string.
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None


## Tests


def test_fuzzy_parsing():
    response = dedent(
        """
        ```
        code
        ```
        """
    ).strip()
    assert strip_markdown_fence(response) == "code"

    response = dedent(
        """
        Blah blah.
        
        ```markdown
        This is a test.
        ```

        Blah blah.
        """
    )
    assert strip_markdown_fence(response) == "This is a test."

    response = """
    ```json
    {
        "key": "value"
    }
    """
    expected = {"key": "value"}
    assert fuzzy_parse_json(response) == expected

    response = '{ "key": "value" }'
    expected = {"key": "value"}
    assert fuzzy_parse_json(response) == expected

    response = "This is not JSON."
    assert fuzzy_parse_json(response) is None
