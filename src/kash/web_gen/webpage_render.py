from kash.model.items_model import Item
from kash.utils.file_utils.file_formats_model import Format
from kash.web_gen.template_render import render_web_template


def render_webpage(
    *,
    title: str,
    content_html: str,
    thumbnail_url: str | None = None,
    add_title_h1: bool = True,
    show_theme_toggle: bool = False,
    page_template: str = "youtube_webpage.html.jinja",
) -> str:
    """
    Generate a simple web page from a single item.
    If `add_title_h1` is True, the title will be inserted as an h1 heading above the body.
    """
    return render_web_template(
        template_filename=page_template,
        data={
            "title": title,
            "add_title_h1": add_title_h1,
            "content_html": content_html,
            "thumbnail_url": thumbnail_url,
            "enable_themes": show_theme_toggle,
            "show_theme_toggle": show_theme_toggle,
        },
    )


## Tests


def test_render():
    import os

    from kash.model.items_model import ItemType

    # Create a test item
    item = Item(
        type=ItemType.doc,
        format=Format.html,
        title="A Simple Web Page",
        body="<p>This is a simple web page with <b>HTML content</b>.</p>",
    )

    # Generate HTML
    html = render_webpage(
        title=item.pick_title(),
        content_html=item.body_as_html(),
        thumbnail_url=item.thumbnail_url,
    )

    os.makedirs("tmp", exist_ok=True)
    with open("tmp/simple_webpage.html", "w") as f:
        f.write(html)
    print("Rendered simple webpage to tmp/simple_webpage.html")

    # Basic validation
    assert item.title and item.title in html
    assert "<b>HTML content</b>" in html
