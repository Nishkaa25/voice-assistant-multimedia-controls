
import re


class CommandParser:
    def __init__(self):
        """
        Maps supported spoken phrases to internal command identifiers.
        Unsupported or ambiguous phrases return None.
        """
        self.intent_map = {
            # Playback
            "play": "PLAY",
            "start": "PLAY",
            "play music": "PLAY",

            "pause": "PAUSE",
            "pause playback": "PAUSE",
            "stop": "PAUSE",

            "resume": "RESUME",
            "continue": "RESUME",
            "resume playback": "RESUME",

            # Volume
            "volume up": "VOLUME_UP",
            "increase volume": "VOLUME_UP",
            "louder": "VOLUME_UP",

            "volume down": "VOLUME_DOWN",
            "decrease volume": "VOLUME_DOWN",
            "quieter": "VOLUME_DOWN",

            # Mute controls
            "mute": "MUTE",
            "mute audio": "MUTE",

            "unmute": "UNMUTE",
            "unmute audio": "UNMUTE",

            # Track navigation
            "next": "NEXT",
            "next track": "NEXT",
            "skip": "NEXT",

            "previous": "PREVIOUS",
            "previous track": "PREVIOUS",
            "back": "PREVIOUS",
        }

    def parse_intent(self, phrase):
        """
        Convert a recognized phrase into a command identifier.

        Returns:
            A command identifier if the phrase is supported.
            None if the phrase is empty, unsupported, or ambiguous.
        """
        if not isinstance(phrase, str) or not phrase.strip():
            return None

        # Normalize case, punctuation and extra spaces.
        clean_phrase = re.sub(r"[^a-z0-9\s]", "", phrase.lower())
        clean_phrase = " ".join(clean_phrase.split())

        # Exact matching prevents accidental commands from substrings.
        return self.intent_map.get(clean_phrase)
