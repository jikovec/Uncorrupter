from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


CORE_MUTATION_CLASSES = frozenset(
    {
        "valid",
        "head-truncated",
        "tail-truncated",
        "prefixed",
        "suffixed",
        "bit-flipped",
        "wrong-suffix",
        "empty",
    }
)

SPECIAL_MUTATION_CLASSES = frozenset(
    {"missing-index", "oversized-declaration", "path-attack", "resource-attack"}
)


@dataclass(frozen=True, slots=True)
class MutationCase:
    name: str
    payload: bytes
    suffix: str


def truncate_head(data: bytes, count: int) -> bytes:
    return data[max(0, count):]


def truncate_tail(data: bytes, count: int) -> bytes:
    return data[: max(0, len(data) - max(0, count))]


def prefix_garbage(data: bytes, prefix: bytes = b"PREFIX_GARBAGE") -> bytes:
    return prefix + data


def suffix_garbage(data: bytes, suffix: bytes = b"SUFFIX_GARBAGE") -> bytes:
    return data + suffix


def bit_flip(data: bytes, offset: int, mask: int = 0x01) -> bytes:
    if not 0 <= offset < len(data):
        raise IndexError(offset)
    result = bytearray(data)
    result[offset] ^= mask & 0xFF
    return bytes(result)


def remove_range(data: bytes, start: int, end: int) -> bytes:
    if not 0 <= start <= end <= len(data):
        raise ValueError((start, end))
    return data[:start] + data[end:]


def patch_bytes(data: bytes, offset: int, replacement: bytes) -> bytes:
    end = offset + len(replacement)
    if not 0 <= offset <= end <= len(data):
        raise ValueError((offset, end))
    return data[:offset] + replacement + data[end:]


def mutation_matrix(data: bytes) -> Iterable[tuple[str, bytes]]:
    yield "valid", data
    if data:
        yield "head-truncated", truncate_head(data, min(8, len(data)))
        yield "tail-truncated", truncate_tail(data, min(8, len(data)))
        yield "bit-flipped", bit_flip(data, len(data) // 2)
    yield "prefixed", prefix_garbage(data)
    yield "suffixed", suffix_garbage(data)
    yield "empty", b""


def evidence_mutation_matrix(
    data: bytes,
    *,
    suffix: str,
    wrong_suffix: str = ".bin",
    missing_index: bytes | None = None,
    oversized_declaration: bytes | None = None,
    path_attack: bytes | None = None,
    resource_attack: bytes | None = None,
) -> tuple[MutationCase, ...]:
    """Build the deterministic mutation inventory used by capability gates.

    Special mutations are supplied by format fixture builders because an index,
    size field, archive member path, or expansion attack is format-specific.
    """

    cases = [MutationCase(name, payload, suffix) for name, payload in mutation_matrix(data)]
    cases.insert(-1, MutationCase("wrong-suffix", data, wrong_suffix))
    for name, payload in (
        ("missing-index", missing_index),
        ("oversized-declaration", oversized_declaration),
        ("path-attack", path_attack),
        ("resource-attack", resource_attack),
    ):
        if payload is not None:
            cases.append(MutationCase(name, payload, suffix))
    return tuple(cases)
