import urllib.parse

from kash.exec import kash_command
from kash.shell.utils.native_utils import native_open_url


@kash_command
def browser(url_or_query: str) -> None:
    """
    Open a URL or query in the browser.
    """
    native_open_url(url_or_query)


@kash_command
def web_search_google(query: str) -> None:
    """
    Open browser with a Google for a query.
    """
    native_open_url(f"https://www.google.com/search?q={urllib.parse.quote(query)}")


@kash_command
def web_search_duckduckgo(query: str) -> None:
    """
    Open browser with a DuckDuckGo search for a query.
    """
    native_open_url(f"https://duckduckgo.com/?q={urllib.parse.quote(query)}")


@kash_command
def web_search_bing(query: str) -> None:
    """
    Open browser with a Bing search for a query.
    """
    native_open_url(f"https://www.bing.com/search?q={urllib.parse.quote(query)}")


@kash_command
def web_search_youtube(query: str) -> None:
    """
    Open browser with a YouTube search for a query.
    """
    params = {"search_query": query}
    url = f"https://www.youtube.com/results?{urllib.parse.urlencode(params)}"
    native_open_url(url)


@kash_command
def web_search_amazon(query: str) -> None:
    """
    Open browser with an Amazon search for a query.
    """
    native_open_url(f"https://www.amazon.com/s?k={urllib.parse.quote(query)}")


@kash_command
def web_search_perplexity(query: str) -> None:
    """
    Open browser with a Perplexity search for a query.
    """
    native_open_url(f"https://www.perplexity.ai/search?q={urllib.parse.quote(query)}")
