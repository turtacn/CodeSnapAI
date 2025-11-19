import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from codesage.config.audit import AuditConfig
from .models import AuditEvent


class AuditLogger:
    def __init__(self, config: AuditConfig) -> None:
        self._config = config
        self._current_file: Optional[Path] = None
        self._current_size: int = 0
        self._log_dir_created = False
        self._log_dir: Optional[Path] = None

    def log(self, event: AuditEvent) -> None:
        if not self._config.enabled:
            return

        # One-time setup for the log directory
        if not self._log_dir_created:
            try:
                self._log_dir = Path(self._config.log_dir)
                self._log_dir.mkdir(parents=True, exist_ok=True)
                self._log_dir_created = True
            except (IOError, PermissionError):
                # If we can't create the log dir, disable logging for this session.
                self._config.enabled = False
                return

        # Prepare the log line
        line = event.model_dump_json() + "\n"
        line_bytes = line.encode("utf-8")

        # Rotate log file if needed or open for the first time
        try:
            if self._current_file is None or (self._current_size + len(line_bytes)) > (self._config.max_file_size_mb * 1024 * 1024):
                self._open_new_file()

            # If opening the new file failed, _current_file will be None
            if self._current_file is None:
                return

            with self._current_file.open("ab") as f:
                f.write(line_bytes)
            self._current_size += len(line_bytes)

        except (IOError, PermissionError):
            # If any file operation fails, disable logging for this session.
            self._config.enabled = False
            self._current_file = None

    def _open_new_file(self) -> None:
        try:
            if self._log_dir is None:
                self._log_dir = Path(self._config.log_dir)
                self._log_dir.mkdir(parents=True, exist_ok=True)
                self._log_dir_created = True

            ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            self._current_file = self._log_dir / f"audit_{ts}.log"
            self._current_file.touch()
            self._current_size = 0
        except (IOError, PermissionError):
            self._config.enabled = False
            self._current_file = None
