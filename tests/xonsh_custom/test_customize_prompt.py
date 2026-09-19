"""Prompt rendering must survive workspace and style failures."""

from __future__ import annotations

from prompt_toolkit.formatted_text import FormattedText

from kash.config.text_styles import LOGO_NAME
from kash.xonsh_custom.customize_prompt import get_prompt_info, kash_xonsh_prompt, kash_xonsh_title


def test_get_prompt_info_survives_workspace_error(monkeypatch):
    def boom():
        raise RuntimeError("workspace exploded")

    monkeypatch.setattr("kash.xonsh_custom.customize_prompt.current_ws", boom)
    info = get_prompt_info()
    assert info.workspace_name == "kash"
    assert info.cwd_details.startswith("Current directory at ")
    assert info.cwd_in_workspace is False


def test_kash_xonsh_prompt_survives_style_error(monkeypatch):
    def boom():
        raise RuntimeError("style exploded")

    monkeypatch.setattr("kash.xonsh_custom.customize_prompt.get_prompt_style", boom)
    text = kash_xonsh_prompt()
    assert isinstance(text, FormattedText)
    assert "".join(token[1] for token in text).strip()


def test_kash_xonsh_title_survives_error(monkeypatch):
    def boom():
        raise RuntimeError("title exploded")

    monkeypatch.setattr("kash.xonsh_custom.customize_prompt.get_prompt_info", boom)
    assert kash_xonsh_title() == LOGO_NAME
