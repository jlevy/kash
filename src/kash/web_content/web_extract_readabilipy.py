from kash.utils.common.url import Url
from kash.utils.errors import InvalidInput
from kash.web_content.web_page_model import WebPageData


def extract_text_readabilipy(url: Url, html: str) -> WebPageData:
    """
    Extracts text from HTML using readability.
    This requires Node readability. Justext is an alternative and seems good for
    getting title and description metadata.
    """
    from readabilipy.simple_json import simple_json_from_html_string

    result = simple_json_from_html_string(html, use_readability=True)
    if not result["content"]:
        raise InvalidInput("No clean HTML found")

    return WebPageData(
        url=url,
        title=result["title"],
        byline=result["byline"],
        clean_html=result["content"],
    )
