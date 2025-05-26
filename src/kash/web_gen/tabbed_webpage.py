import os
from dataclasses import asdict, dataclass

from frontmatter_format import read_yaml_file, to_yaml_string, write_yaml_file
from prettyfmt import abbrev_on_words, sanitize_title

from kash.config.logger import get_logger
from kash.exec.preconditions import has_thumbnail_url
from kash.llm_utils.clean_headings import clean_heading, summary_heading
from kash.model.items_model import Item, ItemType
from kash.model.paths_model import StorePath
from kash.utils.common.type_utils import as_dataclass, not_none
from kash.utils.errors import NoMatch
from kash.utils.file_utils.file_formats_model import Format
from kash.web_gen.template_render import render_web_template
from kash.workspaces import current_ws
from kash.workspaces.source_items import find_upstream_item

log = get_logger(__name__)


@dataclass
class TabInfo:
    label: str
    id: str | None = None
    content_html: str | None = None
    store_path: str | None = None
    thumbnail_url: str | None = None


@dataclass
class TabbedWebpage:
    title: str
    tabs: list[TabInfo]
    show_tabs: bool = True
    add_title_h1: bool = True


def _fill_in_ids(tabs: list[TabInfo]):
    for i, tab in enumerate(tabs):
        if not tab.id:
            tab.id = f"tab_{i}"


def tabbed_webpage_config(
    items: list[Item], clean_headings: bool = False, add_title_h1: bool = True
) -> Item:
    """
    Get an item with the config for a tabbed web page.
    """
    for item in items:
        if not item.store_path:
            raise ValueError(f"Item has no store_path: {item}")

    def get_thumbnail_url(item: Item) -> str | None:
        try:
            item_with_thumbnail = find_upstream_item(item, has_thumbnail_url)
            return item_with_thumbnail.thumbnail_url
        except NoMatch:
            log.warning("Item has no thumbnail URL: %s", item)
            return None

    def clean_label(label: str) -> str:
        if clean_headings:
            return clean_heading(label)
        else:
            return abbrev_on_words(sanitize_title(label), max_len=40)

    tabs = [
        TabInfo(
            label=clean_label(item.pick_title()),
            store_path=item.store_path,
            thumbnail_url=get_thumbnail_url(item),
        )
        for item in items
    ]
    _fill_in_ids(tabs)
    title = summary_heading([item.pick_title() for item in items])
    config = TabbedWebpage(
        title=title, tabs=tabs, show_tabs=len(tabs) > 1, add_title_h1=add_title_h1
    )

    config_item = Item(
        title=f"{title} (config)",
        type=ItemType.config,
        format=Format.yaml,
        body=to_yaml_string(asdict(config)),
    )

    return config_item


def _load_tab_content(config: TabbedWebpage):
    """
    Load the content for each tab.
    """
    for tab in config.tabs:
        html = current_ws().load(StorePath(not_none(tab.store_path))).body_as_html()
        tab.content_html = html


def tabbed_webpage_generate(
    config_item: Item, page_template: str = "base_webpage.html.jinja", add_title_h1: bool = True
) -> str:
    """
    Generate a web page using the supplied config.
    """
    config = config_item.read_as_config()
    tabbed_webpage = as_dataclass(config, TabbedWebpage)  # Checks the format.

    _load_tab_content(tabbed_webpage)

    content = render_web_template(
        template_filename="tabbed_webpage.html.jinja",
        data=asdict(tabbed_webpage),
    )

    return render_web_template(
        page_template,
        data={
            "title": tabbed_webpage.title,
            "add_title_h1": add_title_h1,
            "content": content,
        },
    )


## Tests


def test_render():
    config = TabbedWebpage(
        title="An Elegant Web Page",
        tabs=[
            TabInfo(
                label="Home <escaped HTML chars>",
                content_html="Welcome to the home page! confirming <b>this is HTML</b>",
            ),
            TabInfo(label="Profile", content_html="This is the profile page."),
            TabInfo(label="Contact", content_html="This is the contact page."),
        ],
    )

    os.makedirs("tmp", exist_ok=True)
    write_yaml_file(asdict(config), "tmp/webpage_config.yaml")
    print("\nWrote config to tmp/webpage_config.yaml")

    # Check config reads correctly.
    new_config = as_dataclass(read_yaml_file("tmp/webpage_config.yaml"), TabbedWebpage)
    assert new_config == config

    html = render_web_template(template_filename="tabbed_webpage.html.jinja", data=asdict(config))
    with open("tmp/webpage.html", "w") as f:
        f.write(html)
    print("Rendered tabbed webpage to tmp/webpage.html")

    lines = open("tmp/webpage.html").readlines()
    assert any("Home &lt;escaped HTML chars&gt;" in line for line in lines)
    assert any("<b>this is HTML</b>" in line for line in lines)
