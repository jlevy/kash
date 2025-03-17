import re

from kash.utils.common.parse_shell_args import shell_quote


def is_assist_request_str(line: str) -> str | None:
    """
    Is this a query to the assistant?
    Checks for phrases ending in a ? or starting with a ?.
    """
    line = line.strip()
    if re.search(r"\b\w+\?$", line) or line.startswith("?"):
        return line.lstrip("?").strip()
    return None


def assist_request_str(nl_req: str) -> str:
    """
    Command string to call the assistant with a natural language request.
    """
    nl_req = nl_req.lstrip("? ").rstrip()
    # Quoting isn't necessary unless we have quote marks.
    if "'" in nl_req or '"' in nl_req:
        return f"? {shell_quote(nl_req, idempotent=True)}"
    else:
        return f"? {nl_req}"
