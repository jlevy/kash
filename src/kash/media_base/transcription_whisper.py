from os.path import getsize

from openai import OpenAI

from kash.config.logger import CustomLogger, get_logger

log: CustomLogger = get_logger(__name__)


def openai_whisper_transcribe_audio_small(audio_file_path: str) -> str:
    """
    Transcribe an audio file. Whisper is very good quality but (as of 2024-05)
    OpenAI's version does not support diarization and must be under 25MB.

    https://help.openai.com/en/articles/7031512-whisper-api-faq
    """
    WHISPER_MAX_SIZE = 25 * 1024 * 1024

    size = getsize(audio_file_path)
    if size > WHISPER_MAX_SIZE:
        raise ValueError("Audio file too large for Whisper (%s > %s)" % (size, WHISPER_MAX_SIZE))
    log.info(
        "Transcribing via Whisper: %s (size %s)",
        audio_file_path,
        size,
    )

    client = OpenAI()
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            # For when we want timestamps:
            # response_format="verbose_json",
            # timestamp_granularities=["word"]
        )
        text = transcription.text
    return text
