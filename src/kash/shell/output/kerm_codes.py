"""
Kerm Codes
==========

This is a draft schema for "Kerm codes" for terminal applications.

The idea of Kerm codes is to enable terminals and command-line applications
to provide a richer user interface, blending terminal and basic web-style UI
elements. By incorporating these codes, rather than just plain text, advanced
terminals can display links, tooltips, buttons, and interactive input elements.

This schema specifies a method to encode UI elements as structured data and
transmit them through OSC (Operating System Command) codes. These codes are
named after Kerm, a new terminal app, but could be used with any application.

These codes are backward compatible with existing terminals, which will either
ignore these codes or render them as links.

UI elements such as tooltips, buttons, popovers, and input fields are defined
via a simple JSON schema, specified here using Pydantic. These elements
are serialized in either of two ways:

- Directly as JSON
- As "kui://" URIs (called here KRIs)

The terminal or any other front-end code parses and renders these elements
encoded in these formats.

JSON and KRI formats are each useful in different contexts. Some UI elements
are attached to text in the terminal, while other times, an application may
just want to create a new UI element.

If the UI element is attached to text, such as a tooltip or a button, OSC 8
hyperlinks are used encode the KRI for the desired UI element. Note regular
URLs are a special case of KRIs so can be used as normal in a terminal that
supports OSC 8 links, so this scheme simply augments standard terminal links.

If the UI element is standalone, such as a button or input field, we use a new,
previously unused code, OSC 77. We've picked this code since it's not used by
other applications and is ignored by terminals that don't support it.

By adding these two codes to terminal text, it's possible to create a flexible
system for displaying enriched UIs within terminal applications that support
them. This approach allows incrementally adding rich UIs to text applications
while not breaking functionality in existing terminals.

See also:
https://github.com/Alhadis/OSC8-Adoption
https://github.com/chromium/hterm/blob/main/doc/ControlSequences.md#OSC
https://www.ethanheilman.com/x/28/index.html
"""

# TODO: Think through more use cases:
# - Toggle boxes around content in a terminal (e.g. log details hidden by
#   default that can be expanded; in xterm.js this would be a combo of
#   decoration and refreshing the buffer code on expand).
# - Multiple command confirmation (or line-by-line script execution), e.g.
#   sending a script with a list of commands the user can click one by one to run.
# - Marking multiple lines of text (e.g. output of a command) with context
#   (e.g. command that generated text output) on hover.
# - Status (e.g. progress bars or network usage or progress stats, probably
#   via an iframe with live updates).
# - Notifications.
# - Editable state, e.g. display a list of settings with checkboxes or
#   fields the user can edit (saved via a web server serving the page in an iframe).
# - Registering behaviors on regexes (e.g. local web server with info about
#   files, so that legacy shell commands automatically have tooltips with info
#   about files).

from enum import Enum
from html import escape
from typing import Annotated, Literal, Self, TypeAlias
from urllib.parse import parse_qs, quote, urlencode, urlparse

from prompt_toolkit.formatted_text import FormattedText
from pydantic import BaseModel, Field, TypeAdapter, model_validator
from rich.style import Style
from rich.text import Text

from kash.shell.utils.osc_utils import OscStr, osc8_link, osc8_link_codes, osc8_link_rich, osc_code

KC_VERSION = 0
"""Version of the Kerm codes format. Update when we make breaking changes."""

KERM_OSC = 77
"""A lucky OSC code not used by other applications."""

KUI_PROTOCOL = "kui:"
"""The "protocol" portion of Kerm code URIs."""

KUI_SCHEME = f"{KUI_PROTOCOL}//"
"""The Kerm code URI scheme for embedding UI elements into links."""


class UIActionType(str, Enum):
    paste_text = "paste_text"
    """Default action for pasting text into the terminal. If value is omitted, paste the link text."""

    paste_href = "paste_href"
    """Action for pasting the link URL into the terminal. If value is omitted, paste the href attribute."""

    run_command = "run_command"
    """Action for running a command in the terminal. If value is omitted, run the link text."""

    open_iframe_popover = "open_iframe_popover"
    """Action for opening an iframe popover. If value is omitted, open the href attribute."""


class UIAction(BaseModel):
    """
    An action triggered by a UI element, such as pasting text or running a command.
    """

    action_type: UIActionType = Field(..., description="Action type.")
    value: str | None = Field(default=None, description="Action value.")

    def as_json(self) -> str:
        """
        Serialize to standard JSON format.
        """
        return self.model_dump_json()


class DisplayStyle(str, Enum):
    """
    Style for text.
    """

    plain = "plain"
    underline = "underline"
    highlight = "highlight"


class Position(BaseModel):
    """
    Position hints for UI elements.
    """

    x: int = Field(..., description="X position.")
    y: int = Field(..., description="Y position.")


class Dimensions(BaseModel):
    """
    Dimensions hints for UI elements.
    """

    width: int = Field(..., description="Width.")
    height: int = Field(..., description="Height.")


class DisplayHints(BaseModel):
    """
    Hints for UI elements.
    """

    position: Position | None = Field(default=None, description="Position.")
    dimensions: Dimensions | None = Field(default=None, description="Dimensions.")


class UIRole(str, Enum):
    tooltip = "tooltip"
    popover = "popover"
    output = "output"
    input = "input"


class UIElementType(str, Enum):
    text_tooltip = "text_tooltip"
    link_tooltip = "link_tooltip"
    iframe_tooltip = "iframe_tooltip"

    iframe_popover = "iframe_popover"

    chat_output = "chat_output"

    chat_input = "chat_input"
    button = "button"
    multiple_choice = "multiple_choice"


class UIElement(BaseModel):
    """
    Base class for all UI elements.
    """

    role: UIRole
    element_type: UIElementType
    kc_version: int = Field(default=KC_VERSION, description="Kerm code version.")
    hints: DisplayHints | None = Field(default=None, description="Display hints.")

    @model_validator(mode="after")
    def validate_version(self) -> Self:
        if self.kc_version < KC_VERSION:
            raise ValueError(
                f"Incompatible Kerm code version: expected {KC_VERSION}, got {self.kc_version}"
            )
        return self

    def as_json(self) -> str:
        """
        Serialize to a standard JSON format.
        """
        return self.model_dump_json()

    def as_osc(self) -> OscStr:
        """
        Convert to an OSC 77 code.
        """
        return osc_code(KERM_OSC, self.as_json())


class TooltipElement(UIElement):
    """
    Base for tooltip elements, which appear over the terminal and are transient.
    """

    role: Literal[UIRole.tooltip] = UIRole.tooltip


class PopoverElement(UIElement):
    """
    Base for popover elements, which appear over the terminal and are persistent.
    """

    role: Literal[UIRole.popover] = UIRole.popover


class TerminalElement(UIElement):
    """
    Base for elements that can be displayed within the terminal (as text or in
    place of text).
    """


class OutputElement(TerminalElement):
    """
    Base for output elements.
    """

    role: Literal[UIRole.output] = UIRole.output


class InputElement(TerminalElement):
    """
    Base for input elements.
    """

    role: Literal[UIRole.input] = UIRole.input


class TextTooltip(TooltipElement):
    """
    A simple text tooltip.
    """

    element_type: Literal[UIElementType.text_tooltip] = UIElementType.text_tooltip
    text: str = Field(..., description="Tooltip text.")


class LinkTooltip(TooltipElement):
    """
    A tooltip with info about a URL. Typically this would be a tooltip like with a
    preview of the page or the title and description of the page.
    """

    element_type: Literal[UIElementType.link_tooltip] = UIElementType.link_tooltip
    url: str = Field(..., description="Tooltip URL.")


class IframeTooltip(TooltipElement):
    """
    A tooltip that is an iframe.
    """

    element_type: Literal[UIElementType.iframe_tooltip] = UIElementType.iframe_tooltip
    url: str = Field(..., description="Tooltip iframe URL.")

    def to_kri(self) -> str:
        return self.url


class IframePopover(PopoverElement):
    """
    A popover that is an iframe.
    """

    element_type: Literal[UIElementType.iframe_popover] = UIElementType.iframe_popover
    url: str = Field(..., description="Popover iframe URL.")


class ChatOutput(OutputElement):
    """
    Chat-like output or response element.
    """

    element_type: Literal[UIElementType.chat_output] = UIElementType.chat_output
    text: str = Field(..., description="Chat text.")


class ChatInput(InputElement):
    """
    Chat-like input element.
    """

    element_type: Literal[UIElementType.chat_input] = UIElementType.chat_input
    prompt: str = Field(..., description="Initial prompt.")


class Button(InputElement):
    """
    A clickable button.
    """

    element_type: Literal[UIElementType.button] = UIElementType.button
    text: str = Field(..., description="Button label.")
    action: UIAction = Field(..., description="Button action.")


class MultipleChoice(InputElement):
    """
    Multiple-choice input element.
    """

    element_type: Literal[UIElementType.multiple_choice] = UIElementType.multiple_choice
    options: list[str] = Field(..., description="Choice options.")


TooltipUnion: TypeAlias = Annotated[
    TextTooltip | LinkTooltip | IframeTooltip,
    Field(discriminator="element_type"),
]

tooltip_adapter: TypeAdapter[TooltipUnion] = TypeAdapter(TooltipUnion)


UIElementUnion: TypeAlias = Annotated[
    TextTooltip
    | LinkTooltip
    | IframeTooltip
    | IframePopover
    | ChatOutput
    | ChatInput
    | Button
    | MultipleChoice,
    Field(discriminator="element_type"),
]

ui_element_adapter: TypeAdapter[UIElementUnion] = TypeAdapter(UIElementUnion)


class TextAttrs(BaseModel):
    """
    Attributes, including link, hover, click, and display element, for text.
    """

    href: str | None = Field(
        default=None,
        description="Target URL, if this text is a link.",
    )
    hover: TooltipUnion | None = Field(default=None, description="Hover element.")
    click: UIAction | None = Field(default=None, description="Click action.")
    double_click: UIAction | None = Field(default=None, description="Double click action.")
    display_style: DisplayStyle = Field(
        default=DisplayStyle.plain, description="Display style for this text."
    )

    @model_validator(mode="after")
    def validate_self(self) -> Self:
        if self.href and not urlparse(self.href).scheme:
            raise ValueError(f"Not a valid URL: {self.href}")
        if not self.href and not self.hover and not self.click and not self.double_click:
            raise ValueError(f"No text attributes set: {self}")
        return self

    @classmethod
    def from_json_dict(cls, json_dict: dict[str, str]) -> Self:
        """
        Deserialize from a set of JSON values.
        """
        href = json_dict.get("href")
        hover = json_dict.get("hover")
        click = json_dict.get("click")
        double_click = json_dict.get("double_click")
        return cls(
            href=href,
            hover=(tooltip_adapter.validate_json(hover) if hover else None),
            click=(UIAction.model_validate_json(click) if click else None),
            double_click=(UIAction.model_validate_json(double_click) if double_click else None),
        )

    def as_json_dict(self) -> dict[str, str]:
        """
        Convert to a dictionary of JSON values, omitting None values.
        Sort keys to ensure deterministic ordering.
        """
        base = {
            "href": self.href,
            "hover": self.hover.as_json() if self.hover else None,
            "click": self.click.as_json() if self.click else None,
            "double_click": self.double_click.as_json() if self.double_click else None,
            "display_style": self.display_style.value,
        }
        # Filter out None values and sort by keys
        return dict(sorted((k, v) for k, v in base.items() if v is not None))


class Kri(BaseModel):
    """
    A KRI is a URI that can be used to specify how terminal text will be displayed.

    It may be a regular URL, which is usable as the href of a link in the usual way,
    or a "Kerm URI" conveying richer metadata.

    A Kerm URI is a `kui://` URI with a query string containing key-value pairs
    that specify the attributes for the text.

    Each query string value is optional and may be omitted. If present it is
    an escaped, serialized JSON string. Within serialized JSON, fields that are
    optional may either be omitted or set to null.
    """

    attrs: TextAttrs = Field(
        description="Attributes for this KRI, either the href or the other attributes.",
    )

    @classmethod
    def for_url(cls, url: str) -> Self:
        return cls(attrs=TextAttrs(href=url))

    @classmethod
    def parse(cls, uri_str: str) -> Self:
        """
        Parse a URI string into a Kri.
        """
        # Convert AnyUrl to string if needed
        uri_str = str(uri_str)

        # Parse kui:// URIs.
        if uri_str.startswith(KUI_SCHEME):
            parsed = urlparse(uri_str)
            qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            if not qs:
                raise ValueError(f"Invalid KRI with no query string: {uri_str}")
            metadata = TextAttrs.from_json_dict(qs)
            return cls(attrs=metadata)
        else:
            return cls.for_url(uri_str)

    @property
    def uri_str(self) -> str:
        """
        The full URI, including the type and metadata.
        Note that we use cautious URL encoding, i.e. %20 and not + for encodingspaces.
        """
        if self.attrs.href and self.is_simple_url():
            return self.attrs.href
        else:
            return f"{KUI_SCHEME}?{urlencode(self.attrs.as_json_dict(), quote_via=quote)}"

    def is_simple_url(self) -> bool:
        return bool(
            self.attrs.href
            and not self.attrs.hover
            and not self.attrs.click
            and not self.attrs.double_click
            and self.attrs.display_style == DisplayStyle.plain
        )

    def __str__(self) -> str:
        return self.uri_str


class KriLink(BaseModel):
    """
    A text link with a URL or KRI and link text. Serializable as an OSC 8 hyperlink.
    """

    kri: Kri
    link_text: str

    @classmethod
    def with_attrs(
        cls,
        link_text: str,
        href: str | None = None,
        hover: TooltipUnion | None = None,
        click: UIAction | None = None,
        double_click: UIAction | None = None,
        display_style: DisplayStyle = DisplayStyle.plain,
    ) -> Self:
        return cls(
            kri=Kri(
                attrs=TextAttrs(
                    href=href,
                    hover=hover,
                    click=click,
                    double_click=double_click,
                    display_style=display_style,
                )
            ),
            link_text=link_text,
        )

    def as_osc8(self) -> OscStr:
        return osc8_link(self.kri.uri_str, self.link_text)

    def as_ptk_tokens(self, style: str = "") -> FormattedText:
        osc8_start, osc8_end = osc8_link_codes(self.kri.uri_str, self.link_text)
        fragments = [
            ("[ZeroWidthEscape]", osc8_start),  # Start of OSC8 hyperlink (zero-width escape).
            (style, self.link_text),  # The visible hyperlink text
            ("[ZeroWidthEscape]", osc8_end),  # End of OSC8 hyperlink (zero-width escape)
        ]
        return FormattedText(fragments)

    def as_rich(self, style: str | Style = "") -> Text:
        return osc8_link_rich(self.kri.uri_str, self.link_text, style=style)

    def as_html(self) -> str:
        return f'<a href="{escape(self.kri.uri_str, quote=True)}">{escape(self.link_text)}</a>'

    def as_json(self) -> str:
        return self.model_dump_json()


## Tests


def test_examples():
    text_tooltip = TextTooltip(text="Hello")
    link_tooltip = LinkTooltip(url="https://example.com")
    button = Button(
        text="Click me",
        action=UIAction(action_type=UIActionType.paste_text, value="ls"),
    )
    popover_element = IframePopover(
        url="https://example.com",
        hints=DisplayHints(
            position=Position(x=10, y=10), dimensions=Dimensions(width=100, height=100)
        ),
    )

    print(f"\ntext_tooltip: {text_tooltip.as_json()}")
    print(f"\nlink_tooltip: {link_tooltip.as_json()}")
    print(f"\nbutton: {button.as_json()}")
    print(f"\npopover_element: {popover_element.as_json()}")

    # Test round-tripping.
    for element in [button, popover_element]:
        parsed = ui_element_adapter.validate_json(element.as_json())
        assert parsed.element_type == element.element_type
        assert parsed.as_json() == element.as_json()
        assert parsed.as_osc() == element.as_osc()


def test_kri():
    kri1 = Kri.for_url("https://example.com")
    kri2 = Kri(attrs=TextAttrs(hover=TextTooltip(text="Tooltip text")))
    kri3 = Kri(
        attrs=TextAttrs(
            hover=TextTooltip(text="List files"),
            click=UIAction(action_type=UIActionType.paste_text),
            double_click=UIAction(action_type=UIActionType.run_command, value="ls -l"),
        )
    )

    print(f"\nkri1: {kri1.uri_str}")
    print(f"\nkri2: {kri2.uri_str}")
    print(f"\nkri3: {kri3.uri_str}")

    assert Kri.parse(kri1.uri_str) == kri1
    assert Kri.parse(kri2.uri_str) == kri2
    assert Kri.parse(kri3.uri_str) == kri3

    link1 = KriLink(kri=kri1, link_text="Example link")
    link2 = KriLink(kri=kri2, link_text="Text with hover")
    link3 = KriLink(kri=kri3, link_text="List files")

    print(f"\nlink1: {link1.as_html()}")
    print(f"\nlink2: {link2.as_html()}")
    print(f"\nlink3: {link3.as_html()}")

    assert link1.as_html() == '<a href="https://example.com">Example link</a>'
    assert (
        link2.as_html()
        == '<a href="kui://?display_style=plain&amp;hover=%7B%22role%22%3A%22tooltip%22%2C%22element_type%22%3A%22text_tooltip%22%2C%22kc_version%22%3A0%2C%22hints%22%3Anull%2C%22text%22%3A%22Tooltip%20text%22%7D">Text with hover</a>'
    )
