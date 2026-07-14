from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from kash.media_base.transcription_deepgram import deepgram_transcribe_raw


def test_deepgram_request_uses_current_transcription_and_diarization_models():
    client = MagicMock()
    response = MagicMock()
    client.listen.v1.media.transcribe_file.return_value = response

    with TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "audio.mp3"
        audio_path.write_bytes(b"audio")

        with patch("deepgram.DeepgramClient", return_value=client):
            result = deepgram_transcribe_raw(audio_path, language="multi")

    assert result is response
    call = client.listen.v1.media.transcribe_file.call_args
    assert call.kwargs["model"] == "nova-3"
    assert call.kwargs["diarize_model"] == "latest"
    assert "diarize" not in call.kwargs
    assert call.kwargs["language"] == "multi"
