import sys

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

class FeedbackHandler:
    @staticmethod
    def play_success_chime():
        """FR-10 / NF-4: Audio feedback for executed commands."""
        print("[FEEDBACK] Command Executed (880 Hz Chime)")
        if HAS_WINSOUND:
            winsound.Beep(880, 150)
        else:
            print("\a")

    @staticmethod
    def play_error_chime(message="An error occurred."):
        print(f"[ERROR] {message}")
        if HAS_WINSOUND:
            winsound.Beep(440, 250)
        else:
            print("\a")
