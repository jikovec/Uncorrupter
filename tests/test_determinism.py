from __future__ import annotations

import hashlib
import json
from pathlib import Path

from file_uncorrupter.cli import EXIT_OK, main
from file_uncorrupter.reporting import normalized_manifest_for_comparison


def _artifact_bytes(root: Path) -> dict[str, tuple[str, bytes]]:
    result: dict[str, tuple[str, bytes]] = {}
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix().casefold()):
        payload = path.read_bytes()
        result[path.relative_to(root).as_posix()] = (hashlib.sha256(payload).hexdigest(), payload)
    return result


def test_two_recovery_runs_have_identical_normalized_manifests_and_artifact_bytes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    input_root = tmp_path / "input"
    input_root.mkdir()
    (input_root / "note.md").write_text("# Stable heading\n\nStable body.\n", encoding="utf-8")
    manifests = []
    outputs = []

    for index in (1, 2):
        output_root = tmp_path / f"output-{index}"
        manifest = tmp_path / f"manifest-{index}.json"
        result = main(
            [
                "recover",
                str(input_root),
                str(output_root),
                "--db",
                str(tmp_path / f"run-{index}.sqlite3"),
                "--workspace-root",
                str(tmp_path / f"workspace-{index}"),
                "--manifest",
                str(manifest),
                "--goal",
                "normalize",
                "--all-files",
                "--workers",
                "1",
                "--quiet",
            ]
        )
        capsys.readouterr()
        assert result == EXIT_OK
        manifests.append(json.loads(manifest.read_text(encoding="utf-8")))
        outputs.append(_artifact_bytes(output_root))

    assert normalized_manifest_for_comparison(manifests[0]) == normalized_manifest_for_comparison(manifests[1])
    assert outputs[0] == outputs[1]
