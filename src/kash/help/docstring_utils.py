from dataclasses import field
from textwrap import dedent

from pydantic.dataclasses import dataclass


@dataclass
class Docstring:
    body: str = ""
    param: dict[str, str] = field(default_factory=dict)
    type: dict[str, str] = field(default_factory=dict)
    returns: str = ""
    rtype: str = ""


def parse_docstring(docstring: str) -> Docstring:
    """
    Parse a reStructuredText-style docstring.
    """
    # TODO: Support other standard docstring formats too.
    docstring = dedent(docstring).strip()

    lines = docstring.split("\n")

    result = Docstring()
    body_lines = []

    for line in lines:
        if line.strip().startswith(":"):
            break
        body_lines.append(line)

    result.body = "\n".join(body_lines).strip()

    parse_fields(lines[len(body_lines) :], result)

    return result


def parse_fields(lines: list[str], result: Docstring):
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


def test_parse_docstring():
    docstring1 = """
    Search for a string in files at the given paths and return their store paths.
    Useful to find all docs or resources matching a string or regex.

    :param sort: How to sort results. Can be `path` or `score`.
    :param ignore_case: Ignore case when searching.
    :type sort: str
    :type ignore_case: bool
    :return: The search results.
    :rtype: CommandOutput
    """

    parsed1 = parse_docstring(docstring1)

    print(f"Body: {parsed1.body}")
    print(f"Params: {parsed1.param}")
    print(f"Types: {parsed1.type}")
    print(f"Returns: {parsed1.returns}")
    print(f"Return type: {parsed1.rtype}")

    assert (
        parsed1.body
        == "Search for a string in files at the given paths and return their store paths.\nUseful to find all docs or resources matching a string or regex."
    )
    assert parsed1.param == {
        "sort": "How to sort results. Can be `path` or `score`.",
        "ignore_case": "Ignore case when searching.",
    }
    assert parsed1.type == {"sort": "str", "ignore_case": "bool"}
    assert parsed1.returns == "The search results."
    assert parsed1.rtype == "CommandOutput"

    docstring2 = """Some text."""

    parsed2 = parse_docstring(docstring2)

    assert parsed2.body == "Some text."
    assert parsed2.param == {}
    assert parsed2.type == {}
    assert parsed2.returns == ""
    assert parsed2.rtype == ""
