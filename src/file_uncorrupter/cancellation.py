from __future__ import annotations

import threading
from pathlib import Path


class CancelledError(RuntimeError):
    pass


class CancellationToken:
    def __init__(self, marker_path: Path | None = None) -> None:
        self._event = threading.Event()
        self._reason: str | None = None
        self.marker_path = Path(marker_path) if marker_path is not None else None

    def cancel(self, reason: str = "requested") -> None:
        self._reason = reason
        self._event.set()

    @property
    def reason(self) -> str | None:
        if self.marker_path is not None and self.marker_path.exists() and not self._event.is_set():
            self.cancel("marker_file")
        return self._reason

    @property
    def cancelled(self) -> bool:
        _ = self.reason
        return self._event.is_set()

    def checkpoint(self) -> None:
        if self.cancelled:
            raise CancelledError(self.reason or "cancelled")

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)
