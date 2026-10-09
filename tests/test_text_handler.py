from __future__ import annotations

import json

import pytest

from file_uncorrupter.budgets import BudgetTracker, ResourceLimits
from file_uncorrupter.byte_source import FileByteSource
from file_uncorrupter.cancellation import CancellationToken
from file_uncorrupter.classification import classify_record
from file_uncorrupter.handlers.base import HandlerContext, RecoveryGoal
from file_uncorrupter.handlers.text import TextHandler
from file_uncorrupter.intake import build_file_record


@pytest.mark.parametrize(
    ("encoding", "payload"),
    [
        ("utf-8", "Ahoj žluťoučký".encode("utf-8")),
        ("utf-8-sig", b"\xef\xbb\xbf" + "Ahoj".encode("utf-8")),
        ("utf-16-le", b"\xff\xfe" + "Ahoj".encode("utf-16-le")),
        ("utf-16-be", b"\xfe\xff" + "Ahoj".encode("utf-16-be")),
        ("utf-32-le", b"\xff\xfe\x00\x00" + "Ahoj".encode("utf-32-le")),
        ("utf-32-be", b"\x00\x00\xfe\xff" + "Ahoj".encode("utf-32-be")),
        ("windows-1252", b"Price \x80 and smart \x93quote\x94"),
        ("iso-8859-1", b"Latin \xa3 text"),
    ],
)
def test_enumerated_text_encodings_are_detected_with_offset_evidence(encoding, payload):
    result = TextHandler().recover_bytes(payload, suffix=".txt")

    assert result.encoding == encoding
    assert result.confidence > 0.5
    assert result.text
    assert result.spans
    assert result.spans[0]["source_start"] >= 0
    assert result.spans[-1]["source_end"] <= len(payload)


def test_invalid_and_binary_spans_are_explicit_and_every_output_character_is_mapped():
    payload = b"good utf8 \xe2\x82\xac\xfftail\x00binary"
    result = TextHandler().recover_bytes(payload, suffix=".txt")

    assert "good utf8" in result.text
    assert "tail" in result.text
    assert any(span["span_type"] == "replacement" for span in result.spans)
    assert any(span["span_type"] == "skipped_binary" for span in result.spans)
    assert result.spans[0]["output_start"] == 0
    assert result.spans[-1]["output_end"] == len(result.text)
    for left, right in zip(result.spans, result.spans[1:]):
        assert left["output_end"] == right["output_start"]


def test_normalization_is_separate_from_byte_preserving_recovery():
    payload = b"one\r\ntwo\rthree\n"
    result = TextHandler().recover_bytes(payload, suffix=".txt", normalize=True)

    assert result.recovered_bytes == payload
    assert result.normalized_bytes == b"one\ntwo\nthree\n"
    assert result.normalized_bytes != result.recovered_bytes


@pytest.mark.parametrize(
    ("suffix", "payload", "expected_key"),
    [
        (".json", b'{"ok": true', "json"),
        (".xml", b"<root><item></root>", "xml"),
        (".csv", b"a,b\n1,2\n3\n", "csv"),
        (".html", b'<html><script>x()</script><a href="x">x</a></html>', "html"),
        (".md", b"# Heading\n```py\nprint(1)\n[link](target)\n", "markdown"),
    ],
)
def test_structured_text_diagnostics_do_not_rewrite_semantics(suffix, payload, expected_key):
    result = TextHandler().recover_bytes(payload, suffix=suffix)

    assert expected_key in result.diagnostics
    assert result.recovered_bytes == payload


def test_json_diagnostics_distinguish_valid_and_truncated_content():
    handler = TextHandler()
    valid = handler.recover_bytes(json.dumps({"a": [1, 2]}).encode(), suffix=".json")
    invalid = handler.recover_bytes(b'{"a": [1, 2]', suffix=".json")

    assert valid.diagnostics["json"]["valid"] is True
    assert invalid.diagnostics["json"]["valid"] is False
    assert invalid.diagnostics["json"]["position"] > 0


def test_invalid_structured_text_is_never_labeled_validated_original(tmp_path):
    source_path = tmp_path / "truncated.json"
    source_path.write_bytes(b'{"a": [1, 2]')
    limits = ResourceLimits()
    source = FileByteSource(source_path, limits=limits)
    prefix = source.prefix(source.size)
    record = build_file_record(tmp_path, source_path, prefix)
    context = HandlerContext(
        source=source,
        record=record,
        classification=classify_record(record, prefix),
        limits=limits,
        budget=BudgetTracker(limits.budget_limits()),
        cancellation=CancellationToken(),
        output_root=tmp_path / "out",
    )
    handler = TextHandler()
    plan = handler.plan(context, RecoveryGoal.REPAIR)[0]
    outcome = handler.execute(context, plan)

    assert outcome.grade == "partial_content"
    assert outcome.decode.telemetry["structurally_invalid"] is True
    repaired = next(artifact for artifact in outcome.artifacts if artifact.artifact_type == "repaired")
    assert repaired.fidelity_grade == "partial_content"
