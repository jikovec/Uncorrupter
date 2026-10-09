from __future__ import annotations

from file_uncorrupter.capabilities import build_capability_manifest
from file_uncorrupter.classification import classify_record
from file_uncorrupter.handlers.registry import build_handler_registry
from file_uncorrupter.intake import build_file_record

from fixtures import format_evidence_inventory
from mutations import CORE_MUTATION_CLASSES, SPECIAL_MUTATION_CLASSES


def test_mutation_inventory_covers_every_public_family_deterministically(monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    first = format_evidence_inventory()
    second = format_evidence_inventory()
    public_families = {record["family"] for record in build_capability_manifest()["capabilities"]}
    public_variants = {
        (record["family"], variant)
        for record in build_capability_manifest()["capabilities"]
        for variant in record["variants"]
    }

    assert {fixture.family for fixture in first} == public_families
    assert {(fixture.family, fixture.variant) for fixture in first} == public_variants
    assert first == second
    assert all(CORE_MUTATION_CLASSES <= fixture.mutation_classes for fixture in first)


def test_special_mutation_classes_have_executable_format_specific_fixtures():
    inventory = format_evidence_inventory()
    observed = set().union(*(fixture.mutation_classes for fixture in inventory))

    assert SPECIAL_MUTATION_CLASSES <= observed
    by_family = {
        family: set().union(*(fixture.mutation_classes for fixture in inventory if fixture.family == family))
        for family in {fixture.family for fixture in inventory}
    }
    assert {"missing-index", "oversized-declaration", "path-attack", "resource-attack"} <= by_family["archive"]
    assert {"missing-index", "path-attack", "resource-attack"} <= by_family["package_document"]
    assert "missing-index" in by_family["pdf"]
    assert "missing-index" in by_family["media"]
    assert "oversized-declaration" in by_family["image"]


def test_every_public_variant_has_valid_suffix_recognition_and_reaches_its_owner(tmp_path, monkeypatch):
    monkeypatch.setenv("UNCORRUPTER_DISABLE_EXTERNAL_TOOLS", "1")
    inventory = format_evidence_inventory()
    registry = build_handler_registry()
    owners = {
        variant: record.handler_id
        for record in registry.capabilities()
        for variant in record.variants
    }

    for position, fixture in enumerate(inventory):
        valid = next(case for case in fixture.cases if case.name == "valid")
        path = tmp_path / f"fixture-{position:03d}{fixture.suffix}"
        path.write_bytes(valid.payload)
        record = build_file_record(tmp_path, path, valid.payload)
        classification = classify_record(record, valid.payload)
        expected_declared = "text" if fixture.variant == "txt" else fixture.variant

        assert record.declared_kind == expected_declared, fixture.variant
        assert classification.family == expected_declared, (
            fixture.variant,
            classification.family,
            classification.label,
        )
        assert owners[fixture.variant] in {
            handler.handler_id for handler in registry.for_family(classification.family)
        }, fixture.variant


def test_every_public_variant_mutation_case_is_executable_through_intake_and_classification(tmp_path):
    for fixture_index, fixture in enumerate(format_evidence_inventory()):
        for case_index, case in enumerate(fixture.cases):
            path = tmp_path / f"mutation-{fixture_index:03d}-{case_index:02d}{case.suffix}"
            path.write_bytes(case.payload)
            record = build_file_record(tmp_path, path, case.payload)
            classification = classify_record(record, case.payload)

            assert 0.0 <= classification.confidence <= 1.0
            assert isinstance(classification.evidence, dict)
            assert record.size == len(case.payload)
