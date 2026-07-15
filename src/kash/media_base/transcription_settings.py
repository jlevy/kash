from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from strif import file_mtime_hash

from kash.utils.common.url import Url, is_file_url, parse_file_url


@dataclass(frozen=True)
class TranscriptionSettings:
    """
    Provider-facing settings that affect transcription output and cache identity.
    """

    language: str | None = None
    model: str = "nova-3"
    diarize_model: str = "latest"
    smart_format: bool = True
    key_terms: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        language: str | None = None,
        model: str = "nova-3",
        diarize_model: str = "latest",
        smart_format: bool = True,
        key_terms: Sequence[str] | None = None,
    ) -> TranscriptionSettings:
        normalized_terms = tuple(
            dict.fromkeys(term.strip() for term in key_terms or () if term.strip())
        )
        return cls(
            language=language,
            model=model,
            diarize_model=diarize_model,
            smart_format=smart_format,
            key_terms=normalized_terms,
        )

    def cache_key(self, source: Url | Path) -> str:
        """
        Return a stable cache key including the local file identity when available.
        """
        source_str = str(source)
        source_path: Path | None = None
        if isinstance(source, Path):
            source_path = source
        elif is_file_url(source):
            source_path = parse_file_url(source)

        source_identity = source_str
        if source_path and source_path.exists():
            source_identity = f"{source_str}#{file_mtime_hash(source_path)}"

        return json.dumps(
            {"source": source_identity, "settings": asdict(self)},
            sort_keys=True,
            separators=(",", ":"),
        )


## Tests


def test_transcription_settings_cache_key_tracks_accuracy_inputs(tmp_path: Path) -> None:
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"first")

    default = TranscriptionSettings.create(language="en")
    contextual = TranscriptionSettings.create(language="en", key_terms=["SignalFlow"])
    multilingual = TranscriptionSettings.create(language="multi", key_terms=["SignalFlow"])

    assert default.cache_key(audio_path) != contextual.cache_key(audio_path)
    assert contextual.cache_key(audio_path) != multilingual.cache_key(audio_path)

    previous_key = contextual.cache_key(audio_path)
    audio_path.write_bytes(b"updated audio")
    assert contextual.cache_key(audio_path) != previous_key
