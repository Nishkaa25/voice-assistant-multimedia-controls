import os
from requests import Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

TRACK_COMMANDS = {
    "PLAY",
    "RESUME",
    "PAUSE",
    "NEXT",
    "PREVIOUS",
}

VOLUME_COMMANDS = {
    "VOLUME_UP",
    "VOLUME_DOWN",
    "MUTE",
    "UNMUTE",
}

COMMANDS = {
    "PLAY": ("status.json", {"command": "pl_play"}),
    "RESUME": ("status.json", {"command": "pl_forceresume"}),
    "PAUSE": ("status.json", {"command": "pl_forcepause"}),
    "VOLUME_UP": ("status.json", {"command": "volume", "val": "+10"}),
    "VOLUME_DOWN": ("status.json", {"command": "volume", "val": "-10"}),
}

class VLCBackend:
    """Control an existing VLC instance through its HTTP interface."""

    def __init__(self):
        self.base_url = os.getenv(
            "VLC_HTTP_URL", "http://localhost:8080"
        ).rstrip("/")

        self.previous_volume = None

        password = os.getenv("VLC_HTTP_PASSWORD")
        if not password:
            raise ValueError(
                "Set the VLC_HTTP_PASSWORD environment variable."
            )

        self.session = Session()
        self.session.auth = HTTPBasicAuth("", password)
        self.session.timeout = 3

        # Verify that the existing VLC instance is reachable.
        try:
            self._request("status.json")
            print("[VLC] Connected successfully.")

            if not self.enable_looping():
                print("[VLC WARNING] Could not enable playlist looping.")

        except RequestException as exc:
            self.session.close()
            raise RuntimeError(
                f"Could not connect to VLC at {self.base_url}: {exc}"
            ) from exc

    def _request(self, endpoint, **params):
        response = self.session.get(
            f"{self.base_url}/requests/{endpoint}",
            params=params,
            timeout=3,
        )
        response.raise_for_status()
        return response

    def _has_tracks(self):
        try:
            playlist = self._get_playlist()
            items = playlist.get("children", [])

            for item in items:
                if item.get("type") == "leaf":
                    return True

                if any(
                    child.get("type") == "leaf"
                    for child in item.get("children", [])
                ):
                    return True

            return False

        except (RequestException, ValueError) as exc:
            print(f"[VLC ERROR] Could not read playlist: {exc}")
            return None
        
    def execute_intent(self, intent):
        intent = intent.upper()

        if intent not in TRACK_COMMANDS | VOLUME_COMMANDS:
            print(f"[VLC ERROR] Unsupported intent: {intent}")
            return False

        # Only playback and track navigation require a loaded track.
        if intent in TRACK_COMMANDS:
            has_tracks = self._has_tracks()

            if has_tracks is False:
                print("[VLC] Playlist is empty.")
                return False

            if has_tracks is None:
                return False

        if intent == "MUTE":
            return self._mute()
        if intent == "UNMUTE":
            return self._unmute()

        if intent in ("NEXT", "PREVIOUS"):
            return self._navigate(intent)

        endpoint, params = COMMANDS[intent]

        try:
            self._request(endpoint, **params)
            return True
        except RequestException as exc:
            print(f"[VLC ERROR] HTTP command failed: {exc}")
            return False
        
    def _get_playlist(self):
        response = self._request("playlist.json")
        return response.json()
    
    def _navigate(self, intent):
        try:
            playlist = self._get_playlist()
            items = playlist.get("children", [])

            # VLC's playlist response may contain nested groups, for the mvp we will only
            # handle direct file uploads(in VLC that means choosing multiple files, no folders or no nested folders)
            items = [
                item
                for item in items
                if item.get("type") == "leaf"
            ]

            if len(items) == 1:
                print("[VLC] Only one track in playlist.")
                return True

            command = "pl_next" if intent == "NEXT" else "pl_previous"
            self._request("status.json", command=command)
            return True

        except (RequestException, ValueError) as exc:
            print(f"[VLC ERROR] Navigation failed: {exc}")
            return False
        
    def _mute(self):
        try:
            status = self._request("status.json").json()
            current_volume = status.get("volume", 0)

            if current_volume > 0:
                self.previous_volume = current_volume
                self._request(
                    "status.json", command="volume", val="0"
                )
            return True
        
        except (RequestException, ValueError) as exc:
            print(f"[VLC ERROR] Could not mute VLC: {exc}")
            return False


    def _unmute(self):
        try:
            status = self._request("status.json").json()
            current_volume = status.get("volume", 0)

            if current_volume == 0 and self.previous_volume is not None:
                self._request(
                    "status.json",
                    command="volume",
                    val=str(self.previous_volume),
                )
                self.previous_volume = None

            return True
        except (RequestException, ValueError) as exc:
            print(f"[VLC ERROR] Could not unmute VLC: {exc}")
            return False

    def enable_looping(self):
        """Enable VLC playlist looping if it is not already enabled."""
        try:
            status = self._request("status.json").json()

            if not status.get("loop", False):
                self._request("status.json", command="pl_loop")

            return True
        except (RequestException, ValueError) as exc:
            print(f"[VLC ERROR] Could not enable playlist looping: {exc}")
            return False
        
    def close(self):
        self.session.close()
