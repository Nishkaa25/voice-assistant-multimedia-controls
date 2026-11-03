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

#this is i think for os media keys
messages = {
    "PLAY": "Playback started.",
    "PAUSE": "Playback paused.",
    "RESUME": "Playback resumed.",
    "NEXT": "Skipped to next track.",
    "PREVIOUS": "Returned to previous track.",
    "MUTE": "Audio muted.",
    "UNMUTE": "Audio unmuted.",
    "VOLUME_UP": "Volume up command sent.",
    "VOLUME_DOWN": "Volume down command sent.",
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
            FeedbackHandler.rejected("No command was recognized.")
            return False

        intent = intent.upper()

        if intent not in KEY_MAP:
            FeedbackHandler.rejected(
                f"Unsupported media command: {intent}."
            )
            return False

        print(
            f"[MEDIA CONTROLLER] Executing "
            f"{self.backend.upper()} action: {intent}"
        )

        if self.backend == "vlc":
            try:
                success = self.vlc_backend.execute_intent(intent)
            except Exception as exc:
                FeedbackHandler.failure(
                    f"Could not execute {intent.lower()}: {exc}"
                )
                return False

            if not success:
                FeedbackHandler.failure(
                    f"Could not execute {intent.lower()}."
                )
                return False

            if intent in ("VOLUME_UP", "VOLUME_DOWN"):
                volume = self.vlc_backend.get_volume()

                if volume is not None:
                    FeedbackHandler.success(
                        f"Volume: {volume}%"
                    )
                else:
                    FeedbackHandler.success(
                        "Volume command dispatched."
                    )

            elif intent in ("NEXT", "PREVIOUS"):
                title = self.vlc_backend.get_current_track()

                if title:
                    FeedbackHandler.success(
                        f"Now playing: {title}"
                    )
                else:
                    FeedbackHandler.success(
                        messages[intent]
                    )

            else:
                FeedbackHandler.success(messages[intent])

            return True

        # OS backend: sending a media key does not verify
        # the resulting state in the media application.

        if intent == "MUTE":
            if self.is_muted:
                FeedbackHandler.success("Microphone already muted.")
                return True
            self.is_muted = True

        elif intent == "UNMUTE":
            if not self.is_muted:
                FeedbackHandler.success("Microphone already unmuted.")
                return True
            self.is_muted = False

        key = KEY_MAP[intent]

        try:
            _press(key)

            if intent in ("VOLUME_UP", "VOLUME_DOWN"):
                FeedbackHandler.success(
                    f"{messages.get(intent, intent)} command dispatched."
                )
            else:
                FeedbackHandler.success(
                    f"{messages.get(intent, intent)} "
                    "command dispatched."
                )

            return True

        except Exception as exc:
            FeedbackHandler.failure(
                f"Could not execute {intent.lower()}: {exc}"
            )
            return False
    
    def close(self):
        """Release backend resources."""
        if self.vlc_backend is not None:
            self.vlc_backend.close()