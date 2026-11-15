# src/command_logger.py
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class CommandLogger:
    """
    Records privacy-safe command metadata (no raw audio/video) with bounded
    disk growth via RotatingFileHandler and fault-tolerant write handling.
    """

    MAX_BYTES = 1 * 1024 * 1024  # 1 MB per log file
    BACKUP_COUNT = 3             # Keep up to 3 rotated archives (~4 MB total cap)

    def __init__(self, log_dir: str = "logs", filename: str = "command_history.jsonl"):
        self.log_path = Path(log_dir) / filename
        self._logger = logging.getLogger("VoiceAssistantCommandLogger")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._enabled = False

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            if not self._logger.handlers:
                handler = RotatingFileHandler(
                    self.log_path,
                    maxBytes=self.MAX_BYTES,
                    backupCount=self.BACKUP_COUNT,
                    encoding="utf-8",
                )
                handler.setFormatter(logging.Formatter("%(message)s"))
                self._logger.addHandler(handler)
            self._enabled = True
        except OSError as exc:
            print(f"[LOGGER WARNING] Could not initialize log file at {self.log_path}: {exc}")

    def log_event(
        self,
        command: Optional[str],
        source: str,
        status: str,
        latency_ms: float,
        error_code: Optional[str] = None,
    ) -> bool:
        """
        Writes a single JSONL metadata record. Never raises exceptions to caller
        so a logging failure cannot interrupt command execution.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "command": command if command else "UNRECOGNIZED",
            "source": source,
            "status": status.upper(),
            "latency_ms": round(latency_ms, 2),
            "error_code": error_code,
        }

        if not self._enabled:
            print(f"[LOGGER FALLBACK] {json.dumps(record)}")
            return False

        try:
            self._logger.info(json.dumps(record))
            return True
        except Exception as exc:
            # Graceful degradation: warn in console without stopping assistant loop
            print(f"[LOGGER WARNING] Failed to write command log ({exc}): {json.dumps(record)}")
            return False