
from unittest.mock import patch

import pytest

from src.voice_engine import VoiceEngine


@pytest.fixture
def engine():
    voice = VoiceEngine.__new__(VoiceEngine)
    voice.wake_word = "assistant"
    voice.activation_timeout = 5.0
    voice.is_listening_for_command = False
    voice.activation_started_at = None
    return voice


def test_wake_word_alone_activates(engine):
    with patch("src.voice_engine.time.monotonic", return_value=10.0):
        phrase, detected = engine.parse_wake_word_and_intent("assistant")

    assert phrase is None
    assert detected is True
    assert engine.is_listening_for_command is True
    assert engine.activation_started_at == 10.0


def test_wake_word_and_command_together(engine):
    with patch("src.voice_engine.time.monotonic", return_value=10.0):
        phrase, detected = engine.parse_wake_word_and_intent(
            "assistant volume up"
        )

    assert phrase == "volume up"
    assert detected is True
    assert engine.is_listening_for_command is False


def test_wake_word_must_be_first_word(engine):
    with patch("src.voice_engine.time.monotonic", return_value=10.0):
        phrase, detected = engine.parse_wake_word_and_intent(
            "please assistant volume up"
        )

    assert phrase is None
    assert detected is False
    assert engine.is_listening_for_command is False


def test_command_accepted_within_activation_window(engine):
    with patch(
        "src.voice_engine.time.monotonic",
        side_effect=[10.0, 14.0],
    ):
        engine.parse_wake_word_and_intent("assistant")

        phrase, detected = engine.parse_wake_word_and_intent("volume up")

    assert phrase == "volume up"
    assert detected is True
    assert engine.is_listening_for_command is False
    assert engine.activation_started_at is None


def test_command_rejected_after_activation_expires(engine):
    with patch(
        "src.voice_engine.time.monotonic",
        side_effect=[10.0, 15.1],
    ):
        engine.parse_wake_word_and_intent("assistant")

        phrase, detected = engine.parse_wake_word_and_intent("volume up")

    assert phrase is None
    assert detected is False
    assert engine.is_listening_for_command is False
    assert engine.activation_started_at is None


def test_activation_expires_exactly_at_timeout_boundary(engine):
    with patch(
        "src.voice_engine.time.monotonic",
        side_effect=[10.0, 15.0],
    ):
        engine.parse_wake_word_and_intent("assistant")

        phrase, detected = engine.parse_wake_word_and_intent("volume up")

    assert phrase == "volume up"
    assert detected is True


def test_activation_is_single_use_even_for_invalid_command(engine):
    with patch(
        "src.voice_engine.time.monotonic",
        side_effect=[10.0, 11.0, 12.0],
    ):
        engine.parse_wake_word_and_intent("assistant")

        phrase, detected = engine.parse_wake_word_and_intent("dance")

        next_phrase, next_detected = (
            engine.parse_wake_word_and_intent("volume up")
        )

    assert phrase == "dance"
    assert detected is True

    assert next_phrase is None
    assert next_detected is False


def test_empty_transcript_does_not_activate_or_consume(engine):
    with patch("src.voice_engine.time.monotonic", return_value=10.0):
        phrase, detected = engine.parse_wake_word_and_intent("")

    assert phrase is None
    assert detected is False
    assert engine.is_listening_for_command is False


def test_wake_word_followed_by_punctuation(engine):
    with patch("src.voice_engine.time.monotonic", return_value=10.0):
        phrase, detected = engine.parse_wake_word_and_intent(
            "assistant, volume up"
        )

    assert phrase == "volume up"
    assert detected is True
