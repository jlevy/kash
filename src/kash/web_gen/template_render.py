from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from kash.config import colors

_base_templates_dir = Path(__file__).parent / "templates"
"""Common base web page templates."""


_additional_template_dirs: ContextVar[list[Path] | None] = ContextVar(
    "_additional_template_dirs", default=None
)


def get_template_dirs(*dirs: Path) -> list[Path]:
    """
    Returns template directories currently in context along with any
    additional template directories.
    """
    additional = _additional_template_dirs.get() or []
    return list(dirs) + [*additional, _base_templates_dir]


@contextmanager
def additional_template_dirs(*dirs: Path) -> Iterator[None]:
    """
    Context manager for temporarily adding template directories to the search path.
    """
    original = _additional_template_dirs.get()
    current = [] if not original else original.copy()
    token = _additional_template_dirs.set(current + list(dirs))
    try:
        yield
    finally:
        _additional_template_dirs.reset(token)


def render_web_template(
    template_filename: str,
    data: dict,
    autoescape: bool = True,
    css_overrides: dict[str, str] | None = None,
) -> str:
    """
    Render a Jinja2 template file with the given data, returning an HTML string.
    Uses template directories from the base directory and any added via context manager.
    """
    if css_overrides is None:
        css_overrides = {}

    search_paths = get_template_dirs()
    env = Environment(loader=FileSystemLoader(search_paths), autoescape=autoescape)

    # Load and render the template.
    template = env.get_template(template_filename)

    data = {**data, "color_defs": colors.generate_css_vars(css_overrides)}

    rendered_html = template.render(data)
    return rendered_html
