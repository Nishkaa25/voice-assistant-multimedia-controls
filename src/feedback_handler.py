"""FR-10 / NF-4: Audio feedback for executed commands."""
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class FeedbackHandler:

    @staticmethod
    def _beep(frequency=1000, duration=100):
        if HAS_WINSOUND:
            winsound.Beep(frequency, duration)
        else:
            print("\a", end="", flush=True)

    @staticmethod
    def success(message):
        print(f"[SUCCESS] {message}")
        FeedbackHandler._beep(880, 150)

    @staticmethod
    def failure(message):
        print(f"[ERROR] {message}")
        FeedbackHandler._beep(440, 250)

    @staticmethod
    def rejected(message):
        print(f"[REJECTED] {message}")
        FeedbackHandler._beep(600, 250)