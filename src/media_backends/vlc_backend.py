import os
from requests import Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException


class VLCBackend:
    """Control an existing VLC instance through its HTTP interface."""

    def __init__(self):
        self.base_url = os.getenv(
            "VLC_HTTP_URL", "http://localhost:8080"
        ).rstrip("/")

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

    def execute_intent(self, intent):
        intent = intent.upper()

        commands = {
            "PLAY": ("status.json", {"command": "pl_play"}),
            "RESUME": ("status.json", {"command": "pl_forceresume"}),
            "PAUSE": ("status.json", {"command": "pl_forcepause"}),
            "NEXT": ("status.json", {"command": "pl_next"}),
            "PREVIOUS": ("status.json", {"command": "pl_previous"}),
            "VOLUME_UP": ("status.json", {"command": "volume", "val": "+10"}),
            "VOLUME_DOWN": ("status.json", {"command": "volume", "val": "-10"}),
            "MUTE": ("status.json", {"command": "volume", "val": "0"}),
        }

        if intent == "UNMUTE":
            return self._unmute()

        if intent not in commands:
            print(f"[VLC ERROR] Unsupported intent: {intent}")
            return False

        endpoint, params = commands[intent]

        try:
            self._request(endpoint, **params)
            return True
        except RequestException as exc:
            print(f"[VLC ERROR] HTTP command failed: {exc}")
            return False

    def _unmute(self):
        try:
            status = self._request("status.json").json()
            current_volume = status.get("volume", 100)

            # VLC reports volume as an integer, commonly 0 to 512.
            if current_volume == 0:
                self._request(
                    "status.json", command="volume", val="256"
                )
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
