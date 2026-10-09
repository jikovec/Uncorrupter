from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .atomic import AtomicArtifactWriter, CollisionError

@dataclass(slots=True)
class WorkspaceLayout:
    root: Path
    db_path: Path
    blobs_dir: Path
    outputs_dir: Path
    reports_dir: Path
    configs_dir: Path

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

    def store_blob(self, data: bytes, suffix: str = ".bin") -> Path:
        digest = hashlib.sha256(data).hexdigest()
        relative = Path(digest[:2]) / f"{digest}{suffix}"
        path = self.blobs_dir / relative
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"content-addressed blob collision at {path}")
            return path
        try:
            return AtomicArtifactWriter(self.blobs_dir).publish_bytes(relative, data).path
        except CollisionError:
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
                return path
            raise

    def write_config_snapshot(self, run_id: int, config: dict[str, Any]) -> Path:
        payload = (json.dumps(config, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        return AtomicArtifactWriter(self.configs_dir).publish_bytes(f"run-{run_id:06d}.json", payload).path


def build_workspace_layout(
    *,
    input_root: Path,
    db_path: Path,
    output_root: Path | None = None,
    workspace_root: Path | None = None,
) -> WorkspaceLayout:
    if workspace_root is None:
        if output_root is not None:
            workspace_root = output_root / ".uncorrupter-workspace"
        else:
            workspace_root = db_path.parent / ".uncorrupter-workspace"
    return WorkspaceLayout(
        root=workspace_root,
        db_path=db_path,
        blobs_dir=workspace_root / "blobs",
        outputs_dir=workspace_root / "outputs",
        reports_dir=workspace_root / "reports",
        configs_dir=workspace_root / "configs",
    )
