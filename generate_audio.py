
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("synthetic_voice_samples")
MODEL = Path("en_US-lessac-medium.onnx")

COMMANDS = {
    "assistant": "assistant",
    "play": "play",
    "pause": "pause",
    "volume_up": "volume up",
    "volume_down": "volume down",
    "mute": "mute",
    "unmute": "[[ ʌnmjˈuːt ]]",
    "quiet": "quiet",
    "speak": "[[ spˈiːk ]]",
    "next": "next",
    "previous": "previous",
}


def generate_audio(filename, text):
    output_file = OUTPUT_DIR / f"{filename}.wav"

    print(f"Generating {output_file}...")

    subprocess.run(
        [
            "python",
            "-m",
            "piper",
            "-m", str(MODEL),
            "-f", str(output_file),
            "--",
            text,
        ],
        check=True,
    )


def main():
    if not MODEL.exists():
        raise FileNotFoundError(
            f"Voice model not found: {MODEL}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename, text in COMMANDS.items():
        generate_audio(filename, text)

    print("\nAll audio files generated successfully.")


if __name__ == "__main__":
    main()
