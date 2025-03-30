from funlog import log_calls

from kash.utils.common.url import Url
from kash.web_content.canon_url import thumbnail_url
from kash.web_content.file_cache_utils import cache_file
from kash.web_content.web_extract_justext import extract_text_justext
from kash.web_content.web_fetch import fetch_url
from kash.web_content.web_page_model import PageExtractor, WebPageData


@log_calls(level="message")
def fetch_extract(
    url: Url, use_cache: bool = True, extractor: PageExtractor = extract_text_justext
) -> WebPageData:
    """
    Fetches a URL and extracts the title, description, and content.
    """

    if use_cache:
        path, _was_cached = cache_file(url)
        with open(path, "rb") as file:
            content = file.read()
        page_data = extractor(url, content)
    else:
        response = fetch_url(url)
        page_data = extractor(url, response.content)

    # Add a thumbnail, if available.
    page_data.thumbnail_url = thumbnail_url(url)

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
        print(fetch_extract(Url(url)))
        print()
