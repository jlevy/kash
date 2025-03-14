from collections.abc import Callable
from typing import Any

# Make type checker happy with xonsh globals:


def get_env(name: str) -> Any:
    return __xonsh__.env[name]  # type: ignore  # noqa: F821


def set_env(name: str, value: Any) -> None:
    __xonsh__.env[name] = value  # type: ignore  # noqa: F821


def unset_env(name: str) -> None:
    del __xonsh__.env[name]  # type: ignore  # noqa: F821


def set_alias(name: str, value: str | Callable) -> None:
    aliases[name] = value  # type: ignore  # noqa: F821


def update_aliases(new_aliases: dict[str, Callable]) -> None:
    aliases.update(new_aliases)  # type: ignore  # noqa: F821


def is_interactive() -> bool:
    return get_env("XONSH_INTERACTIVE")
