from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from file_uncorrupter.atomic import (
    AtomicArtifactWriter,
    CollisionError,
    CollisionPolicy,
    ValidationError,
)
from file_uncorrupter.paths import PathLayoutError, contained_path, safe_relative_path, validate_layout


def test_layout_rejects_outputs_workspace_and_database_inside_input(tmp_path):
    source = tmp_path / "input"
    source.mkdir()

    with pytest.raises(PathLayoutError):
        validate_layout(source, source / "output", tmp_path / "workspace", tmp_path / "runs.sqlite3")
    with pytest.raises(PathLayoutError):
        validate_layout(source, tmp_path / "output", source / "workspace", tmp_path / "runs.sqlite3")
    with pytest.raises(PathLayoutError):
        validate_layout(source, tmp_path / "output", tmp_path / "workspace", source / "runs.sqlite3")


@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "C:/drive.txt", "CON.txt", "a/../../b"])
def test_safe_relative_path_rejects_traversal_absolute_and_reserved_names(name):
    with pytest.raises(PathLayoutError):
        safe_relative_path(name)


def test_contained_path_stays_under_root(tmp_path):
    root = tmp_path / "out"
    path = contained_path(root, "folder/recovered.txt")
    assert path == root.resolve() / "folder" / "recovered.txt"


def test_atomic_writer_defaults_to_no_clobber(tmp_path):
    writer = AtomicArtifactWriter(tmp_path)
    destination = tmp_path / "artifact.bin"
    destination.write_bytes(b"existing")
    before = hashlib.sha256(destination.read_bytes()).hexdigest()

    with pytest.raises(CollisionError):
        writer.publish_bytes("artifact.bin", b"replacement")

    assert hashlib.sha256(destination.read_bytes()).hexdigest() == before
    assert not list(tmp_path.glob(".*.uncorrupter-*.tmp"))


def test_atomic_writer_supports_deterministic_suffix_and_explicit_replace(tmp_path):
    (tmp_path / "artifact.txt").write_text("existing", encoding="utf-8")
    writer = AtomicArtifactWriter(tmp_path, collision_policy=CollisionPolicy.SUFFIX)

    first = writer.publish_bytes("artifact.txt", b"first")
    second = writer.publish_bytes("artifact.txt", b"second")

    assert first.path.name == "artifact (1).txt"
    assert second.path.name == "artifact (2).txt"
    replaced = AtomicArtifactWriter(tmp_path, collision_policy=CollisionPolicy.REPLACE).publish_bytes(
        "artifact.txt", b"replacement"
    )
    assert replaced.path.read_bytes() == b"replacement"


def test_atomic_writer_validates_before_publication_and_cleans_temporary_file(tmp_path):
    writer = AtomicArtifactWriter(tmp_path)

    with pytest.raises(ValidationError):
        writer.publish_bytes("bad.bin", b"bad", validator=lambda path: False)

    assert not (tmp_path / "bad.bin").exists()
    assert not list(tmp_path.glob(".*.uncorrupter-*.tmp"))
