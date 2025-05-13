from functools import cache


@cache
def init_litellm():
    """
    Configure litellm to suppress overly prominent exception messages.
    Do this lazily since litellm is slow to import.
    """
    try:
        import litellm
        from litellm import _logging  # noqa: F401

        litellm.suppress_debug_info = True  # Suppress overly prominent exception messages.
    except ImportError:
        pass
