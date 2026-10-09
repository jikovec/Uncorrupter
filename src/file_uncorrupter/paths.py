from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath


class PathLayoutError(ValueError):
    pass


_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{value}" for value in range(1, 10)),
    *(f"LPT{value}" for value in range(1, 10)),
}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _overlaps(first: Path, second: Path) -> bool:
    return _is_relative_to(first, second) or _is_relative_to(second, first)


def validate_layout(
    input_root: Path,
    output_root: Path,
    workspace_root: Path,
    database_path: Path,
    *,
    allow_risky: bool = False,
) -> dict[str, Path]:
    paths = {
        "input_root": Path(input_root).resolve(),
        "output_root": Path(output_root).resolve(),
        "workspace_root": Path(workspace_root).resolve(),
        "database_path": Path(database_path).resolve(),
    }
    risks: list[str] = []
    input_path = paths["input_root"]
    for name in ("output_root", "workspace_root", "database_path"):
        if _overlaps(input_path, paths[name]):
            risks.append(f"{name} overlaps input_root")
    if paths["output_root"] == paths["workspace_root"]:
        risks.append("workspace_root equals output_root")
    if paths["database_path"] in {paths["input_root"], paths["output_root"], paths["workspace_root"]}:
        risks.append("database_path is a directory root")
    if risks and not allow_risky:
        raise PathLayoutError("; ".join(risks))
    return paths


def safe_relative_path(value: str | os.PathLike[str]) -> Path:
    raw = os.fspath(value)
    if not raw or "\x00" in raw or any(ord(char) < 32 for char in raw):
        raise PathLayoutError("relative path contains empty or control data")
    if re.match(r"^[A-Za-z]:", raw) or raw.startswith(("/", "\\")):
        raise PathLayoutError("absolute and drive-qualified paths are not allowed")
    normalized = raw.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise PathLayoutError("path traversal is not allowed")
    for part in pure.parts:
        trimmed = part.rstrip(" .")
        stem = trimmed.split(".", 1)[0].upper()
        if not trimmed or stem in _WINDOWS_RESERVED:
            raise PathLayoutError(f"unsafe or reserved path component: {part}")
        if any(char in '<>:"|?*' for char in part):
            raise PathLayoutError(f"unsafe path character in component: {part}")
    return Path(*pure.parts)


def contained_path(root: Path, relative: str | os.PathLike[str]) -> Path:
    canonical_root = Path(root).resolve()
    candidate = (canonical_root / safe_relative_path(relative)).resolve()
    if not _is_relative_to(candidate, canonical_root):
        raise PathLayoutError("resolved path escapes the selected root")
    return candidate


def require_suffix(path: Path, allowed_suffixes: set[str]) -> None:
    normalized = {suffix.lower() if suffix.startswith(".") else f".{suffix.lower()}" for suffix in allowed_suffixes}
    if path.suffix.lower() not in normalized:
        raise PathLayoutError(f"artifact suffix {path.suffix!r} is not valid for its type")
