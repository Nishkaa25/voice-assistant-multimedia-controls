import json
import os
import sys
import time

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    Model = None
    KaldiRecognizer = None


class VoiceEngine:
    def __init__(
        self,
        model_path="model",
        sample_rate=16000,
        wake_word="assistant",
        activation_timeout=5.0,
    ):
        """
        Initialize the local, offline Vosk speech-recognition engine.
        """
        self.sample_rate = sample_rate
        self.wake_word = wake_word.lower()
        self.activation_timeout = float(activation_timeout)

        if self.activation_timeout <= 0:
            raise ValueError(
                "Activation timeout must be greater than zero."
            )

        self.is_listening_for_command = False
        self.activation_started_at = None

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
        Validate wake-word activation before accepting a command.

        The wake word must be the first word of an utterance.

        If spoken alone, the next completed utterance is accepted
        only within the configured activation timeout.

        Activation is consumed after one subsequent utterance.
        """
        if (
            not isinstance(text_transcript, str)
            or not text_transcript.strip()
        ):
            return None, False

        words = text_transcript.lower().split()
        first_word = words[0].strip(".,!?;:")
        current_time = time.monotonic()

        # Wake word must appear at the beginning.
        if first_word == self.wake_word:
            self.is_listening_for_command = False
            self.activation_started_at = None

            print(
                f"[VOICE] Wake word '{self.wake_word.upper()}' detected."
            )

            command_phrase = " ".join(words[1:]).strip()

            # Wake word and command in the same utterance.
            if command_phrase:
                return command_phrase, True

            # Wake word alone starts a timed activation window.
            self.is_listening_for_command = True
            self.activation_started_at = current_time

            return None, True

        # A previous wake word may authorize one subsequent utterance.
        if self.is_listening_for_command:
            activation_time = self.activation_started_at

            # Always consume the activation after this utterance.
            self.is_listening_for_command = False
            self.activation_started_at = None

            if (
                activation_time is not None
                and current_time - activation_time
                <= self.activation_timeout
            ):
                return text_transcript.strip().lower(), True

        # No valid activation.
        return None, False
