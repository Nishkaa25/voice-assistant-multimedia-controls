import os
import sys
import time
from src.audio_capture import AudioCapturer
from src.voice_engine import VoiceEngine
from src.command_parser import CommandParser
from src.media_controller import MediaController
from src.feedback_handler import FeedbackHandler
from dotenv import load_dotenv

load_dotenv()

def handle_transcript(
    transcript,
    voice_engine,
    command_parser,
    media_controller,
):
    """
    Safely process one completed speech transcript.

    Unsupported or inactive input must never execute a media action.
    """
    if not isinstance(transcript, str) or not transcript.strip():
        return False

    phrase, wake_detected = (
        voice_engine.parse_wake_word_and_intent(transcript)
    )

    # Ignore speech without valid activation.
    if not wake_detected:
        return False

    # Wake word detected, but no command yet.
    if not phrase:
        print("[STATUS] Wake Word detected. Listening for command...")
        FeedbackHandler._beep()
        return False

    # Accept only explicitly supported commands.
    intent = command_parser.parse_intent(phrase)

    if intent is None:
        FeedbackHandler.rejected("Command not recognized.")
        return False

    # Execute only a validated intent.
    return bool(media_controller.execute_intent(intent))

def main():
    print("==================================================")
    print(" Voice Assistant for MultiMedia Controls - Backlog 2")
    print(" Privacy Guarantee: 100% Local Processing (NF-3)")
    print(" Instructions: Say 'ASSISTANT' followed by a command")
    print(" Commands: play, pause, volume up, volume down, mute, next, previous")
    print(" Press Ctrl+C to exit")
    print("==================================================\n")

        # Initialize modules
    try:
        voice_engine = VoiceEngine(
            model_path="model",
            sample_rate=16000,
            wake_word="assistant",
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[STARTUP ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    audio_capturer = AudioCapturer(
        sample_rate=16000,
        blocksize=4000,
    )

    if not audio_capturer.start_stream():
        audio_capturer.stop_stream()
        print(
            "[STARTUP ERROR] Unable to start microphone.",
            file=sys.stderr,
        )
        sys.exit(1)

    command_parser = CommandParser()
    media_backend = os.getenv("MEDIA_BACKEND", "os").lower()
    print(f"[CONFIG] Media backend: {media_backend.upper()}")

    try:
        media_controller = MediaController(backend=media_backend)
    except Exception as exc:
        print(f"[STARTUP ERROR] Could not initialize media controller: {exc}")
        audio_capturer.stop_stream()
        sys.exit(1)

    try:
        while True:
            # 1. Fetch raw PCM audio chunk from microphone stream
            pcm_chunk = audio_capturer.get_audio_chunk(timeout=0.5)
            if not pcm_chunk:
                continue

            # 2. Process audio with offline Vosk engine
            transcript = voice_engine.process_audio_chunk(pcm_chunk)
            if transcript:
                print(f"[TRANSCRIPT] Spoken Text: '{transcript}'")

                handle_transcript(
                    transcript,
                    voice_engine,
                    command_parser,
                    media_controller,
                )

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping Voice Assistant...")
    finally:
        audio_capturer.stop_stream()
        media_controller.close() #release VLC instance upon application exit
        print("[SHUTDOWN] Clean exit complete.")

if __name__ == "__main__":
    main()
