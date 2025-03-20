from collections.abc import Callable
from typing import Any

# Make type checker happy with xonsh globals:


def get_env(name: str) -> Any:
    return __xonsh__.env[name]  # noqa: F821 # pyright: ignore[reportUndefinedVariable]


def set_env(name: str, value: Any) -> None:
    __xonsh__.env[name] = value  # noqa: F821 # pyright: ignore[reportUndefinedVariable]


def unset_env(name: str) -> None:
    del __xonsh__.env[name]  # noqa: F821 # pyright: ignore[reportUndefinedVariable]


def set_alias(name: str, value: str | Callable[..., Any]) -> None:
    aliases[name] = value  # noqa: F821 # pyright: ignore[reportUndefinedVariable]


def update_aliases(new_aliases: dict[str, Callable[..., Any]]) -> None:
    aliases.update(new_aliases)  # noqa: F821 # pyright: ignore[reportUndefinedVariable]


def is_interactive() -> bool:
    return get_env("XONSH_INTERACTIVE")
