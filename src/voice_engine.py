
import json
import os
import sys

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    Model = None
    KaldiRecognizer = None


class VoiceEngine:
    def __init__(self, model_path="model", sample_rate=16000,
                 wake_word="assistant"):
        """
        Initialize the local, offline Vosk speech-recognition engine.
        """
        self.sample_rate = sample_rate
        self.wake_word = wake_word.lower()
        self.is_listening_for_command = False

        if Model is None or KaldiRecognizer is None:
            raise RuntimeError(
                "Vosk is not installed. Run "
                "'python -m pip install -r requirements.txt'."
            )

        if not os.path.isdir(model_path):
            raise FileNotFoundError(
                f"Vosk model folder '{model_path}' was not found. "
                "Download an offline Vosk model and extract it "
                "to the configured model path."
            )

        try:
            print(
                f"[VOICE] Loading offline speech model from "
                f"'{model_path}'..."
            )
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(
                self.model, self.sample_rate
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Vosk model from '{model_path}': {exc}"
            ) from exc

    def process_audio_chunk(self, pcm_data):
        """
        Return recognized text only when a complete utterance is ready.

        Partial recognition results are ignored to prevent duplicate
        command processing.
        """
        if not pcm_data:
            return None

        try:
            if not self.recognizer.AcceptWaveform(pcm_data):
                return None

            result = json.loads(self.recognizer.Result())
            text = result.get("text", "")

            if not isinstance(text, str):
                return None

            return text.strip().lower() or None

        except Exception as exc:
            print(
                f"[VOICE ERROR] Speech recognition failed: {exc}",
                file=sys.stderr,
            )
            return None

    def parse_wake_word_and_intent(self, text_transcript):
        """
        Require the wake word before accepting a command.
        """
        if not text_transcript or not text_transcript.strip():
            return None, False

        words = text_transcript.lower().split()

        if self.wake_word in words:
            self.is_listening_for_command = True
            wake_index = words.index(self.wake_word)
            command_phrase = " ".join(words[wake_index + 1:])

            print(
                f"[VOICE] Wake word '{self.wake_word.upper()}' detected."
            )
            return command_phrase, True

        if self.is_listening_for_command:
            self.is_listening_for_command = False
            return text_transcript.strip().lower(), True

        return None, False
