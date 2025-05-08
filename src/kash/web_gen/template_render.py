from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from kash.config import colors


def render_web_template(
    templates_dir: list[Path] | Path,
    template_filename: str,
    data: dict,
    autoescape: bool = True,
    css_overrides: dict[str, str] | None = None,
) -> str:
    """
    Render a Jinja2 template file with the given data, returning an HTML string.
    Can work with one or more template directories.
    """
    if css_overrides is None:
        css_overrides = {}

    search_paths = [templates_dir] if isinstance(templates_dir, Path) else templates_dir
    env = Environment(loader=FileSystemLoader(search_paths), autoescape=autoescape)

    # Load and render the template.
    template = env.get_template(template_filename)

    data = {**data, "color_defs": colors.generate_css_vars(css_overrides)}

    rendered_html = template.render(data)
    return rendered_html
