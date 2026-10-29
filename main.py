import sys
import time
from src.audio_capture import AudioCapturer
from src.voice_engine import VoiceEngine
from src.command_parser import CommandParser
from src.media_controller import MediaController
from src.feedback_handler import FeedbackHandler

def main():
    print("==================================================")
    print(" Voice Assistant for MultiMedia Controls - Backlog 2")
    print(" Privacy Guarantee: 100% Local Processing (NF-3)")
    print(" Instructions: Say 'ASSISTANT' followed by a command")
    print(" Commands: play, pause, volume up, volume down, mute, next, previous")
    print(" Press Ctrl+C to exit")
    print("==================================================\n")

    # Initialize modules
    audio_capturer = AudioCapturer(sample_rate=16000, blocksize=4000)
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
    media_controller = MediaController()

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

                # 3. Check for wake word & extract intent phrase
                phrase, wake_detected = voice_engine.parse_wake_word_and_intent(transcript)

                if wake_detected:
                    if phrase:
                        # 4. Parse intent from vocabulary map
                        intent = command_parser.parse_intent(phrase)
                        if intent:
                            # 5. Execute OS media command
                            media_controller.execute_intent(intent)
                        else:
                            print(f"[STATUS] Unrecognized Command Phrase: '{phrase}'")
                            FeedbackHandler.play_error_chime()
                    else:
                        print("[STATUS] Wake Word detected. Listening for command...")

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping Voice Assistant...")
    finally:
        audio_capturer.stop_stream()
        print("[SHUTDOWN] Clean exit complete.")

if __name__ == "__main__":
    main()