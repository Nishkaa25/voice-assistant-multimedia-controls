
import pytest
from unittest.mock import Mock

from src.voice_engine import VoiceEngine


@pytest.fixture
def engine():
    voice_engine = VoiceEngine.__new__(VoiceEngine)
    voice_engine.recognizer = Mock()
    return voice_engine


def test_empty_audio_is_ignored(engine):
    assert engine.process_audio_chunk(b"") is None

    engine.recognizer.AcceptWaveform.assert_not_called()


def test_incomplete_speech_is_ignored(engine):
    engine.recognizer.AcceptWaveform.return_value = False

    result = engine.process_audio_chunk(b"audio data")

    assert result is None
    engine.recognizer.Result.assert_not_called()


def test_empty_recognition_result_is_ignored(engine):
    engine.recognizer.AcceptWaveform.return_value = True
    engine.recognizer.Result.return_value = '{"text": ""}'

    assert engine.process_audio_chunk(b"audio data") is None


def test_valid_recognition_result_is_normalized(engine):
    engine.recognizer.AcceptWaveform.return_value = True
    engine.recognizer.Result.return_value = (
        '{"text": " PLAY MUSIC "}'
    )

    assert engine.process_audio_chunk(b"audio data") == "play music"


def test_recognition_exception_does_not_crash(engine):
    engine.recognizer.AcceptWaveform.side_effect = RuntimeError(
        "Recognition failure"
    )

    result = engine.process_audio_chunk(b"audio data")

    assert result is None


def test_invalid_recognition_json_does_not_crash(engine):
    engine.recognizer.AcceptWaveform.return_value = True
    engine.recognizer.Result.return_value = "invalid json"

    result = engine.process_audio_chunk(b"audio data")

    assert result is None
