#!/usr/bin/env python3
"""Run repository-level consistency and safety checks using the standard library."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
REQUIRED_FILES = (
    "README.md",
    "PRINT_ME_FIRST.md",
    "ENGINEERING_DESIGN.md",
    "SAFETY.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "config.json",
    "requirements.txt",
    "generated/artifact_manifest.json",
    "generated/corner_layout.svg",
    "generated/cut_plan.csv",
    "generated/model_3mf_report.json",
    "generated/palatine_elevation.svg",
    "generated/structural_sanity_check.json",
    "generated/support_layout.svg",
    "generated/support_plan.csv",
    "generated/validation.json",
    "generated/artist_rendering_triadic_palatine_order.png",
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
GENERATED_NONPRINTABLE_ALLOWLIST = {
    "artifact_manifest.json",
    "artist_rendering_triadic_palatine_order.png",
    "bambu_import_report.json",  # local integration evidence; intentionally ignored by Git
    "corner_layout.svg",
    "cut_plan.csv",
    "model_3mf_report.json",
    "palatine_elevation.svg",
    "structural_sanity_check.json",
    "support_layout.svg",
    "support_plan.csv",
    "validation.json",
}


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )


def check_markdown_links(errors: list[str]) -> None:
    for markdown in ROOT.glob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            decoded = unquote(target)
            if not (markdown.parent / decoded).exists():
                errors.append(f"Broken relative link in {markdown.name}: {raw_target}")


def check_manifest(errors: list[str]) -> None:
    manifest = load_json("generated/artifact_manifest.json")
    listed = set()
    for item in manifest.get("artifacts", []):
        relative = item["path"]
        path = ROOT / relative
        listed.add(relative)
        if not path.is_file():
            errors.append(f"Manifest artifact is missing: {relative}")
            continue
        payload = path.read_bytes()
        if len(payload) != item["bytes"]:
            errors.append(f"Manifest size mismatch: {relative}")
        if hashlib.sha256(payload).hexdigest() != item["sha256"]:
            errors.append(f"Manifest SHA-256 mismatch: {relative}")

    actual = {
        path.relative_to(ROOT).as_posix()
        for path in [*GENERATED.glob("*.stl"), *(GENERATED / "model_only_3mf").glob("*.3mf")]
    }
    if listed != actual:
        errors.append(
            "Artifact manifest coverage mismatch; "
            f"unlisted={sorted(actual - listed)}, missing={sorted(listed - actual)}"
        )


def check_generated_tree(errors: list[str]) -> None:
    unexpected = sorted(
        path.name
        for path in GENERATED.iterdir()
        if path.is_file()
        and path.suffix.lower() not in {".stl"}
        and path.name not in GENERATED_NONPRINTABLE_ALLOWLIST
    )
    unexpected_dirs = sorted(
        path.name
        for path in GENERATED.iterdir()
        if path.is_dir() and path.name not in {"model_only_3mf", "previews"}
    )
    if unexpected:
        errors.append(f"Unexpected generated deliverables would be published: {unexpected}")
    if unexpected_dirs:
        errors.append(f"Unexpected generated directories would be published: {unexpected_dirs}")


def check_model_packages(errors: list[str]) -> None:
    report = load_json("generated/model_3mf_report.json")
    validation = load_json("generated/validation.json")
    if not report.get("all_files_pass"):
        errors.append("generated/model_3mf_report.json does not report a complete pass")

    model_paths = sorted((GENERATED / "model_only_3mf").glob("*.3mf"))
    actual_names = {path.name for path in model_paths}
    report_files = report.get("files", [])
    report_names = {item.get("file") for item in report_files}
    validation_names = set(validation.get("model_3mf_files", []))
    if (
        report.get("generated_files") != len(actual_names)
        or len(report_files) != len(actual_names)
        or report_names != actual_names
    ):
        errors.append("3MF validation report file set does not match the generated model-only directory")
    if validation_names != actual_names:
        errors.append("validation.json 3MF file set does not match the generated model-only directory")

    meshes = validation.get("meshes", [])
    mesh_names = [mesh.get("name") for mesh in meshes]
    if len(mesh_names) != len(set(mesh_names)) or any(not name for name in mesh_names):
        errors.append("Generated mesh names must be present and unique")
    if any(int(mesh.get("repeat_count", 0)) <= 0 for mesh in meshes):
        errors.append("Every generated mesh family must have a positive repeat count")
    packages = validation.get("model_3mf_packages", {})
    catalog_name = packages.get("parts_catalog")
    full_name = packages.get("full_print_set")
    expected_names = {f"MODEL_ONLY_{name}.3mf" for name in mesh_names if name}
    if catalog_name:
        expected_names.add(catalog_name)
    if full_name:
        expected_names.add(full_name)
    if not catalog_name or not full_name or expected_names != actual_names:
        errors.append(
            "Model-only directory must contain one package per mesh plus the role-mapped catalog and full set"
        )

    by_name = {item.get("file"): item for item in report_files}
    for name in actual_names:
        item = by_name.get(name)
        if not item or not item.get("all_checks_pass"):
            errors.append(f"3MF report does not show a complete pass for {name}")
    for mesh_name in mesh_names:
        item = by_name.get(f"MODEL_ONLY_{mesh_name}.3mf")
        if not item or item.get("object_count") != 1 or item.get("build_item_count") != 1:
            errors.append(f"Individual 3MF package must contain exactly one referenced object: {mesh_name}")
    catalog = by_name.get(catalog_name)
    if not catalog or catalog.get("object_count") != len(meshes) or catalog.get("build_item_count") != len(meshes):
        errors.append("Parts-catalog 3MF object count does not match the number of unique mesh families")
    declared_count = int(validation.get("modularity", {}).get("full_set_object_count", -1))
    full = by_name.get(full_name)
    if not full or full.get("object_count") != declared_count or full.get("build_item_count") != declared_count:
        errors.append("Full-print-set 3MF object count does not match the generated repeat-count total")

    for path in model_paths:
        with zipfile.ZipFile(path) as archive:
            entries = archive.namelist()
            if any("gcode" in entry.lower() for entry in entries):
                errors.append(f"Embedded G-code found in {path.relative_to(ROOT)}")

    forbidden = [
        path.relative_to(ROOT).as_posix()
        for pattern in ("*.gcode", "*.gcode.3mf", "*.bgcode")
        for path in ROOT.rglob(pattern)
        if ".venv" not in path.parts and "archive" not in path.parts
    ]
    if forbidden:
        errors.append(f"Publishable tree contains machine code: {sorted(set(forbidden))}")


def check_project_consistency(errors: list[str]) -> None:
    config = load_json("config.json")
    validation = load_json("generated/validation.json")
    manifest = load_json("generated/artifact_manifest.json")
    model_report = load_json("generated/model_3mf_report.json")
    project = config["project"]
    provenance_fields = {
        "project_name": project["name"],
        "design_edition": project["edition"],
        "revision": project["revision"],
        "embedded_gcode_allowed": project["embedded_gcode_allowed"],
    }
    for field, expected in provenance_fields.items():
        for label, payload in (
            ("validation", validation),
            ("artifact manifest", manifest),
            ("3MF report", model_report),
        ):
            if payload.get(field) != expected:
                errors.append(f"{field} differs between config and {label}")
    if config["project"].get("embedded_gcode_allowed") is not False:
        errors.append("config.json must keep embedded_gcode_allowed=false until hardware is confirmed")
    if "PETG" not in config["printer"].get("filament", ""):
        errors.append("Printable material must remain explicitly identified as PETG")
    if config.get("closet", {}).get("arrangement") != "same_elevation_inside_corner_L":
        errors.append("The active repository must declare the same-elevation inside-corner L arrangement")
    if validation.get("palatine_design") != config.get("palatine"):
        errors.append("validation.json Palatine configuration is stale relative to config.json")
    if validation.get("finish_attachment") != config.get("finish_attachment"):
        errors.append("validation.json finish-attachment policy is stale relative to config.json")
    corner = validation.get("inside_corner", {})
    if corner.get("deck_footprint_overlap_in") != 0.0:
        errors.append("The through/return plywood footprints must not overlap")
    if corner.get("nominal_nearest_conservative_8in_shelf_envelope_clearance_in", -1.0) < config["structural"]["minimum_nominal_corner_bracket_clearance_in"]:
        errors.append("Nominal perpendicular bracket-envelope clearance is below the configured minimum")
    mesh_instance_count = sum(int(mesh["repeat_count"]) for mesh in validation.get("meshes", []))
    declared_count = int(validation.get("modularity", {}).get("full_set_object_count", -1))
    if mesh_instance_count != declared_count:
        errors.append(f"Repeat counts total {mesh_instance_count}, but validation declares {declared_count}")


def main() -> None:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"Required repository file is missing: {relative}")

    if not errors:
        try:
            check_project_consistency(errors)
            check_manifest(errors)
            check_model_packages(errors)
            check_generated_tree(errors)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, zipfile.BadZipFile) as exc:
            errors.append(f"Repository metadata could not be validated: {exc}")
    check_markdown_links(errors)

    if errors:
        print("Repository checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Repository checks passed: documentation links, revisions, manifests, counts, and model-only policy are consistent.")


if __name__ == "__main__":
    main()
