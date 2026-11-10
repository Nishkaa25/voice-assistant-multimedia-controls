
import queue
from unittest.mock import Mock, patch

import pytest

from src.audio_capture import AudioCapturer


@pytest.fixture
def mock_audio():
    return Mock()


@pytest.fixture
def capturer(mock_audio):
    return AudioCapturer(audio_module=mock_audio)

# Initialization

def test_default_initialization(capturer):
    assert capturer.sample_rate == 16000
    assert capturer.blocksize == 4000
    assert capturer.channels == 1
    assert capturer.stream is None
    assert capturer.is_running is False
    assert capturer.audio_queue.empty()


def test_custom_initialization():
    capturer = AudioCapturer(
        sample_rate=44100,
        blocksize=2048,
        channels=2,
    )

    assert capturer.sample_rate == 44100
    assert capturer.blocksize == 2048
    assert capturer.channels == 2


# Audio callback

def test_callback_adds_audio_to_queue(capturer):
    audio_data = bytearray(b"audio data")
    status = Mock(input_overflow=False)

    capturer._audio_callback(audio_data, 10, None, status)

    assert capturer.audio_queue.get_nowait() == bytes(audio_data)


def test_callback_suppresses_overflow_warning(capturer, capsys):
    status = Mock(input_overflow=True)

    capturer._audio_callback(b"audio", 10, None, status)

    captured = capsys.readouterr()
    assert "[AUDIO WARN]" not in captured.err


def test_callback_reports_other_stream_status(capturer, capsys):
    status = Mock(input_overflow=False)
    status.__bool__ = Mock(return_value=True)

    capturer._audio_callback(b"audio", 10, None, status)

    captured = capsys.readouterr()
    assert "[AUDIO WARN]" in captured.err


def test_callback_handles_full_queue(capturer):
    capturer.audio_queue = queue.Queue(maxsize=1)
    capturer.audio_queue.put_nowait(b"existing")

    capturer._audio_callback(
        b"new audio",
        10,
        None,
        Mock(input_overflow=False),
    )

    assert capturer.audio_queue.get_nowait() == b"existing"


# Stream startup

def test_start_stream_success(capturer, mock_audio):
    stream = mock_audio.RawInputStream.return_value

    assert capturer.start_stream() is True

    mock_audio.RawInputStream.assert_called_once_with(
        samplerate=16000,
        blocksize=4000,
        dtype="int16",
        channels=1,
        callback=capturer._audio_callback,
    )

    stream.start.assert_called_once()
    assert capturer.stream is stream
    assert capturer.is_running is True


def test_start_stream_failure(capturer, mock_audio):
    mock_audio.RawInputStream.side_effect = RuntimeError("Device unavailable")

    assert capturer.start_stream() is False
    assert capturer.is_running is False


def test_start_stream_stops_existing_stream(capturer, mock_audio):
    old_stream = Mock()
    capturer.stream = old_stream
    capturer.is_running = True

    assert capturer.start_stream() is True

    old_stream.stop.assert_called_once()
    old_stream.close.assert_called_once()



# Audio retrieval

def test_get_audio_chunk_returns_queued_data(capturer):
    capturer.audio_queue.put(b"audio data")

    assert capturer.get_audio_chunk() == b"audio data"


def test_get_audio_chunk_timeout_without_running_stream(capturer):
    assert capturer.get_audio_chunk(timeout=0.01) is None


def test_get_audio_chunk_timeout_restarts_running_stream(capturer):
    capturer.is_running = True

    with patch.object(capturer, "restart_stream") as restart:
        result = capturer.get_audio_chunk(timeout=0.01)

    assert result is None
    restart.assert_called_once()


# Stream recovery


def test_restart_stream_calls_start_stream(capturer, mock_audio):
    stream = mock_audio.RawInputStream.return_value

    capturer.restart_stream()

    stream.start.assert_called_once()
    assert capturer.is_running is True


# Shutdown

def test_stop_stream_stops_and_closes_stream(capturer):
    stream = Mock()
    capturer.stream = stream
    capturer.is_running = True

    capturer.audio_queue.put(b"stale audio")

    capturer.stop_stream()

    stream.stop.assert_called_once()
    stream.close.assert_called_once()

    assert capturer.stream is None
    assert capturer.is_running is False
    assert capturer.audio_queue.empty()


def test_stop_stream_without_existing_stream(capturer):
    capturer.audio_queue.put(b"stale audio")

    capturer.stop_stream()

    assert capturer.stream is None
    assert capturer.is_running is False
    assert capturer.audio_queue.empty()


def test_stop_stream_handles_cleanup_errors(capturer):
    stream = Mock()
    stream.stop.side_effect = RuntimeError("Stream already stopped")

    capturer.stream = stream
    capturer.is_running = True

    capturer.stop_stream()

    assert capturer.stream is None
    assert capturer.is_running is False
