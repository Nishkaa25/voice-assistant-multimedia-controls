class CommandParser:
    def __init__(self):
        """
        FR-12, FR-11, UC-09, UC-10: Command Parser & Intent Mapper.
        Maps spoken words/phrases to normalized internal media intents.
        """
        self.intent_map = {
            "play": "PLAY",
            "start": "PLAY",
            "resume": "PLAY",
            "pause": "PAUSE",
            "stop": "PAUSE",
            "volume up": "VOLUME_UP",
            "increase volume": "VOLUME_UP",
            "louder": "VOLUME_UP",
            "volume down": "VOLUME_DOWN",
            "decrease volume": "VOLUME_DOWN",
            "quieter": "VOLUME_DOWN",
            "mute": "MUTE",
            "unmute": "MUTE",
            "next": "NEXT",
            "next track": "NEXT",
            "skip": "NEXT",
            "previous": "PREVIOUS",
            "previous track": "PREVIOUS",
            "back": "PREVIOUS"
        }

    def parse_intent(self, phrase):
        """
        Validates spoken phrase against vocabulary map.
        Returns mapped intent string or None if unrecognized (FR-11).
        """
        if not phrase:
            return None

        clean_phrase = phrase.strip().lower()

        # Direct string lookup
        if clean_phrase in self.intent_map:
            return self.intent_map[clean_phrase]

        # Partial phrase matching
        for keyword, intent in self.intent_map.items():
            if keyword in clean_phrase:
                return intent

        # FR-11 / UC-10: Unrecognized Command Fallback
        return None