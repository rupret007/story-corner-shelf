#!/usr/bin/env python3
"""Generate the Story Corner Mini — one stud-bay, all-PETG printable shelf.

Reuses mesh helpers and layout math from generate_shelf_parts.py. Outputs STL
and model-only 3MFs under generated/mini/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import generate_shelf_parts as gen  # noqa: E402

MINI_CONFIG_PATH = ROOT / "config.mini.json"
BASE_CONFIG_PATH = ROOT / "config.json"


def load_mini_config() -> dict:
    mini = json.loads(MINI_CONFIG_PATH.read_text(encoding="utf-8"), object_pairs_hook=gen.reject_duplicate_json_keys)
    base = json.loads(BASE_CONFIG_PATH.read_text(encoding="utf-8"), object_pairs_hook=gen.reject_duplicate_json_keys)
    merged = {
        "project": {**base.get("project", {}), **mini.get("project", {})},
        "printer": {**base.get("printer", {}), **mini.get("printer", {})},
        "print_profile": {**base.get("print_profile", {}), **mini.get("print_profile", {})},
        "skin": {**base.get("skin", {}), **mini.get("skin", {})},
        "closet": mini.get("closet", {}),
        "structural_mini": mini.get("structural_mini", {}),
        "profile": mini.get("profile"),
        "output": mini.get("output", {"directory": "generated/mini"}),
    }
    return merged


def effective_build_envelope_mm(cfg: dict) -> np.ndarray:
    build = np.asarray(cfg["printer"]["minimum_model_build_envelope_mm"], dtype=float)
    margin = float(cfg["printer"].get("build_fit_margin_mm", 0.0))
    if margin < 0.0:
        raise ValueError("build_fit_margin_mm must be non-negative")
    effective = build - 2.0 * margin
    if np.any(effective <= 0.0):
        raise ValueError("build_fit_margin_mm consumes the entire build envelope")
    return effective


def deck_dimensions(cfg: dict) -> dict:
    span_in = float(cfg["closet"]["deck_clear_span_in"])
    depth_in = float(cfg["closet"]["shelf_depth_in"])
    length_mm = gen.inches(span_in)
    depth_mm = gen.inches(depth_in)
    rows = int(cfg["skin"]["tile_depth_rows"])
    gap = float(cfg["skin"]["tile_gap_mm"])
    module_depth = (depth_mm - (rows - 1) * gap) / rows
    top_layout = gen.module_layout(
        cfg,
        length_mm,
        rows=rows,
        columns_override=None,
        label="mini deck",
    )
    top_layout["module_depth_mm"] = module_depth
    top_layout["deck_length_mm"] = length_mm
    top_layout["deck_depth_mm"] = depth_mm
    return top_layout


def _deck_interlock_features(
    cfg: dict,
    width: float,
    depth: float,
    thickness: float,
    *,
    tongue_on_right: bool,
    groove_on_left: bool,
    groove_on_right: bool,
) -> tuple[list[trimesh.Trimesh], list[trimesh.Trimesh]]:
    sm = cfg["structural_mini"]
    tongue_d = float(sm["interlock_tongue_depth_mm"])
    clearance = float(sm["interlock_clearance_mm"])
    tongue_t = thickness * 0.5
    y0 = depth * 0.15
    y_len = depth * 0.7
    unions: list[trimesh.Trimesh] = []
    cuts: list[trimesh.Trimesh] = []
    if tongue_on_right:
        unions.append(
            gen.cuboid((tongue_d, y_len, tongue_t), origin=(width - clearance, y0, thickness - tongue_t))
        )
    if groove_on_left:
        cuts.append(
            gen.cuboid(
                (tongue_d + 2.0 * clearance, y_len, tongue_t + clearance),
                origin=(-clearance - tongue_d, y0, thickness - tongue_t - clearance),
            )
        )
    if groove_on_right:
        cuts.append(
            gen.cuboid(
                (tongue_d + 2.0 * clearance, y_len, tongue_t + clearance),
                origin=(width - tongue_d - clearance, y0, thickness - tongue_t - clearance),
            )
        )
    return unions, cuts


def deck_tile(
    cfg: dict,
    width: float,
    depth: float,
    *,
    interlock: str,
) -> trimesh.Trimesh:
    sm = cfg["structural_mini"]
    thickness = float(sm["deck_tile_thickness_mm"])
    radius = float(cfg["skin"]["top_tile_plan_radius_mm"])
    body = gen.rounded_prism(width, depth, thickness, radius=radius)
    if interlock == "none":
        return gen.normalize_mesh(body)
    if interlock == "end_left":
        unions, cuts = _deck_interlock_features(
            cfg, width, depth, thickness, tongue_on_right=True, groove_on_left=False, groove_on_right=False
        )
    elif interlock == "end_right":
        unions, cuts = _deck_interlock_features(
            cfg, width, depth, thickness, tongue_on_right=False, groove_on_left=True, groove_on_right=False
        )
    elif interlock == "center":
        unions, cuts = _deck_interlock_features(
            cfg, width, depth, thickness, tongue_on_right=True, groove_on_left=True, groove_on_right=False
        )
    else:
        raise ValueError(f"unknown interlock mode {interlock!r}")
    if cuts:
        body = gen.boolean_difference(body, cuts)
    if unions:
        body = gen.boolean_union([body, *unions])
    return gen.normalize_mesh(body)


def stud_bracket(cfg: dict) -> trimesh.Trimesh:
    """Wall strap plus shelf arm; saved with the wall strap on the build plate."""
    sm = cfg["structural_mini"]
    strap_w = float(sm["bracket_wall_strap_width_mm"])
    strap_t = float(sm["bracket_wall_strap_thickness_mm"])
    arm_len = float(sm["bracket_shelf_arm_length_mm"])
    arm_t = float(sm["bracket_shelf_arm_thickness_mm"])
    drop = float(sm["bracket_vertical_drop_mm"])

    # Wall strap lies on Y-Z when installed; print with strap face on bed (X=strap_w, Y=strap_t, Z=drop).
    strap = gen.cuboid((strap_w, strap_t, drop))
    bore_d = float(sm["mounting_bore_diameter_mm"])
    pitch = float(sm["mounting_bore_vertical_pitch_mm"])
    count = int(sm["mounting_bore_count_per_bracket"])
    top_offset = float(sm.get("mounting_bore_top_offset_mm", 12.0))
    centers_z = [drop - top_offset - index * pitch for index in range(count)]
    if min(centers_z) < bore_d or max(centers_z) > drop - bore_d:
        raise ValueError("Mounting bore pattern does not fit the bracket wall strap height")
    cutters = []
    for zc in centers_z:
        cyl = trimesh.creation.cylinder(radius=bore_d / 2.0, height=strap_t + 4.0, sections=32)
        cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1.0, 0.0, 0.0]))
        cyl.apply_translation((strap_w / 2.0, strap_t / 2.0, zc))
        cutters.append(cyl)
    strap = gen.boolean_difference(strap, cutters)
    arm = gen.cuboid((arm_len, arm_t, arm_t), origin=(0.0, strap_t - 0.02, drop - arm_t))
    body = gen.boolean_union([strap, arm])
    # Shelf arm on build plate: rotate so strap is vertical on plate, arm grows in +Y.
    body.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2.0, [1.0, 0.0, 0.0]))
    return gen.normalize_mesh(body)


def validate_mini_part(part: gen.Part, cfg: dict, build: np.ndarray) -> dict:
    mesh = part.mesh.copy()
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()
    bounds = np.asarray(mesh.bounds)
    size = bounds[1] - bounds[0]
    density = float(cfg["skin"]["petg_density_g_cm3"])
    mass_g = mesh.volume / 1000.0 * density
    fits = bool(np.all(size <= build + 1e-6))
    result = {
        "name": part.name,
        "run_id": part.run_id,
        "repeat_count": part.repeat_count,
        "purpose": part.purpose,
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "body_count": int(len(mesh.split(only_watertight=False))),
        "bounds_mm": np.round(bounds, 4).tolist(),
        "size_mm": np.round(size, 4).tolist(),
        "volume_mm3": round(float(mesh.volume), 2),
        "estimated_petg_g_each": round(float(mass_g), 1),
        "fits_effective_build_envelope_in_saved_orientation": fits,
        "effective_build_envelope_mm": build.tolist(),
    }
    if not result["watertight"] or not result["winding_consistent"]:
        raise ValueError(f"{part.name} is not a closed, consistently wound mesh")
    if result["body_count"] != 1:
        raise ValueError(f"{part.name} unexpectedly has {result['body_count']} bodies")
    if not fits:
        raise ValueError(f"{part.name} exceeds the effective build envelope {build}: {size}")
    return result


def save_mini_stl(part: gen.Part, out_dir: Path) -> Path:
    path = out_dir / f"{part.name}.stl"
    path.write_bytes(trimesh.exchange.stl.export_stl(part.mesh))
    return path


def write_mini_3mfs(parts: list[gen.Part], cfg: dict, out_dir: Path) -> None:
    model_dir = out_dir / "model_only_3mf"
    model_dir.mkdir(parents=True, exist_ok=True)
    project_name = cfg["project"]["name"]
    edition = cfg["project"]["edition"]
    revision = cfg["project"]["revision"]
    description = (
        f"{project_name} — {edition}; revision {revision}. MODEL ONLY - NO EMBEDDED G-CODE. "
        "SUNLU PETG on Bambu Lab A1 mini; confirm plate and preset before slicing."
    )
    for part in parts:
        gen.write_model_3mf(
            model_dir / f"MODEL_ONLY_{part.name}.3mf",
            part.name,
            description,
            [(part.name, part.mesh, (0.0, 0.0, 0.0))],
        )
    catalog_name = "MODEL_ONLY_STORY_CORNER_MINI_PARTS_CATALOG.3mf"
    full_name = "MODEL_ONLY_STORY_CORNER_MINI_FULL_PRINT_SET.3mf"
    master_objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]] = []
    y_cursor = 0.0
    for part in parts:
        master_objects.append((part.name, part.mesh, (0.0, y_cursor, 0.0)))
        y_cursor += float(part.mesh.extents[1]) + 15.0
    gen.write_model_3mf(
        model_dir / catalog_name,
        f"{project_name} — {edition} PETG parts catalog",
        description,
        master_objects,
    )
    full_objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]] = []
    x_cursor = 0.0
    y_cursor = 0.0
    row_height = 0.0
    catalog_width = 750.0
    for part in parts:
        size = np.asarray(part.mesh.extents)
        for index in range(part.repeat_count):
            if x_cursor and x_cursor + float(size[0]) > catalog_width:
                x_cursor = 0.0
                y_cursor += row_height + 15.0
                row_height = 0.0
            full_objects.append((f"{part.name}_{index + 1:02d}", part.mesh, (x_cursor, y_cursor, 0.0)))
            x_cursor += float(size[0]) + 15.0
            row_height = max(row_height, float(size[1]))
    gen.write_model_3mf(
        model_dir / full_name,
        f"{project_name} — {edition} full PETG print set",
        description + " Exact repeat quantities on a virtual catalog canvas.",
        full_objects,
    )


def compare_to_r12_mass(mini_g: float) -> dict:
    r12_path = ROOT / "generated" / "validation.json"
    if not r12_path.exists():
        return {"r12_packaged_kg": None, "mini_packaged_kg": mini_g, "note": "R12 validation.json missing"}
    r12 = json.loads(r12_path.read_text(encoding="utf-8"))
    r12_kg = float(r12.get("estimated_packaged_petg_mass_kg", 0.0))
    return {
        "r12_packaged_kg_source": "generated/validation.json estimated_packaged_petg_mass_kg",
        "r12_packaged_kg": r12_kg,
        "mini_packaged_kg_source": "generated/mini/validation.json geometry volume x petg_density",
        "mini_packaged_kg": round(mini_g, 3),
        "mini_to_r12_mass_ratio": round(mini_g / r12_kg, 4) if r12_kg > 0 else None,
        "print_time_estimate": "unverified — repository provides no slicer time metadata for mini or R12",
    }


def main() -> None:
    cfg = load_mini_config()
    out_dir = ROOT / cfg["output"]["directory"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(out_dir.glob("*.stl")):
        path.unlink()
    mini_3mf = out_dir / "model_only_3mf"
    if mini_3mf.exists():
        for path in sorted(mini_3mf.glob("*.3mf")):
            path.unlink()

    layout = deck_dimensions(cfg)
    center_w = layout["center_module_width_mm"]
    end_w = layout["parametric_end_module_width_mm"]
    depth = layout["module_depth_mm"]
    center_cols = layout["center_columns"]
    rows = layout["rows"]

    center_count = center_cols * rows
    end_count = 2 * rows

    parts: list[gen.Part] = [
        gen.Part(
            "MINI_PETG_StudBracket",
            stud_bracket(cfg),
            "mini_single_bay",
            2,
            "printed wall strap and shelf arm for one verified stud; two 7 mm through-bores per bracket; not a rated substitute for steel hardware",
        ),
        gen.Part(
            "MINI_PETG_DeckTile_Center",
            deck_tile(cfg, center_w, depth, interlock="center"),
            "mini_single_bay",
            center_count,
            "interlocking deck tile; tongue engages the next tile along the wall axis",
        ),
        gen.Part(
            "MINI_PETG_DeckTile_End_Left",
            deck_tile(cfg, end_w, depth, interlock="end_left"),
            "mini_single_bay",
            rows,
            "wall-adjacent deck end; single outward tongue",
        ),
        gen.Part(
            "MINI_PETG_DeckTile_End_Right",
            deck_tile(cfg, end_w, depth, interlock="end_right"),
            "mini_single_bay",
            rows,
            "outer deck end; groove receives center or neighbor tile",
        ),
    ]

    build = effective_build_envelope_mm(cfg)
    validation = []
    for part in parts:
        validation.append(validate_mini_part(part, cfg, build))
        save_mini_stl(part, out_dir)

    write_mini_3mfs(parts, cfg, out_dir)

    packaged_g = sum(entry["estimated_petg_g_each"] * entry["repeat_count"] for entry in validation)
    stud_centers = cfg["closet"]["stud_centers_from_inside_corner_in"]
    report = {
        "profile": cfg["profile"],
        "project": cfg["project"],
        "printer": {
            **cfg["printer"],
            "effective_build_envelope_mm": build.tolist(),
        },
        "closet": cfg["closet"],
        "structural_mini": cfg["structural_mini"],
        "deck_layout": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in layout.items()},
        "part_count_unique": len(parts),
        "part_count_total": sum(p.repeat_count for p in parts),
        "meshes": validation,
        "estimated_packaged_petg_mass_kg": round(packaged_g / 1000.0, 3),
        "mass_estimate_note": "Geometry volume times petg_density_g_cm3; excludes purge, supports, failures, spares, and fasteners.",
        "comparison_to_r12": compare_to_r12_mass(packaged_g / 1000.0),
        "stud_mounting": {
            "stud_center_stations_in": stud_centers,
            "bracket_quantity": 2,
            "fastener_candidate": cfg["structural_mini"]["fastener_candidate_product"],
        },
        "load_boundary": (
            "Untested all-PETG development shelf. Not covered by R12 hybrid safety claims. "
            "Zero lb rated load; 15 lb contents figure is a design-selection hint only."
        ),
    }
    (out_dir / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mini_packaged_kg": report["estimated_packaged_petg_mass_kg"], "parts": report["part_count_total"]}, indent=2))


if __name__ == "__main__":
    main()
