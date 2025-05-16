from kash.model.items_model import Item
from kash.utils.file_utils.file_formats_model import Format
from kash.web_gen.template_render import render_web_template


def simple_webpage_render(
    item: Item,
    page_template: str = "simple_webpage.html.jinja",
    add_title_h1: bool = True,
) -> str:
    """
    Generate a simple web page from a single item.
    If `add_title_h1` is True, the title will be inserted as an h1 heading above the body.
    """
    return render_web_template(
        template_filename=page_template,
        data={
            "title": item.abbrev_title(),
            "add_title_h1": add_title_h1,
            "content_html": item.body_as_html(),
            "thumbnail_url": item.thumbnail_url,
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
    html = simple_webpage_render(item)

    os.makedirs("tmp", exist_ok=True)
    with open("tmp/simple_webpage.html", "w") as f:
        f.write(html)
    print("Rendered simple webpage to tmp/simple_webpage.html")

    # Basic validation
    assert item.title and item.title in html
    assert "<b>HTML content</b>" in html
