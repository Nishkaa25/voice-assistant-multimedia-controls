
import pytest

from src.command_parser import CommandParser


@pytest.fixture
def parser():
    return CommandParser()


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("play", "PLAY"),
        ("start", "PLAY"),
        ("play music", "PLAY"),
        ("pause", "PAUSE"),
        ("resume", "RESUME"),
        ("continue", "RESUME"),
        ("volume up", "VOLUME_UP"),
        ("increase volume", "VOLUME_UP"),
        ("volume down", "VOLUME_DOWN"),
        ("decrease volume", "VOLUME_DOWN"),
        ("mute", "MUTE"),
        ("unmute", "UNMUTE"),
        ("next", "NEXT"),
        ("next track", "NEXT"),
        ("previous", "PREVIOUS"),
        ("previous track", "PREVIOUS"),
    ],
)
def test_supported_phrases(parser, phrase, expected):
    assert parser.parse_intent(phrase) == expected


@pytest.mark.parametrize(
    "phrase",
    [
        None,
        "",
        "   ",
        "open settings",
        "play and pause",
        "please play something",
        "unmute mute",
        123,
    ],
)
def test_invalid_or_ambiguous_phrases(parser, phrase):
    assert parser.parse_intent(phrase) is None


def test_mute_and_unmute_are_distinct(parser):
    assert parser.parse_intent("mute") == "MUTE"
    assert parser.parse_intent("unmute") == "UNMUTE"
