#!/usr/bin/env python3
"""Validate model-only 3MFs and optionally confirm Bambu Studio imports.

The archive/mesh checks are deterministic and suitable for continuous
integration. Bambu Studio import checks are local integration evidence because
the application is not available on standard Linux GitHub-hosted runners.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.json"
MODEL_DIR = ROOT / "generated" / "model_only_3mf"
OUT = ROOT / "generated" / "model_3mf_report.json"
BAMBU_OUT = ROOT / "generated" / "bambu_import_report.json"
BAMBU = Path(os.environ.get("BAMBU_BIN", "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"))
NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_config() -> dict:
    try:
        config = json.loads(
            CONFIG.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Cannot load {CONFIG}: {exc}") from exc
    if not isinstance(config, dict):
        raise SystemExit(f"{CONFIG} must contain a JSON object")
    return config


def report_provenance(config: dict) -> dict:
    try:
        project = config["project"]
        provenance = {
            "project_name": project["name"],
            "design_edition": project["edition"],
            "revision": project["revision"],
            "embedded_gcode_allowed": project["embedded_gcode_allowed"],
            "source_config": "config.json",
        }
    except (KeyError, TypeError) as exc:
        raise SystemExit(f"config.json is missing required project provenance: {exc}") from exc
    if provenance["embedded_gcode_allowed"] is not False:
        raise SystemExit("config.json must keep embedded_gcode_allowed=false")
    return provenance


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def not_performed_bambu_report(provenance: dict, files: list[Path], reason: str) -> dict:
    return {
        **provenance,
        "artifact_type": "local Bambu Studio import/export integration check",
        "bambu_executable": str(BAMBU),
        "performed": False,
        "status": "not_performed",
        "reason": reason,
        "generated_files": len(files),
        "performed_files": 0,
        "all_files_pass": None,
        "package_files": [path.name for path in files],
        "files": [
            {
                "file": path.name,
                "performed": False,
                "import_and_stl_export_pass": None,
                "detail": reason,
            }
            for path in files
        ],
    }


def bambu_import_check(path: Path, expected_object_count: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="petg-shelf-3mf-check-") as tmp:
        try:
            completed = subprocess.run(
                [str(BAMBU), "--export-stls", tmp, str(path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=tmp,
                timeout=90,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            return {
                "file": path.name,
                "performed": True,
                "import_and_stl_export_pass": False,
                "returncode": None,
                "expected_object_count": expected_object_count,
                "exported_stl_count": 0,
                "export_count_matches": False,
                "exported_stl_bytes": 0,
                "all_exported_stls_nonempty": False,
                "detail": f"Bambu Studio timed out after 90 seconds: {output[-1200:]}",
            }
        except OSError as exc:
            return {
                "file": path.name,
                "performed": True,
                "import_and_stl_export_pass": False,
                "returncode": None,
                "expected_object_count": expected_object_count,
                "exported_stl_count": 0,
                "export_count_matches": False,
                "exported_stl_bytes": 0,
                "all_exported_stls_nonempty": False,
                "detail": f"Could not execute Bambu Studio: {exc}",
            }

        exported = sorted(Path(tmp).rglob("*.stl"))
        sizes = [item.stat().st_size for item in exported]
        export_count_matches = len(exported) == expected_object_count
        all_nonempty = bool(exported) and all(size > 84 for size in sizes)
        passed = completed.returncode == 0 and export_count_matches and all_nonempty
        output_tail = " ".join((completed.stdout or "").strip().splitlines()[-5:])[-1200:]
        if passed:
            detail = (
                f"imported and exported {len(exported)} nonempty STL file(s), "
                "matching the 3MF object count"
            )
        else:
            detail = output_tail or "Bambu Studio did not produce the expected nonempty STL exports"
        return {
            "file": path.name,
            "performed": True,
            "import_and_stl_export_pass": passed,
            "returncode": completed.returncode,
            "expected_object_count": expected_object_count,
            "exported_stl_count": len(exported),
            "export_count_matches": export_count_matches,
            "exported_stl_bytes": sum(sizes),
            "all_exported_stls_nonempty": all_nonempty,
            "detail": detail,
        }


def inspect(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        bad_entry = archive.testzip()
        names = set(archive.namelist())
        required = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
        missing = sorted(required - names)
        gcode_entries = sorted(name for name in names if "gcode" in name.lower())
        model_bytes = archive.read("3D/3dmodel.model")

    root = ET.fromstring(model_bytes)
    objects = root.findall("m:resources/m:object", NS)
    build_items = root.findall("m:build/m:item", NS)
    object_id_values = [obj.attrib.get("id") for obj in objects]
    referenced_id_values = [item.attrib.get("objectid") for item in build_items]
    object_names = [obj.attrib.get("name") for obj in objects]
    object_ids_present_and_unique = (
        all(object_id_values) and len(object_id_values) == len(set(object_id_values))
    )
    build_references_exact_once = (
        bool(objects)
        and object_ids_present_and_unique
        and len(build_items) == len(objects)
        and Counter(referenced_id_values) == Counter(object_id_values)
    )
    object_names_present = all(name and name.strip() for name in object_names)
    object_names_unique = object_names_present and len(object_names) == len(set(object_names))
    mesh_counts = []
    triangle_indices_valid = True
    for obj in objects:
        vertices = obj.findall("m:mesh/m:vertices/m:vertex", NS)
        triangles = obj.findall("m:mesh/m:triangles/m:triangle", NS)
        vertex_count = len(vertices)
        for triangle in triangles:
            indices = [int(triangle.attrib[key]) for key in ("v1", "v2", "v3")]
            if not all(0 <= index < vertex_count for index in indices):
                triangle_indices_valid = False
        mesh_counts.append({
            "name": obj.attrib.get("name"),
            "vertices": vertex_count,
            "triangles": len(triangles),
        })

    checks = {
        "zip_crc_ok": bad_entry is None,
        "required_entries_present": not missing,
        "millimeter_units": root.attrib.get("unit") == "millimeter",
        "contains_mesh_objects": bool(objects) and all(item["vertices"] and item["triangles"] for item in mesh_counts),
        "object_ids_present_and_unique": object_ids_present_and_unique,
        "object_names_present": object_names_present,
        "object_names_unique": object_names_unique,
        "build_references_valid": build_references_exact_once,
        "build_references_exactly_once": build_references_exact_once,
        "triangle_indices_valid": triangle_indices_valid,
        "contains_no_embedded_gcode": not gcode_entries,
    }
    return {
        "file": path.name,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "missing_entries": missing,
        "unexpected_gcode_entries": gcode_entries,
        "object_count": len(objects),
        "build_item_count": len(build_items),
        "total_vertices": sum(item["vertices"] for item in mesh_counts),
        "total_triangles": sum(item["triangles"] for item in mesh_counts),
        "mesh_details": mesh_counts if len(mesh_counts) <= 20 else None,
        "mesh_details_omitted": len(mesh_counts) > 20,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--require-bambu", action="store_true", help="Fail unless every file imports in the configured Bambu Studio executable")
    mode.add_argument("--skip-bambu", action="store_true", help="Run deterministic archive/mesh checks only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    provenance = report_provenance(config)
    files = sorted(MODEL_DIR.glob("*.3mf"))
    if not files:
        write_json(
            BAMBU_OUT,
            not_performed_bambu_report(
                provenance,
                files,
                "No model-only 3MF files found",
            ),
        )
        raise SystemExit("No model-only 3MF files found")

    run_bambu = not args.skip_bambu and BAMBU.is_file()
    if args.skip_bambu:
        not_performed_reason = "Bambu Studio check explicitly skipped"
    elif not BAMBU.is_file():
        not_performed_reason = f"Bambu Studio executable not found at {BAMBU}"
    else:
        not_performed_reason = "Bambu Studio check pending for the current package set"
    write_json(
        BAMBU_OUT,
        not_performed_bambu_report(provenance, files, not_performed_reason),
    )

    results = [inspect(path) for path in files]
    report = {
        **provenance,
        "artifact_type": "model-only 3MF; no embedded G-code",
        "generated_files": len(results),
        "all_files_pass": all(item["all_checks_pass"] for item in results),
        "package_files": [path.name for path in files],
        "files": results,
    }
    write_json(OUT, report)
    print(json.dumps(report, indent=2))
    if not report["all_files_pass"]:
        write_json(
            BAMBU_OUT,
            not_performed_bambu_report(
                provenance,
                files,
                "Bambu Studio check not performed because deterministic 3MF validation failed",
            ),
        )
        raise SystemExit(1)

    if args.require_bambu and not BAMBU.is_file():
        raise SystemExit(f"Bambu Studio executable not found at {BAMBU}")
    if run_bambu:
        object_counts = {item["file"]: item["object_count"] for item in results}
        bambu_results = [
            bambu_import_check(path, object_counts[path.name])
            for path in files
        ]
        bambu_report = {
            **provenance,
            "artifact_type": "local Bambu Studio import/export integration check",
            "bambu_executable": str(BAMBU),
            "performed": True,
            "status": "passed" if all(item["import_and_stl_export_pass"] for item in bambu_results) else "failed",
            "generated_files": len(bambu_results),
            "performed_files": len(bambu_results),
            "all_files_pass": all(item["import_and_stl_export_pass"] for item in bambu_results),
            "package_files": [path.name for path in files],
            "files": bambu_results,
        }
        write_json(BAMBU_OUT, bambu_report)
        print(json.dumps(bambu_report, indent=2))
        if not bambu_report["all_files_pass"]:
            raise SystemExit(1)
    elif args.require_bambu:
        raise SystemExit("Bambu Studio integration check was required but not performed")


if __name__ == "__main__":
    main()
