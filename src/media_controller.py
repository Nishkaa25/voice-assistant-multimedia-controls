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
    "UNMUTE": Key.media_volume_mute,  # Add UNMUTE mapping
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
        self.is_muted = False  # Track system mute state

        if self.backend == "vlc":
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
            FeedbackHandler.play_error_chime("No command was recognized.")
            return False

        intent = intent.upper()
        print(f"[MEDIA CONTROLLER] Executing {self.backend.upper()} action: {intent}")

        if self.backend == "vlc":
            try:
                success = self.vlc_backend.execute_intent(intent)
            except Exception as exc:
                FeedbackHandler.play_error_chime(f"VLC operation failed: {exc}")        
                success = False

            if success:
                FeedbackHandler.play_success_chime()
            else:
                FeedbackHandler.play_error_chime(f"Could not execute command: {intent}.")

            return success
        
        # Idempotency guard for OS backend
        if intent == "MUTE":
            if self.is_muted:
                FeedbackHandler.play_success_chime()
                return True
            self.is_muted = True
        elif intent == "UNMUTE":
            if not self.is_muted:
                FeedbackHandler.play_success_chime()
                return True
            self.is_muted = False

        key = KEY_MAP.get(intent)
        if key is None:
            FeedbackHandler.play_error_chime(f"Unrecognized media command: {intent}.")
            return False
        try:
            _press(key)
            FeedbackHandler.play_success_chime()
            return True
        except Exception as exc:
            print(f"[MEDIA ERROR] Could not execute {intent}: {exc}")
            FeedbackHandler.play_error_chime(
                f"Could not execute {intent}: {exc}"
            )
            return False
    
    def close(self):
        """Release backend resources."""
        if self.vlc_backend is not None:
            self.vlc_backend.close()