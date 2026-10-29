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