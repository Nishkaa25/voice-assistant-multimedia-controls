import pyautogui
from src.feedback_handler import FeedbackHandler

class MediaController:
    def __init__(self):
        # Configure pyautogui safety pause
        pyautogui.PAUSE = 0.05

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

        if intent in ("PLAY", "PAUSE", "RESUME"):
            pyautogui.press("playpause")
        elif intent == "VOLUME_UP":
            pyautogui.press("volumeup")
        elif intent == "VOLUME_DOWN":
            pyautogui.press("volumedown")
        elif intent == "MUTE":
            pyautogui.press("volumemute")
        elif intent == "NEXT":
            pyautogui.press("nexttrack")
        elif intent == "PREVIOUS":
            pyautogui.press("prevtrack")
        else:
            print(f"[MEDIA ERROR] Invalid Intent: {intent}")
            FeedbackHandler.play_error_chime()
            return False

        FeedbackHandler.play_success_chime()
        return True