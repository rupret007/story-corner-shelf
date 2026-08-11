#!/usr/bin/env python3
"""Fail-closed repository and generated-release checks for Story Corner r6.

This module is intentionally independent of mesh generation.  Source-only
checks can run before any artifacts exist; full checks treat ``manifest.json``
as an exact allow-list and validate every model-only 3MF with the canonical
package validator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from package_layout import (
    ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS,
    EXPECTED_EMITTED_SOURCE_PART_COUNT,
    EXPECTED_EXACT_PACKAGE_COUNTS,
    PACKAGE_FILENAMES,
    PACKAGE_ORDER,
    SAFETY_DESCRIPTION,
)
from package_validation import (
    inspect_model_only_3mf,
    inspect_serialized_stl_geometry,
)
from release_inventory import (
    ORNAMENT_BLUEPRINT_FAMILY_COUNTS,
    enumerate_level_inventory,
    enumerate_selected_inventory,
    inventory_reconciliation,
)


REQUIRED_DOCS: tuple[str, ...] = (
    "README.md",
    "PRINT_ME_FIRST.md",
    "ENGINEERING_DESIGN.md",
    "SAFETY.md",
    "ASSEMBLY.md",
    "MEASUREMENT_WORKSHEET.md",
    "TEST_PROTOCOL.md",
    "CONTRIBUTING.md",
    "CHANGELOG_ENTRY.md",
)
GENERATION_SOURCE_FILES: tuple[str, ...] = (
    "crown_retention_pin.py",
    "design_math.py",
    "generate_all_petg_r6.py",
    "generate_drawings.py",
    "interface_geometry.py",
    "model_io.py",
    "ornament_access.py",
    "ornament_geometry.py",
    "package_layout.py",
    "package_validation.py",
    "rail_geometry.py",
    "release_inventory.py",
    "release_plan.py",
    "retention_cross_key.py",
)
GENERATION_SOURCE_BUNDLE_SERIALIZATION = (
    "UTF-8 path + NUL + decimal size_bytes + NUL + lowercase hex sha256 + LF; "
    "records sorted by path"
)
PRINTABLE_SUFFIXES = frozenset({".3mf", ".stl"})
QUALIFICATION_WORDS = ("qualification", "coupon", "creep", "wall-mockup")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GENERATOR_LABEL = "generate_all_petg_r6.py"


class DuplicateJsonKey(ValueError):
    """Raised when a JSON object repeats a key."""


@dataclass(frozen=True)
class Issue:
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> Any:
    """Load JSON while rejecting duplicate object keys at every depth."""

    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateJsonKey) as exc:
        raise ValueError(f"{path}: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_generation_source_bundle(root: Path) -> dict[str, Any]:
    """Independently fingerprint the exact source inputs used for generation."""

    records: list[dict[str, Any]] = []
    aggregate = hashlib.sha256()
    for relative in GENERATION_SOURCE_FILES:
        payload = (root / relative).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        size = len(payload)
        record = {"path": relative, "size_bytes": size, "sha256": digest}
        records.append(record)
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
    return {
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "aggregate_serialization": GENERATION_SOURCE_BUNDLE_SERIALIZATION,
        "config_sha256_enforced_separately": True,
        "source_file_count": len(GENERATION_SOURCE_FILES),
        "aggregate_sha256": aggregate.hexdigest(),
        "records": records,
    }


def _generation_source_bundle_has_exact_schema(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "hash_algorithm",
        "aggregate_serialization",
        "config_sha256_enforced_separately",
        "source_file_count",
        "aggregate_sha256",
        "records",
    }:
        return False
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        return False
    if value.get("hash_algorithm") != "sha256":
        return False
    if value.get("aggregate_serialization") != GENERATION_SOURCE_BUNDLE_SERIALIZATION:
        return False
    if type(value.get("config_sha256_enforced_separately")) is not bool:
        return False
    if value["config_sha256_enforced_separately"] is not True:
        return False
    if type(value.get("source_file_count")) is not int:
        return False
    if value["source_file_count"] != len(GENERATION_SOURCE_FILES):
        return False
    aggregate = value.get("aggregate_sha256")
    if not isinstance(aggregate, str) or not _SHA256_RE.fullmatch(aggregate):
        return False
    records = value.get("records")
    if not isinstance(records, list) or len(records) != len(GENERATION_SOURCE_FILES):
        return False
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "size_bytes", "sha256"}:
            return False
        if not isinstance(record.get("path"), str):
            return False
        if type(record.get("size_bytes")) is not int or record["size_bytes"] < 0:
            return False
        digest = record.get("sha256")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            return False
    return True


def _check_generation_source_bundle(
    root: Path,
    manifest: Mapping[str, Any],
    validation: Mapping[str, Any],
    issues: list[Issue],
) -> None:
    """Require exact schema, agreement, and current bytes independently."""

    try:
        expected = _expected_generation_source_bundle(root)
    except (OSError, UnicodeError, ValueError) as exc:
        issues.append(Issue("generation_source_bundle.source_error", str(exc)))
        return
    observed: dict[str, Any] = {}
    schema_validity: dict[str, bool] = {}
    for label, document in (("manifest", manifest), ("validation", validation)):
        bundle = document.get("generation_source_bundle")
        observed[label] = bundle
        schema_valid = _generation_source_bundle_has_exact_schema(bundle)
        schema_validity[label] = schema_valid
        _add(
            issues,
            schema_valid,
            f"{label}.generation_source_bundle_schema",
            f"{label} generation_source_bundle schema is not exact",
        )
        _add(
            issues,
            schema_valid and bundle == expected,
            f"{label}.generation_source_bundle_freshness",
            f"{label} generation_source_bundle does not match current generation sources",
        )
    _add(
        issues,
        schema_validity.get("manifest") is True
        and schema_validity.get("validation") is True
        and observed.get("manifest") == observed.get("validation"),
        "generated.generation_source_bundle_alignment",
        "manifest and validation generation_source_bundle records differ",
    )


def _add(issues: list[Issue], condition: bool, code: str, message: str) -> None:
    if not condition:
        issues.append(Issue(code, message))


def _walk_dicts(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _release_validation_reports(validation: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    reports: dict[str, Mapping[str, Any]] = {}
    for item in _walk_dicts(validation):
        package_id = item.get("package_id")
        if package_id in PACKAGE_ORDER and "all_checks_pass" in item:
            reports[str(package_id)] = item
    return reports


def _plan_records(*documents: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    plans: dict[str, Mapping[str, Any]] = {}
    for document in documents:
        for item in _walk_dicts(document):
            candidate = item.get("plans")
            if not isinstance(candidate, list):
                continue
            for plan in candidate:
                if isinstance(plan, dict) and plan.get("package_id") in PACKAGE_ORDER:
                    plans[str(plan["package_id"])] = plan
    return plans


def _source_contract(root: Path, cfg: Mapping[str, Any], issues: list[Issue]) -> dict[str, Any]:
    project = cfg.get("project", {})
    protocol = cfg.get("test_protocol", {})
    support = cfg.get("support", {})
    corbel = cfg.get("corbel", {})
    project_name = project.get("name")
    revision = project.get("revision")
    edition = project.get("edition")
    _add(issues, isinstance(project_name, str) and bool(project_name.strip()), "config.project", "project.name must be nonempty")
    _add(issues, isinstance(revision, str) and bool(revision.strip()), "config.revision", "project.revision must be nonempty")
    _add(issues, isinstance(edition, str) and bool(edition.strip()), "config.edition", "project.edition must be nonempty")
    _add(issues, project.get("production_release_allowed") is False, "config.production", "production_release_allowed must remain false")
    _add(issues, project.get("embedded_gcode_allowed") is False, "config.gcode", "embedded G-code must remain forbidden")
    _add(issues, protocol.get("tested_load_rating_exists") is False, "config.rating", "a tested load rating may not be claimed")
    _add(issues, support.get("printed_wall_anchors_allowed") is False, "config.anchor", "printed wall anchors must remain forbidden")
    _add(issues, support.get("hollow_wall_anchors_allowed_in_primary_load_path") is False, "config.anchor", "primary hollow-wall anchors must remain forbidden")
    _add(issues, corbel.get("production_fastener_geometry_allowed") is False, "config.wall_bore", "production fastener geometry must remain blocked")

    try:
        one_level = enumerate_level_inventory(dict(cfg), "lower")
        selected = enumerate_selected_inventory(dict(cfg))
        one_report = inventory_reconciliation(dict(cfg), one_level)
        selected_report = inventory_reconciliation(dict(cfg), selected)
        one_count = int(one_report["physical_object_count"])
        selected_count = int(selected_report["physical_object_count"])
        ornament_count = sum(ORNAMENT_BLUEPRINT_FAMILY_COUNTS.values())
        _add(issues, not one_report["contradictions"], "inventory.one_level", f"one-level inventory contradictions: {one_report['contradictions']}")
        _add(issues, not selected_report["contradictions"], "inventory.selected", f"selected-level inventory contradictions: {selected_report['contradictions']}")
        _add(issues, selected_count == one_count * int(selected_report["level_count"]), "inventory.levels", "selected inventory is not an exact independent-level multiple")
    except Exception as exc:  # fail closed on schema or inventory drift
        issues.append(Issue("inventory.error", str(exc)))
        one_count = selected_count = ornament_count = -1

    expected_package_counts = dict(EXPECTED_EXACT_PACKAGE_COUNTS)
    _add(issues, expected_package_counts.get("one_level_l") == one_count, "packages.one_level_count", "one-level package count differs from release_inventory")
    _add(issues, expected_package_counts.get("two_level_full_project") == selected_count, "packages.two_level_count", "two-level package count differs from release_inventory")
    _add(issues, tuple(PACKAGE_FILENAMES) == PACKAGE_ORDER, "packages.order", "package filename keys do not match canonical package order")
    _add(issues, len(set(PACKAGE_FILENAMES.values())) == len(PACKAGE_FILENAMES), "packages.filenames", "package filenames must be unique")

    documents: dict[str, str] = {}
    for name in REQUIRED_DOCS:
        path = root / "docs" / name
        try:
            documents[name] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(Issue("docs.missing", f"{path}: {exc}"))
    corpus = "\n".join(documents.values())
    lowered = corpus.lower()
    if isinstance(project_name, str):
        _add(issues, project_name.lower() in lowered, "docs.project", "documentation does not name the configured project")
    if isinstance(revision, str):
        revision_marker = next((part for part in revision.lower().split("_") if re.fullmatch(r"r\d+", part)), revision.lower())
        _add(issues, revision_marker in lowered, "docs.revision", f"documentation does not identify configured revision marker {revision_marker!r}")
    if isinstance(edition, str):
        edition_tokens = [token.lower() for token in re.findall(r"[A-Za-z]+", edition) if len(token) >= 6 and token.lower() not in {"experimental"}]
        _add(issues, all(token in lowered for token in edition_tokens), "docs.edition", f"documentation does not reflect edition tokens {edition_tokens}")
    for value, label in ((one_count, "one-level"), (selected_count, "selected-level"), (ornament_count, "ornament")):
        if value >= 0:
            _add(issues, re.search(rf"(?<!\d){value}(?!\d)", corpus) is not None, f"docs.count.{label}", f"documentation omits derived {label} count {value}")
    _add(issues, "no g-code" in lowered, "docs.gcode", "documentation must state the no-G-code policy")
    _add(issues, "no tested load rating" in lowered, "docs.rating", "documentation must state that no tested load rating exists")
    _add(issues, any(word in lowered for word in QUALIFICATION_WORDS), "docs.qualification", "physical qualification gates must remain explicit")
    _add(issues, "software-model package" in lowered, "docs.software_model_scope", "documentation must define software-model package scope")
    _add(issues, "physical_installation_qualified: false" in lowered, "docs.physical_qualification", "documentation must explicitly keep physical installation unqualified")
    _add(issues, "production_release_eligible: false" in lowered, "docs.production_eligibility", "documentation must explicitly keep production release ineligible")

    return {
        "project_name": project_name,
        "revision": revision,
        "edition": edition,
        "one_level_physical_object_count": one_count,
        "selected_levels_physical_object_count": selected_count,
        "ornament_objects_per_level": ornament_count,
        "package_filenames": dict(PACKAGE_FILENAMES),
        "package_counts": expected_package_counts,
    }


def _check_artifact_allowlist(root: Path, manifest: Mapping[str, Any], issues: list[Issue]) -> dict[str, Mapping[str, Any]]:
    generated = root / "generated"
    records = manifest.get("artifacts")
    if not isinstance(records, list):
        issues.append(Issue("manifest.artifacts", "manifest artifacts must be a list"))
        return {}
    by_path: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            issues.append(Issue("manifest.artifact_record", f"invalid artifact record: {record!r}"))
            continue
        relative = Path(record["path"])
        safe = not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == record["path"]
        _add(issues, safe, "manifest.artifact_path", f"unsafe/noncanonical artifact path {record['path']!r}")
        if record["path"] in by_path:
            issues.append(Issue("manifest.duplicate_artifact", f"duplicate manifest artifact {record['path']!r}"))
        by_path[record["path"]] = record
        path = generated / relative
        _add(issues, path.is_file(), "manifest.missing_artifact", f"manifest artifact is missing: {relative}")
        expected_hash = record.get("sha256")
        _add(issues, isinstance(expected_hash, str) and bool(_SHA256_RE.fullmatch(expected_hash)), "manifest.artifact_hash", f"invalid SHA-256 for {relative}")
        if path.is_file() and isinstance(expected_hash, str) and _SHA256_RE.fullmatch(expected_hash):
            _add(issues, _sha256(path) == expected_hash, "manifest.stale_artifact", f"artifact digest differs from manifest: {relative}")
            if isinstance(record.get("bytes"), int):
                _add(issues, path.stat().st_size == record["bytes"], "manifest.artifact_size", f"artifact size differs from manifest: {relative}")
    declared_artifacts = set(by_path)
    actual_artifacts = {
        path.relative_to(generated).as_posix()
        for path in generated.rglob("*")
        if path.is_file() and path != generated / "manifest.json"
    }
    for extra in sorted(actual_artifacts - declared_artifacts):
        printable = Path(extra).suffix.lower() in PRINTABLE_SUFFIXES
        issues.append(
            Issue(
                "generated.extra_printable" if printable else "generated.extra_artifact",
                f"generated {'printable' if printable else 'artifact'} is not in manifest: {extra}",
            )
        )
    for missing in sorted(declared_artifacts - actual_artifacts):
        printable = Path(missing).suffix.lower() in PRINTABLE_SUFFIXES
        issues.append(
            Issue(
                "generated.missing_printable" if printable else "generated.missing_artifact",
                f"manifest {'printable' if printable else 'artifact'} is absent: {missing}",
            )
        )
    _add(issues, manifest.get("generated_artifact_count_excluding_manifest") == len(records), "manifest.artifact_count", "manifest artifact count does not equal artifact records")
    return by_path


def _check_release_sidecars(
    root: Path,
    source: Mapping[str, Any],
    manifest: Mapping[str, Any],
    validation: Mapping[str, Any],
    issues: list[Issue],
) -> None:
    """Require explicit unsliced/model audit reports for every canonical package."""

    generated = root / "generated"
    expected_names = {
        "slice_report": "slice_report.json",
        "model_3mf_report": "model_3mf_report.json",
    }
    for label, document in (("manifest", manifest), ("validation", validation)):
        _add(
            issues,
            document.get("release_report_artifacts") == expected_names,
            f"{label}.release_reports",
            f"{label} must name the exact slice/model report artifacts",
        )
    try:
        slice_report = load_json_strict(generated / expected_names["slice_report"])
        model_report = load_json_strict(generated / expected_names["model_3mf_report"])
    except ValueError as exc:
        issues.append(Issue("reports.json", str(exc)))
        return
    if not isinstance(slice_report, dict) or not isinstance(model_report, dict):
        issues.append(Issue("reports.schema", "slice/model reports must be JSON objects"))
        return

    expected_packages = [
        {"package_id": package_id, "filename": PACKAGE_FILENAMES[package_id]}
        for package_id in PACKAGE_ORDER
    ]
    config_hash = _sha256(root / "config.json")
    for label, report in (("slice", slice_report), ("model", model_report)):
        prefix = f"reports.{label}"
        _add(issues, report.get("project_name") == source.get("project_name"), f"{prefix}.project", f"{label} report project differs from config")
        _add(issues, report.get("revision") == source.get("revision"), f"{prefix}.revision", f"{label} report revision differs from config")
        _add(issues, report.get("config_sha256") == config_hash, f"{prefix}.config_hash", f"{label} report config digest is stale")
        _add(issues, report.get("canonical_packages") == expected_packages, f"{prefix}.packages", f"{label} report does not contain the exact five canonical packages in order")
        _add(issues, report.get("software_model_package_eligible") is True, f"{prefix}.software", f"{label} report must affirm software-model package eligibility")
        _add(issues, report.get("physical_installation_qualified") is False, f"{prefix}.physical", f"{label} report must keep physical installation unqualified")
        _add(issues, report.get("production_release_eligible") is False, f"{prefix}.production", f"{label} report must keep production release ineligible")
        blockers = report.get("physical_qualification_blockers")
        _add(issues, isinstance(blockers, list) and bool(blockers), f"{prefix}.blockers", f"{label} report must retain nonempty physical qualification blockers")

    for field in (
        "performed",
        "embedded_gcode_allowed",
        "printer_profile_embedded",
        "printer_confirmed",
        "nozzle_confirmed",
        "build_plate_confirmed",
        "petg_product_confirmed",
    ):
        _add(issues, slice_report.get(field) is False, f"reports.slice.{field}", f"slice report {field} must remain false")
    _add(issues, slice_report.get("bambu_studio_sliced_mass_required") is True, "reports.slice.sliced_mass", "slice report must require a later Bambu Studio sliced-mass report")
    _add(issues, slice_report.get("weighed_finished_tare_required") is True, "reports.slice.tare", "slice report must require a weighed finished tare")

    _add(issues, model_report.get("all_packages_model_only") is True, "reports.model.model_only", "model report must affirm that every package is model-only")
    _add(issues, model_report.get("safety_description") == SAFETY_DESCRIPTION, "reports.model.safety", "model report safety description is not canonical")
    _add(issues, model_report.get("canonical_package_count") == len(PACKAGE_ORDER), "reports.model.package_count", "model report canonical package count is wrong")
    _add(issues, model_report.get("all_package_audits_pass") is True, "reports.model.audits", "model report does not affirm all package audits")
    package_audits = model_report.get("package_audits")
    observed_audit_ids = [
        item.get("package_id")
        for item in package_audits
        if isinstance(item, dict)
    ] if isinstance(package_audits, list) else []
    _add(issues, observed_audit_ids == list(PACKAGE_ORDER), "reports.model.audit_set", "model report package audits do not exactly match canonical order")
    if isinstance(package_audits, list):
        for item in package_audits:
            if not isinstance(item, dict):
                continue
            package_id = item.get("package_id", "unknown")
            _add(issues, item.get("all_checks_pass") is True, "reports.model.audit_pass", f"{package_id} model report audit did not pass")
            _add(issues, item.get("software_model_package_eligible") is True, "reports.model.audit_software", f"{package_id} is not software-model eligible")
            _add(issues, item.get("physical_installation_qualified") is False, "reports.model.audit_physical", f"{package_id} must remain physically unqualified")
            _add(issues, item.get("production_release_eligible") is False, "reports.model.audit_production", f"{package_id} must remain production-ineligible")

    mass = model_report.get("repeat_weighted_solid_model_mass")
    if not isinstance(mass, dict):
        issues.append(Issue("reports.model.mass", "model report lacks repeat-weighted solid-model mass context"))
        return
    estimates = mass.get("package_estimates")
    if not isinstance(estimates, dict):
        issues.append(Issue("reports.model.mass_estimates", "model report lacks per-package mass estimates"))
        return
    _add(issues, set(estimates) == set(PACKAGE_ORDER), "reports.model.mass_set", "solid-model mass estimates do not cover exactly the five canonical packages")
    sidecar_plans = _plan_records(manifest, validation)
    for package_id in PACKAGE_ORDER:
        estimate = estimates.get(package_id)
        if not isinstance(estimate, dict):
            continue
        _add(issues, estimate.get("filename") == PACKAGE_FILENAMES[package_id], "reports.model.mass_filename", f"{package_id} mass estimate filename drifted")
        plan_record = sidecar_plans.get(package_id)
        expected_count = (
            plan_record.get("physical_object_count")
            if isinstance(plan_record, Mapping)
            else source.get("package_counts", {}).get(package_id)
        )
        if expected_count is not None:
            _add(issues, estimate.get("physical_object_count") == expected_count, "reports.model.mass_count", f"{package_id} mass estimate count drifted")
        _add(issues, isinstance(estimate.get("repeat_weighted_model_solid_volume_mm3"), (int, float)) and estimate.get("repeat_weighted_model_solid_volume_mm3", 0) > 0, "reports.model.mass_volume", f"{package_id} mass estimate has no positive repeat-weighted volume")
        _add(issues, isinstance(estimate.get("contextual_all_solid_petg_mass_g"), (int, float)) and estimate.get("contextual_all_solid_petg_mass_g", 0) > 0, "reports.model.mass_value", f"{package_id} mass estimate has no positive contextual mass")
        _add(issues, estimate.get("sliced_or_finished_mass_claim") is False, "reports.model.mass_scope", f"{package_id} mass estimate improperly claims sliced/finished mass")
        _add(issues, estimate.get("load_capacity_claim") is False, "reports.model.mass_capacity", f"{package_id} mass estimate improperly claims load capacity")
    _add(issues, mass.get("bambu_sliced_mass_required_before_print") is True, "reports.model.mass_slice_gate", "model mass report must require later sliced mass")
    _add(issues, mass.get("weighed_finished_tare_required_for_physical_qualification") is True, "reports.model.mass_tare_gate", "model mass report must require weighed finished tare")
    _add(issues, mass.get("tested_load_rating_created") is False, "reports.model.mass_rating", "model mass report must not create a load rating")
    one_mass = mass.get("one_level_contextual_all_solid_petg_mass_g")
    two_mass = mass.get("two_level_contextual_all_solid_petg_mass_g")
    one_volume = estimates.get("one_level_l", {}).get(
        "repeat_weighted_model_solid_volume_mm3"
    )
    two_volume = estimates.get("two_level_full_project", {}).get(
        "repeat_weighted_model_solid_volume_mm3"
    )
    _add(
        issues,
        isinstance(one_volume, (int, float))
        and isinstance(two_volume, (int, float))
        and math.isclose(
            float(two_volume),
            2.0 * float(one_volume),
            rel_tol=0.0,
            abs_tol=0.00100001,
        ),
        "reports.model.volume_levels",
        "two-level repeat-weighted volume is not two independent levels",
    )
    _add(
        issues,
        isinstance(one_mass, (int, float))
        and isinstance(two_mass, (int, float))
        and math.isclose(
            float(two_mass),
            2.0 * float(one_mass),
            rel_tol=0.0,
            abs_tol=0.00100001,
        ),
        "reports.model.mass_levels",
        "two-level contextual solid mass is not exactly two independent levels",
    )


def _check_top_level_generated_semantics(
    manifest: Mapping[str, Any],
    validation: Mapping[str, Any],
    issues: list[Issue],
) -> None:
    """Keep software conformance separate from every physical release gate."""

    blocker_lists: dict[str, list[Any]] = {}
    for label, document in (("manifest", manifest), ("validation", validation)):
        _add(
            issues,
            document.get("software_model_package_eligible") is True,
            f"{label}.software_model_eligibility",
            f"{label} must explicitly affirm software-model package eligibility",
        )
        _add(
            issues,
            document.get("production_release_allowed") is False,
            f"{label}.production_release_allowed",
            f"{label} must explicitly keep production_release_allowed false",
        )
        blockers = document.get("physical_qualification_blockers")
        valid_blockers = (
            isinstance(blockers, list)
            and bool(blockers)
            and all(isinstance(item, (str, dict)) for item in blockers)
        )
        _add(
            issues,
            valid_blockers,
            f"{label}.physical_qualification_blockers",
            f"{label} physical qualification blockers must remain explicit and nonempty",
        )
        if isinstance(blockers, list):
            blocker_lists[label] = blockers
        _add(
            issues,
            document.get("unresolved_software_interface_blockers") == [],
            f"{label}.software_interface_blockers",
            f"{label} must carry an explicit empty software-interface blocker list",
        )
        blocker_count = document.get("unresolved_software_interface_blocker_count")
        if blocker_count is not None:
            _add(
                issues,
                blocker_count == 0,
                f"{label}.software_interface_blocker_count",
                f"{label} software-interface blocker count must be zero",
            )
    _add(
        issues,
        blocker_lists.get("manifest") == blocker_lists.get("validation")
        and "manifest" in blocker_lists
        and "validation" in blocker_lists,
        "generated.physical_blocker_alignment",
        "manifest and validation physical qualification blocker lists must be identical",
    )
    _add(
        issues,
        manifest.get("embedded_gcode_file_count") == 0,
        "manifest.gcode_count",
        "manifest must explicitly report zero embedded G-code files",
    )


def _check_individual_model_bijection(
    root: Path,
    manifest: Mapping[str, Any],
    validation: Mapping[str, Any],
    issues: list[Issue],
) -> None:
    """Require all 49 STL sources to have one exact neutral individual 3MF."""

    generated = root / "generated"
    stl_dir = generated / "stl"
    individual_dir = generated / "individual_model_only_3mf"
    stl_paths = sorted(stl_dir.rglob("*.stl")) if stl_dir.is_dir() else []
    individual_paths = (
        sorted(individual_dir.rglob("*.3mf"))
        if individual_dir.is_dir()
        else []
    )
    stl_sources = [path.stem for path in stl_paths]
    expected_individual_by_source = {
        source: individual_dir / f"MODEL_ONLY_{source}.3mf"
        for source in stl_sources
    }
    actual_individual_set = set(individual_paths)
    expected_individual_set = set(expected_individual_by_source.values())
    _add(
        issues,
        len(stl_paths) == EXPECTED_EMITTED_SOURCE_PART_COUNT,
        "individual_3mf.stl_count",
        "the emitted source set must contain exactly 49 STL files",
    )
    _add(
        issues,
        len(stl_sources) == len(set(stl_sources)),
        "individual_3mf.stl_names",
        "STL source basenames must be unique",
    )
    _add(
        issues,
        len(individual_paths) == EXPECTED_EMITTED_SOURCE_PART_COUNT,
        "individual_3mf.count",
        "the individual neutral-3MF set must contain exactly 49 files",
    )
    _add(
        issues,
        actual_individual_set == expected_individual_set,
        "individual_3mf.basename_bijection",
        "individual 3MF basenames are not an exact MODEL_ONLY_<STL-stem> bijection",
    )

    observed_pairs: list[dict[str, Any]] = []
    for source in sorted(expected_individual_by_source):
        stl_path = stl_dir / f"{source}.stl"
        three_mf_path = expected_individual_by_source[source]
        if not stl_path.is_file() or not three_mf_path.is_file():
            continue
        try:
            stl = inspect_serialized_stl_geometry(stl_path)
            three_mf = inspect_model_only_3mf(three_mf_path)
        except Exception as exc:
            issues.append(
                Issue("individual_3mf.invalid_pair", f"{source}: {exc}")
            )
            continue
        geometry_records = three_mf.get("serialized_mesh_geometry_records", [])
        geometry = (
            geometry_records[0]
            if isinstance(geometry_records, list) and len(geometry_records) == 1
            else {}
        )
        pair_checks = {
            "stl_serialized_closed_solid": stl.get(
                "serialized_geometry_audit_passed"
            )
            is True,
            "individual_3mf_neutral_core_audit_passed": (
                three_mf.get("all_checks_pass") is True
            ),
            "individual_3mf_exactly_one_mesh_and_one_build_item": (
                three_mf.get("resource_object_count") == 1
                and three_mf.get("mesh_family_count") == 1
                and three_mf.get("component_object_count") == 0
                and three_mf.get("build_object_count") == 1
            ),
            "individual_3mf_names_equal_source": (
                three_mf.get("metadata", {}).get("Title") == source
                and three_mf.get("mesh_resource_names") == [source]
                and three_mf.get("build_object_names") == [source]
            ),
            "stl_and_3mf_triangle_counts_equal": (
                stl.get("triangle_count") == geometry.get("triangle_count")
            ),
            "stl_and_3mf_bounds_equal_on_common_grid": (
                stl.get("bounds_mm") == geometry.get("bounds_mm")
            ),
            "stl_and_3mf_canonical_triangle_geometry_digest_equal": (
                isinstance(
                    stl.get("canonical_triangle_digest_common_grid"), str
                )
                and stl.get("canonical_triangle_digest_common_grid")
                == geometry.get("canonical_triangle_digest_common_grid")
            ),
            "individual_3mf_contains_no_embedded_gcode": (
                three_mf.get("checks", {}).get("contains_no_embedded_gcode")
                is True
            ),
        }
        for check, passed in pair_checks.items():
            _add(
                issues,
                passed,
                f"individual_3mf.{check}",
                f"{source} failed {check}",
            )
        observed_pairs.append(
            {
                "source_part_name": source,
                "stl_path": stl_path.relative_to(generated).as_posix(),
                "individual_3mf_path": three_mf_path.relative_to(
                    generated
                ).as_posix(),
                "common_canonical_triangle_digest": stl.get(
                    "canonical_triangle_digest_common_grid"
                ),
            }
        )

    declared_manifest_pairs = manifest.get("individual_stl_3mf_bijection")
    _add(
        issues,
        declared_manifest_pairs == observed_pairs,
        "manifest.individual_3mf_bijection",
        "manifest individual STL/3MF bijection differs from exact generated geometry",
    )
    for label, document in (("manifest", manifest), ("validation", validation)):
        _add(
            issues,
            document.get("individual_model_only_3mf_count")
            == EXPECTED_EMITTED_SOURCE_PART_COUNT,
            f"{label}.individual_3mf_count",
            f"{label} must report exactly 49 individual model-only 3MFs",
        )
        _add(
            issues,
            document.get("all_individual_model_only_3mf_pair_audits_pass")
            is True,
            f"{label}.individual_3mf_audits",
            f"{label} must affirm every individual STL/3MF pair audit",
        )
    _add(
        issues,
        manifest.get("individual_model_only_3mf_directory")
        == "individual_model_only_3mf",
        "manifest.individual_3mf_directory",
        "manifest individual-model directory label is missing or stale",
    )

    validation_audits = validation.get("individual_model_only_3mf_audits")
    audit_by_source = {
        item.get("source_part_name"): item
        for item in validation_audits
        if isinstance(item, dict) and isinstance(item.get("source_part_name"), str)
    } if isinstance(validation_audits, list) else {}
    _add(
        issues,
        set(audit_by_source) == set(stl_sources)
        and len(audit_by_source) == EXPECTED_EMITTED_SOURCE_PART_COUNT,
        "validation.individual_3mf_audit_set",
        "validation individual pair audits do not exactly cover all 49 STL sources",
    )
    for observed in observed_pairs:
        declared = audit_by_source.get(observed["source_part_name"])
        _add(
            issues,
            isinstance(declared, dict)
            and declared.get("stl_path") == observed["stl_path"]
            and declared.get("individual_3mf_path")
            == observed["individual_3mf_path"]
            and declared.get("common_canonical_triangle_digest")
            == observed["common_canonical_triangle_digest"]
            and declared.get("all_checks_pass") is True
            and isinstance(declared.get("checks"), dict)
            and all(value is True for value in declared["checks"].values()),
            "validation.individual_3mf_pair_evidence",
            f"validation pair evidence is missing/stale for {observed['source_part_name']}",
        )


def _check_canonical_package_source_bijection(
    root: Path,
    manifest: Mapping[str, Any],
    validation: Mapping[str, Any],
    issues: list[Issue],
) -> None:
    """Compare every canonical 3MF source resource to the emitted STL source.

    This is intentionally independent of the generator's own report.  It
    decodes the final files and prevents a canonical package from retaining a
    higher-precision or otherwise different mesh under the same source name.
    """

    generated = root / "generated"
    stl_dir = generated / "stl"
    source_geometry: dict[str, dict[str, Any]] = {}
    for path in sorted(stl_dir.glob("*.stl")) if stl_dir.is_dir() else []:
        try:
            source_geometry[path.stem] = inspect_serialized_stl_geometry(path)
        except Exception as exc:
            issues.append(
                Issue("packages.source_geometry_stl", f"{path.name}: {exc}")
            )
    _add(
        issues,
        len(source_geometry) == EXPECTED_EMITTED_SOURCE_PART_COUNT,
        "packages.source_geometry_stl_set",
        "canonical source comparison requires the exact 49 emitted STL sources",
    )

    planning = validation.get("release_package_planning")
    plan_records = planning.get("plans") if isinstance(planning, dict) else None
    plan_by_id = {
        item.get("package_id"): item
        for item in plan_records
        if isinstance(item, dict) and isinstance(item.get("package_id"), str)
    } if isinstance(plan_records, list) else {}

    package_evidence: list[dict[str, Any]] = []
    total_comparisons = 0
    for package_id in PACKAGE_ORDER:
        filename = PACKAGE_FILENAMES[package_id]
        path = generated / "model_only_3mf" / filename
        try:
            report = inspect_model_only_3mf(path)
        except Exception as exc:
            issues.append(
                Issue("packages.source_geometry_3mf", f"{filename}: {exc}")
            )
            continue
        records = report.get("serialized_mesh_geometry_records")
        record_by_name = {
            item.get("name"): item
            for item in records
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        } if isinstance(records, list) else {}
        plan = plan_by_id.get(package_id)
        families = plan.get("mesh_families") if isinstance(plan, dict) else None
        expected_names = {
            f"SOURCE__{family}"
            for family in families
            if isinstance(family, str)
        } if isinstance(families, list) else set()
        _add(
            issues,
            bool(expected_names) and set(record_by_name) == expected_names,
            "packages.source_geometry_resource_set",
            f"{package_id}: canonical source names differ from the exact package plan",
        )
        package_passed = bool(expected_names) and set(record_by_name) == expected_names
        for resource_name, record in sorted(record_by_name.items()):
            family = resource_name.removeprefix("SOURCE__")
            family_class, separator, source_name = family.partition("::")
            expected = source_geometry.get(source_name)
            valid_name = (
                resource_name.startswith("SOURCE__")
                and separator == "::"
                and family_class in {"source", "prototype"}
                and expected is not None
            )
            comparisons = {
                "name_resolves_to_emitted_stl": valid_name,
                "triangle_count": valid_name
                and record.get("triangle_count") == expected.get("triangle_count"),
                "bounds": valid_name
                and record.get("bounds_mm") == expected.get("bounds_mm"),
                "canonical_digest": valid_name
                and record.get("canonical_triangle_digest_common_grid")
                == expected.get("canonical_triangle_digest_common_grid"),
                "closed_positive_one_body": (
                    record.get("zero_area_triangle_count") == 0
                    and record.get("watertight") is True
                    and record.get("winding_consistent") is True
                    and record.get("positive_volume") is True
                    and record.get("body_count") == 1
                ),
            }
            for label, passed in comparisons.items():
                _add(
                    issues,
                    bool(passed),
                    f"packages.source_geometry_{label}",
                    f"{package_id}: {resource_name} differs from its emitted STL source",
                )
            package_passed &= all(comparisons.values())
        total_comparisons += len(record_by_name)
        package_evidence.append(
            {
                "package_id": package_id,
                "source_resource_count": len(record_by_name),
                "all_sources_equal_named_individual_exports": package_passed,
            }
        )

    observed_summary = {
        "individual_source_count": len(source_geometry),
        "canonical_package_count": len(package_evidence),
        "canonical_source_resource_comparison_count": total_comparisons,
        "packages": package_evidence,
        "all_checks_pass": (
            len(source_geometry) == EXPECTED_EMITTED_SOURCE_PART_COUNT
            and len(package_evidence) == len(PACKAGE_ORDER)
            and all(
                item["all_sources_equal_named_individual_exports"]
                for item in package_evidence
            )
        ),
    }
    for label, document in (("manifest", manifest), ("validation", validation)):
        release_planning = document.get("release_package_planning")
        declared = (
            release_planning.get("canonical_package_source_geometry_bijection")
            if isinstance(release_planning, dict)
            else None
        )
        declared_comparable = {
            key: declared.get(key)
            for key in observed_summary
        } if isinstance(declared, dict) else None
        _add(
            issues,
            declared_comparable == observed_summary,
            f"{label}.canonical_package_source_geometry_bijection",
            f"{label} canonical-package source geometry audit is missing or stale",
        )
        _add(
            issues,
            isinstance(release_planning, dict)
            and release_planning.get(
                "all_canonical_package_sources_equal_individual_exports"
            )
            is True,
            f"{label}.canonical_package_source_geometry_complete",
            f"{label} must affirm canonical resources equal individual exports",
        )


def _full_contract(root: Path, cfg: Mapping[str, Any], source: Mapping[str, Any], issues: list[Issue]) -> None:
    generated = root / "generated"
    try:
        manifest = load_json_strict(generated / "manifest.json")
        validation = load_json_strict(generated / "validation.json")
    except ValueError as exc:
        issues.append(Issue("generated.json", str(exc)))
        return
    if not isinstance(manifest, dict) or not isinstance(validation, dict):
        issues.append(Issue("generated.schema", "manifest and validation must be JSON objects"))
        return
    config_hash = _sha256(root / "config.json")
    for label, document in (("manifest", manifest), ("validation", validation)):
        _add(issues, document.get("project_name") == source["project_name"], f"{label}.project", f"{label} project_name differs from config")
        _add(issues, document.get("revision") == source["revision"], f"{label}.revision", f"{label} revision differs from config")
        _add(issues, document.get("config_sha256") == config_hash, f"{label}.config_hash", f"{label} config digest is stale")
        _add(issues, document.get("production_ready") is False, f"{label}.production", f"{label} must not claim production readiness")
        _add(issues, document.get("physical_installation_qualified") is False, f"{label}.physical_qualification", f"{label} must say physical installation remains unqualified")
        _add(issues, document.get("production_release_eligible") is False, f"{label}.production_eligibility", f"{label} must say production release remains ineligible")
        _add(issues, document.get("production_release_allowed") is False, f"{label}.production_allowed", f"{label} must keep production_release_allowed false")
        _add(issues, document.get("tested_load_rating_exists") is False, f"{label}.rating", f"{label} must not claim a tested load rating")
        _add(issues, document.get("generator") == GENERATOR_LABEL, f"{label}.generator", f"{label} generator label must be root-relocatable")
    _check_generation_source_bundle(root, manifest, validation, issues)
    _check_top_level_generated_semantics(manifest, validation, issues)
    _add(issues, validation.get("embedded_gcode_allowed") is False, "validation.gcode", "validation must prohibit embedded G-code")
    _add(issues, validation.get("x_corbel_production_screw_bore_count") == 0, "validation.wall_bores", "validation reports production X-corbel wall bores")
    _check_artifact_allowlist(root, manifest, issues)
    _check_release_sidecars(root, source, manifest, validation, issues)
    _check_individual_model_bijection(root, manifest, validation, issues)
    _check_canonical_package_source_bijection(root, manifest, validation, issues)

    audits = validation.get("model_only_3mf_audits")
    audit_paths = {
        item.get("path") for item in audits if isinstance(item, dict) and isinstance(item.get("path"), str)
    } if isinstance(audits, list) else set()
    three_mf_paths = sorted(generated.rglob("*.3mf"))
    for path in three_mf_paths:
        relative = path.relative_to(generated).as_posix()
        try:
            report = inspect_model_only_3mf(path)
        except Exception as exc:
            issues.append(Issue("3mf.invalid", f"{relative}: {exc}"))
            continue
        _add(issues, report.get("all_checks_pass") is True, "3mf.noncanonical", f"model-only package fails canonical metadata/core/no-G-code checks: {relative}")
        _add(issues, relative in audit_paths, "validation.missing_3mf_audit", f"validation omits 3MF audit: {relative}")
    _add(issues, audit_paths == {path.relative_to(generated).as_posix() for path in three_mf_paths}, "validation.stale_3mf_audits", "validation 3MF audit paths do not exactly match generated 3MF files")
    _add(issues, validation.get("all_3mf_packages_model_only") is True, "validation.model_only", "validation does not affirm all 3MFs are model-only")
    _add(issues, validation.get("all_3mf_artifacts_model_only") is True, "validation.all_3mf_model_only", "validation does not affirm every canonical and individual 3MF is model-only")
    physical_blockers = validation.get("production_and_physical_blockers")
    _add(
        issues,
        isinstance(physical_blockers, list)
        and bool(physical_blockers)
        and all(isinstance(item, (str, dict)) for item in physical_blockers),
        "validation.physical_blockers",
        "production/physical blockers must remain explicit and nonempty",
    )

    plans = _plan_records(manifest, validation)
    reports = _release_validation_reports(validation)
    emitted_ids = {
        package_id
        for package_id, filename in PACKAGE_FILENAMES.items()
        if (generated / "model_only_3mf" / filename).is_file()
    }
    canonical_ids = set(PACKAGE_ORDER)
    canonical_files = {
        path.name for path in (generated / "model_only_3mf").glob("*.3mf")
    }
    expected_canonical_files = set(PACKAGE_FILENAMES.values())
    _add(
        issues,
        canonical_files == expected_canonical_files,
        "packages.canonical_directory_exact",
        "model_only_3mf must contain exactly the five canonical package files",
    )
    missing_ids = canonical_ids - emitted_ids
    _add(
        issues,
        emitted_ids == canonical_ids,
        "packages.incomplete_release_set",
        f"full release must emit every canonical package; missing={sorted(missing_ids)}",
    )
    _add(
        issues,
        canonical_ids <= set(plans),
        "packages.incomplete_plan_set",
        f"manifest/validation must contain plans for every canonical package; missing={sorted(canonical_ids - set(plans))}",
    )
    _add(
        issues,
        canonical_ids <= set(reports),
        "packages.incomplete_validation_set",
        f"validation must contain reports for every canonical package; missing={sorted(canonical_ids - set(reports))}",
    )
    for package_id in PACKAGE_ORDER:
        plan = plans.get(package_id)
        _add(issues, plan is not None, "packages.missing_plan", f"canonical package has no derived plan: {package_id}")
        if plan is not None:
            _add(issues, plan.get("filename") == PACKAGE_FILENAMES[package_id], "packages.filename", f"{package_id} filename differs across package source/manifest/validation")
            expected_count = source["package_counts"].get(package_id)
            if expected_count is not None:
                _add(issues, plan.get("physical_object_count") == expected_count, "packages.count", f"{package_id} physical count differs from release inventory")
        report = reports.get(package_id)
        _add(issues, report is not None and report.get("all_checks_pass") is True, "packages.validation", f"canonical package lacks a passing package_validation report: {package_id}")
        if package_id in ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS and report is not None:
            plan_checks = report.get("plan_checks", {})
            required = (
                "mesh_source::no_source_is_a_placeholder_or_coupon",
                "mesh_source::all_source_wall_bore_counts_are_zero",
                "mesh_source::all_sources_are_current_interface_geometry",
                "mesh_source::all_sources_are_software_model_package_eligible",
                "mesh_source::no_source_is_physical_installation_qualified",
                "mesh_source::no_source_is_production_release_eligible",
                "mesh_source::all_source_interface_blockers_are_closed",
            )
            for check in required:
                _add(issues, isinstance(plan_checks, dict) and plan_checks.get(check) is True, "packages.software_model_source", f"{package_id} failed or omitted {check}")
            _add(issues, report.get("software_model_package_eligible") is True, "packages.software_model_eligibility", f"{package_id} is not software-model-package eligible")
            _add(issues, report.get("physical_installation_qualified") is False, "packages.physical_qualification", f"{package_id} must remain physically unqualified")
            _add(issues, report.get("production_release_eligible") is False, "packages.production_eligibility", f"{package_id} must remain production-ineligible")
        if package_id == "unique_parts_catalog" and report is not None:
            plan_checks = report.get("plan_checks", {})
            required_catalog_checks = (
                "mesh_source::catalog_source_audits_supplied",
                "mesh_source::catalog_audit_keys_equal_all_emitted_mesh_families",
                "mesh_source::catalog_audit_keys_equal_declared_mesh_families",
                "mesh_source::catalog_source_names_are_exact_unique_family_suffixes",
                "mesh_source::catalog_classifications_are_exact_and_explicit",
                "mesh_source::catalog_all_source_geometry_validation_passed",
                "mesh_source::catalog_all_sources_inclusion_eligible",
                "mesh_source::catalog_installed_sources_are_current_and_software_eligible",
                "mesh_source::catalog_no_source_is_physical_or_production_qualified",
                "mesh_source::catalog_all_source_wall_bore_counts_are_zero",
                "mesh_source::catalog_no_source_contains_rail_or_saddle_geometry",
            )
            for check in required_catalog_checks:
                _add(
                    issues,
                    isinstance(plan_checks, dict)
                    and plan_checks.get(check) is True,
                    "packages.catalog_source",
                    f"unique_parts_catalog failed or omitted {check}",
                )
            expected_catalog_families = {
                f"source::{path.stem}"
                for path in (generated / "stl").glob("*.stl")
            }
            plan_families = plan.get("mesh_families") if plan else None
            _add(
                issues,
                isinstance(plan_families, list)
                and set(plan_families) == expected_catalog_families
                and len(plan_families) == EXPECTED_EMITTED_SOURCE_PART_COUNT,
                "packages.catalog_exact_source_set",
                "unique_parts_catalog is not the exact all-49 emitted STL source set",
            )
    assembly_models_emitted = canonical_ids & ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS
    if assembly_models_emitted:
        unresolved = validation.get("unresolved_software_interface_blockers")
        _add(issues, unresolved == [], "packages.unresolved_software_interfaces", "software assembly-model packages were emitted while software/interface blockers remain")
        docs_corpus = "\n".join((root / "docs" / name).read_text(encoding="utf-8") for name in REQUIRED_DOCS if (root / "docs" / name).is_file())
        for package_id in sorted(assembly_models_emitted):
            filename = PACKAGE_FILENAMES[package_id]
            _add(issues, filename in docs_corpus, "docs.package_filename", f"documentation omits emitted software-model package filename {filename}")


def check_repository(root: Path, *, source_only: bool = False) -> dict[str, Any]:
    root = root.resolve()
    issues: list[Issue] = []
    json_paths = sorted(root.rglob("*.json"))
    if source_only:
        generated = root / "generated"
        json_paths = [path for path in json_paths if generated not in path.parents]
    loaded: dict[Path, Any] = {}
    for path in json_paths:
        try:
            loaded[path] = load_json_strict(path)
        except ValueError as exc:
            issues.append(Issue("json.invalid", str(exc)))
    config_path = root / "config.json"
    cfg = loaded.get(config_path)
    if not isinstance(cfg, dict):
        if config_path not in loaded:
            issues.append(Issue("config.missing", f"strict config unavailable: {config_path}"))
        source: dict[str, Any] = {}
    else:
        source = _source_contract(root, cfg, issues)
        if not source_only:
            _full_contract(root, cfg, source, issues)
    return {
        "schema_version": 1,
        "mode": "source-only" if source_only else "full-release",
        "root": str(root),
        "passed": not issues,
        "derived": source,
        "issues": [issue.to_dict() for issue in issues],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--source-only", action="store_true", help="check sources/config/docs without requiring generated artifacts")
    parser.add_argument("--json", action="store_true", help="emit the complete machine-readable report")
    args = parser.parse_args(argv)
    report = check_repository(args.root, source_only=args.source_only)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["passed"]:
        derived = report["derived"]
        print(f"PASS {report['mode']}: {derived.get('revision')} ({derived.get('one_level_physical_object_count')}/{derived.get('selected_levels_physical_object_count')} objects)")
    else:
        print(f"FAIL {report['mode']}: {len(report['issues'])} issue(s)", file=sys.stderr)
        for issue in report["issues"]:
            print(f"- {issue['code']}: {issue['message']}", file=sys.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
