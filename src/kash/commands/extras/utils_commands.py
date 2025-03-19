from flowmark import Wrap
from rich.text import Text

from kash.exec import kash_command
from kash.shell.output.shell_output import cprint


@kash_command
def explain_unicode(text: str) -> None:
    """
    Explain the Unicode characters in the given text, showing their hex code and their full Unicode name.
    """
    import unicodedata

    def unicode_char_name(char: str) -> str:
        try:
            return unicodedata.name(char)
        except ValueError:
            return hex(ord(char))

    for i, char in enumerate(text):
        cprint(
            Text.from_markup(
                f"[hint]{i:05d}[/hint]: [key]{char}[/key] [hint]([/hint][emph]{unicode_char_name(char)}[/emph][hint])[/hint]"
            ),
            text_wrap=Wrap.NONE,
        )
