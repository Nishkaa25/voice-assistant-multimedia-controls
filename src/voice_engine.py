import os
import sys
import json
from vosk import Model, KaldiRecognizer

class VoiceEngine:
    def __init__(self, model_path="model", sample_rate=16000, wake_word="assistant"):
        """
        FR-02, FR-03, FR-12, PRJ-SR-002: Offline Speech Engine using Vosk.
        - Wake Word required before accepting media command intents.
        """
        self.sample_rate = sample_rate
        self.wake_word = wake_word.lower()
        self.is_listening_for_command = False
        
        if not os.path.exists(model_path):
            print(f"[VOICE ERROR] Vosk model path '{model_path}' not found!", file=sys.stderr)
            print(" -> Download from https://alphacephei.com/vosk/models and extract to 'model/'", file=sys.stderr)
            sys.exit(1)

        print(f"[VOICE] Loading offline speech model from '{model_path}'...")
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

    def process_audio_chunk(self, pcm_data):
        """
        Processes a raw PCM audio chunk. Returns recognized text string if a full utterance is parsed.
        """
        if self.recognizer.AcceptWaveform(pcm_data):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").strip().lower()
            return text
        return None

    def parse_wake_word_and_intent(self, text_transcript):
        """
        PRJ-SR-002: Enforces wake-word gating.
        - If wake word is detected, unlocks system to parse command intent.
        """
        if not text_transcript:
            return None, False

        words = text_transcript.split()
        
        # Check for wake word trigger
        if self.wake_word in words:
            self.is_listening_for_command = True
            # Extract remaining phrase after wake word
            wake_index = words.index(self.wake_word)
            command_phrase = " ".join(words[wake_index + 1:])
            print(f"\n[PRJ-SR-002] Wake Word '{self.wake_word.upper()}' Detected!")
            return command_phrase, True

        # If already triggered in previous turn
        if self.is_listening_for_command:
            self.is_listening_for_command = False
            return text_transcript, True

        return None, False