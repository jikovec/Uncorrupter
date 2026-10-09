from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def stable_source_id(path: Path, *, salt: str) -> str:
    canonical = str(Path(path).resolve()).encode("utf-8", errors="surrogatepass")
    return "source:" + hashlib.sha256(salt.encode("utf-8") + b"\0" + canonical).hexdigest()[:20]


def redact_paths(value: Any, *, roots: list[Path], salt: str) -> Any:
    canonical = sorted(((str(root.resolve()), stable_source_id(root, salt=salt)) for root in roots), key=lambda item: -len(item[0]))
    if isinstance(value, str):
        result = value
        for raw, identifier in canonical:
            flags = re.IGNORECASE if os.name == "nt" else 0
            result = re.sub(re.escape(raw), lambda _: identifier, result, flags=flags)
            result = re.sub(re.escape(raw.replace("\\", "/")), lambda _: identifier, result, flags=flags)
        return result
    if isinstance(value, dict):
        return {key: redact_paths(item, roots=roots, salt=salt) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_paths(item, roots=roots, salt=salt) for item in value]
    if isinstance(value, tuple):
        return [redact_paths(item, roots=roots, salt=salt) for item in value]
    return value


class MachineEventWriter:
    def __init__(
        self,
        path: Path,
        *,
        redact_roots: list[Path] | None = None,
        redaction_salt: str = "uncorrupter",
        clock: Callable[[], datetime] | None = None,
        initialize: bool = True,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.redact_roots = redact_roots or []
        self.redaction_salt = redaction_salt
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._sequence = 0
        self._lock = threading.Lock()
        if initialize:
            with self.path.open("x", encoding="utf-8"):
                pass

    def emit(self, event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            self._sequence += 1
            record = {
                "sequence": self._sequence,
                "timestamp": self.clock().isoformat().replace("+00:00", "Z"),
                "event": event,
                "payload": redact_paths(payload or {}, roots=self.redact_roots, salt=self.redaction_salt),
            }
            line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            return record
