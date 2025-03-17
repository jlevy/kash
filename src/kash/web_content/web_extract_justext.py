import justext

from kash.config.logger import get_logger
from kash.utils.common.url import Url
from kash.web_content.web_page_model import WebPageData

log = get_logger(__name__)


def extract_text_justext(url: Url, raw_html: bytes) -> WebPageData:
    dom, paragraphs = _justext_custom(raw_html, justext.get_stoplist("English"))
    # Extract title and description.
    title = None
    description = None
    try:
        title = str(dom.cssselect("title")[0].text_content()).strip()
    except IndexError:
        log.warning("Page missing title: %s", url)
        log.save_object("Page missing title", "web", raw_html)
        pass
    try:
        description = str(dom.cssselect('meta[name="description"]')[0].get("content"))
    except IndexError:
        pass

    # Content without boilerplate.
    content = "\n\n".join([para.text for para in paragraphs if not para.is_boilerplate])
    return WebPageData(url, title=title, description=description, text=content)


from justext.core import (
    DEFAULT_ENC_ERRORS,
    DEFAULT_ENCODING,
    LENGTH_HIGH_DEFAULT,
    LENGTH_LOW_DEFAULT,
    MAX_HEADING_DISTANCE_DEFAULT,
    MAX_LINK_DENSITY_DEFAULT,
    NO_HEADINGS_DEFAULT,
    STOPWORDS_HIGH_DEFAULT,
    STOPWORDS_LOW_DEFAULT,
    ParagraphMaker,
    classify_paragraphs,
    html_to_dom,
    preprocessor,
    revise_paragraph_classification,
)


# Copied from justext to expose the dom and save time parsing.
def _justext_custom(
    html_text,
    stoplist,
    length_low=LENGTH_LOW_DEFAULT,
    length_high=LENGTH_HIGH_DEFAULT,
    stopwords_low=STOPWORDS_LOW_DEFAULT,
    stopwords_high=STOPWORDS_HIGH_DEFAULT,
    max_link_density=MAX_LINK_DENSITY_DEFAULT,
    max_heading_distance=MAX_HEADING_DISTANCE_DEFAULT,
    no_headings=NO_HEADINGS_DEFAULT,
    encoding=None,
    default_encoding=DEFAULT_ENCODING,
    enc_errors=DEFAULT_ENC_ERRORS,
    preprocessor=preprocessor,
):
    """
    Converts an HTML page into a list of classified paragraphs. Each paragraph
    is represented as instance of class ˙˙justext.paragraph.Paragraph˙˙.
    """
    dom = html_to_dom(html_text, default_encoding, encoding, enc_errors)
    clean_dom = preprocessor(dom)

    paragraphs = ParagraphMaker.make_paragraphs(clean_dom)

    classify_paragraphs(
        paragraphs,
        stoplist,
        length_low,
        length_high,
        stopwords_low,
        stopwords_high,
        max_link_density,
        no_headings,
    )
    revise_paragraph_classification(paragraphs, max_heading_distance)

    return dom, paragraphs
