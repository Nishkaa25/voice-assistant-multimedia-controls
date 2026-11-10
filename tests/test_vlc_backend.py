
import pytest
from unittest.mock import MagicMock, patch

from requests.exceptions import ConnectionError, HTTPError

from src.media_backends.vlc_backend import VLCBackend


@pytest.fixture
def backend():
    """Create a backend without connecting to a real VLC instance."""
    instance = VLCBackend.__new__(VLCBackend)
    instance.base_url = "http://localhost:8080"
    instance.previous_volume = None
    instance.session = MagicMock()
    instance.session.get.return_value.raise_for_status.return_value = None
    return instance


def response(data):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    return mock


# Initialization

@patch.dict("os.environ", {}, clear=True)
def test_missing_password():
    with pytest.raises(ValueError, match="VLC_HTTP_PASSWORD"):
        VLCBackend()


@patch("src.media_backends.vlc_backend.Session")
@patch.dict("os.environ", {"VLC_HTTP_PASSWORD": "test"})
def test_successful_initialization(mock_session):
    session = mock_session.return_value
    session.get.return_value = response({"loop": True})

    backend = VLCBackend()

    assert backend.session is session
    session.close.assert_not_called()


# Playlist

def test_has_tracks(backend):
    backend._get_playlist = MagicMock(return_value={
        "children": [{"type": "leaf", "name": "song.mp3"}]
    })

    assert backend._has_tracks() is True


def test_empty_playlist(backend):
    backend._get_playlist = MagicMock(return_value={"children": []})

    assert backend._has_tracks() is False


def test_playlist_error(backend):
    backend._get_playlist = MagicMock(side_effect=ConnectionError())

    assert backend._has_tracks() is None


# Playback commands

@pytest.mark.parametrize("intent, command", [
    ("PLAY", "pl_play"),
    ("RESUME", "pl_forceresume"),
    ("PAUSE", "pl_forcepause"),
    ("VOLUME_UP", "volume"),
    ("VOLUME_DOWN", "volume"),
])
def test_execute_command(backend, intent, command):
    backend._has_tracks = MagicMock(return_value=True)

    assert backend.execute_intent(intent) is True

    called_params = backend.session.get.call_args.kwargs["params"]
    assert called_params["command"] == command


def test_unsupported_intent(backend):
    assert backend.execute_intent("DANCE") is False
    backend.session.get.assert_not_called()


def test_play_with_empty_playlist(backend):
    backend._has_tracks = MagicMock(return_value=False)

    assert backend.execute_intent("PLAY") is False
    backend.session.get.assert_not_called()


def test_play_when_playlist_unavailable(backend):
    backend._has_tracks = MagicMock(return_value=None)

    assert backend.execute_intent("PLAY") is False


def test_http_command_failure(backend):
    backend._has_tracks = MagicMock(return_value=True)
    backend.session.get.side_effect = ConnectionError()

    assert backend.execute_intent("PLAY") is False


# Navigation

def test_next_track(backend):
    backend._get_playlist = MagicMock(return_value={
        "children": [
            {"type": "leaf", "name": "one.mp3"},
            {"type": "leaf", "name": "two.mp3"},
        ]
    })

    assert backend._navigate("NEXT") is True

    params = backend.session.get.call_args.kwargs["params"]
    assert params["command"] == "pl_next"


def test_previous_track(backend):
    backend._get_playlist = MagicMock(return_value={
        "children": [
            {"type": "leaf", "name": "one.mp3"},
            {"type": "leaf", "name": "two.mp3"},
        ]
    })

    assert backend._navigate("PREVIOUS") is True

    params = backend.session.get.call_args.kwargs["params"]
    assert params["command"] == "pl_previous"


def test_navigation_with_single_track(backend):
    backend._get_playlist = MagicMock(return_value={
        "children": [{"type": "leaf", "name": "one.mp3"}]
    })

    assert backend._navigate("NEXT") is True
    backend.session.get.assert_not_called()


# Volume

def test_get_volume(backend):
    backend._request = MagicMock(return_value=response({"volume": 174}))

    assert backend.get_volume() == 68


def test_get_volume_failure(backend):
    backend._request = MagicMock(side_effect=ConnectionError())

    assert backend.get_volume() is None


# Mute and unmute

def test_mute_saves_previous_volume(backend):
    backend._request = MagicMock(side_effect=[
        response({"volume": 174}),
        response({}),
    ])

    assert backend._mute() is True
    assert backend.previous_volume == 174

    assert backend._request.call_args.kwargs == {
        "command": "volume",
        "val": "0",
    }


def test_unmute_restores_previous_volume(backend):
    backend.previous_volume = 174
    backend._request = MagicMock(side_effect=[
        response({"volume": 0}),
        response({}),
    ])

    assert backend._unmute() is True
    assert backend.previous_volume is None

    assert backend._request.call_args.kwargs == {
        "command": "volume",
        "val": "174",
    }


def test_unmute_without_saved_volume(backend):
    backend._request = MagicMock(return_value=response({"volume": 0}))

    assert backend._unmute() is True
    assert backend._request.call_count == 1


# Track information

def test_get_current_track(backend):
    backend._request = MagicMock(return_value=response({
        "currentplid": 1
    }))
    backend._get_playlist = MagicMock(return_value={
        "children": [
            {"type": "leaf", "id": 1, "name": "song.mp3"}
        ]
    })

    assert backend.get_current_track() == "song.mp3"


def test_current_track_missing(backend):
    backend._request = MagicMock(return_value=response({}))

    assert backend.get_current_track() is None


# Cleanup

def test_close(backend):
    backend.close()
    backend.session.close.assert_called_once()
