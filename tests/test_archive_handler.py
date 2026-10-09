from __future__ import annotations

import io
import tarfile
import zipfile

from file_uncorrupter.budgets import ResourceLimits
from file_uncorrupter.handlers.archive import ArchiveHandler


def make_zip(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
    return buffer.getvalue()


def test_zip_inspection_and_contained_extraction(tmp_path):
    data = make_zip([("folder/a.txt", b"alpha"), ("b.txt", b"beta")])
    result = ArchiveHandler().recover_bytes(data, suffix=".zip", output_root=tmp_path)

    assert result.outcome == "validated_original"
    assert [member.safe_name for member in result.members if member.outcome == "extracted"] == ["b.txt", "folder/a.txt"]
    assert (tmp_path / "folder" / "a.txt").read_bytes() == b"alpha"
    assert (tmp_path / "b.txt").read_bytes() == b"beta"


def test_zip_traversal_duplicates_and_encryption_are_explicit(tmp_path):
    traversal = make_zip([("../escape.txt", b"no"), ("safe.txt", b"yes")])
    result = ArchiveHandler().recover_bytes(traversal, suffix=".zip", output_root=tmp_path / "traversal")
    assert any(member.outcome == "unsafe_path" for member in result.members)
    assert not (tmp_path / "escape.txt").exists()

    duplicate = make_zip([("same.txt", b"one"), ("same.txt", b"two")])
    result = ArchiveHandler().recover_bytes(duplicate, suffix=".zip", output_root=tmp_path / "duplicate")
    assert any(member.outcome == "duplicate_rejected" for member in result.members)

    encrypted = bytearray(make_zip([("secret.txt", b"secret")]))
    local = encrypted.find(b"PK\x03\x04")
    central = encrypted.find(b"PK\x01\x02")
    encrypted[local + 6:local + 8] = (1).to_bytes(2, "little")
    encrypted[central + 8:central + 10] = (1).to_bytes(2, "little")
    result = ArchiveHandler().recover_bytes(bytes(encrypted), suffix=".zip", output_root=tmp_path / "encrypted")
    assert any(member.encrypted and member.outcome == "encrypted" for member in result.members)


def test_zip_expansion_budget_stops_before_publication(tmp_path):
    data = make_zip([("bomb.txt", b"A" * 100_000)])
    limits = ResourceLimits(max_expansion_ratio=2.0, max_decompressed_bytes=200_000)
    result = ArchiveHandler().recover_bytes(data, suffix=".zip", output_root=tmp_path, limits=limits)

    assert result.outcome == "budget_exceeded"
    assert not (tmp_path / "bomb.txt").exists()


def test_zip_missing_directory_is_reconstructed_only_from_unambiguous_local_members(tmp_path):
    original = make_zip([("a.txt", b"alpha"), ("b.txt", b"beta")])
    central = original.find(b"PK\x01\x02")
    truncated = original[:central]

    result = ArchiveHandler().recover_bytes(truncated, suffix=".zip", output_root=tmp_path)

    assert result.outcome == "reconstructed"
    assert result.rebuilt_bytes is not None
    with zipfile.ZipFile(io.BytesIO(result.rebuilt_bytes)) as rebuilt:
        assert rebuilt.read("a.txt") == b"alpha"
        assert rebuilt.read("b.txt") == b"beta"


def make_tar(entries: list[tuple[str, bytes, bytes | None]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, payload, link_target in entries:
            info = tarfile.TarInfo(name)
            if link_target is not None:
                info.type = tarfile.SYMTYPE
                info.linkname = link_target.decode()
                info.size = 0
                archive.addfile(info)
            else:
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def test_tar_salvages_later_valid_members_and_rejects_links(tmp_path):
    data = make_tar([("one.txt", b"one", None), ("link", b"", b"../outside"), ("two.txt", b"two", None)])
    damaged = bytearray(data)
    damaged[0:512] = b"X" * 512

    result = ArchiveHandler().recover_bytes(bytes(damaged), suffix=".tar", output_root=tmp_path)

    assert (tmp_path / "two.txt").read_bytes() == b"two"
    assert any(member.original_name == "link" and member.outcome == "link_or_device_rejected" for member in result.members)
    assert not (tmp_path / "link").exists()
    assert result.rebuilt_bytes is not None
    assert result.diagnostics == [{"tar_resynchronization": {"skipped_blocks": 2}}]


def test_valid_tar_is_validated_without_needless_rebuild(tmp_path):
    data = make_tar([("one.txt", b"one", None)])

    result = ArchiveHandler().recover_bytes(data, suffix=".tar", output_root=tmp_path)

    assert result.outcome == "validated_original"
    assert result.rebuilt_bytes is None
    assert not (tmp_path / "repaired.tar").exists()
