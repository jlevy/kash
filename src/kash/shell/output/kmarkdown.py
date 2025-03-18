from collections.abc import Callable
from textwrap import dedent
from typing import TypeAlias

from markdown_it.token import Token
from rich.console import Console, ConsoleOptions, RenderResult
from rich.padding import Padding
from rich.text import Text

from kash.config.text_styles import STYLE_HINT
from kash.shell.output.kerm_code_utils import clickable_script_block
from kash.utils.rich_custom.rich_markdown_fork import FEATURES, CodeBlock, Markdown

Transform: TypeAlias = Callable[[str], Text]


class TransformingCodeBlock(CodeBlock):
    """
    CodeBlock that applies a transform to its content.
    """

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> "TransformingCodeBlock":
        node_info = token.info or ""
        lexer_name = node_info.partition(" ")[0]
        # Retrieve the code_transform from the markdown instance.
        code_transform = getattr(markdown, "code_transform", None)
        return cls(lexer_name or "text", markdown.code_theme, transform=code_transform)

    def __init__(self, lexer_name: str, theme: str, transform: Transform | None = None) -> None:
        super().__init__(lexer_name, theme)
        self.transform = transform

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        code = str(self.text).lstrip("\n").rstrip()

        if self.transform:
            code = self.transform(code)

        if FEATURES.include_fences:
            # Create the fence line with language if present
            lexer_name = self.lexer_name if self.lexer_name != "text" else ""
            yield Text(f"```{lexer_name}", style=STYLE_HINT)

        # pad=0 for no extra newlines around code blocks.
        yield Padding(code, pad=0)

        if FEATURES.include_fences:
            # Close the fence
            yield Text("```", style=STYLE_HINT)

        # Previously, we used syntax highlighting, but right now having transform do it.
        # yield Syntax(code, self.lexer_name, theme=self.theme, word_wrap=True, padding=0)


class TransformingMarkdown(Markdown):
    """
    Customize Rich's Markdown to apply a transform to code blocks.
    """

    # Override the elements dictionary to use TransformingCodeBlock.
    elements = dict(Markdown.elements)
    elements["fence"] = TransformingCodeBlock
    elements["code_block"] = TransformingCodeBlock

    def __init__(self, markup: str, code_transform: Transform | None = None, **kwargs) -> None:
        super().__init__(markup, **kwargs)
        self.code_transform = code_transform  # Store the transform function.


class KMarkdown(TransformingMarkdown):
    """
    A Markdown instance that renders as usual, but with added Kerm codes.
    Currently just to make code lines clickable.
    """

    def __init__(self, markup: str, **kwargs) -> None:
        super().__init__(markup, code_transform=clickable_script_block, **kwargs)


## Tests


def test_custom_markdown():
    markdown_text = dedent(
        """
        Testing
        ```python
        def hello():
            print("world")
        ```
        """
    )

    def uppercase_code(code: str) -> Text:
        return Text(code.upper())

    md = TransformingMarkdown(markdown_text, code_transform=uppercase_code)

    console = Console(force_terminal=False)
    with console.capture() as capture:
        console.print(md)
    result = [line.rstrip() for line in capture.get().splitlines()]

    expected = [
        "Testing",
        "",
        "```python",
        "DEF HELLO():",
        '    PRINT("WORLD")',
        "```",
    ]

    print(f"\nresult: {result}")
    print(f"\nexpected: {expected}")

    assert result == expected
