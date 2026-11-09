
import argparse
import json
import subprocess
import sys

from src.voice_engine import VoiceEngine


class MediaFileTranscriber:
    def __init__(self, file_path, model_path="model"):
        self.file_path = file_path
        self.voice_engine = VoiceEngine(
            model_path=model_path,
            sample_rate=16000,
        )

    def transcribe(self):
        command = [
            "ffmpeg",
            "-v", "error",
            "-i", self.file_path,
            "-vn",
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "pipe:1",
        ]

        print(f"[INFO] Processing: {self.file_path}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        transcripts = []
        chunk_size = 4000 * 2  # 4000 samples, 2 bytes each

        try:
            while True:
                chunk = process.stdout.read(chunk_size)

                if not chunk:
                    break

                transcript = self.voice_engine.process_audio_chunk(chunk)

                if transcript:
                    transcripts.append(transcript)
                    print(f"[TRANSCRIPT] {transcript}")

            # Flush the final unfinished utterance.
            final_result = json.loads(
                self.voice_engine.recognizer.FinalResult()
            )

            final_text = final_result.get("text", "").strip().lower()

            if final_text:
                transcripts.append(final_text)
                print(f"[TRANSCRIPT] {final_text}")

        finally:
            process.stdout.close()
            stderr = process.stderr.read()
            process.stderr.close()
            return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(
                f"FFmpeg failed: {stderr.decode(errors='replace')}"
            )

        return transcripts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe audio or video files using Vosk."
    )

    parser.add_argument("file", help="Input media file")
    parser.add_argument("--model", default="model")

    args = parser.parse_args()

    try:
        transcriber = MediaFileTranscriber(
            args.file,
            args.model,
        )

        results = transcriber.transcribe()

        print("\n========== FINAL TRANSCRIPT ==========")
        print(" ".join(results) if results else "No speech recognized.")

    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
