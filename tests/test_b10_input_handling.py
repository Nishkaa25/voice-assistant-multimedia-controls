import pytest
from unittest.mock import Mock, patch, call

from main import handle_transcript
import main
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

@patch("main.VoiceEngine", side_effect=RuntimeError("Model unavailable"))
def test_main_exits_when_voice_engine_initialization_fails(mock_voice, capsys):
    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 1


@patch("main.AudioCapturer")
@patch("main.VoiceEngine")
def test_main_exits_when_microphone_fails(mock_voice, mock_audio):
    mock_audio.return_value.start_stream.return_value = False

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 1
    mock_audio.return_value.stop_stream.assert_called_once()


@patch("main.MediaController", side_effect=RuntimeError("Backend unavailable"))
@patch("main.AudioCapturer")
@patch("main.VoiceEngine")
def test_main_exits_when_media_controller_fails(
    mock_voice, mock_audio, mock_media
):
    mock_audio.return_value.start_stream.return_value = True

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 1
    mock_audio.return_value.stop_stream.assert_called_once()


@patch("main.MediaController")
@patch("main.AudioCapturer")
@patch("main.VoiceEngine")
def test_main_processes_audio_and_shuts_down(
    mock_voice, mock_audio, mock_media
):
    voice = mock_voice.return_value
    audio = mock_audio.return_value
    media = mock_media.return_value

    audio.start_stream.return_value = True
    audio.get_audio_chunk.side_effect = [b"audio", KeyboardInterrupt]

    voice.process_audio_chunk.return_value = "assistant play"
    voice.parse_wake_word_and_intent.return_value = ("play", True)

    with patch("main.handle_transcript", return_value=True) as handler:
        main.main()

    voice.process_audio_chunk.assert_called_once_with(b"audio")
    handler.assert_called_once()
    audio.stop_stream.assert_called_once()
    media.close.assert_called_once()


@patch("main.MediaController")
@patch("main.AudioCapturer")
@patch("main.VoiceEngine")
def test_main_skips_empty_audio_chunks(
    mock_voice, mock_audio, mock_media
):
    voice = mock_voice.return_value
    audio = mock_audio.return_value

    audio.start_stream.return_value = True
    audio.get_audio_chunk.side_effect = [None, KeyboardInterrupt]

    main.main()

    voice.process_audio_chunk.assert_not_called()
    audio.stop_stream.assert_called_once()
    mock_media.return_value.close.assert_called_once()
