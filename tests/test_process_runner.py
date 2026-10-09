from __future__ import annotations

import os
import sys
import threading
import time

import pytest

from file_uncorrupter.cancellation import CancellationToken
from file_uncorrupter.process_runner import (
    IsolationUnavailableError,
    ProcessPolicy,
    configure_process_isolation,
    probe_tool,
    run_process,
)


def python_command(source: str) -> list[str]:
    return [sys.executable, "-c", source]


@pytest.fixture(autouse=True)
def enable_runner_for_unit_tests(monkeypatch):
    monkeypatch.delenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", raising=False)


def test_process_runner_bounds_output_and_uses_minimal_environment(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_TEST_SECRET", "must-not-leak")
    result = run_process(
        python_command(
            "import os; print(os.getenv('UNCORRUPTER_TEST_SECRET', '<absent>')); print('x' * 10000)"
        ),
        ProcessPolicy(timeout_seconds=5, max_output_bytes=128),
    )

    assert result.returncode == 0
    assert b"<absent>" in result.stdout
    assert len(result.stdout) + len(result.stderr) <= 128
    assert result.output_truncated is True
    assert result.cleanup_ok is True


def test_process_runner_times_out_and_cleans_up():
    result = run_process(
        python_command("import time; time.sleep(30)"),
        ProcessPolicy(timeout_seconds=0.2, max_output_bytes=128),
    )

    assert result.timed_out is True
    assert result.returncode is not None
    assert result.cleanup_ok is True


def test_process_runner_honors_cancellation():
    token = CancellationToken()
    timer = threading.Timer(0.15, lambda: token.cancel("test"))
    timer.start()
    try:
        result = run_process(
            python_command("import time; time.sleep(30)"),
            ProcessPolicy(timeout_seconds=5, max_output_bytes=128),
            cancellation=token,
        )
    finally:
        timer.cancel()

    assert result.cancelled is True
    assert result.cleanup_ok is True


def test_required_isolation_fails_closed_before_launch(tmp_path):
    marker = tmp_path / "launched.txt"
    with pytest.raises(IsolationUnavailableError):
        run_process(
            python_command(f"from pathlib import Path; Path({str(marker)!r}).write_text('launched')"),
            ProcessPolicy(required_isolation=True, isolation_wrapper=None),
        )
    assert not marker.exists()


def test_external_tools_can_be_disabled_globally(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    with pytest.raises(IsolationUnavailableError, match="disabled"):
        run_process(python_command("print('never')"), ProcessPolicy())


def test_probe_tool_records_resolved_identity_and_version():
    record = probe_tool(sys.executable, version_args=("--version",), policy=ProcessPolicy(timeout_seconds=5))

    assert record.available is True
    assert record.resolved_path
    assert record.version


def test_run_wide_required_isolation_cannot_be_bypassed_by_a_local_policy():
    configure_process_isolation(required=True, wrapper=("definitely-missing-wrapper",))
    try:
        with pytest.raises(IsolationUnavailableError, match="required process isolation"):
            run_process(python_command("print('must not launch')"), ProcessPolicy())
    finally:
        configure_process_isolation(required=False, wrapper=None)
