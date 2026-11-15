
import os
import time
from pathlib import Path

import pytest
import requests
from requests.auth import HTTPBasicAuth

from src.voice_engine import VoiceEngine
from src.command_parser import CommandParser
from src.media_controller import MediaController
from main import handle_transcript

from tests.performance.benchmark import decode, transcribe_pcm


ROOT_DIR = Path(__file__).resolve().parents[2]
AUDIO_DIR = ROOT_DIR / "synthetic_test_audio"
MODEL_DIR = ROOT_DIR / "model"
MEDIA_DIR = ROOT_DIR / "tests" / "fixtures" / "audio"

VLC_URL = os.getenv(
    "VLC_HTTP_URL",
    "http://127.0.0.1:8081",
).rstrip("/")

VLC_PASSWORD = os.getenv("VLC_HTTP_PASSWORD")

POLL_TIMEOUT = 10
POLL_INTERVAL = 0.2


def wait_until(condition, timeout=POLL_TIMEOUT):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(POLL_INTERVAL)

    return False


def get_vlc_status():
    response = requests.get(
        f"{VLC_URL}/requests/status.json",
        auth=HTTPBasicAuth("", VLC_PASSWORD),
        timeout=3,
    )
    response.raise_for_status()
    return response.json()


@pytest.fixture
def audio_file():
    """Find a prerecorded audio file containing the PLAY command."""

    files = [
        path
        for path in AUDIO_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in (".wav", ".mp3", ".ogg", ".flac", ".m4a")
        and "play" in path.stem.lower()
    ]

    if not files:
        pytest.skip("No PLAY audio fixture found.")

    return files[0]


@pytest.fixture
def vlc_playlist():
    """Prepare a controlled VLC playlist."""

    if not VLC_PASSWORD:
        pytest.skip("VLC_HTTP_PASSWORD is not configured.")

    tracks = sorted(MEDIA_DIR.glob("*.mp3"))

    if len(tracks) < 2:
        pytest.skip("At least two media fixtures are required.")

    auth = HTTPBasicAuth("", VLC_PASSWORD)

    def command(**params):
        response = requests.get(
            f"{VLC_URL}/requests/status.json",
            params=params,
            auth=auth,
            timeout=3,
        )
        response.raise_for_status()

    try:
        command(command="pl_stop")
        command(command="pl_empty")

        for track in tracks:
            command(
                command="in_enqueue",
                input=track.resolve().as_uri(),
            )

        def tracks_loaded():
            response = requests.get(
                f"{VLC_URL}/requests/playlist.json",
                auth=auth,
                timeout=3,
            )
            response.raise_for_status()

            playlist = response.json()

            return sum(
                1
                for group in playlist.get("children", [])
                for item in group.get("children", [])
                if item.get("type") == "leaf"
            ) >= 2

        assert wait_until(tracks_loaded), "VLC failed to load test tracks."

        yield

    finally:
        command(command="pl_stop")
        command(command="pl_empty")


def test_voice_to_vlc_play(audio_file, vlc_playlist):
    """Test prerecorded speech through the application's actual orchestration."""

    assert MODEL_DIR.is_dir(), "Vosk model directory is missing."
    assert VLC_PASSWORD, "VLC_HTTP_PASSWORD is not configured."

    # 1. Decode audio into PCM.
    pcm = decode(str(audio_file))
    assert pcm, "Audio decoding produced no PCM data."

    # 2. Initialize the voice engine.
    voice_engine = VoiceEngine(
        model_path=str(MODEL_DIR),
        sample_rate=16000,
        wake_word="assistant",
    )

    # 3. Perform actual speech recognition.
    transcript, _ = transcribe_pcm(voice_engine, pcm)

    assert transcript, "Speech recognition produced no transcript."
    print(f"\nRecognized transcript: {transcript}")

    # 4. Initialize application components.
    parser = CommandParser()
    controller = MediaController(backend="vlc")

    try:
        # 5. Run the application's actual command orchestration.
        result = handle_transcript(
            transcript,
            voice_engine,
            parser,
            controller,
        )

        assert result is True, (
            f"Application rejected the command. Transcript: {transcript!r}"
        )

        # 6. Verify actual VLC playback.
        assert wait_until(
            lambda: get_vlc_status().get("state") == "playing"
        ), "VLC did not start playback."

        status = get_vlc_status()
        assert status.get("currentplid", -1) != -1

    finally:
        controller.close()

