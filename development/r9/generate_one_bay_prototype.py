#!/usr/bin/env python3
"""Publish the first printable R9 tabletop one-bay shelf prototype.

The bundle is neutral and unsliced. It contains five individually printable
parts plus one off-plate assembly reference. It emits printed candidate wall
bores, but cannot emit a slicer profile, G-code, wall-install release, or load
rating.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

try:
    from . import field_layout
    from . import model_io
    from . import one_bay_geometry as one_bay
    from . import render_one_bay_reference as renderer
except ImportError:  # pragma: no cover - direct script execution
    import field_layout  # type: ignore[no-redef]
    import model_io  # type: ignore[no-redef]
    import one_bay_geometry as one_bay  # type: ignore[no-redef]
    import render_one_bay_reference as renderer  # type: ignore[no-redef]


R9_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = R9_ROOT.parents[1]
DEFAULT_OUTPUT = R9_ROOT / "generated" / "one_bay_prototype_v3"
PACKAGE_ID = "r9_palatine_moderne_tabletop_one_bay_prototype_v3"
SUPERSEDES_PACKAGE_ID = "r9_tabletop_one_bay_prototype_v2"
PUBLISHED_V1 = R9_ROOT / "generated" / "one_bay_prototype_v1"
PUBLISHED_V1_MANIFEST_SHA256 = (
    "333392504bd099ffd682b724bb00f1a96412d0a5db4aac9b8ab8bf5dc60be21a"
)
PUBLISHED_V1_TREE_SHA256 = (
    "a19fc94cacd464540b317adb1fe2f6fe6315cb84b0b54ca1d1c77dfbe9163d92"
)
PUBLISHED_V1_FILE_COUNT = 17
PUBLISHED_V1_TOTAL_BYTES = 138632
PUBLISHED_V2 = R9_ROOT / "generated" / "one_bay_prototype_v2"
PUBLISHED_V2_MANIFEST_SHA256 = (
    "28d540f40b9441b73f2cd0e8b362271c1410989c2795061be30202ea641cc551"
)
PUBLISHED_V2_TREE_SHA256 = (
    "f8b30f8b921c08a062d6ffecd3a44ea61524fcad194461e16c1a022b1cefad63"
)
PUBLISHED_V2_FILE_COUNT = 17
PUBLISHED_V2_TOTAL_BYTES = 88685
MODEL_DESCRIPTION = (
    "R9 full-depth tabletop one-bay PETG prototype; neutral unsliced geometry; "
    "three printed wall-mount candidate bores per support; zero-rated and not "
    "authorized for wall installation or stored load"
)
PART_ORDER = (
    "r9_one_bay_left_compact_support",
    "r9_one_bay_right_compact_support",
    "r9_one_bay_rear_ledger",
    "r9_one_bay_front_beam",
    "r9_one_bay_shelf_cassette",
)
SOURCE_PATHS = (
    R9_ROOT / "one_bay_geometry.py",
    R9_ROOT / "field_layout.py",
    R9_ROOT / "render_one_bay_reference.py",
    R9_ROOT / "support_geometry.py",
    R9_ROOT / "design_math.py",
    R9_ROOT / "model_io.py",
    R9_ROOT / "config.json",
    R9_ROOT / "docs" / "MATERIALS_AND_HARDWARE.md",
    R9_ROOT / "docs" / "DESIGN_LANGUAGE.md",
    Path(__file__).resolve(),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _strict_json(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON value in {path}: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=reject_constant,
    )


def _tree_evidence(root: Path) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        relative = str(path.relative_to(root))
        file_digest = hashlib.sha256(payload).hexdigest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
        count += 1
        total += len(payload)
    return count, total, digest.hexdigest()


def _validate_published_v1() -> None:
    if not PUBLISHED_V1.is_dir():
        raise ValueError("Published one-bay prototype v1 is missing")
    if _sha256(PUBLISHED_V1 / "manifest.json") != PUBLISHED_V1_MANIFEST_SHA256:
        raise ValueError("Published one-bay prototype v1 manifest changed")
    evidence = _tree_evidence(PUBLISHED_V1)
    expected = (
        PUBLISHED_V1_FILE_COUNT,
        PUBLISHED_V1_TOTAL_BYTES,
        PUBLISHED_V1_TREE_SHA256,
    )
    if evidence != expected:
        raise ValueError("Published one-bay prototype v1 tree changed")


def _validate_published_v2() -> None:
    if not PUBLISHED_V2.is_dir():
        raise ValueError("Published one-bay prototype v2 is missing")
    if _sha256(PUBLISHED_V2 / "manifest.json") != PUBLISHED_V2_MANIFEST_SHA256:
        raise ValueError("Published one-bay prototype v2 manifest changed")
    evidence = _tree_evidence(PUBLISHED_V2)
    expected = (
        PUBLISHED_V2_FILE_COUNT,
        PUBLISHED_V2_TOTAL_BYTES,
        PUBLISHED_V2_TREE_SHA256,
    )
    if evidence != expected:
        raise ValueError("Published one-bay prototype v2 tree changed")


def _validate_destination(target: Path) -> None:
    resolved = target.resolve()
    if resolved == DEFAULT_OUTPUT.resolve():
        return
    if resolved == PROJECT_ROOT or PROJECT_ROOT in resolved.parents:
        raise ValueError(
            "Custom output may not be inside the repository; use a fresh /tmp path"
        )


def _source_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in SOURCE_PATHS:
        records.append(
            {
                "path": str(path.relative_to(R9_ROOT)),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return records


def _readme() -> str:
    return """# R9 Palatine Moderne tabletop one-bay prototype v3

This is the first R9 package that assembles into an actual shelf section.  It
is a **160 mm-wide, 152.4 mm-deep, 30 mm-high no-load tabletop prototype**.
It contains two handed compact supports, a rear ledger, a front beam, and one
open-bottom three-web shelf cassette. The compressed Roman support arches now
carry additive stepped keystones, and the front beam has a stepped Art-Deco
center relief. Each support has three authored diamond mounting bores at 16,
80, and 144 mm below the shelf underside. They clear a 7.0 mm round metal-
fastener envelope; do not drill or enlarge the PETG after printing.

## Hard boundary

This package is for fit, printability, appearance, mounting-hole inspection,
and hand-assembly evidence.  It has **0 kg / 0 lb rating**.  Do not drill a
wall, mount it, store anything on it, or print production quantities.  The
selected screw/washer candidate is documented in `MATERIALS_AND_HARDWARE.md`,
but substrate, continuous blocking, the PETG clamping interface, long-span,
corner, and load paths remain intentionally unapproved.

## What to print

Use only the five files in `individual_model_only_3mf/`.  Do not print the
assembly-reference 3MF or the STLs unless a documented recovery requires an
STL.  Each individual 3MF contains one object at 100% scale in its authored
print orientation.

1. `MODEL_ONLY_r9_one_bay_left_compact_support.3mf`
2. `MODEL_ONLY_r9_one_bay_right_compact_support.3mf`
3. `MODEL_ONLY_r9_one_bay_rear_ledger.3mf`
4. `MODEL_ONLY_r9_one_bay_front_beam.3mf`
5. `MODEL_ONLY_r9_one_bay_shelf_cassette.3mf`

Print one file at a time.  The rear and front members intentionally share the
same physical interface but are separate required articles.  Stop after every
part for cooling and inspection.  Any crack, layer split, rocking, visible
warp, whitening, increasing bind, or forced fit is a failure.

## Frozen slicer process

- Bambu Lab A1 mini, 0.4 mm nozzle, Textured PEI plate
- SUNLU PETG `@BBL A1M 0.4 nozzle`
- `0.20mm Strength @BBL A1M`
- 0.20 mm layers; 6 walls; 25% grid; 5 top / 3 bottom
- Support OFF
- Outer brim only, 5.0 mm width, 0.1 mm object gap
- 100% scale; no auto-orient, auto-arrange, or repair

The 3MF files are neutral and contain no slicer profile or G-code.  Verify the
settings and Preview for every part.  Codex must report time/material and wait
for explicit approval before every physical print.

## Assembly

Read `MATERIALS_AND_HARDWARE.md`, `DESIGN_LANGUAGE.md`, then `ASSEMBLY.md`.
First verify all six printed mounting bores are open and clean without
reaming. Then stand both supports on a padded
table, lower the rear ledger and front beam into their top-open sockets, then
lower the cassette onto the four top locator bosses.  Never hammer, clamp,
twist, sand, file, lubricate, or load it.

## Measured-wall continuation

After this bay passes, the first installed-design phase is the 61.25 in outlet
wall at the 68 in shelf-top elevation.  Its exact candidate is six stations at
equal 304.75 mm / 11.998 in pitch: one far-left bookend, four short compact
supports, and one concealed corner-end support.  These are design centers, not
released drilling coordinates; trim, wall bow, framing/blocking, substrate,
and one exact fastener system still have to be bound.
"""


def _assembly_doc() -> str:
    return """# R9 Palatine Moderne one-bay tabletop assembly

All five parts must be fully cool, clean, and free of cracks, layer separation,
rocking, visible warp, or damaged interfaces before assembly.

Read `MATERIALS_AND_HARDWARE.md` first. Confirm that each support has three
clean, fully open diamond wall-mount bores at 16, 80, and 144 mm below the
shelf underside. A nominal 7.0 mm round gauge may pass without force; do not
drill, ream, file, or countersink a printed bore. This inspection does not
authorize wall installation.

## Identify the parts

- Left support: member sockets open on its right/inside face.
- Right support: member sockets open on its left/inside face.
- Rear ledger: installs at the wall side of the bay.
- Front beam: installs at the front edge.
- Shelf cassette: finished textured face is the top; its open webbed face is
  underneath.

## Assemble, unloaded

1. Stand the left and right supports upright on a padded flat table, with their
   socket faces pointing inward.  Keep their outer faces 160 mm apart.
2. Align both rear-ledger tongues over the rear top-open sockets.  Lower the
   member vertically until its shoulders meet both support faces.  Stop at the
   first resistance beyond light guidance.
3. Repeat with the front beam and the two front top-open sockets.  Both
   supports must remain square without twist.
4. Orient the cassette with its finished top upward.  Align the four underside
   pockets over the four support bosses and lower it vertically.  Do not rock
   or lever it into place.
5. Photograph the front, rear, both sides, underside, and top.  On the padded
   table only, gently check for rocking and visible gaps.  Do not place an
   object or hand load on the shelf.

## Disassemble

Lift the cassette vertically.  Lift the front beam and rear ledger vertically,
then separate the supports.  Inspect every tongue, socket,
boss, and pocket for whitening, abrasion, cracking, permanent deformation, or
increasing bind.  Complete ten gentle assembly/removal cycles only if every
prior cycle remains clean.

## Pass meaning

A pass authorizes CAD work on the measured full L-shaped set.  It does not
authorize wall bores, installation, stored load, a load rating, or production
quantities.
"""


def _build_stage(stage: Path) -> None:
    evidence = one_bay.build_one_bay_evidence()
    measured = field_layout.build_even_field_layout()
    if not evidence.target_pose_collision_free:
        raise ValueError("One-bay installed target contains a positive overlap")
    if not evidence.service_paths_collision_free:
        raise ValueError("One-bay installation path contains a positive overlap")
    saved = one_bay.build_saved_one_bay_parts()
    if tuple(saved) != PART_ORDER:
        raise ValueError("One-bay part order changed")
    envelopes = one_bay.print_envelopes()
    serialized: dict[str, model_io.SerializedMesh] = {}
    geometry_records: list[dict[str, Any]] = []
    stl_root = stage / "stl"
    individual_root = stage / "individual_model_only_3mf"
    for item in evidence.parts:
        mesh = saved[item.name]
        frozen = model_io.canonicalize_mesh(mesh)
        serialized[item.name] = frozen
        serialized_evidence = model_io.serialized_mesh_evidence(frozen)
        if not serialized_evidence["closed_one_body_positive"]:
            raise ValueError(f"Invalid serialized one-bay part: {item.name}")
        if not envelopes[item.name].fits:
            raise ValueError(f"One-bay part exceeds A1 mini: {item.name}")
        stl_path = stl_root / f"{item.name}.stl"
        model_path = individual_root / f"MODEL_ONLY_{item.name}.3mf"
        model_io.write_binary_stl(stl_path, frozen)
        model_io.write_model_only_3mf(
            model_path,
            title=item.name,
            description=MODEL_DESCRIPTION,
            objects=(model_io.ModelObject(item.name, frozen),),
        )
        inspection = model_io.inspect_model_only_3mf(model_path)
        if tuple(inspection.objects) != (item.name,):
            raise ValueError(f"Individual object name changed: {item.name}")
        if inspection.translations_mm[item.name] != (0.0, 0.0, 0.0):
            raise ValueError(f"Individual object transform changed: {item.name}")
        geometry_records.append(
            {
                "mesh_id": item.name,
                "saved_orientation": item.saved_orientation,
                "support_required": item.support_required,
                "raw_extents_mm": [round(float(value), 6) for value in mesh.extents],
                "required_build_volume_mm": [
                    round(float(value), 6)
                    for value in envelopes[item.name].required_build_volume_mm
                ],
                "solid_volume_mm3": round(float(mesh.volume), 6),
                "serialized_mesh": serialized_evidence,
            }
        )

    catalog_path = stage / "model_only_3mf" / "R9_ONE_BAY_PRINTABLE_PARTS_CATALOG_NOT_A_PLATE.3mf"
    translations: dict[str, tuple[float, float, float]] = {}
    cursor = 0.0
    catalog_objects: list[model_io.ModelObject] = []
    for name in PART_ORDER:
        translation = (round(cursor, 6), 0.0, 0.0)
        translations[name] = translation
        catalog_objects.append(model_io.ModelObject(name, serialized[name], translation))
        cursor = round(cursor + float(saved[name].extents[0]) + 20.0, 6)
    model_io.write_model_only_3mf(
        catalog_path,
        title="R9 one-bay printable-parts catalog",
        description=MODEL_DESCRIPTION + "; OFF-PLATE CATALOG; DO NOT PRINT",
        objects=tuple(catalog_objects),
    )
    catalog = model_io.inspect_model_only_3mf(catalog_path)
    if tuple(catalog.objects) != PART_ORDER or catalog.translations_mm != translations:
        raise ValueError("One-bay catalog order or transforms changed")

    installed = one_bay.build_installed_one_bay_parts()
    assembly_objects: list[model_io.ModelObject] = []
    for name in PART_ORDER:
        assembly_objects.append(
            model_io.ModelObject(name, model_io.canonicalize_mesh(installed[name]))
        )
    assembly_path = (
        stage
        / "assembly_reference"
        / "R9_ONE_BAY_ASSEMBLED_REFERENCE_NOT_A_PRINT_PLATE.3mf"
    )
    model_io.write_model_only_3mf(
        assembly_path,
        title="R9 assembled tabletop one-bay reference",
        description=MODEL_DESCRIPTION + "; ASSEMBLY REFERENCE; DO NOT PRINT",
        objects=tuple(assembly_objects),
    )
    assembly = model_io.inspect_model_only_3mf(assembly_path)
    if tuple(assembly.objects) != PART_ORDER:
        raise ValueError("Assembly reference object order changed")

    model_io.write_bytes_exclusive(stage / "README.md", _readme().encode("utf-8"))
    model_io.write_bytes_exclusive(stage / "ASSEMBLY.md", _assembly_doc().encode("utf-8"))
    model_io.write_bytes_exclusive(
        stage / "MATERIALS_AND_HARDWARE.md",
        (R9_ROOT / "docs" / "MATERIALS_AND_HARDWARE.md").read_bytes(),
    )
    model_io.write_bytes_exclusive(
        stage / "DESIGN_LANGUAGE.md",
        (R9_ROOT / "docs" / "DESIGN_LANGUAGE.md").read_bytes(),
    )
    model_io.write_bytes_exclusive(
        stage / "R9_ONE_BAY_ASSEMBLY_REFERENCE.svg", renderer.svg_bytes()
    )
    validation = {
        "package_id": PACKAGE_ID,
        "supersedes_package_id": SUPERSEDES_PACKAGE_ID,
        "supersession_reason": (
            "members now print with their complete footprint on layer one and "
            "lower vertically into top-open support sockets"
        ),
        "qualification_only": True,
        "production_ready": False,
        "physical_qualification_complete": False,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "wall_bores_emitted": True,
        "wall_mounting_candidate": {
            "bores_per_support": evidence.mounting_bores_per_support,
            "round_fastener_clearance_diameter_mm": (
                evidence.mounting_bore_diameter_mm
            ),
            "drops_below_shelf_underside_mm": (
                evidence.mounting_bore_drops_below_underside_mm
            ),
            "maximum_flat_washer_outer_diameter_mm": (
                evidence.maximum_flat_washer_outer_diameter_mm
            ),
            "bores_clear_member_sockets": (
                evidence.mounting_bores_clear_member_sockets
            ),
            "bore_center_spacing_mm": evidence.mounting_bore_center_spacing_mm,
            "fastener_candidate_product": evidence.fastener_candidate_product,
            "fastener_candidate_minimum_spacing_mm": (
                evidence.fastener_candidate_minimum_spacing_mm
            ),
            "geometry_spacing_passes": (
                evidence.fastener_candidate_geometry_spacing_passes
            ),
            "exact_fastener_or_anchor_selected": False,
            "framing_or_blocking_verified": False,
            "wall_installation_authorized": False,
        },
        "aesthetic_contract": {
            "id": evidence.aesthetic_contract_id,
            "name": "Palatine Moderne",
            "roman_arch_support_keystone_emitted": True,
            "art_deco_front_beam_relief_emitted": True,
            "decoration_removes_structural_core_material": False,
        },
        "full_measured_shelf_set_present": False,
        "tabletop_one_bay_present": True,
        "unsliced": True,
        "embedded_print_profile_present": False,
        "generated_gcode_present": False,
        "part_order": PART_ORDER,
        "geometry_records": geometry_records,
        "installed_target": {
            "bay_width_mm": evidence.bay_width_mm,
            "shelf_depth_mm": evidence.shelf_depth_mm,
            "shelf_height_mm": evidence.shelf_height_mm,
            "member_socket_clearance_per_face_mm": evidence.member_socket_clearance_per_face_mm,
            "deck_locator_clearance_per_face_mm": evidence.deck_locator_clearance_per_face_mm,
            "maximum_pair_intersection_volume_mm3": evidence.maximum_intersection_volume_mm3,
            "collision_free": evidence.target_pose_collision_free,
            "service_path_maximum_intersection_volume_mm3": (
                evidence.service_path_maximum_intersection_volume_mm3
            ),
            "service_paths_collision_free": evidence.service_paths_collision_free,
            "assembly_order": evidence.tabletop_assembly_order,
        },
        "measured_even_support_candidate": {
            "level_top_elevations_in": measured.level_top_elevations_in,
            "supports_per_level": measured.supports_per_level,
            "visible_supports_per_level": measured.visible_supports_per_level,
            "mounting_bores_per_support": measured.mounting_bores_per_support,
            "drilling_coordinates_released": (
                measured.drilling_coordinates_released
            ),
            "primary_hollow_wall_anchor_authorized": (
                measured.primary_hollow_wall_anchor_authorized
            ),
            "runs": [
                {
                    "run_id": run.run_id,
                    "clear_length_mm": run.clear_length_mm,
                    "support_count": len(run.stations),
                    "equal_pitch_mm": run.actual_pitch_mm,
                    "equal_pitch_in": run.actual_pitch_in,
                    "station_centers_from_datum_mm": [
                        station.center_from_run_datum_mm
                        for station in run.stations
                    ],
                    "roles": [station.role for station in run.stations],
                }
                for run in measured.runs
            ],
        },
        "first_shelf_execution_phase": {
            "run_id": "through",
            "wall_clear_length_in": 61.25,
            "shelf_top_elevation_in": 68.0,
            "support_count": len(measured.runs[0].stations),
            "equal_pitch_mm": measured.runs[0].actual_pitch_mm,
            "station_centers_from_far_left_in": [
                station.center_from_run_datum_in
                for station in measured.runs[0].stations
            ],
            "upper_84_in_shelf_deferred": True,
            "return_wall_deferred": True,
            "wall_installation_authorized": False,
        },
        "source_records": _source_records(),
    }
    model_io.write_bytes_exclusive(stage / "validation.json", _json_bytes(validation))


def _artifact_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(
        item
        for item in root.rglob("*")
        if item.is_file() and item.name != "manifest.json"
    ):
        records.append(
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return records


def validate_bundle(root: Path) -> None:
    bundle = Path(root)
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("One-bay bundle must be a real directory")
    if any(path.is_symlink() for path in bundle.rglob("*")):
        raise ValueError("One-bay bundle may not contain symlinks")
    manifest = _strict_json(bundle / "manifest.json")
    if manifest["package_id"] != PACKAGE_ID:
        raise ValueError("One-bay package ID changed")
    expected = manifest["artifact_records"]
    actual = _artifact_records(bundle)
    if actual != expected:
        raise ValueError("One-bay artifact hashes or allowlist changed")
    if manifest["source_records"] != _source_records():
        raise ValueError("One-bay source bundle no longer matches live source")
    validation = _strict_json(bundle / "validation.json")
    if validation["package_id"] != PACKAGE_ID:
        raise ValueError("One-bay validation package ID changed")
    if tuple(validation["part_order"]) != PART_ORDER:
        raise ValueError("One-bay validation part order changed")
    if not validation["installed_target"]["collision_free"]:
        raise ValueError("One-bay validation lost collision-free target")
    if not validation["installed_target"]["service_paths_collision_free"]:
        raise ValueError("One-bay validation lost collision-free service paths")
    mounting = validation["wall_mounting_candidate"]
    if (
        validation["wall_bores_emitted"] is not True
        or mounting["bores_per_support"] != 3
        or mounting["round_fastener_clearance_diameter_mm"] != 7.0
        or mounting["bores_clear_member_sockets"] is not True
        or mounting["wall_installation_authorized"] is not False
    ):
        raise ValueError("One-bay mounting-bore contract changed")
    measured = validation["measured_even_support_candidate"]
    if (
        measured["supports_per_level"] != 10
        or [run["support_count"] for run in measured["runs"]] != [6, 4]
        or measured["drilling_coordinates_released"] is not False
        or measured["primary_hollow_wall_anchor_authorized"] is not False
    ):
        raise ValueError("Measured equal-support layout contract changed")
    first_phase = validation["first_shelf_execution_phase"]
    if (
        first_phase["run_id"] != "through"
        or first_phase["shelf_top_elevation_in"] != 68.0
        or first_phase["support_count"] != 6
        or first_phase["upper_84_in_shelf_deferred"] is not True
        or first_phase["return_wall_deferred"] is not True
        or first_phase["wall_installation_authorized"] is not False
    ):
        raise ValueError("First-shelf execution boundary changed")
    if validation["source_records"] != _source_records():
        raise ValueError("One-bay validation source records changed")
    geometry = {item["mesh_id"]: item for item in validation["geometry_records"]}
    if tuple(geometry) != PART_ORDER:
        raise ValueError("One-bay geometry record order changed")
    saved = one_bay.build_saved_one_bay_parts()
    for name in PART_ORDER:
        path = bundle / "individual_model_only_3mf" / f"MODEL_ONLY_{name}.3mf"
        inspection = model_io.inspect_model_only_3mf(path)
        if tuple(inspection.objects) != (name,):
            raise ValueError(f"One-bay object identity changed: {name}")
        expected_digest = geometry[name]["serialized_mesh"][
            "canonical_float32_triangle_digest"
        ]
        if model_io.canonical_triangle_digest(inspection.objects[name]) != expected_digest:
            raise ValueError(f"Individual 3MF geometry changed: {name}")
        stl = model_io.read_binary_stl(bundle / "stl" / f"{name}.stl")
        if model_io.canonical_triangle_digest(stl) != expected_digest:
            raise ValueError(f"STL geometry changed: {name}")
        live = model_io.canonicalize_mesh(saved[name])
        if model_io.canonical_triangle_digest(live) != expected_digest:
            raise ValueError(f"Live one-bay geometry changed: {name}")
    catalog = model_io.inspect_model_only_3mf(
        bundle
        / "model_only_3mf"
        / "R9_ONE_BAY_PRINTABLE_PARTS_CATALOG_NOT_A_PLATE.3mf"
    )
    assembly = model_io.inspect_model_only_3mf(
        bundle
        / "assembly_reference"
        / "R9_ONE_BAY_ASSEMBLED_REFERENCE_NOT_A_PRINT_PLATE.3mf"
    )
    if tuple(catalog.objects) != PART_ORDER or tuple(assembly.objects) != PART_ORDER:
        raise ValueError("One-bay catalog or assembly object order changed")
    installed = one_bay.build_installed_one_bay_parts()
    for name in PART_ORDER:
        expected_digest = geometry[name]["serialized_mesh"][
            "canonical_float32_triangle_digest"
        ]
        if model_io.canonical_triangle_digest(catalog.objects[name]) != expected_digest:
            raise ValueError(f"Catalog geometry changed: {name}")
        installed_digest = model_io.canonical_triangle_digest(
            model_io.canonicalize_mesh(installed[name])
        )
        if model_io.canonical_triangle_digest(assembly.objects[name]) != installed_digest:
            raise ValueError(f"Assembly-reference geometry changed: {name}")


def build_bundle(destination: Path = DEFAULT_OUTPUT) -> Path:
    target = Path(destination).resolve()
    _validate_destination(target)
    _validate_published_v1()
    _validate_published_v2()
    source_before = _source_records()
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(target):
        raise FileExistsError(f"Refusing existing one-bay bundle: {target}")
    stage = Path(tempfile.mkdtemp(prefix=".one-bay-stage-", dir=target.parent))
    try:
        _build_stage(stage)
        manifest = {
            "package_id": PACKAGE_ID,
            "supersedes_package_id": SUPERSEDES_PACKAGE_ID,
            "artifact_records": _artifact_records(stage),
            "source_records": _source_records(),
            "publication_contract": {
                "qualification_only": True,
                "unsliced": True,
                "no_profile_or_gcode": True,
                "manual_preview_and_explicit_print_approval_required": True,
                "no_wall_installation_or_load": True,
            },
        }
        model_io.write_bytes_exclusive(stage / "manifest.json", _json_bytes(manifest))
        if _source_records() != source_before:
            raise RuntimeError("One-bay source changed during staged build")
        validate_bundle(stage)
        model_io.atomic_publish_directory(stage, target)
        if _source_records() != source_before:
            raise RuntimeError("One-bay source changed during publication")
        _validate_published_v1()
        _validate_published_v2()
        validate_bundle(target)
        return target
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    published = build_bundle(arguments.output)
    print(published)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
