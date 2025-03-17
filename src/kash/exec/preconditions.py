import re

from chopdiff.divs import CHUNK
from chopdiff.docs import first_wordtok
from chopdiff.docs.wordtoks import is_div
from chopdiff.html import has_timestamp

from kash.exec.precondition_registry import kash_precondition
from kash.model.items_model import Item, ItemType
from kash.text_handling.markdown_util import extract_bullet_points
from kash.utils.file_utils.file_formats_model import Format


@kash_precondition
def is_resource(item: Item) -> bool:
    return item.type == ItemType.resource


@kash_precondition
def is_concept(item: Item) -> bool:
    return item.type == ItemType.concept


@kash_precondition
def is_config(item: Item) -> bool:
    return item.type == ItemType.config


@kash_precondition
def is_chat(item: Item) -> bool:
    return item.type == ItemType.chat


@kash_precondition
def is_instructions(item: Item) -> bool:
    return is_chat(item) and has_body(item) and item.format == Format.yaml


@kash_precondition
def is_url_item(item: Item) -> bool:
    return bool(item.type == ItemType.resource and item.url)


@kash_precondition
def is_audio_resource(item: Item) -> bool:
    return bool(item.type == ItemType.resource and item.format and item.format.is_audio)


@kash_precondition
def is_video_resource(item: Item) -> bool:
    return bool(item.type == ItemType.resource and item.format and item.format.is_video)


@kash_precondition
def has_body(item: Item) -> bool:
    return bool(item.body and item.body.strip())


@kash_precondition
def contains_fenced_code(item: Item) -> bool:
    return bool(
        item.body and any(line.strip().startswith("```") for line in item.body.splitlines())
    )


@kash_precondition
def contains_curly_vars(item: Item) -> bool:
    return bool(item.body and re.search(r"\{(\w+)\}", item.body))


@kash_precondition
def has_text_body(item: Item) -> bool:
    return has_body(item) and item.format in (Format.plaintext, Format.markdown, Format.md_html)


@kash_precondition
def has_html_body(item: Item) -> bool:
    return has_body(item) and item.format in (Format.html, Format.md_html)


@kash_precondition
def is_plaintext(item: Item) -> bool:
    return has_body(item) and item.format == Format.plaintext


@kash_precondition
def is_markdown(item: Item) -> bool:
    return has_body(item) and item.format in (Format.markdown, Format.md_html)


@kash_precondition
def is_markdown_template(item: Item) -> bool:
    return is_markdown(item) and contains_curly_vars(item)


@kash_precondition
def is_html(item: Item) -> bool:
    return has_body(item) and item.format == Format.html


@kash_precondition
def is_text_doc(item: Item) -> bool:
    """
    A document that can be processed by LLMs and other plaintext tools.
    """
    return (is_plaintext(item) or is_markdown(item)) and has_body(item)


@kash_precondition
def is_markdown_list(item: Item) -> bool:
    try:
        return (
            is_markdown(item)
            and item.body is not None
            and len(extract_bullet_points(item.body)) >= 2
        )
    except TypeError:
        return False


@kash_precondition
def has_thumbnail_url(item: Item) -> bool:
    return bool(item.thumbnail_url)


@kash_precondition
def starts_with_div(item: Item) -> bool:
    return bool(item.body and is_div(first_wordtok(item.body)))


@kash_precondition
def has_lots_of_html_tags(item: Item) -> bool:
    if not item.body:
        return False
    tag_free_body = re.sub(r"<[^>]*>", "", item.body)
    tag_chars = len(item.body) - len(tag_free_body)
    return tag_chars > max(5, len(item.body) * 0.1)


@kash_precondition
def has_many_paragraphs(item: Item) -> bool:
    return bool(item.body and item.body.count("\n\n") > 4)


@kash_precondition
def has_timestamps(item: Item) -> bool:
    return bool(item.body and has_timestamp(item.body))


@kash_precondition
def has_div_chunks(item: Item) -> bool:
    return bool(item.body and item.body.find(f'<div class="{CHUNK}">') != -1)
