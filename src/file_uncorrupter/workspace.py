from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
        leaf = self.blobs_dir / digest[:2]
        leaf.mkdir(parents=True, exist_ok=True)
        path = leaf / f"{digest}{suffix}"
        if not path.exists():
            path.write_bytes(data)
        return path

    def write_config_snapshot(self, run_id: int, config: dict[str, Any]) -> Path:
        path = self.configs_dir / f"run-{run_id:06d}.json"
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


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
