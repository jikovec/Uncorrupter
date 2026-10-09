from __future__ import annotations

import hashlib
import os
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence

from .cancellation import CancellationToken


class IsolationUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProcessPolicy:
    timeout_seconds: float = 30.0
    max_output_bytes: int = 1 << 20
    required_isolation: bool = False
    isolation_wrapper: tuple[str, ...] | None = None
    environment: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be greater than zero")


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int | None
    stdout: bytes
    stderr: bytes
    stdout_sha256: str
    stderr_sha256: str
    timed_out: bool
    cancelled: bool
    output_truncated: bool
    duration_seconds: float
    isolation: str | None
    cleanup_ok: bool


@dataclass(frozen=True, slots=True)
class ToolRecord:
    name: str
    available: bool
    resolved_path: str | None
    version: str | None
    error: str | None = None


_MINIMAL_ENV_KEYS = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "LANG")
_GLOBAL_REQUIRED_ISOLATION = False
_GLOBAL_ISOLATION_WRAPPER: tuple[str, ...] | None = None


def configure_process_isolation(*, required: bool = False, wrapper: Sequence[str] | None = None) -> None:
    """Configure a CLI-run-wide fail-closed isolation requirement."""
    global _GLOBAL_REQUIRED_ISOLATION, _GLOBAL_ISOLATION_WRAPPER
    _GLOBAL_REQUIRED_ISOLATION = bool(required)
    _GLOBAL_ISOLATION_WRAPPER = tuple(wrapper) if wrapper else None


def _minimal_environment(extra: Mapping[str, str] | None) -> dict[str, str]:
    env = {key: os.environ[key] for key in _MINIMAL_ENV_KEYS if key in os.environ}
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update({str(key): str(value) for key, value in extra.items()})
    return env


def _resolve_wrapper(wrapper: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if not wrapper:
        return None
    executable = wrapper[0]
    resolved = shutil.which(executable) if not Path(executable).is_absolute() else (executable if Path(executable).is_file() else None)
    if resolved is None:
        return None
    return (str(resolved), *wrapper[1:])


def _terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _read_bounded(path: Path, limit: int) -> tuple[bytes, bool, str]:
    digest = hashlib.sha256()
    kept = bytearray()
    total = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
            total += len(chunk)
            remaining = max(0, limit - len(kept))
            if remaining:
                kept.extend(chunk[:remaining])
    return bytes(kept), total > limit, digest.hexdigest()


def run_process(
    command: Sequence[str],
    policy: ProcessPolicy | None = None,
    *,
    cancellation: CancellationToken | None = None,
) -> ProcessResult:
    policy = policy or ProcessPolicy()
    if _GLOBAL_REQUIRED_ISOLATION or _GLOBAL_ISOLATION_WRAPPER:
        policy = replace(
            policy,
            required_isolation=policy.required_isolation or _GLOBAL_REQUIRED_ISOLATION,
            isolation_wrapper=policy.isolation_wrapper or _GLOBAL_ISOLATION_WRAPPER,
        )
    if os.environ.get("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "").lower() in {"1", "true", "yes", "on"}:
        raise IsolationUnavailableError("external tools are disabled by UNCORRUPTER_DISABLE_EXTERNAL_TOOLS")
    if not command or any(not isinstance(part, str) or not part for part in command):
        raise ValueError("command must contain non-empty strings")
    wrapper = _resolve_wrapper(policy.isolation_wrapper)
    if policy.required_isolation and wrapper is None:
        raise IsolationUnavailableError("required process isolation wrapper is unavailable")
    effective = (*wrapper, *command) if wrapper else tuple(command)
    if cancellation is not None and cancellation.cancelled:
        return ProcessResult(tuple(effective), None, b"", b"", hashlib.sha256(b"").hexdigest(), hashlib.sha256(b"").hexdigest(), False, True, False, 0.0, wrapper[0] if wrapper else None, True)

    started = time.monotonic()
    timed_out = False
    cancelled = False
    cleanup_ok = True
    with tempfile.TemporaryDirectory(prefix="uncorrupter-tool-") as temp_dir:
        root = Path(temp_dir)
        stdout_path = root / "stdout.bin"
        stderr_path = root / "stderr.bin"
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            process = subprocess.Popen(
                effective,
                cwd=root,
                env=_minimal_environment(policy.environment),
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                shell=False,
                creationflags=creationflags,
                start_new_session=os.name != "nt",
            )
            while process.poll() is None:
                if cancellation is not None and cancellation.cancelled:
                    cancelled = True
                    _terminate_tree(process)
                    break
                if time.monotonic() - started >= policy.timeout_seconds:
                    timed_out = True
                    _terminate_tree(process)
                    break
                time.sleep(0.02)
            if process.poll() is None:
                _terminate_tree(process)
            returncode = process.returncode
        stdout, stdout_truncated, stdout_hash = _read_bounded(stdout_path, policy.max_output_bytes)
        remaining = max(0, policy.max_output_bytes - len(stdout))
        stderr, stderr_truncated, stderr_hash = _read_bounded(stderr_path, remaining)
        cleanup_ok = process.poll() is not None
    return ProcessResult(
        tuple(effective), returncode, stdout, stderr, stdout_hash, stderr_hash,
        timed_out, cancelled, stdout_truncated or stderr_truncated,
        time.monotonic() - started, wrapper[0] if wrapper else None, cleanup_ok,
    )


def probe_tool(
    executable: str,
    *,
    version_args: Sequence[str] = ("--version",),
    policy: ProcessPolicy | None = None,
    cancellation: CancellationToken | None = None,
) -> ToolRecord:
    resolved = executable if Path(executable).is_absolute() and Path(executable).is_file() else shutil.which(executable)
    if resolved is None:
        return ToolRecord(executable, False, None, None, "not_found")
    try:
        result = run_process(
            [str(resolved), *version_args],
            policy or ProcessPolicy(timeout_seconds=5, max_output_bytes=16 * 1024),
            cancellation=cancellation,
        )
    except Exception as exc:
        return ToolRecord(executable, False, str(resolved), None, str(exc))
    raw = (result.stdout or result.stderr).decode("utf-8", errors="replace").strip().splitlines()
    version = raw[0][:500] if raw else None
    return ToolRecord(executable, result.returncode == 0, str(Path(resolved).resolve()), version, None if result.returncode == 0 else f"exit_{result.returncode}")
