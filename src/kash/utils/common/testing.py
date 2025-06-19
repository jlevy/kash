from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from typing import Literal, TypeAlias

TestMarker: TypeAlias = Literal["online", "integration"]
"""
Valid markers for tests. Currently just marking online tests (e.g. LLM APIs that
that require keys) and more complex integration tests.
"""


def enable_if(marker: TestMarker) -> Callable:
    """
    Mark a test as having external dependencies.

    Test runs only if the corresponding environment variable is set, e.g.
    for the marker "online", checks for ENABLE_TESTS_ONLINE=1.

    Automatically sets pytest markers when pytest is available, but safe to use in
    runtime code as well.

    Example usage:

    ```
    def test_foo():
        ...

    @enable_if("online")  # Only runs if ENABLE_TESTS_ONLINE=1
    def test_bar():
        ...
    ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            env_var = f"ENABLE_TESTS_{marker.upper()}"
            if not os.getenv(env_var):
                print(f"Skipping test function: {func.__name__} (set {env_var}=1 to enable)")
                return
            return func(*args, **kwargs)

        # Set pytest markers automatically if pytest is available
        try:
            import pytest

            wrapper = pytest.mark.integration(wrapper)
            wrapper = getattr(pytest.mark, marker)(wrapper)
        except ImportError:
            # Pytest not available, which is fine for non-test runs
            pass

        return wrapper

    return decorator
