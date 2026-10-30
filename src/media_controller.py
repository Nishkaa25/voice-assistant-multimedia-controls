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
    def __init__(self, backend="os"):
        self.backend = backend.lower()
        self.vlc_backend = None

        if self.backend == "vlc":
            # Import VLCBackend only when the VLC backend is selected.
# This lazy import allows the default OS backend to work without
# python-vlc or the VLC native libraries installed.
#If we moved the import to the top of media_controller.py, Python would import vlc even when using the OS backend, potentially breaking existing functionality if python-vlc or the native LibVLC library isn't installed

            from src.media_backends.vlc_backend import VLCBackend
            self.vlc_backend = VLCBackend()
        elif self.backend != "os":
            raise ValueError(
                f"Unsupported media backend: {backend}"
            )
    def execute_intent(self, intent):
        """
        FR-04 through FR-09, FR-13, FR-14: Maps intents to OS Media Keys.
        NF-1: Execution latency <= 1.5 seconds.
        """
        if not intent:
            FeedbackHandler.play_error_chime()
            return False

        intent = intent.upper()
        print(f"[MEDIA CONTROLLER] Executing {self.backend.upper()} action: {intent}")

        if self.backend == "vlc":
            try:
                success = self.vlc_backend.execute_intent(intent)
            except Exception as exc:
                print(f"[MEDIA ERROR] VLC operation failed: {exc}")
                success = False

            if success:
                FeedbackHandler.play_success_chime()
            else:
                FeedbackHandler.play_error_chime()

            return success
        
        key = KEY_MAP.get(intent)
        if key is None:
            print(f"[MEDIA ERROR] Invalid Intent: {intent}")
            FeedbackHandler.play_error_chime()
            return False

        _press(key)
        FeedbackHandler.play_success_chime()
        return True
    
    def close(self):
        """Release backend resources."""
        if self.vlc_backend is not None:
            self.vlc_backend.close()