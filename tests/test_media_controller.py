import pytest
from unittest.mock import patch
from pynput.keyboard import Key
from src.media_controller import MediaController


@pytest.mark.parametrize("intent, key", [
    ("PLAY", Key.media_play_pause),
    ("PAUSE", Key.media_play_pause),
    ("RESUME", Key.media_play_pause),
    ("VOLUME_UP", Key.media_volume_up),
    ("VOLUME_DOWN", Key.media_volume_down),
    ("MUTE", Key.media_volume_mute),
    ("NEXT", Key.media_next),
    ("PREVIOUS", Key.media_previous),
])
@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press")
def test_intent_presses_correct_key(mock_press, mock_feedback, intent, key):
    assert MediaController().execute_intent(intent) is True
    mock_press.assert_called_once_with(key)


@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press")
def test_invalid_intent_presses_nothing(mock_press, mock_feedback):
    assert MediaController().execute_intent("DANCE") is False
    mock_press.assert_not_called()


@pytest.mark.parametrize("intent", [None, ""])
@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press")
def test_empty_intent_is_rejected(mock_press, mock_feedback, intent):
    assert MediaController().execute_intent(intent) is False
    mock_press.assert_not_called()
    mock_feedback.rejected.assert_called_once()


@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press")
def test_mute_updates_state_and_presses_key(mock_press, mock_feedback):
    controller = MediaController()

    assert controller.execute_intent("MUTE") is True
    assert controller.is_muted is True
    mock_press.assert_called_once()


@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press")
def test_repeated_mute_does_not_press_key(mock_press, mock_feedback):
    controller = MediaController()

    controller.execute_intent("MUTE")
    mock_press.reset_mock()

    assert controller.execute_intent("MUTE") is True
    mock_press.assert_not_called()


@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press")
def test_unmute_updates_state_and_presses_key(mock_press, mock_feedback):
    controller = MediaController()
    controller.is_muted = True

    assert controller.execute_intent("UNMUTE") is True
    assert controller.is_muted is False
    mock_press.assert_called_once()


@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press")
def test_repeated_unmute_does_not_press_key(mock_press, mock_feedback):
    controller = MediaController()

    assert controller.execute_intent("UNMUTE") is True
    mock_press.assert_not_called()


@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller._press", side_effect=RuntimeError("Keyboard failure"))
def test_keyboard_failure_returns_false(mock_press, mock_feedback):
    controller = MediaController()

    assert controller.execute_intent("PLAY") is False
    mock_feedback.failure.assert_called_once()


def test_unsupported_backend_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported media backend"):
        MediaController(backend="unknown")


@patch("src.media_backends.vlc_backend.VLCBackend")
def test_close_releases_vlc_backend(mock_vlc):
    controller = MediaController(backend="vlc")

    controller.close()

    controller.vlc_backend.close.assert_called_once()


def test_close_without_backend_does_not_raise():
    controller = MediaController(backend="os")

    controller.close()
