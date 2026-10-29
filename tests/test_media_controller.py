import pytest
from unittest.mock import patch
from src.media_controller import MediaController


@pytest.mark.parametrize("intent, key", [
    ("PLAY", "playpause"),
    ("PAUSE", "playpause"),
    ("RESUME", "playpause"),
    ("VOLUME_UP", "volumeup"),
    ("VOLUME_DOWN", "volumedown"),
])
@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller.pyautogui.press")
def test_intent_presses_correct_key(mock_press, mock_feedback, intent, key):
    assert MediaController().execute_intent(intent) is True
    mock_press.assert_called_once_with(key)


@patch("src.media_controller.FeedbackHandler")
@patch("src.media_controller.pyautogui.press")
def test_invalid_intent_presses_nothing(mock_press, mock_feedback):
    assert MediaController().execute_intent("DANCE") is False
    mock_press.assert_not_called()