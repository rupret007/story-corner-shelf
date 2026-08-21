#!/usr/bin/env python3
"""Generate 100% PETG two-deck storage system.

Every gram printed stores something or carries load. No decorative elements.

=== ARCHITECTURE ===
- TWO stacked PETG decks on the 61.5 in long wall, above the electric box
- Stud spines at 17.0 / 32.5 / 48.5 in are the ONLY wall-load parts
- Storage is functional attachments between the two decks:
  - Cable trough (hooks + channel)
  - String cassette / drawer
  - Guitar neck hanger (bolts to spine, guitar hangs in room)

=== WHY NO ARCHES ===
Arches were removed because they are not in the load path.
Spines carry the load directly to studs. Arches would be decorative mass.
Every gram printed must store something or carry load.

=== CONSTRAINTS ===
- 100% PETG. No plywood, steel angle, KV, Palatine, R13 tubes.
- Bambu A1 mini 180mm, 0.4mm nozzle. Every part: XY ≤160mm with brim.
- Long wall 61.5 in. Studs at 17.0, 32.5, 48.5 in from inside corner.
- Mechanical screws (wood into studs, M4 through PETG). No snap-fit load path.
- Short wall (~36 in) ON HOLD until measured.

=== HEIGHT ASSUMPTION (UNVERIFIED) ===
- Outlet-top to ceiling: 43.5 in (user-reported, NOT field-verified)
- Measure before cutting/printing final spine lengths
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "storage_arcade"

# A1 mini build constraints
BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
MAX_BED_XY_MM = 160.0  # HARD LIMIT with 3mm brim + calibration region

# === HEIGHT ASSUMPTIONS (UNVERIFIED) ===
OUTLET_TO_CEILING_IN = 43.5  # USER-REPORTED, NOT FIELD-VERIFIED
OUTLET_TO_CEILING_MM = OUTLET_TO_CEILING_IN * 25.4  # 1104.9 mm

# Design clearances
CEILING_CLEARANCE_MM = 25.0
OUTLET_CLEARANCE_MM = 50.0
INTER_DECK_GAP_MM = 200.0  # Space between decks for attachments

# === WALL LAYOUT ===
LONG_WALL_LENGTH_IN = 61.5
STUD_POSITIONS_IN = [17.0, 32.5, 48.5]
STUD_SPACING_MM = [
    (STUD_POSITIONS_IN[1] - STUD_POSITIONS_IN[0]) * 25.4,  # 393.7 mm
    (STUD_POSITIONS_IN[2] - STUD_POSITIONS_IN[1]) * 25.4,  # 406.4 mm
]

SHORT_WALL_LENGTH_IN = 36.0  # Nominal, NEEDS MEASUREMENT
SHORT_WALL_ON_HOLD = True

# === STUD SPINE ===
# The ONLY wall-load part. Everything hangs from spines.
SPINE_WIDTH_MM = 40.0   # Along wall run
SPINE_HEIGHT_MM = 158.0 # Printable height (fits A1 mini)
SPINE_DEPTH_MM = 25.0   # Wall projection (enough for M4 grid)
SPINE_WALL_MM = 5.0

# Crown extends out to support deck
SPINE_CROWN_HEIGHT_MM = 30.0
SPINE_CROWN_DEPTH_MM = 160.0  # Full deck depth support

# Screw holes (3 per spine section)
WOOD_SCREW_DIAMETER_MM = 5.5
WOOD_SCREW_POSITIONS_Z_MM = [25.0, 79.0, 133.0]
COUNTERBORE_DIAMETER_MM = 12.0
COUNTERBORE_DEPTH_MM = 4.0

# M4 grid
M4_CLEARANCE_MM = 4.5
M4_GRID_Y_MM = [20.0, 60.0, 100.0, 140.0]  # 4 positions across crown depth
M4_GRID_X_MM = [10.0, 30.0]  # 2 positions across width

# === DECK MODULE ===
DECK_LENGTH_MM = 158.0  # Along wall run
DECK_WIDTH_MM = 155.0   # Depth into room
DECK_HEIGHT_MM = 30.0   # Box section depth
DECK_WALL_MM = 4.0
DECK_RIB_COUNT = 3

# === CABLE TROUGH ===
# Mounts between decks, provides cable organization
TROUGH_LENGTH_MM = 155.0  # Spans between spines
TROUGH_WIDTH_MM = 60.0    # Depth
TROUGH_HEIGHT_MM = 50.0   # Height
TROUGH_WALL_MM = 3.0
HOOK_COUNT = 4
HOOK_HEIGHT_MM = 30.0
HOOK_DEPTH_MM = 15.0

# === STRING CASSETTE ===
# Drawer-style insert for guitar strings, picks, etc.
CASSETTE_LENGTH_MM = 100.0
CASSETTE_WIDTH_MM = 80.0
CASSETTE_HEIGHT_MM = 60.0
CASSETTE_WALL_MM = 2.5

# === INTER-DECK BRACKET ===
# Connects upper and lower deck, provides attachment points
BRACKET_WIDTH_MM = 40.0   # Same as spine width
BRACKET_DEPTH_MM = 155.0  # Full deck depth
BRACKET_HEIGHT_MM = 158.0 # Fills inter-deck gap (printable)
BRACKET_WALL_MM = 4.0

# === GUITAR HANGER ===
GUITAR_HANGER_WIDTH_MM = 60.0
GUITAR_HANGER_DEPTH_MM = 100.0
GUITAR_HANGER_HEIGHT_MM = 30.0
GUITAR_NECK_SLOT_WIDTH_MM = 48.0
GUITAR_NECK_SLOT_DEPTH_MM = 25.0


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


def cylinder_x(radius: float, length: float, center: tuple[float, float, float], segments: int = 32) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=segments)
    rot = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])
    mesh.apply_transform(rot)
    mesh.apply_translation(center)
    return clean_mesh(mesh)


def boolean_union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("No meshes to union")
    if len(meshes) == 1:
        return meshes[0].copy()
    result = trimesh.boolean.union(list(meshes), engine="manifold")
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return clean_mesh(result)


def boolean_difference(body: trimesh.Trimesh, cutters: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not cutters:
        return body.copy()
    result = trimesh.boolean.difference([body] + list(cutters), engine="manifold")
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return clean_mesh(result)


def build_stud_spine() -> trimesh.Trimesh:
    """Build the wall-mount spine - the ONLY wall-load part.
    
    Screws to stud. Crown projects out to support deck.
    M4 grid on crown for deck and attachment mounting.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Main backplate (screws to stud)
    backplate = box(
        (SPINE_WALL_MM, SPINE_WIDTH_MM, SPINE_HEIGHT_MM),
        (0, 0, 0)
    )
    parts.append(backplate)
    
    # Ribs from wall to crown (triangular support)
    for y in [5.0, SPINE_WIDTH_MM - 10.0]:
        rib = box(
            (SPINE_DEPTH_MM, SPINE_WALL_MM, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM),
            (0, y, 0)
        )
        parts.append(rib)
    
    # Crown (supports deck) - solid block with M4 grid
    crown = box(
        (SPINE_CROWN_DEPTH_MM, SPINE_WIDTH_MM, SPINE_CROWN_HEIGHT_MM),
        (0, 0, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM)
    )
    parts.append(crown)
    
    # Triangular gussets under crown for strength
    gusset_height = 40.0
    gusset_depth = SPINE_CROWN_DEPTH_MM - SPINE_DEPTH_MM
    for y in [SPINE_WALL_MM, SPINE_WIDTH_MM - SPINE_WALL_MM * 2]:
        gusset = box(
            (gusset_depth, SPINE_WALL_MM, gusset_height),
            (SPINE_DEPTH_MM, y, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM - gusset_height)
        )
        parts.append(gusset)
    
    body = boolean_union(parts)
    
    # Cut screw holes for wood screws
    cutters: list[trimesh.Trimesh] = []
    for z in WOOD_SCREW_POSITIONS_Z_MM:
        hole = cylinder_y(
            WOOD_SCREW_DIAMETER_MM / 2,
            SPINE_WALL_MM + 2,
            (SPINE_WALL_MM / 2, SPINE_WIDTH_MM / 2, z)
        )
        cutters.append(hole)
        cbore = cylinder_y(
            COUNTERBORE_DIAMETER_MM / 2,
            COUNTERBORE_DEPTH_MM + 0.1,
            (SPINE_DEPTH_MM - COUNTERBORE_DEPTH_MM / 2, SPINE_WIDTH_MM / 2, z)
        )
        cutters.append(cbore)
    
    # M4 holes in crown for deck mounting
    for x in M4_GRID_Y_MM:  # These run along crown depth
        for y in M4_GRID_X_MM:  # These run along spine width
            m4_hole = cylinder_z(
                M4_CLEARANCE_MM / 2,
                SPINE_CROWN_HEIGHT_MM + 2,
                (x, y, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM / 2)
            )
            cutters.append(m4_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_deck_module() -> trimesh.Trimesh:
    """Build a ribbed deck module - sits on spine crowns.
    
    Box-beam construction. M4 holes for mounting to spines.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Top surface
    top = box((DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM), (0, 0, DECK_HEIGHT_MM - DECK_WALL_MM))
    parts.append(top)
    
    # Bottom surface
    bottom = box((DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM), (0, 0, 0))
    parts.append(bottom)
    
    # Front wall
    front = box((DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM), (0, 0, 0))
    parts.append(front)
    
    # Back wall
    back = box((DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM), (0, DECK_WIDTH_MM - DECK_WALL_MM, 0))
    parts.append(back)
    
    # End walls
    left_end = box((DECK_WALL_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM), (0, 0, 0))
    parts.append(left_end)
    right_end = box((DECK_WALL_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM), (DECK_LENGTH_MM - DECK_WALL_MM, 0, 0))
    parts.append(right_end)
    
    # Cross ribs
    rib_spacing = (DECK_LENGTH_MM - 2 * DECK_WALL_MM) / (DECK_RIB_COUNT + 1)
    for i in range(1, DECK_RIB_COUNT + 1):
        x_pos = DECK_WALL_MM + i * rib_spacing - DECK_WALL_MM / 2
        rib = box(
            (DECK_WALL_MM, DECK_WIDTH_MM - 2 * DECK_WALL_MM, DECK_HEIGHT_MM - 2 * DECK_WALL_MM),
            (x_pos, DECK_WALL_MM, DECK_WALL_MM)
        )
        parts.append(rib)
    
    # Longitudinal rib
    long_rib = box(
        (DECK_LENGTH_MM - 2 * DECK_WALL_MM, DECK_WALL_MM, DECK_HEIGHT_MM - 2 * DECK_WALL_MM),
        (DECK_WALL_MM, DECK_WIDTH_MM / 2 - DECK_WALL_MM / 2, DECK_WALL_MM)
    )
    parts.append(long_rib)
    
    body = boolean_union(parts)
    
    # M4 holes for mounting
    cutters: list[trimesh.Trimesh] = []
    for x_pos in [15.0, DECK_LENGTH_MM - 15.0]:
        for y_pos in [20.0, 60.0, 100.0, 140.0]:
            m4_hole = cylinder_z(
                M4_CLEARANCE_MM / 2,
                DECK_HEIGHT_MM + 2,
                (x_pos, y_pos, DECK_HEIGHT_MM / 2)
            )
            cutters.append(m4_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_cable_trough() -> trimesh.Trimesh:
    """Build a cable trough with integrated hooks.
    
    Mounts between spines in the inter-deck space.
    Hooks hold cables, trough catches loose ends.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Main trough body (U-channel)
    # Bottom
    bottom = box((TROUGH_LENGTH_MM, TROUGH_WIDTH_MM, TROUGH_WALL_MM), (0, 0, 0))
    parts.append(bottom)
    
    # Front wall
    front = box((TROUGH_LENGTH_MM, TROUGH_WALL_MM, TROUGH_HEIGHT_MM), (0, 0, 0))
    parts.append(front)
    
    # Back wall (shorter to allow cable draping)
    back = box((TROUGH_LENGTH_MM, TROUGH_WALL_MM, TROUGH_HEIGHT_MM * 0.6), (0, TROUGH_WIDTH_MM - TROUGH_WALL_MM, 0))
    parts.append(back)
    
    # End walls
    left = box((TROUGH_WALL_MM, TROUGH_WIDTH_MM, TROUGH_HEIGHT_MM), (0, 0, 0))
    parts.append(left)
    right = box((TROUGH_WALL_MM, TROUGH_WIDTH_MM, TROUGH_HEIGHT_MM), (TROUGH_LENGTH_MM - TROUGH_WALL_MM, 0, 0))
    parts.append(right)
    
    # Cable hooks along front edge
    hook_spacing = (TROUGH_LENGTH_MM - 2 * TROUGH_WALL_MM) / (HOOK_COUNT + 1)
    for i in range(1, HOOK_COUNT + 1):
        x_pos = TROUGH_WALL_MM + i * hook_spacing
        
        # Vertical post
        post = box(
            (8.0, 8.0, HOOK_HEIGHT_MM),
            (x_pos - 4.0, -4.0, TROUGH_HEIGHT_MM)
        )
        parts.append(post)
        
        # Hook arm
        arm = box(
            (8.0, HOOK_DEPTH_MM, 6.0),
            (x_pos - 4.0, -4.0, TROUGH_HEIGHT_MM + HOOK_HEIGHT_MM - 6.0)
        )
        parts.append(arm)
        
        # Hook lip (prevents cable sliding off)
        lip = box(
            (8.0, 6.0, 12.0),
            (x_pos - 4.0, HOOK_DEPTH_MM - 10.0, TROUGH_HEIGHT_MM + HOOK_HEIGHT_MM - 18.0)
        )
        parts.append(lip)
    
    body = boolean_union(parts)
    
    # M4 mounting holes in end walls
    cutters: list[trimesh.Trimesh] = []
    for x_pos in [TROUGH_WALL_MM / 2, TROUGH_LENGTH_MM - TROUGH_WALL_MM / 2]:
        for z_pos in [15.0, TROUGH_HEIGHT_MM - 10.0]:
            hole = cylinder_x(
                M4_CLEARANCE_MM / 2,
                TROUGH_WALL_MM + 2,
                (x_pos, TROUGH_WIDTH_MM / 2, z_pos)
            )
            cutters.append(hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_string_cassette() -> trimesh.Trimesh:
    """Build a drawer-style cassette for guitar strings, picks, etc.
    
    Open top for easy access. Dividers for organization.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Outer shell
    outer = box((CASSETTE_LENGTH_MM, CASSETTE_WIDTH_MM, CASSETTE_HEIGHT_MM), (0, 0, 0))
    parts.append(outer)
    
    # Inner cavity (open top)
    inner = box(
        (CASSETTE_LENGTH_MM - 2 * CASSETTE_WALL_MM, 
         CASSETTE_WIDTH_MM - 2 * CASSETTE_WALL_MM, 
         CASSETTE_HEIGHT_MM - CASSETTE_WALL_MM + 1),  # +1 to open top
        (CASSETTE_WALL_MM, CASSETTE_WALL_MM, CASSETTE_WALL_MM)
    )
    
    # Center divider (lengthwise)
    divider_l = box(
        (CASSETTE_LENGTH_MM - 2 * CASSETTE_WALL_MM, CASSETTE_WALL_MM, CASSETTE_HEIGHT_MM - CASSETTE_WALL_MM - 10),
        (CASSETTE_WALL_MM, CASSETTE_WIDTH_MM / 2 - CASSETTE_WALL_MM / 2, CASSETTE_WALL_MM)
    )
    parts.append(divider_l)
    
    # Cross divider
    divider_c = box(
        (CASSETTE_WALL_MM, CASSETTE_WIDTH_MM - 2 * CASSETTE_WALL_MM, CASSETTE_HEIGHT_MM - CASSETTE_WALL_MM - 10),
        (CASSETTE_LENGTH_MM / 2 - CASSETTE_WALL_MM / 2, CASSETTE_WALL_MM, CASSETTE_WALL_MM)
    )
    parts.append(divider_c)
    
    # Handle cutout on front
    handle = box(
        (40.0, CASSETTE_WALL_MM + 2, 15.0),
        (CASSETTE_LENGTH_MM / 2 - 20.0, -1, CASSETTE_HEIGHT_MM - 25.0)
    )
    
    body = boolean_union(parts)
    result = boolean_difference(body, [inner, handle])
    return normalize_mesh(result)


def build_inter_deck_bracket() -> trimesh.Trimesh:
    """Build a bracket that connects upper and lower decks.
    
    Provides attachment points for cable troughs, cassettes, etc.
    Adds rigidity to the two-deck system.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Main vertical panel
    panel = box(
        (BRACKET_WALL_MM, BRACKET_DEPTH_MM, BRACKET_HEIGHT_MM),
        (0, 0, 0)
    )
    parts.append(panel)
    
    # Top flange (connects to upper deck)
    top_flange = box(
        (BRACKET_WIDTH_MM, BRACKET_DEPTH_MM, BRACKET_WALL_MM),
        (0, 0, BRACKET_HEIGHT_MM - BRACKET_WALL_MM)
    )
    parts.append(top_flange)
    
    # Bottom flange (connects to lower deck)
    bottom_flange = box(
        (BRACKET_WIDTH_MM, BRACKET_DEPTH_MM, BRACKET_WALL_MM),
        (0, 0, 0)
    )
    parts.append(bottom_flange)
    
    # Stiffening ribs
    rib_spacing = BRACKET_DEPTH_MM / 4
    for i in range(1, 4):
        y_pos = i * rib_spacing
        rib = box(
            (BRACKET_WIDTH_MM - BRACKET_WALL_MM, BRACKET_WALL_MM, BRACKET_HEIGHT_MM - 2 * BRACKET_WALL_MM),
            (BRACKET_WALL_MM, y_pos - BRACKET_WALL_MM / 2, BRACKET_WALL_MM)
        )
        parts.append(rib)
    
    body = boolean_union(parts)
    
    # M4 holes in flanges
    cutters: list[trimesh.Trimesh] = []
    for y_pos in [30.0, 80.0, 130.0]:
        for z_pos in [BRACKET_WALL_MM / 2, BRACKET_HEIGHT_MM - BRACKET_WALL_MM / 2]:
            for x_pos in [10.0, 30.0]:
                hole = cylinder_z(
                    M4_CLEARANCE_MM / 2,
                    BRACKET_WALL_MM + 2,
                    (x_pos, y_pos, z_pos)
                )
                cutters.append(hole)
    
    # M4 holes in main panel for attachments
    for y_pos in [40.0, 80.0, 120.0]:
        for z_pos in [40.0, 80.0, 120.0]:
            hole = cylinder_x(
                M4_CLEARANCE_MM / 2,
                BRACKET_WALL_MM + 2,
                (BRACKET_WALL_MM / 2, y_pos, z_pos)
            )
            cutters.append(hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_guitar_hanger() -> trimesh.Trimesh:
    """Build a guitar neck hanger - bolts to spine.
    
    Guitar hangs in the ROOM (body in free space, not on deck).
    """
    parts: list[trimesh.Trimesh] = []
    
    # Main body
    main = box((GUITAR_HANGER_WIDTH_MM, GUITAR_HANGER_DEPTH_MM, GUITAR_HANGER_HEIGHT_MM), (0, 0, 0))
    parts.append(main)
    
    # Mounting plate (thicker at wall)
    mount_plate = box((GUITAR_HANGER_WIDTH_MM, 25.0, GUITAR_HANGER_HEIGHT_MM + 15.0), (0, GUITAR_HANGER_DEPTH_MM - 25.0, 0))
    parts.append(mount_plate)
    
    # Support arms
    arm_width = (GUITAR_HANGER_WIDTH_MM - GUITAR_NECK_SLOT_WIDTH_MM) / 2
    arm_height = 30.0
    
    left_arm = box((arm_width, GUITAR_HANGER_DEPTH_MM - 25.0, arm_height), (0, 0, GUITAR_HANGER_HEIGHT_MM))
    parts.append(left_arm)
    
    right_arm = box((arm_width, GUITAR_HANGER_DEPTH_MM - 25.0, arm_height), (GUITAR_HANGER_WIDTH_MM - arm_width, 0, GUITAR_HANGER_HEIGHT_MM))
    parts.append(right_arm)
    
    body = boolean_union(parts)
    
    # Cut neck slot
    cutters: list[trimesh.Trimesh] = []
    neck_slot = box(
        (GUITAR_NECK_SLOT_WIDTH_MM, GUITAR_NECK_SLOT_DEPTH_MM + 1, GUITAR_HANGER_HEIGHT_MM + arm_height + 2),
        ((GUITAR_HANGER_WIDTH_MM - GUITAR_NECK_SLOT_WIDTH_MM) / 2, -1, -1)
    )
    cutters.append(neck_slot)
    
    # M4 mounting holes
    for z_offset in [12.0, GUITAR_HANGER_HEIGHT_MM + 5.0]:
        for x_offset in [15.0, GUITAR_HANGER_WIDTH_MM - 15.0]:
            hole = cylinder_y(
                M4_CLEARANCE_MM / 2,
                30.0,
                (x_offset, GUITAR_HANGER_DEPTH_MM - 12.0, z_offset)
            )
            cutters.append(hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def check_fits_bed(mesh: trimesh.Trimesh, name: str) -> bool:
    """Check if mesh fits A1 mini bed with brim clearance."""
    extents = mesh.bounding_box.extents
    sorted_extents = sorted(extents)
    
    xy_dims = sorted_extents[:2]
    fits_bed = all(d <= MAX_BED_XY_MM for d in xy_dims)
    fits_z = sorted_extents[2] <= BUILD_VOLUME_MM[2]
    
    if fits_bed and fits_z:
        status = "✓ fits A1 mini"
    else:
        status = f"✗ FAILS ({sorted_extents[0]:.1f}×{sorted_extents[1]:.1f}×{sorted_extents[2]:.1f})"
    
    print(f"  {name}: {extents[0]:.1f} × {extents[1]:.1f} × {extents[2]:.1f} mm {status}")
    return fits_bed and fits_z


def write_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    mesh.export(str(path), file_type="stl")
    print(f"    → {path.name} ({path.stat().st_size / 1024:.1f} KB)")


def write_3mf(mesh: trimesh.Trimesh, path: Path, name: str) -> None:
    try:
        scene = trimesh.Scene()
        scene.add_geometry(mesh, node_name=name)
        scene.export(str(path), file_type="3mf")
        print(f"    → {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"    (3MF skipped: {e})")


def calculate_layout() -> dict:
    """Calculate two-deck layout for long wall."""
    
    # Deck count per level
    total_span_mm = LONG_WALL_LENGTH_IN * 25.4  # 1562.1 mm
    deck_per_level = int(total_span_mm / DECK_LENGTH_MM) + 1  # ~10 decks
    total_deck = deck_per_level * 2  # Two levels
    
    # Spine count: 3 studs × 2 levels = 6 spine sections
    spine_sections = 3 * 2
    
    # Inter-deck brackets: between spines
    bracket_count = 2 * 2  # 2 per span × 2 spans = 4 brackets per level, but shared
    
    return {
        "levels": 2,
        "stud_count": 3,
        "stud_positions_in": STUD_POSITIONS_IN,
        "deck_per_level": deck_per_level,
        "total_deck": total_deck,
        "spine_sections": spine_sections,
        "bracket_count": bracket_count,
        "inter_deck_gap_mm": INTER_DECK_GAP_MM,
    }


def main():
    print("=" * 70)
    print("100% PETG TWO-DECK STORAGE SYSTEM")
    print("Every gram stores or carries. No arches. No decoration.")
    print("=" * 70)
    print()
    print("WHY NO ARCHES:")
    print("  Arches were removed because they are not in the load path.")
    print("  Spines carry the load directly to studs.")
    print("  Arches would be decorative mass. Every gram must work.")
    print()
    print("HEIGHT ASSUMPTION (UNVERIFIED):")
    print(f"  Outlet-top to ceiling: {OUTLET_TO_CEILING_IN} in ({OUTLET_TO_CEILING_MM:.1f} mm)")
    print("  THIS IS USER-REPORTED, NOT FIELD-VERIFIED.")
    print()
    
    OUT.mkdir(parents=True, exist_ok=True)
    
    # Delete old arch files if they exist
    old_files = ["arch_bay.stl", "arch_bay.3mf"]
    for f in old_files:
        old_path = OUT / f
        if old_path.exists():
            old_path.unlink()
            print(f"  Deleted old file: {f}")
    
    print("[1] Generating stud spine (print 6 for two levels)...")
    spine = build_stud_spine()
    spine_ok = check_fits_bed(spine, "stud_spine")
    if spine_ok:
        write_stl(spine, OUT / "stud_spine.stl")
        write_3mf(spine, OUT / "stud_spine.3mf", "stud_spine")
    
    print("\n[2] Generating deck module (print ~20 for two levels)...")
    deck = build_deck_module()
    deck_ok = check_fits_bed(deck, "deck_module")
    if deck_ok:
        write_stl(deck, OUT / "deck_module.stl")
        write_3mf(deck, OUT / "deck_module.3mf", "deck_module")
    
    print("\n[3] Generating cable trough...")
    trough = build_cable_trough()
    trough_ok = check_fits_bed(trough, "cable_trough")
    if trough_ok:
        write_stl(trough, OUT / "cable_trough.stl")
        write_3mf(trough, OUT / "cable_trough.3mf", "cable_trough")
    
    print("\n[4] Generating string cassette...")
    cassette = build_string_cassette()
    cassette_ok = check_fits_bed(cassette, "string_cassette")
    if cassette_ok:
        write_stl(cassette, OUT / "string_cassette.stl")
        write_3mf(cassette, OUT / "string_cassette.3mf", "string_cassette")
    
    print("\n[5] Generating inter-deck bracket...")
    bracket = build_inter_deck_bracket()
    bracket_ok = check_fits_bed(bracket, "inter_deck_bracket")
    if bracket_ok:
        write_stl(bracket, OUT / "inter_deck_bracket.stl")
        write_3mf(bracket, OUT / "inter_deck_bracket.3mf", "inter_deck_bracket")
    
    print("\n[6] Generating guitar hanger...")
    hanger = build_guitar_hanger()
    hanger_ok = check_fits_bed(hanger, "guitar_hanger")
    if hanger_ok:
        write_stl(hanger, OUT / "guitar_hanger.stl")
        write_3mf(hanger, OUT / "guitar_hanger.3mf", "guitar_hanger")
    
    layout = calculate_layout()
    
    manifest = {
        "description": "100% PETG two-deck storage system - no arches, no decoration",
        "why_no_arches": "Arches were removed because they are not in the load path. Spines carry load directly to studs. Every gram must store or carry.",
        "height_assumption": {
            "outlet_to_ceiling_in": OUTLET_TO_CEILING_IN,
            "outlet_to_ceiling_mm": OUTLET_TO_CEILING_MM,
            "verified": False,
            "note": "USER-REPORTED, NOT FIELD-VERIFIED"
        },
        "architecture": {
            "stud_spine": "ONLY wall-load part. Screws to stud, crown supports deck.",
            "deck_module": "Ribbed box-beam. Sits on spine crowns.",
            "cable_trough": "U-channel with hooks. Mounts between decks.",
            "string_cassette": "Drawer for strings/picks. Sits on lower deck or mounts to bracket.",
            "inter_deck_bracket": "Connects upper/lower decks. Provides attachment points.",
            "guitar_hanger": "Neck hanger bolts to spine. Guitar hangs in room."
        },
        "long_wall": {
            "status": "ACTIVE",
            "length_in": LONG_WALL_LENGTH_IN,
            "stud_positions_in": STUD_POSITIONS_IN,
            "levels": 2,
        },
        "short_wall": {
            "status": "ON HOLD",
            "length_in": SHORT_WALL_LENGTH_IN,
            "note": "NEEDS FIELD MEASUREMENT"
        },
        "calculated_layout": layout,
        "parts": {
            "stud_spine": {
                "file": "stud_spine.stl",
                "quantity": 6,
                "note": "2 per stud × 3 studs",
                "dimensions_mm": [round(x, 1) for x in spine.bounding_box.extents],
            },
            "deck_module": {
                "file": "deck_module.stl",
                "quantity": layout["total_deck"],
                "note": f"{layout['deck_per_level']} per level × 2 levels",
                "dimensions_mm": [round(x, 1) for x in deck.bounding_box.extents],
            },
            "cable_trough": {
                "file": "cable_trough.stl",
                "quantity": "2-4 as needed",
                "dimensions_mm": [round(x, 1) for x in trough.bounding_box.extents],
            },
            "string_cassette": {
                "file": "string_cassette.stl",
                "quantity": "1-2 as needed",
                "dimensions_mm": [round(x, 1) for x in cassette.bounding_box.extents],
            },
            "inter_deck_bracket": {
                "file": "inter_deck_bracket.stl",
                "quantity": layout["bracket_count"],
                "dimensions_mm": [round(x, 1) for x in bracket.bounding_box.extents],
            },
            "guitar_hanger": {
                "file": "guitar_hanger.stl",
                "quantity": 1,
                "dimensions_mm": [round(x, 1) for x in hanger.bounding_box.extents],
            },
        },
        "hardware": {
            "wood_screws": {"spec": "#10 × 3 in", "quantity": 18, "note": "3 per spine × 6 spines"},
            "m4_bolts": {"spec": "M4 × 25mm socket head", "quantity": 150},
            "m4_nuts": {"spec": "M4 nylock", "quantity": 150},
            "washers": {"spec": "M4 flat", "quantity": 300},
        },
        "print_settings": {
            "material": "PETG",
            "wall_loops": 6,
            "infill_percent": 40,
            "infill_pattern": "gyroid",
        },
    }
    
    with open(OUT / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("\n[7] Wrote manifest.json")
    
    print("\n" + "=" * 70)
    print("TWO-DECK STORAGE SYSTEM SUMMARY")
    print("=" * 70)
    print(f"\nLONG WALL: {LONG_WALL_LENGTH_IN} in with studs at {STUD_POSITIONS_IN}")
    print(f"  Two stacked decks, NO ARCHES")
    print(f"  Decks per level: {layout['deck_per_level']} → Total: {layout['total_deck']}")
    print(f"  Spines: {layout['spine_sections']} (2 per stud × 3 studs)")
    print(f"  Inter-deck gap: {layout['inter_deck_gap_mm']} mm for attachments")
    print(f"\nSHORT WALL: ~{SHORT_WALL_LENGTH_IN} in (nominal)")
    print("  STATUS: ON HOLD — needs field measurement")
    print(f"\nHEIGHT: {OUTLET_TO_CEILING_IN} in outlet-to-ceiling (UNVERIFIED)")
    print("=" * 70)


if __name__ == "__main__":
    main()
