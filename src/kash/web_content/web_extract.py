from funlog import log_calls

from kash.utils.common.url import Url
from kash.utils.file_utils.file_formats_model import file_format_info
from kash.web_content.canon_url import thumbnail_url
from kash.web_content.file_cache_utils import cache_file
from kash.web_content.web_extract_justext import extract_text_justext
from kash.web_content.web_page_model import PageExtractor, WebPageData


@log_calls(level="message")
def fetch_page_content(
    url: Url,
    *,
    refetch: bool = False,
    cache: bool = True,
    text_extractor: PageExtractor = extract_text_justext,
) -> WebPageData:
    """
    Fetches a URL and extracts the title, description, and content.
    Always uses the content cache, at least temporarily.

    Force re-fetching and updating the cache by setting `refetch` to true.
    Cached file path is returned in the content, unless `cache` is false,
    in case the cached content is deleted.

    For HTML and other text files, uses the `text_extractor` to extract
    clean text and page metadata.
    """
    expiration_sec = 0 if refetch else None

    path = cache_file(url, expiration_sec=expiration_sec).content.path
    format_info = file_format_info(path)

    content = None
    if format_info.format and format_info.format.is_text:
        content = path.read_bytes()
        page_data = text_extractor(url, content)
    else:
        page_data = WebPageData(url)

    # Add file format info (for both HTML/text and all other file types).

    page_data.format_info = format_info

    # Add a thumbnail, if known for this URL.
    page_data.thumbnail_url = thumbnail_url(url)

    # Return the local cache path if we will be keeping it.
    if cache:
        page_data.saved_content = path
    else:
        path.unlink()

    return page_data


# TODO: Consider a JS-enabled headless browser so it works on more sites.
# Example: https://www.inc.com/atish-davda/5-questions-you-should-ask-before-taking-a-start-up-job-offer.html

if __name__ == "__main__":
    sample_urls = [
        "https://hbr.org/2016/12/think-strategically-about-your-career-development",
        "https://www.chicagobooth.edu/review/how-answer-one-toughest-interview-questions",
        "https://www.inc.com/atish-davda/5-questions-you-should-ask-before-taking-a-start-up-job-offer.html",
        "https://www.investopedia.com/terms/r/risktolerance.asp",
        "https://www.upcounsel.com/employee-offer-letter",
        "https://rework.withgoogle.com/guides/pay-equity/steps/introduction/",
        "https://www.forbes.com/sites/tanyatarr/2017/12/31/here-are-five-negotiation-myths-we-can-leave-behind-in-2017/",
        "https://archive.nytimes.com/dealbook.nytimes.com/2009/08/19/googles-ipo-5-years-later/",
    ]

    for url in sample_urls:
        print(f"URL: {url}")
        print(fetch_page_content(Url(url)))
        print()
