from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path

from rich.style import Style
from rich.text import Text
from typing_extensions import override

from kash.config.logger import get_logger
from kash.config.text_styles import STYLE_HINT
from kash.model.paths_model import StorePath
from kash.shell.output.kerm_codes import KriLink, TextTooltip, UIAction, UIActionType
from kash.utils.common.atomic_var import AtomicVar
from kash.utils.common.format_utils import fmt_loc
from kash.utils.errors import InvalidState
from kash.workspaces import current_ws

log = get_logger(__name__)


class LinkFormatter(ABC):
    """
    Base class for adding URL links to values.
    """

    @abstractmethod
    def tooltip_link(self, text: str, tooltip: str | None = None, style: str | Style = "") -> Text:
        """Text with a tooltip."""
        pass

    @abstractmethod
    def path_link(self, path: Path, link_text: str, style: str | Style = "") -> Text:
        """A link to a local path (file or directory)."""
        pass

    @abstractmethod
    def command_link(self, command_str: str, style: str | Style = "") -> Text:
        """Text that links to a command."""
        pass


class PlaintextFormatter(LinkFormatter):
    """
    A plaintext formatter that doesn't use links.
    """

    @override
    def tooltip_link(self, text: str, tooltip: str | None = None, style: str | Style = "") -> Text:
        return Text(text, style=style)

    @override
    def path_link(self, path: Path, link_text: str, style: str | Style = "") -> Text:
        return Text(fmt_loc(link_text), style=style)

    @override
    def command_link(self, command_str: str, style: str | Style = "") -> Text:
        return Text.assemble(
            Text("`", style=STYLE_HINT),
            Text(command_str, style=style),
            Text("`", style=STYLE_HINT),
        )

    def __repr__(self) -> str:
        return "PlaintextFormatter()"


class DefaultLinkFormatter(PlaintextFormatter):
    """
    A formatter that adds OSC 8 links to the local server.
    """

    @override
    def tooltip_link(self, text: str, tooltip: str | None = None, style: str | Style = "") -> Text:
        if tooltip:
            link = KriLink.with_attrs(text, hover=TextTooltip(text=tooltip))
            return link.as_rich(style=style)
        else:
            return Text(text, style=style)

    @override
    def path_link(self, path: Path, link_text: str, style: str | Style = "") -> Text:
        from kash.local_server.local_server_routes import local_url

        url = local_url.file_view(path)
        link = KriLink.with_attrs(
            link_text,
            href=url,
            click=UIAction(action_type=UIActionType.paste_text),
            double_click=UIAction(action_type=UIActionType.open_iframe_popover),
        )
        return link.as_rich(style=style)

    @override
    def command_link(self, command_str: str, style: str | Style = "") -> Text:
        from kash.local_server.local_server_routes import local_url

        url = local_url.explain(text=command_str)
        return Text.assemble(
            Text("`", style=STYLE_HINT),
            KriLink.with_attrs(
                command_str,
                href=url,
                click=UIAction(action_type=UIActionType.paste_text),
                double_click=UIAction(action_type=UIActionType.run_command),
            ).as_rich(style=style),
            Text("`", style=STYLE_HINT),
        )

    def __repr__(self) -> str:
        return "DefaultFormatter()"


class WorkspaceLinkFormatter(DefaultLinkFormatter):
    """
    A formatter that also has workspace context so can add workspace-specific links.
    Works fine for non-workspace Paths too.
    """

    def __init__(self, ws_name: str):
        self.ws_name = ws_name

    @override
    def path_link(self, path: Path, link_text: str, style: str | Style = "") -> Text:
        if isinstance(path, StorePath):
            from kash.local_server.local_server_routes import local_url

            url = local_url.item_view(store_path=path, ws_name=self.ws_name)
            link = KriLink.with_attrs(
                link_text,
                href=url,
                click=UIAction(action_type=UIActionType.paste_text),
                double_click=UIAction(action_type=UIActionType.open_iframe_popover),
            )
            return link.as_rich(style=style)
        else:
            return super().path_link(path, link_text, style=style)

    def __repr__(self):
        return f"WorkspaceLinkFormatter(ws_name={self.ws_name})"


_local_urls_enabled = AtomicVar(False)


def enable_local_urls(enabled: bool):
    _local_urls_enabled.set(enabled)


@contextmanager
def local_url_formatter(ws_name: str | None = None):
    """
    Context manager to make it easy to format store paths with links to the local
    server for more info. If ws_name is None, use the default formatter.
    """
    if _local_urls_enabled:
        try:
            ws_name = current_ws().name
            fmt = WorkspaceLinkFormatter(ws_name)
        except InvalidState:
            fmt = DefaultLinkFormatter()
            log.warning("Using DefaultLinkFormatter()")
    else:
        fmt = PlaintextFormatter()

    log.info("Using %s", fmt)
    try:
        yield fmt
    finally:
        pass
