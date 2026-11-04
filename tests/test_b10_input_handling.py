
import pytest
from unittest.mock import Mock, patch

from main import handle_transcript
from src.command_parser import CommandParser
from src.voice_engine import VoiceEngine


@pytest.fixture
def dependencies():
    voice_engine = Mock()
    command_parser = CommandParser()
    media_controller = Mock()

    return voice_engine, command_parser, media_controller


def test_empty_transcript_is_ignored(dependencies):
    voice, parser, media = dependencies

    result = handle_transcript(None, voice, parser, media)

    assert result is False
    voice.parse_wake_word_and_intent.assert_not_called()
    media.execute_intent.assert_not_called()


def test_speech_without_wake_word_is_ignored(dependencies):
    voice, parser, media = dependencies
    voice.parse_wake_word_and_intent.return_value = (None, False)

    with patch("main.FeedbackHandler") as feedback:
        result = handle_transcript(
            "random background conversation",
            voice, parser, media
        )

    assert result is False
    feedback.rejected.assert_not_called()
    media.execute_intent.assert_not_called()


def test_wake_word_without_command_only_activates(dependencies):
    voice, parser, media = dependencies
    voice.parse_wake_word_and_intent.return_value = ("", True)

    with patch("main.FeedbackHandler") as feedback:
        result = handle_transcript(
            "assistant", voice, parser, media
        )

    assert result is False
    feedback._beep.assert_called_once()
    feedback.rejected.assert_not_called()
    media.execute_intent.assert_not_called()


def test_unsupported_command_is_rejected(dependencies):
    voice, parser, media = dependencies
    voice.parse_wake_word_and_intent.return_value = (
        "turn on the lights", True
    )

    with patch("main.FeedbackHandler") as feedback:
        result = handle_transcript(
            "assistant turn on the lights",
            voice, parser, media
        )

    assert result is False
    feedback.rejected.assert_called_once()
    media.execute_intent.assert_not_called()

def test_valid_command_after_invalid_command(dependencies):
    voice, parser, media = dependencies

    voice.parse_wake_word_and_intent.side_effect = [
        ("turn on the lights", True),
        ("play", True),
    ]

    with patch("main.FeedbackHandler") as feedback:
        first_result = handle_transcript(
            "assistant turn on the lights",
            voice, parser, media
        )

        second_result = handle_transcript(
            "assistant play",
            voice, parser, media
        )

    assert first_result is False
    assert second_result is True

    feedback.rejected.assert_called_once()
    media.execute_intent.assert_called_once_with("PLAY")
