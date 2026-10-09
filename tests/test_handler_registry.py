from file_uncorrupter.handlers.registry import build_handler_registry
from file_uncorrupter.types import Candidate


def test_handler_registry_is_deterministic_and_manifest_is_complete():
    registry = build_handler_registry()
    manifest = registry.manifest()
    capabilities = manifest["capabilities"]

    assert manifest["schema_version"] == 1
    assert capabilities
    assert [item["family"] for item in capabilities] == sorted(item["family"] for item in capabilities)
    variants = {variant for item in capabilities for variant in item["variants"]}
    assert {"jpeg", "png", "mp4", "mkv", "text", "zip", "docx", "pdf"} <= variants | {item["family"] for item in capabilities}
    assert all(set(item["operations"]) == {"detect", "inspect", "validate", "repair", "normalize", "extract", "preview", "carve"} for item in capabilities)


def test_equal_candidate_payloads_share_content_identity_and_keep_strategies():
    first = Candidate("full_file", "png", 100, b"same")
    second = Candidate("signature_offset", "png", 90, b"same", provenance=[{"offset": 0}])

    assert first.dedupe_hash == second.dedupe_hash
    assert first.strategy_hash != second.strategy_hash
    first.merge_strategy(second)
    assert [link["strategy_id"] for link in first.strategy_links] == ["full_file", "signature_offset"]
