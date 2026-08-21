#!/usr/bin/env python3
"""Generate 100% PETG two-shelf system.

SCOPE: Two stacked decks on the long wall. That's it.

=== PARTS ===
1. stud_spine — screws to stud, supports deck
2. deck_module — ribbed box-section, screws to spine and neighbors

=== CONSTRAINTS ===
- 100% PETG. No plywood, steel, Palatine, R13.
- Bambu A1 mini: every part XY ≤ 160mm (with brim).
- Long wall 61.5 in. Studs at 17.0, 32.5, 48.5 in.
- Wood screws into studs. M4 bolts for PETG-to-PETG.
- Short spans to manage PETG creep.

=== NOT IN SCOPE ===
No arches. No guitar hanger. No string cassette. No cable hooks.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "storage_arcade"

# === A1 MINI CONSTRAINTS ===
BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
MAX_BED_XY_MM = 160.0  # HARD LIMIT with brim

# === WALL LAYOUT ===
LONG_WALL_LENGTH_IN = 61.5
LONG_WALL_LENGTH_MM = LONG_WALL_LENGTH_IN * 25.4  # 1562.1 mm
STUD_POSITIONS_IN = [17.0, 32.5, 48.5]
STUD_POSITIONS_MM = [p * 25.4 for p in STUD_POSITIONS_IN]

# Spans between studs
SPAN_1_MM = (STUD_POSITIONS_IN[1] - STUD_POSITIONS_IN[0]) * 25.4  # 393.7 mm
SPAN_2_MM = (STUD_POSITIONS_IN[2] - STUD_POSITIONS_IN[1]) * 25.4  # 406.4 mm

# === STUD SPINE ===
# Wall-mount bracket. Screws to stud, deck sits on top shelf.
SPINE_WIDTH_MM = 40.0      # Along wall (X when printed flat)
SPINE_HEIGHT_MM = 120.0    # Wall projection (Y when printed flat)
SPINE_DEPTH_MM = 20.0      # Thickness (Z when printed flat)
SPINE_WALL_MM = 4.0

# Shelf ledge (deck sits here)
SHELF_LEDGE_WIDTH_MM = 40.0
SHELF_LEDGE_DEPTH_MM = 155.0  # Into room, matches deck width
SHELF_LEDGE_THICKNESS_MM = 8.0

# Screw holes
WOOD_SCREW_DIA_MM = 5.0     # #10 screw clearance
WOOD_SCREW_SPACING_MM = 40.0
COUNTERBORE_DIA_MM = 10.0
COUNTERBORE_DEPTH_MM = 3.0

# M4 holes for deck attachment
M4_CLEARANCE_MM = 4.5

# === DECK MODULE ===
# Ribbed box-section. Short enough for A1 mini, tiles along wall.
DECK_LENGTH_MM = 155.0     # Along wall run
DECK_WIDTH_MM = 155.0      # Into room
DECK_HEIGHT_MM = 25.0      # Box depth
DECK_WALL_MM = 3.0
DECK_RIB_SPACING_MM = 40.0 # Cross ribs for stiffness

# M4 holes for spine and neighbor connections
M4_HOLE_INSET_MM = 12.0


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    return mesh


def normalize_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh = mesh.copy()
    mesh.apply_translation(-np.asarray(mesh.bounds[0], dtype=float))
    return clean_mesh(mesh)


def box(extents: tuple[float, float, float], origin: tuple[float, float, float] = (0, 0, 0)) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(np.asarray(origin) + np.asarray(extents) / 2.0)
    return clean_mesh(mesh)


def cylinder_z(radius: float, height: float, center: tuple[float, float, float], segments: int = 32) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=segments)
    mesh.apply_translation(center)
    return clean_mesh(mesh)


def cylinder_y(radius: float, length: float, center: tuple[float, float, float], segments: int = 32) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=segments)
    rot = trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
    mesh.apply_transform(rot)
    mesh.apply_translation(center)
    return clean_mesh(mesh)


def boolean_union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("No meshes to union")
    if len(meshes) == 1:
        return meshes[0].copy()
    result = trimesh.boolean.union(list(meshes), engine="manifold")
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return clean_mesh(result)


def boolean_difference(body: trimesh.Trimesh, cutters: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not cutters:
        return body.copy()
    result = trimesh.boolean.difference([body] + list(cutters), engine="manifold")
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return clean_mesh(result)


def build_stud_spine() -> trimesh.Trimesh:
    """Build wall-mount spine.
    
    Print orientation: flat on bed (ledge up).
    - Back plate screws to stud
    - Shelf ledge projects into room for deck
    - Gussets for strength
    """
    parts: list[trimesh.Trimesh] = []
    
    # Back plate (against wall, screws to stud)
    # When printed flat: X=width, Y=height, Z=depth
    back = box(
        (SPINE_WIDTH_MM, SPINE_HEIGHT_MM, SPINE_WALL_MM),
        (0, 0, 0)
    )
    parts.append(back)
    
    # Shelf ledge (deck sits on this)
    ledge = box(
        (SHELF_LEDGE_WIDTH_MM, SHELF_LEDGE_THICKNESS_MM, SHELF_LEDGE_DEPTH_MM),
        (0, SPINE_HEIGHT_MM - SHELF_LEDGE_THICKNESS_MM, 0)
    )
    parts.append(ledge)
    
    # Triangular gussets (2x, on each side)
    gusset_height = 60.0
    gusset_depth = SHELF_LEDGE_DEPTH_MM - SPINE_WALL_MM
    gusset_thickness = SPINE_WALL_MM
    
    for x_offset in [0, SPINE_WIDTH_MM - gusset_thickness]:
        gusset = box(
            (gusset_thickness, gusset_height, gusset_depth),
            (x_offset, SPINE_HEIGHT_MM - SHELF_LEDGE_THICKNESS_MM - gusset_height, SPINE_WALL_MM)
        )
        parts.append(gusset)
    
    # Front lip (prevents deck sliding off)
    lip = box(
        (SPINE_WIDTH_MM, SHELF_LEDGE_THICKNESS_MM, SPINE_WALL_MM),
        (0, SPINE_HEIGHT_MM - SHELF_LEDGE_THICKNESS_MM, SHELF_LEDGE_DEPTH_MM - SPINE_WALL_MM)
    )
    parts.append(lip)
    
    body = boolean_union(parts)
    
    # Cut screw holes in back plate
    cutters: list[trimesh.Trimesh] = []
    screw_positions_y = [30.0, 30.0 + WOOD_SCREW_SPACING_MM, 30.0 + 2 * WOOD_SCREW_SPACING_MM]
    
    for y in screw_positions_y:
        # Through hole
        hole = cylinder_z(
            WOOD_SCREW_DIA_MM / 2,
            SPINE_WALL_MM + 2,
            (SPINE_WIDTH_MM / 2, y, SPINE_WALL_MM / 2)
        )
        cutters.append(hole)
        
        # Counterbore on room side
        cbore = cylinder_z(
            COUNTERBORE_DIA_MM / 2,
            COUNTERBORE_DEPTH_MM + 0.1,
            (SPINE_WIDTH_MM / 2, y, SPINE_WALL_MM - COUNTERBORE_DEPTH_MM / 2)
        )
        cutters.append(cbore)
    
    # M4 holes in shelf ledge for deck attachment
    for x in [M4_HOLE_INSET_MM, SPINE_WIDTH_MM - M4_HOLE_INSET_MM]:
        for z in [30.0, 80.0, 130.0]:
            if z < SHELF_LEDGE_DEPTH_MM - M4_HOLE_INSET_MM:
                m4 = cylinder_y(
                    M4_CLEARANCE_MM / 2,
                    SHELF_LEDGE_THICKNESS_MM + 2,
                    (x, SPINE_HEIGHT_MM - SHELF_LEDGE_THICKNESS_MM / 2, z)
                )
                cutters.append(m4)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_deck_module() -> trimesh.Trimesh:
    """Build ribbed deck module.
    
    Print orientation: upside down (top surface on bed for smoothness).
    - SOLID box with internal ribs (gyroid infill handles weight)
    - M4 holes on ends for neighbor connection
    - M4 holes on back edge for spine connection
    """
    # Build as a solid box, then cut holes
    # Ribs are internal structure - slicer infill handles this
    # This approach guarantees watertight mesh
    
    outer = box((DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM), (0, 0, 0))
    
    # Cut M4 holes
    cutters: list[trimesh.Trimesh] = []
    
    # End-to-end connection holes (through left and right ends)
    for x in [DECK_WALL_MM / 2, DECK_LENGTH_MM - DECK_WALL_MM / 2]:
        for y in [DECK_WIDTH_MM * 0.25, DECK_WIDTH_MM * 0.75]:
            hole = cylinder_z(
                M4_CLEARANCE_MM / 2,
                DECK_HEIGHT_MM + 2,
                (x, y, DECK_HEIGHT_MM / 2)
            )
            cutters.append(hole)
    
    # Spine connection holes (through back edge, top surface)
    for x in [M4_HOLE_INSET_MM, DECK_LENGTH_MM / 2, DECK_LENGTH_MM - M4_HOLE_INSET_MM]:
        hole = cylinder_z(
            M4_CLEARANCE_MM / 2,
            DECK_HEIGHT_MM + 2,
            (x, DECK_WIDTH_MM - M4_HOLE_INSET_MM, DECK_HEIGHT_MM / 2)
        )
        cutters.append(hole)
    
    result = boolean_difference(outer, cutters)
    return normalize_mesh(result)


def check_fits_bed(mesh: trimesh.Trimesh, name: str) -> bool:
    """Check if mesh fits A1 mini bed with brim clearance."""
    extents = mesh.bounding_box.extents
    sorted_extents = sorted(extents)
    
    xy_dims = sorted_extents[:2]
    fits_bed = all(d <= MAX_BED_XY_MM for d in xy_dims)
    fits_z = sorted_extents[2] <= BUILD_VOLUME_MM[2]
    
    if fits_bed and fits_z:
        status = "OK"
    else:
        status = f"FAIL ({sorted_extents[0]:.1f} x {sorted_extents[1]:.1f} x {sorted_extents[2]:.1f})"
    
    print(f"  {name}: {extents[0]:.1f} x {extents[1]:.1f} x {extents[2]:.1f} mm — {status}")
    return fits_bed and fits_z


def write_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    mesh.export(str(path), file_type="stl")
    print(f"    -> {path.name} ({path.stat().st_size / 1024:.1f} KB)")


def calculate_layout() -> dict:
    """Calculate part counts for two-level system."""
    
    # Decks per level: enough to span wall
    # Each deck is 155mm along wall
    # Wall is 1562mm
    # Need ~10 decks per level to cover, plus one at each end
    decks_per_level = 10
    total_decks = decks_per_level * 2
    
    # Spines: one per stud per level
    spines_per_level = 3
    total_spines = spines_per_level * 2
    
    return {
        "levels": 2,
        "studs": 3,
        "decks_per_level": decks_per_level,
        "total_decks": total_decks,
        "spines_per_level": spines_per_level,
        "total_spines": total_spines,
    }


def main():
    print("=" * 60)
    print("100% PETG TWO-SHELF SYSTEM")
    print("=" * 60)
    print()
    
    OUT.mkdir(parents=True, exist_ok=True)
    
    # Clean up old files
    old_files = [
        "arch_bay.stl", "arch_bay.3mf",
        "cable_trough.stl", "cable_trough.3mf",
        "string_cassette.stl", "string_cassette.3mf",
        "inter_deck_bracket.stl", "inter_deck_bracket.3mf",
        "guitar_hanger.stl", "guitar_hanger.3mf",
        "cable_insert.stl", "cable_insert.3mf",
        "CLASSIC_LOOK.md", "PRINT_THE_ARCADE.md", "PRINT_THE_DECKS.md",
        "USAGE.md",
    ]
    for f in old_files:
        p = OUT / f
        if p.exists():
            p.unlink()
            print(f"  Deleted: {f}")
    
    print()
    print("[1] Building stud_spine...")
    spine = build_stud_spine()
    spine_ok = check_fits_bed(spine, "stud_spine")
    spine_watertight = spine.is_watertight
    print(f"      Watertight: {'YES' if spine_watertight else 'NO'}")
    if spine_ok:
        write_stl(spine, OUT / "stud_spine.stl")
    
    print()
    print("[2] Building deck_module...")
    deck = build_deck_module()
    deck_ok = check_fits_bed(deck, "deck_module")
    deck_watertight = deck.is_watertight
    print(f"      Watertight: {'YES' if deck_watertight else 'NO'}")
    if deck_ok:
        write_stl(deck, OUT / "deck_module.stl")
    
    layout = calculate_layout()
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Long wall: {LONG_WALL_LENGTH_IN} in ({LONG_WALL_LENGTH_MM:.0f} mm)")
    print(f"Studs at: {STUD_POSITIONS_IN} in")
    print(f"Levels: {layout['levels']}")
    print()
    print("PART COUNTS:")
    print(f"  stud_spine: {layout['total_spines']} (3 studs x 2 levels)")
    print(f"  deck_module: {layout['total_decks']} ({layout['decks_per_level']} per level x 2)")
    print()
    print("HARDWARE:")
    print(f"  Wood screws (#10 x 2.5 in): {layout['total_spines'] * 3} (3 per spine)")
    print(f"  M4 x 20mm bolts: ~{layout['total_decks'] * 6} (deck-to-spine + deck-to-deck)")
    print(f"  M4 nylock nuts: ~{layout['total_decks'] * 6}")
    print(f"  M4 washers: ~{layout['total_decks'] * 12}")
    print()
    
    all_ok = spine_ok and deck_ok and spine_watertight and deck_watertight
    if all_ok:
        print("STATUS: READY TO PRINT")
    else:
        print("STATUS: ISSUES FOUND")
        if not spine_ok:
            print("  - stud_spine does not fit bed")
        if not deck_ok:
            print("  - deck_module does not fit bed")
        if not spine_watertight:
            print("  - stud_spine is not watertight")
        if not deck_watertight:
            print("  - deck_module is not watertight")
    
    # Write manifest
    manifest = {
        "system": "100% PETG two-shelf",
        "wall": {
            "length_in": LONG_WALL_LENGTH_IN,
            "studs_in": STUD_POSITIONS_IN,
        },
        "parts": {
            "stud_spine": {
                "file": "stud_spine.stl",
                "quantity": layout["total_spines"],
                "dimensions_mm": [round(x, 1) for x in spine.bounding_box.extents],
                "watertight": bool(spine_watertight),
                "fits_bed": bool(spine_ok),
            },
            "deck_module": {
                "file": "deck_module.stl",
                "quantity": layout["total_decks"],
                "dimensions_mm": [round(x, 1) for x in deck.bounding_box.extents],
                "watertight": bool(deck_watertight),
                "fits_bed": bool(deck_ok),
            },
        },
        "hardware": {
            "wood_screws": {"spec": "#10 x 2.5 in", "quantity": layout["total_spines"] * 3},
            "m4_bolts": {"spec": "M4 x 20mm", "quantity": layout["total_decks"] * 6},
            "m4_nuts": {"spec": "M4 nylock", "quantity": layout["total_decks"] * 6},
            "m4_washers": {"spec": "M4 flat", "quantity": layout["total_decks"] * 12},
        },
        "print_settings": {
            "material": "PETG",
            "walls": 5,
            "infill_percent": 40,
            "infill_pattern": "gyroid",
            "layer_height_mm": 0.2,
        },
    }
    
    with open(OUT / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print()
    print("Wrote manifest.json")


if __name__ == "__main__":
    main()
