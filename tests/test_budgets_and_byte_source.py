from __future__ import annotations

import hashlib
import tracemalloc
from dataclasses import FrozenInstanceError

import pytest

from file_uncorrupter.budgets import BudgetExceeded, BudgetTracker, ResourceLimits
from file_uncorrupter.byte_source import FileByteSource, SourceChangedError


def test_resource_limits_are_immutable_and_validate_positive_values():
    limits = ResourceLimits(max_candidates=3)

    with pytest.raises(FrozenInstanceError):
        limits.max_candidates = 4  # type: ignore[misc]
    with pytest.raises(ValueError, match="max_candidates"):
        ResourceLimits(max_candidates=0)


def test_hierarchical_budget_consumption_is_shared_and_records_limit():
    events: list[dict[str, object]] = []
    root = BudgetTracker({"scanned_bytes": 10}, scope="run", on_event=events.append)
    child = root.child(scope="file:one")

    child.consume("scanned_bytes", 7)
    assert child.consumed("scanned_bytes") == 7
    assert root.consumed("scanned_bytes") == 7
    assert child.remaining("scanned_bytes") == 3

    with pytest.raises(BudgetExceeded) as raised:
        child.consume("scanned_bytes", 4)

    assert raised.value.name == "scanned_bytes"
    assert raised.value.limit == 10
    assert raised.value.attempted == 11
    assert events[-1]["outcome"] == "exceeded"


def test_file_byte_source_supports_bounded_random_and_streaming_reads(tmp_path):
    path = tmp_path / "source.bin"
    payload = (b"0123456789abcdef" * 4096) + b"tail"
    path.write_bytes(payload)
    limits = ResourceLimits(
        max_source_bytes=len(payload) + 1,
        max_scanned_bytes=len(payload) * 2,
        max_materialized_bytes=1024,
    )
    source = FileByteSource(path, limits=limits)

    assert source.read(4, 8) == payload[4:12]
    assert b"".join(source.iter_chunks(start=10, length=100, chunk_size=17)) == payload[10:110]
    assert source.sha256() == hashlib.sha256(payload).hexdigest()
    assert source.slice(3, 12).materialize() == payload[3:12]
    with pytest.raises(BudgetExceeded, match="materialized_bytes"):
        source.slice(0, 2048).materialize()


def test_file_byte_source_rejects_changed_input(tmp_path):
    path = tmp_path / "changing.bin"
    path.write_bytes(b"before")
    source = FileByteSource(path)

    path.write_bytes(b"after-and-longer")

    with pytest.raises(SourceChangedError):
        source.read(0, 1)


def test_streaming_hash_of_one_gib_sparse_file_stays_below_memory_limit(tmp_path):
    path = tmp_path / "sparse.bin"
    one_gib = 1 << 30
    with path.open("wb") as handle:
        handle.truncate(one_gib)
    limits = ResourceLimits(
        max_source_bytes=one_gib,
        max_scanned_bytes=one_gib,
        max_materialized_bytes=1 << 20,
    )
    source = FileByteSource(path, limits=limits)

    tracemalloc.start()
    digest = source.sha256(chunk_size=1 << 20)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert len(digest) == 64
    assert peak < 256 * (1 << 20)
