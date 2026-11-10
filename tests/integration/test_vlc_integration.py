import os
import time
from pathlib import Path

import pytest
import requests
from requests.auth import HTTPBasicAuth

from src.media_backends.vlc_backend import VLCBackend


# Configuration
BASE_URL = os.getenv("VLC_HTTP_URL", "http://127.0.0.1:8081").rstrip("/")
PASSWORD = os.getenv("VLC_HTTP_PASSWORD")

AUDIO_DIR = Path(__file__).parents[1] / "fixtures" / "audio"

POLL_TIMEOUT = 10
POLL_INTERVAL = 0.2


def wait_until(condition, timeout=POLL_TIMEOUT):
    """Wait until a VLC state condition becomes true."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(POLL_INTERVAL)

    return False


@pytest.fixture(scope="module")
def audio_files():
    files = sorted(AUDIO_DIR.glob("*.mp3"))

    if len(files) < 2:
        pytest.skip("At least two MP3 fixtures are required.")

    return files


@pytest.fixture
def vlc():
    """Connect to the existing VLC HTTP instance."""
    if not PASSWORD:
        pytest.skip("VLC_HTTP_PASSWORD is not configured.")

    backend = VLCBackend()

    yield backend

    backend.close()


@pytest.fixture
def playlist(audio_files):
    """Reset VLC playlist and enqueue test audio files."""
    if not PASSWORD:
        pytest.skip("VLC_HTTP_PASSWORD is not configured.")

    session = requests.Session()
    session.auth = HTTPBasicAuth("", PASSWORD)

    def command(**params):
        response = session.get(
            f"{BASE_URL}/requests/status.json",
            params=params,
            timeout=3,
        )
        response.raise_for_status()
        return response

    try:
        command(command="pl_stop")
        command(command="pl_empty")

        for audio_file in audio_files:
            command(
                command="in_enqueue",
                input=audio_file.resolve().as_uri(),
            )

        def tracks_loaded():
            response = session.get(
                f"{BASE_URL}/requests/playlist.json",
                timeout=3,
            )
            response.raise_for_status()

            playlist_data = response.json()

            return sum(
                1
                for group in playlist_data.get("children", [])
                for item in group.get("children", [])
                if item.get("type") == "leaf"
            ) >= 2

        assert wait_until(tracks_loaded), "VLC failed to load test tracks."

        yield

    finally:
        try:
            command(command="pl_stop")
            command(command="pl_empty")
        finally:
            session.close()


def get_status():
    response = requests.get(
        f"{BASE_URL}/requests/status.json",
        auth=HTTPBasicAuth("", PASSWORD),
        timeout=3,
    )
    response.raise_for_status()
    return response.json()


# Playback

def test_playback(vlc, playlist):
    assert vlc.execute_intent("PLAY") is True

    assert wait_until(
        lambda: get_status().get("state") == "playing"
    )

    status = get_status()

    assert status["currentplid"] != -1
    assert wait_until(
        lambda: get_status().get("time", 0) > 0
    ), "VLC playback time did not advance."


def test_pause_and_resume(vlc, playlist):
    assert vlc.execute_intent("PLAY") is True

    assert wait_until(
        lambda: get_status().get("state") == "playing"
    )

    assert vlc.execute_intent("PAUSE") is True

    assert wait_until(
        lambda: get_status().get("state") == "paused"
    )

    assert vlc.execute_intent("RESUME") is True

    assert wait_until(
        lambda: get_status().get("state") == "playing"
    )


# Navigation

def test_next_and_previous(vlc, playlist):
    assert vlc.execute_intent("PLAY") is True

    assert wait_until(
        lambda: get_status().get("state") == "playing"
    )

    first_track = get_status()["currentplid"]

    assert vlc.execute_intent("NEXT") is True

    assert wait_until(
        lambda: (
            get_status()["currentplid"] != first_track
            and get_status()["state"] == "playing"
        )
    )

    second_track = get_status()["currentplid"]

    assert second_track != first_track

    assert vlc.execute_intent("PREVIOUS") is True

    assert wait_until(
        lambda: (
            get_status()["currentplid"] == first_track
            and get_status()["state"] == "playing"
        )
    )


# Volume

def test_volume_up_and_down(vlc, playlist):
    # Start from a predictable volume.
    requests.get(
        f"{BASE_URL}/requests/status.json",
        params={"command": "volume", "val": "128"},
        auth=HTTPBasicAuth("", PASSWORD),
        timeout=3,
    ).raise_for_status()

    initial_volume = vlc.get_volume()

    assert vlc.execute_intent("VOLUME_UP") is True

    assert wait_until(
        lambda: vlc.get_volume() > initial_volume
    )

    increased_volume = vlc.get_volume()

    assert vlc.execute_intent("VOLUME_DOWN") is True

    assert wait_until(
        lambda: vlc.get_volume() < increased_volume
    )


def test_mute_and_unmute(vlc, playlist):
    requests.get(
        f"{BASE_URL}/requests/status.json",
        params={"command": "volume", "val": "128"},
        auth=HTTPBasicAuth("", PASSWORD),
        timeout=3,
    ).raise_for_status()

    assert vlc.execute_intent("MUTE") is True

    assert wait_until(
        lambda: get_status()["volume"] == 0
    )

    assert vlc.execute_intent("UNMUTE") is True

    assert wait_until(
        lambda: get_status()["volume"] > 0
    )


# Empty playlist

def test_play_with_empty_playlist(vlc, playlist):
    response = requests.get(
        f"{BASE_URL}/requests/status.json",
        params={"command": "pl_empty"},
        auth=HTTPBasicAuth("", PASSWORD),
        timeout=3,
    )
    response.raise_for_status()

    assert vlc.execute_intent("PLAY") is False