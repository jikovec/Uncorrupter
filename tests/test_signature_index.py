from file_uncorrupter.intake import build_file_record


def test_detects_anywhere_signature_for_prefixed_mp4(tmp_path):
    data = b"GARBAGE" + (20).to_bytes(4, "big") + b"ftypisom" + b"\x00" * 32
    path = tmp_path / "broken.bin"
    path.write_bytes(data)
    record = build_file_record(tmp_path, path, data)
    assert record.byte0_kind == "unknown"
    assert record.anywhere_kind == "mp4"
    assert any(hit.family == "mp4" and hit.offset == 7 for hit in record.signature_hits)
