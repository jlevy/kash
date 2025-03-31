from enum import Enum
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from kash.config import colors
from kash.config.logger import get_logger, record_console
from kash.config.settings import global_settings
from kash.file_storage.file_store import FileStore
from kash.help.help_printing import print_explain_command
from kash.llm_utils import LLM
from kash.local_server.rich_html_template import RICH_HTML_TEMPLATE
from kash.model.items_model import Item
from kash.model.paths_model import StorePath
from kash.shell.file_icons.nerd_icons import icon_for_file
from kash.shell.output.shell_output import Wrap
from kash.utils.common.type_utils import not_none
from kash.utils.errors import FileNotFound, InvalidFilename
from kash.web_gen import base_templates_dir
from kash.web_gen.template_render import render_web_template
from kash.workspaces.workspace_output import print_file_info

log = get_logger(__name__)


router = APIRouter()

DEFAULT_MAX_LINES = 1000


def server_get_workspace(ws_name: str) -> FileStore:
    from kash.workspaces import get_ws

    file_store = get_ws(ws_name)
    if not file_store:
        raise HTTPException(status_code=404, detail=f"Workspace not found: `{ws_name}`")
    return file_store


def format_local_url(route_path: str, **params: str | None) -> str:
    """
    URL to content on the local server.
    """
    from kash.local_server.local_server import LOCAL_SERVER_HOST

    settings = global_settings()
    route_path = route_path.strip("/")
    url = f"http://{LOCAL_SERVER_HOST}:{settings.local_server_port}/{route_path}"
    if params:
        query_params = {k: v for k, v in params.items() if v is not None}
        if query_params:
            query_string = urlencode(query_params)
            url += f"?{query_string}"
    return url


class Route(str, Enum):
    file_view = "/file/view"
    item_view = "/item/view"
    explain = "/explain"


class _LocalUrl:
    def file_view(self, path: Path) -> str:
        return format_local_url(Route.file_view, path=str(path))

    def item_view(
        self, store_path: StorePath, ws_name: str, max_lines: int = DEFAULT_MAX_LINES
    ) -> str:
        params = {
            "store_path": store_path.display_str(),
            "ws_name": ws_name,
            "max_lines": str(max_lines),
        }
        return format_local_url(Route.item_view, **params)

    def explain(self, text: str) -> str:
        return format_local_url(Route.explain, text=text)


local_url = _LocalUrl()
"""Create URLs for the local server."""


@router.api_route(Route.file_view, methods=["GET", "HEAD"])
def file_view(request: Request, path: str, max_lines: int = DEFAULT_MAX_LINES):
    # Treat the file like an external path for the purposes of viewing.
    try:
        p = Path(path)
        body_text, footer_note = None, None
        if p.is_file():
            item_or_path = Item.from_external_path(p)
            if item_or_path.format and item_or_path.format.is_text:
                body_text, footer_note = _file_body_and_footer(p, max_lines=max_lines)
        else:
            item_or_path = p

        page_self_url = local_url.file_view(path=p)

        return _serve_item(
            request,
            item_or_path,
            page_self_url,
            body_text,
            footer_note,
            brief_header=True,  # For non-workspace files, don't show the item header.
        )
    except (InvalidFilename, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")


@router.api_route(Route.item_view, methods=["GET", "HEAD"])
def item_view(request: Request, store_path: str, ws_name: str, max_lines: int = DEFAULT_MAX_LINES):
    try:
        sp = StorePath(store_path)
        item = server_get_workspace(ws_name).load(sp)
        if not item:
            raise FileNotFound(store_path)

        page_self_url = local_url.item_view(store_path=sp, ws_name=ws_name, max_lines=max_lines)

        body_text, footer_note = None, None
        if item.format and item.format.is_text:
            body_text, footer_note = _text_body_and_footer(item.body_text(), max_lines=max_lines)

        return _serve_item(request, item, page_self_url, body_text, footer_note, brief_header=False)
    except (FileNotFound, InvalidFilename, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=f"Item not found: {e}")


@router.api_route(Route.explain, methods=["GET"])
def explain(text: str):
    with record_console() as console:
        print_explain_command(text, assistant_model=LLM.default_fast)
    help_html = console.export_html(code_format=RICH_HTML_TEMPLATE, theme=colors.rich_terminal)

    page_url = local_url.explain(text)

    return HTMLResponse(
        render_web_template(
            base_templates_dir,
            "base_webpage.html.jinja",
            {
                "title": f"Help: {text}",
                "content": render_web_template(
                    base_templates_dir,
                    "explain_view.html.jinja",
                    {"help_html": help_html, "page_url": page_url},
                ),
            },
        )
    )


def _read_lines(path: Path, max_lines: int = DEFAULT_MAX_LINES) -> tuple[str, int | None]:
    """
    Read the first `max_lines` lines of a file. Only reads that amount into memory.
    If file was truncated, also return how many bytes were read.
    """
    lines = []
    # TODO: Could make this frontmatter aware but seems okay as is for now.
    # frontmatter_str, offset, _ = fmf_read_frontmatter_raw(path)
    bytes_read = 0
    with open(path) as f:
        for _ in range(max_lines):
            line = f.readline()
            if not line:  # EOF reached
                break
            bytes_read += len(line.encode("utf-8"))
            lines.append(line.rstrip("\n"))

        has_more = bool(f.readline())

    return "\n".join(lines), bytes_read if has_more else None


def _file_body_and_footer(path: Path, max_lines: int) -> tuple[str, str | None]:
    body_text, truncated_at = _read_lines(path, max_lines)
    if truncated_at:
        body_text += "\n…"
        footer_note = f"Text truncated. Showing first {max_lines} lines."
    else:
        footer_note = "(end of file)"
    return body_text, footer_note


def _text_body_and_footer(body_text: str, max_lines: int) -> tuple[str, str | None]:
    if not body_text:
        return "", None

    num_lines = body_text.count("\n")
    if num_lines > max_lines:
        lines = body_text.split("\n", max_lines + 1)
        footer_note = f"Text truncated. Showing first {max_lines} of {num_lines} lines."
        return "\n".join(lines[:max_lines] + ["…"]), footer_note
    else:
        return body_text, "(end of file)"


def _serve_item(
    request: Request,
    item_or_path: Item | Path,
    page_url: str,
    body_text: str | None = None,
    footer_note: str | None = None,
    brief_header: bool = False,
) -> StreamingResponse | HTMLResponse:
    """
    Common logic to serve content of a binary item, or content or info of any item or file.
    """
    if isinstance(item_or_path, Item):
        item = item_or_path
        path = Path(not_none(item.store_path or item.external_path, "Missing path for item"))
    elif isinstance(item_or_path, Path):
        item = None
        path = item_or_path
    else:
        raise ValueError("Missing item or path")

    if not path:
        raise HTTPException(status_code=500, detail="Missing path for item")

    # Handle binary items, serving with a streaming response.
    # TODO: Could also expose thumbnails for images, PDF, etc.
    if item and item.is_binary:
        mime_type = item.format and item.format.mime_type
        if not mime_type:
            mime_type = "application/octet-stream"

        # For HEAD requests, return header with mime type only.
        if request.method == "HEAD":
            return HTMLResponse(status_code=200, headers={"Content-Type": mime_type})

        def file_iterator():
            try:
                with open(path, "rb") as f:
                    while chunk := f.read(8192):  # 8KB chunks
                        yield chunk
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="Item not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error streaming file: {e}")

        return StreamingResponse(
            file_iterator(),
            media_type=mime_type,
        )
    else:
        display_title = item.display_title() if item else str(path)

        # For HEAD requests, return header with mime type only.
        if request.method == "HEAD":
            return HTMLResponse(status_code=200, headers={"Content-Type": "text/html"})

        # Collect file info like size.
        with record_console() as console:
            print_file_info(
                path,
                show_size_details=True,
                show_format=brief_header,  # Don't show format twice.
                text_wrap=Wrap.WRAP,
            )
        file_info_html = console.export_html(
            code_format=RICH_HTML_TEMPLATE, theme=colors.rich_terminal
        )

        dirname = str(path.parent) + "/" if str(path.parent) != "." else ""

        return HTMLResponse(
            render_web_template(
                base_templates_dir,
                "base_webpage.html.jinja",
                {
                    "title": display_title,
                    "content": render_web_template(
                        base_templates_dir,
                        "item_view.html.jinja",
                        {
                            "item": item,
                            "nerd_icon": icon_for_file(path.name, is_dir=path.is_dir()),
                            "brief_header": brief_header,
                            "path": path,
                            "filename": path.name,
                            "dirname": dirname,
                            "page_url": page_url,
                            "file_info_html": file_info_html,
                            "body_text": body_text,
                            "footer_note": footer_note,
                        },
                    ),
                },
            )
        )


# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_text()
#             await websocket.send_text(f"Message received: {data}")
#     except WebSocketDisconnect:
#         log.info("WebSocket disconnected")
