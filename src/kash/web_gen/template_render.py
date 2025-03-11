from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader

from kash.config import colors


def render_web_template(
    templates_dir: Path,
    template_filename: str,
    data: dict,
    autoescape: bool = True,
    css_overrides: Dict[str, str] = {},
) -> str:
    """
    Render a Jinja2 template file with the given data, returning an HTML string.
    """

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=autoescape)

    # Load and render the template.
    template = env.get_template(template_filename)

    data = {**data, "color_defs": colors.generate_css_vars(css_overrides)}

    rendered_html = template.render(data)
    return rendered_html
