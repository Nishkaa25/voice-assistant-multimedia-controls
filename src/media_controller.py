from pynput.keyboard import Key, Controller
from src.feedback_handler import FeedbackHandler

keyboard = Controller()

KEY_MAP = {
    "PLAY": Key.media_play_pause,
    "PAUSE": Key.media_play_pause,
    "RESUME": Key.media_play_pause,
    "VOLUME_UP": Key.media_volume_up,
    "VOLUME_DOWN": Key.media_volume_down,
    "MUTE": Key.media_volume_mute,
    "NEXT": Key.media_next,
    "PREVIOUS": Key.media_previous,
}


def _press(key):
    keyboard.press(key)
    keyboard.release(key)


class MediaController:
    def execute_intent(self, intent):
        """
        FR-04 through FR-09, FR-13, FR-14: Maps intents to OS Media Keys.
        NF-1: Execution latency <= 1.5 seconds.
        """
        if not intent:
            FeedbackHandler.play_error_chime()
            return False

        intent = intent.upper()
        print(f"[MEDIA CONTROLLER] Executing OS Key Action: {intent}")

        key = KEY_MAP.get(intent)
        if key is None:
            print(f"[MEDIA ERROR] Invalid Intent: {intent}")
            FeedbackHandler.play_error_chime()
            return False

        _press(key)
        FeedbackHandler.play_success_chime()
        return True