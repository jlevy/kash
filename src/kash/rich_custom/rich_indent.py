from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult

from rich.jupyter import JupyterMixin
from rich.measure import Measurement
from rich.segment import Segment
from rich.style import Style


class Indent(JupyterMixin):
    """
    Add a left indent to text using a custom string. Rich currently has Padding
    but it only lets you use whitespace indents.

    Example:
        >>> print(Indent("Hello", "-> ", style="blue"))

    Args:
        renderable: String or other renderable.
        indent: Text or string to use for indentation. Default is 4 spaces.
        style: Style to apply to the indent string.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        indent: str = "    ",
        style: Style | None = None,
    ):
        if style is None:
            style = Style.null()
        self.renderable = renderable
        self.indent = indent
        self.style = style

    def __repr__(self) -> str:
        return f"Indent({self.renderable!r}, {self.indent!r})"

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        indent_width = len(self.indent)

        # Calculate available width for content
        width = options.max_width
        render_options = options.update_width(width - indent_width)

        # Get rendered lines
        lines = console.render_lines(self.renderable, render_options, pad=True)

        # Yield indented lines
        for line in lines:
            yield Segment(self.indent, style=self.style)
            yield from line
            yield Segment.line()

    def __rich_measure__(self, console: "Console", options: "ConsoleOptions") -> "Measurement":
        # Get the width of the indent string
        indent_width = len(self.indent)

        # Get measurement of content
        max_width = options.max_width
        if max_width - indent_width < 1:
            return Measurement(max_width, max_width)

        measure_min, measure_max = Measurement.get(console, options, self.renderable)
        measurement = Measurement(measure_min + indent_width, measure_max + indent_width)
        measurement = measurement.with_maximum(max_width)
        return measurement
