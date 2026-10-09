from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

from . import __version__
from .handlers.registry import HandlerRegistry, build_handler_registry


class CapabilityQualityError(RuntimeError):
    pass


def validate_capability_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return errors + ["capabilities must be a non-empty list"]
    required = {"family", "variants", "extensions", "operations", "tools", "limits", "encryption", "outputs", "fixtures", "availability"}
    operations = {"detect", "inspect", "validate", "repair", "normalize", "extract", "preview", "carve"}
    levels = {"none", "detect", "inspect", "baseline", "partial", "validated"}
    ownership: dict[str, str] = {}
    for index, record in enumerate(capabilities):
        missing = required - set(record)
        if missing:
            errors.append(f"capability[{index}] missing {sorted(missing)}")
            continue
        if set(record["operations"]) != operations:
            errors.append(f"{record['family']}: operation set is incomplete")
        if set(record["operations"].values()) - levels:
            errors.append(f"{record['family']}: invalid operation level")
        advertised = [name for name, level in record["operations"].items() if level != "none"]
        if advertised and not record["fixtures"]:
            errors.append(f"{record['family']}: advertised operations lack fixture evidence")
        owner = str(record.get("handler_id") or record["family"])
        for variant in record["variants"]:
            previous = ownership.get(variant)
            if previous is not None and previous != owner:
                errors.append(f"variant {variant} has multiple public owners: {previous}, {owner}")
            ownership[variant] = owner
        if record["availability"] == "unavailable" and not record.get("unavailable_reasons"):
            errors.append(f"{record['family']}: unavailable capability has no reason")
    expected_order = sorted(capabilities, key=lambda item: (item["family"], item.get("handler_id", ""), item["variants"]))
    if capabilities != expected_order:
        errors.append("capabilities are not deterministically ordered")
    return errors


def build_capability_manifest(registry: HandlerRegistry | None = None, *, strict: bool = True) -> dict[str, Any]:
    registry = registry or build_handler_registry()
    manifest = registry.manifest()
    manifest.update(
        {
            "application": "file-uncorrupter",
            "application_version": __version__,
            "python": platform.python_version(),
            "platform": platform.system().lower(),
        }
    )
    errors = validate_capability_manifest(manifest)
    manifest["quality_gate"] = {"passed": not errors, "errors": errors}
    if strict and errors:
        raise CapabilityQualityError("; ".join(errors))
    return manifest


def capability_json(registry: HandlerRegistry | None = None) -> str:
    return json.dumps(build_capability_manifest(registry), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def capability_text(registry: HandlerRegistry | None = None) -> str:
    manifest = build_capability_manifest(registry)
    lines = [f"file-uncorrupter {manifest['application_version']} capabilities", ""]
    for record in manifest["capabilities"]:
        operations = ", ".join(f"{name}={level}" for name, level in sorted(record["operations"].items()))
        variants = ", ".join(record["variants"])
        tools = ", ".join(record["tools"].get("optional", [])) or "none"
        lines.extend(
            [
                f"{record['family']} ({record['availability']})",
                f"  variants: {variants}",
                f"  operations: {operations}",
                f"  optional tools: {tools}",
                f"  fidelity: {record['fidelity']}",
            ]
        )
    return "\n".join(lines) + "\n"


def capability_markdown(registry: HandlerRegistry | None = None) -> str:
    manifest = build_capability_manifest(registry)
    lines = [
        "# Executable Capability Baseline",
        "",
        f"Generated from registered handlers for file-uncorrupter {manifest['application_version']}.",
        "Runtime tool availability can narrow conditional operations; run `file-uncorrupter capabilities --format json` for the current machine.",
        "",
        "| Family | Variants | Repair | Normalize | Extract | Preview | Carve | Availability | Fidelity |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in manifest["capabilities"]:
        fidelity = str(record["fidelity"]).replace("|", "\\|").replace("\n", " ")
        variants = ", ".join(record["variants"]).replace("|", "\\|")
        operations = record["operations"]
        lines.append(
            f"| {record['family']} | {variants} | {operations['repair']} | {operations['normalize']} | "
            f"{operations['extract']} | {operations['preview']} | {operations['carve']} | "
            f"{record['availability']} | {fidelity} |"
        )
    lines.extend(
        [
            "",
            "Quality gate: **passed**. Advertised operations have registered fixture evidence; `none` means the goal is rejected rather than silently substituted.",
            "",
        ]
    )
    return "\n".join(lines)


def write_capability_manifest(path: Path, *, format: str | None = None, as_json: bool | None = None) -> Path:
    from .atomic import AtomicArtifactWriter

    if format is None:
        format = "json" if as_json is not False else "text"
    if format not in {"json", "text", "markdown"}:
        raise ValueError(f"unsupported capability format: {format}")
    rendered = capability_json() if format == "json" else capability_markdown() if format == "markdown" else capability_text()
    payload = rendered.encode("utf-8")
    return AtomicArtifactWriter(path.parent).publish_bytes(path.name, payload).path
