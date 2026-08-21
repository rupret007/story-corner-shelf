#!/usr/bin/env python3
"""Generate Elon-style 100% PETG storage arcade system.

Every gram printed stores something or carries load. No decorative air.

=== TWO-LEVEL ARCHITECTURE ===
Long wall (61.5 in): Two stacked shelf levels above the electric box.
Short wall (~36 in): ON HOLD for print until measured. Same bay/spine language.

HEIGHT ASSUMPTION (UNVERIFIED):
- User-reported outlet-top to ceiling: 43.5 in (1104.9 mm)
- This is UNVERIFIED. Field-measure before printing spines.
- Design provides clearance off ceiling and off the outlet box.

ARCHITECTURE:
1) Stud spine (tall, print 3): Wall-load backplate with two M4 crown levels.
2) Arch-bay module: Roman arch OPENING is a storage bay facing the room.
3) Deck module: Ribbed box section on top of each arcade level.
4) Inserts: Cable hook, string cassette, guitar neck hanger.

HARD CONSTRAINTS:
- 100% PETG. No plywood, steel angle, KV, Palatine tiles, R13 tubes.
- Bambu A1 mini 180mm, 0.4mm nozzle. Every part: XY ≤160mm with brim.
- Long wall 61.5 in. Studs at 17.0, 32.5, 48.5 in from inside corner.
- Mechanical screws (wood into studs, M4 through PETG). No snap-fit load path.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import trimesh
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "storage_arcade"

# A1 mini build constraints
BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
MAX_BED_XY_MM = 160.0  # HARD LIMIT with 3mm brim + calibration region

# === HEIGHT ASSUMPTIONS (UNVERIFIED) ===
# User-reported outlet-top to ceiling: 43.5 in = 1104.9 mm
# THIS IS UNVERIFIED. Field-measure before printing spines.
OUTLET_TO_CEILING_IN = 43.5  # UNVERIFIED - user reported
OUTLET_TO_CEILING_MM = OUTLET_TO_CEILING_IN * 25.4  # 1104.9 mm

# Design clearances
CEILING_CLEARANCE_MM = 25.0  # Gap from top of deck to ceiling
OUTLET_CLEARANCE_MM = 50.0   # Gap from bottom of lower bay to outlet top
INTER_LEVEL_GAP_MM = 20.0    # Gap between upper and lower arcade levels

# Calculate available height for two levels
AVAILABLE_HEIGHT_MM = OUTLET_TO_CEILING_MM - CEILING_CLEARANCE_MM - OUTLET_CLEARANCE_MM
# 1104.9 - 25 - 50 = 1029.9 mm for two levels + gap

# === WALL LAYOUT ===
# Long wall FIRST
LONG_WALL_LENGTH_IN = 61.5
STUD_POSITIONS_IN = [17.0, 32.5, 48.5]  # From inside corner
STUD_SPACING_MM = [
    (STUD_POSITIONS_IN[1] - STUD_POSITIONS_IN[0]) * 25.4,  # 393.7 mm
    (STUD_POSITIONS_IN[2] - STUD_POSITIONS_IN[1]) * 25.4,  # 406.4 mm
]

# Short wall ON HOLD
SHORT_WALL_LENGTH_IN = 36.0  # Nominal, NEEDS MEASUREMENT
SHORT_WALL_ON_HOLD = True

# === ARCH-BAY MODULE ===
# Must fit A1 mini ≤160mm XY with brim
BAY_WIDTH_MM = 155.0   # Along wall run
BAY_DEPTH_MM = 150.0   # Into room  
BAY_HEIGHT_MM = 155.0  # Bay height (fits 160mm bed rule)

# Pier dimensions - hollow for storage
PIER_WIDTH_MM = 25.0
PIER_WALL_MM = 4.0
PIER_INTERNAL_WIDTH_MM = PIER_WIDTH_MM - 2 * PIER_WALL_MM  # 17mm usable

# Arch geometry - true Roman semicircle
ARCH_SPAN_MM = BAY_WIDTH_MM - 2 * PIER_WIDTH_MM  # 105mm opening
ARCH_RADIUS_MM = ARCH_SPAN_MM / 2.0  # 52.5mm radius
ARCH_SPRING_Z_MM = 55.0  # Height where arch starts curving
ARCH_WALL_MM = 5.0

# Bay floor - cable trough / bin seat
BAY_FLOOR_HEIGHT_MM = 25.0
BAY_FLOOR_WALL_MM = 4.0

# Crown that connects to deck
BAY_CROWN_HEIGHT_MM = 20.0
BAY_CROWN_WALL_MM = 4.0

# === DECK MODULE ===
DECK_LENGTH_MM = 158.0
DECK_WIDTH_MM = 150.0
DECK_HEIGHT_MM = 35.0
DECK_WALL_MM = 4.0
DECK_RIB_COUNT = 3

# === STUD SPINE (TALL - TWO LEVELS) ===
# Single bay height: BAY_HEIGHT_MM = 155mm
# Deck height: DECK_HEIGHT_MM = 35mm  
# Per level total: 155 + 35 = 190mm
LEVEL_HEIGHT_MM = BAY_HEIGHT_MM + DECK_HEIGHT_MM  # 190mm per level

# Two levels + gap
TWO_LEVEL_HEIGHT_MM = 2 * LEVEL_HEIGHT_MM + INTER_LEVEL_GAP_MM  # 400mm

# Spine must span from outlet clearance to ceiling clearance
# Total height = outlet clearance + two-level + ceiling clearance
# But spine is printed in sections due to 180mm Z limit
# Design: Two spine sections that stack, or one tall spine printed on side

# For A1 mini, max Z = 180mm. Spine needs ~400mm for two levels.
# Solution: Print spine lying flat (158mm height prints as 158mm Y on bed)
# OR: Modular spine sections that bolt together

# We'll use a single spine design that can print lying flat
SPINE_WIDTH_MM = 40.0   # Along wall run (X on bed when flat)
SPINE_HEIGHT_MM = 158.0 # Height per section (prints as Y)
SPINE_DEPTH_MM = 20.0   # Wall projection
SPINE_WALL_MM = 5.0
SPINE_CROWN_HEIGHT_MM = 25.0
SPINE_CROWN_DEPTH_MM = 50.0

# For two-level system, we print spine sections and stack them
# Lower spine: supports lower arcade
# Upper spine: supports upper arcade
# Both bolt to same stud

# Screw holes (3 per spine section)
WOOD_SCREW_DIAMETER_MM = 5.5
WOOD_SCREW_POSITIONS_Z_MM = [25.0, 79.0, 133.0]
COUNTERBORE_DIAMETER_MM = 12.0
COUNTERBORE_DEPTH_MM = 4.0

# M4 grid for attaching bays and deck
M4_CLEARANCE_MM = 4.5
M4_GRID_Y_MM = [15.0, 35.0]
M4_GRID_X_MM = [10.0, 30.0]

# === INSERTS ===
CABLE_INSERT_WIDTH_MM = PIER_INTERNAL_WIDTH_MM - 1.0
CABLE_INSERT_DEPTH_MM = BAY_DEPTH_MM - 10.0
CABLE_INSERT_HEIGHT_MM = 40.0

STRING_CASSETTE_WIDTH_MM = PIER_INTERNAL_WIDTH_MM - 1.0
STRING_CASSETTE_DEPTH_MM = 60.0
STRING_CASSETTE_HEIGHT_MM = 80.0

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


def extrude_yz_profile(profile: Polygon, x_length: float, x_start: float = 0.0) -> trimesh.Trimesh:
    if not profile.is_valid or profile.is_empty:
        raise ValueError("Invalid profile polygon")
    mesh = trimesh.creation.extrude_polygon(profile, height=x_length, engine="earcut")
    mesh.vertices = mesh.vertices[:, [2, 0, 1]]
    mesh.vertices[:, 0] += x_start
    mesh.fix_normals()
    return clean_mesh(mesh)


def build_stud_spine() -> trimesh.Trimesh:
    """Build a single spine section (158mm tall).
    
    For two-level system: Stack two spine sections on each stud.
    Lower spine at outlet clearance height.
    Upper spine above the lower arcade.
    
    Each spine section has:
    - 3 wood screw holes into stud
    - M4 grid on crown for bay/deck attachment
    """
    parts: list[trimesh.Trimesh] = []
    
    # Main backplate
    backplate = box(
        (SPINE_WALL_MM, SPINE_WIDTH_MM, SPINE_HEIGHT_MM),
        (0, 0, 0)
    )
    parts.append(backplate)
    
    # Ribs for structural depth
    for y in [5.0, SPINE_WIDTH_MM - 10.0]:
        rib = box(
            (SPINE_DEPTH_MM, SPINE_WALL_MM, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM),
            (0, y, 0)
        )
        parts.append(rib)
    
    # Crown section (solid for simplicity, gyroid infill handles weight)
    crown = box(
        (SPINE_CROWN_DEPTH_MM, SPINE_WIDTH_MM, SPINE_CROWN_HEIGHT_MM),
        (0, 0, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM)
    )
    parts.append(crown)
    
    body = boolean_union(parts)
    
    # Cut screw holes
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
    
    # M4 holes in crown
    for x in M4_GRID_X_MM:
        for y in M4_GRID_Y_MM:
            m4_hole = cylinder_z(
                M4_CLEARANCE_MM / 2,
                SPINE_CROWN_HEIGHT_MM + 2,
                (x, y, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM / 2)
            )
            cutters.append(m4_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_arch_bay() -> trimesh.Trimesh:
    """Build an arch-bay module where the arch OPENING is storage.
    
    Same module used on both levels.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Left pier (hollow)
    left_pier_outer = box(
        (PIER_WIDTH_MM, BAY_DEPTH_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM),
        (0, 0, 0)
    )
    left_pier_inner = box(
        (PIER_INTERNAL_WIDTH_MM, BAY_DEPTH_MM - 2 * PIER_WALL_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM - PIER_WALL_MM),
        (PIER_WALL_MM, PIER_WALL_MM, PIER_WALL_MM)
    )
    parts.append(left_pier_outer)
    
    # Right pier (hollow)
    right_pier_outer = box(
        (PIER_WIDTH_MM, BAY_DEPTH_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM),
        (BAY_WIDTH_MM - PIER_WIDTH_MM, 0, 0)
    )
    right_pier_inner = box(
        (PIER_INTERNAL_WIDTH_MM, BAY_DEPTH_MM - 2 * PIER_WALL_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM - PIER_WALL_MM),
        (BAY_WIDTH_MM - PIER_WIDTH_MM + PIER_WALL_MM, PIER_WALL_MM, PIER_WALL_MM)
    )
    parts.append(right_pier_outer)
    
    # Bay floor (trough)
    floor = box(
        (ARCH_SPAN_MM, BAY_DEPTH_MM, BAY_FLOOR_HEIGHT_MM),
        (PIER_WIDTH_MM, 0, 0)
    )
    parts.append(floor)
    
    floor_trough = box(
        (ARCH_SPAN_MM - 2 * BAY_FLOOR_WALL_MM, BAY_DEPTH_MM - 2 * BAY_FLOOR_WALL_MM, BAY_FLOOR_HEIGHT_MM - BAY_FLOOR_WALL_MM),
        (PIER_WIDTH_MM + BAY_FLOOR_WALL_MM, BAY_FLOOR_WALL_MM, BAY_FLOOR_WALL_MM)
    )
    
    # Roman arch ring
    arch_center_x = BAY_WIDTH_MM / 2
    arch_center_z = ARCH_SPRING_Z_MM
    num_points = 48
    outer_r = ARCH_RADIUS_MM + ARCH_WALL_MM
    inner_r = ARCH_RADIUS_MM
    
    outer_points = []
    inner_points = []
    for i in range(num_points + 1):
        angle = math.pi * i / num_points
        outer_points.append((
            arch_center_x + outer_r * math.cos(angle),
            arch_center_z + outer_r * math.sin(angle)
        ))
        inner_points.append((
            arch_center_x + inner_r * math.cos(angle),
            arch_center_z + inner_r * math.sin(angle)
        ))
    
    ring_points = outer_points + inner_points[::-1]
    arch_profile = Polygon(ring_points)
    
    if arch_profile.is_valid and arch_profile.area > 1.0:
        arch_ring = extrude_yz_profile(arch_profile, BAY_DEPTH_MM, 0)
        arch_ring.vertices[:, [0, 1]] = arch_ring.vertices[:, [1, 0]]
        arch_ring.fix_normals()
        parts.append(arch_ring)
    
    # Crown
    crown = box(
        (BAY_WIDTH_MM, BAY_DEPTH_MM, BAY_CROWN_HEIGHT_MM),
        (0, 0, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM + ARCH_WALL_MM)
    )
    crown_hollow = box(
        (BAY_WIDTH_MM - 2 * BAY_CROWN_WALL_MM, BAY_DEPTH_MM - 2 * BAY_CROWN_WALL_MM, BAY_CROWN_HEIGHT_MM - BAY_CROWN_WALL_MM),
        (BAY_CROWN_WALL_MM, BAY_CROWN_WALL_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM + ARCH_WALL_MM)
    )
    parts.append(crown)
    
    # Spandrels
    spandrel_left = box(
        (PIER_WIDTH_MM, BAY_DEPTH_MM, BAY_CROWN_HEIGHT_MM),
        (0, 0, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM)
    )
    spandrel_right = box(
        (PIER_WIDTH_MM, BAY_DEPTH_MM, BAY_CROWN_HEIGHT_MM),
        (BAY_WIDTH_MM - PIER_WIDTH_MM, 0, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM)
    )
    parts.append(spandrel_left)
    parts.append(spandrel_right)
    
    # Back wall
    back_wall = box(
        (BAY_WIDTH_MM, BAY_FLOOR_WALL_MM, BAY_HEIGHT_MM),
        (0, BAY_DEPTH_MM - BAY_FLOOR_WALL_MM, 0)
    )
    parts.append(back_wall)
    
    body = boolean_union(parts)
    
    # Cut hollows
    cutters = [left_pier_inner, right_pier_inner, floor_trough, crown_hollow]
    
    # M4 mounting holes
    for z_offset in [20.0, 70.0, 120.0]:
        for x_offset in [BAY_WIDTH_MM / 3, 2 * BAY_WIDTH_MM / 3]:
            m4_hole = cylinder_y(
                M4_CLEARANCE_MM / 2,
                BAY_FLOOR_WALL_MM + 2,
                (x_offset, BAY_DEPTH_MM - BAY_FLOOR_WALL_MM / 2, z_offset)
            )
            cutters.append(m4_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_deck_module() -> trimesh.Trimesh:
    """Build a ribbed deck module. Same on both levels."""
    parts: list[trimesh.Trimesh] = []
    
    top = box((DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM), (0, 0, DECK_HEIGHT_MM - DECK_WALL_MM))
    parts.append(top)
    
    bottom = box((DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM), (0, 0, 0))
    parts.append(bottom)
    
    front = box((DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM), (0, 0, 0))
    parts.append(front)
    
    back = box((DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM), (0, DECK_WIDTH_MM - DECK_WALL_MM, 0))
    parts.append(back)
    
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
    
    # M4 holes
    cutters: list[trimesh.Trimesh] = []
    for x_pos in [15.0, DECK_LENGTH_MM / 2, DECK_LENGTH_MM - 15.0]:
        for y_pos in [20.0, DECK_WIDTH_MM - 20.0]:
            m4_hole = cylinder_z(
                M4_CLEARANCE_MM / 2,
                DECK_HEIGHT_MM + 2,
                (x_pos, y_pos, DECK_HEIGHT_MM / 2)
            )
            cutters.append(m4_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_cable_insert() -> trimesh.Trimesh:
    """Cable hook insert for pier hollow."""
    parts: list[trimesh.Trimesh] = []
    
    base = box((CABLE_INSERT_WIDTH_MM, CABLE_INSERT_DEPTH_MM, 3.0), (0, 0, 0))
    parts.append(base)
    
    hook_positions = [20.0, 60.0, 100.0]
    hook_width = CABLE_INSERT_WIDTH_MM - 2
    hook_height = CABLE_INSERT_HEIGHT_MM - 3
    hook_depth = 15.0
    
    for y_pos in hook_positions:
        post = box((hook_width, 4.0, hook_height), (1.0, y_pos - 2.0, 3.0))
        parts.append(post)
        hook_top = box((hook_width, hook_depth, 4.0), (1.0, y_pos - 2.0, 3.0 + hook_height - 4.0))
        parts.append(hook_top)
        lip = box((hook_width, 4.0, 10.0), (1.0, y_pos - 2.0 + hook_depth - 4.0, 3.0 + hook_height - 14.0))
        parts.append(lip)
    
    return normalize_mesh(boolean_union(parts))


def build_string_cassette() -> trimesh.Trimesh:
    """String/pick cassette for pier hollow."""
    wall_mm = 2.5
    
    outer = box(
        (STRING_CASSETTE_WIDTH_MM, STRING_CASSETTE_DEPTH_MM, STRING_CASSETTE_HEIGHT_MM),
        (0, 0, 0)
    )
    inner = box(
        (STRING_CASSETTE_WIDTH_MM - 2 * wall_mm, STRING_CASSETTE_DEPTH_MM - wall_mm, STRING_CASSETTE_HEIGHT_MM - wall_mm),
        (wall_mm, 0, wall_mm)
    )
    
    parts = [outer]
    divider = box(
        (wall_mm, STRING_CASSETTE_DEPTH_MM - wall_mm, STRING_CASSETTE_HEIGHT_MM - wall_mm - 10),
        (STRING_CASSETTE_WIDTH_MM / 2 - wall_mm / 2, 0, wall_mm)
    )
    parts.append(divider)
    
    body = boolean_union(parts)
    return normalize_mesh(boolean_difference(body, [inner]))


def build_guitar_hanger() -> trimesh.Trimesh:
    """Guitar neck hanger - bolts to spine, guitar hangs in room."""
    parts: list[trimesh.Trimesh] = []
    
    main = box((GUITAR_HANGER_WIDTH_MM, GUITAR_HANGER_DEPTH_MM, GUITAR_HANGER_HEIGHT_MM), (0, 0, 0))
    parts.append(main)
    
    mount_plate = box((GUITAR_HANGER_WIDTH_MM, 20.0, GUITAR_HANGER_HEIGHT_MM + 10.0), (0, GUITAR_HANGER_DEPTH_MM - 20.0, 0))
    parts.append(mount_plate)
    
    arm_width = (GUITAR_HANGER_WIDTH_MM - GUITAR_NECK_SLOT_WIDTH_MM) / 2
    arm_height = 25.0
    
    left_arm = box((arm_width, GUITAR_HANGER_DEPTH_MM - 20.0, arm_height), (0, 0, GUITAR_HANGER_HEIGHT_MM))
    parts.append(left_arm)
    
    right_arm = box((arm_width, GUITAR_HANGER_DEPTH_MM - 20.0, arm_height), (GUITAR_HANGER_WIDTH_MM - arm_width, 0, GUITAR_HANGER_HEIGHT_MM))
    parts.append(right_arm)
    
    body = boolean_union(parts)
    
    cutters: list[trimesh.Trimesh] = []
    neck_slot = box(
        (GUITAR_NECK_SLOT_WIDTH_MM, GUITAR_NECK_SLOT_DEPTH_MM + 1, GUITAR_HANGER_HEIGHT_MM + arm_height + 2),
        ((GUITAR_HANGER_WIDTH_MM - GUITAR_NECK_SLOT_WIDTH_MM) / 2, -1, -1)
    )
    cutters.append(neck_slot)
    
    for z_offset in [10.0, GUITAR_HANGER_HEIGHT_MM]:
        for x_offset in [15.0, GUITAR_HANGER_WIDTH_MM - 15.0]:
            m4_hole = cylinder_y(M4_CLEARANCE_MM / 2, 25.0, (x_offset, GUITAR_HANGER_DEPTH_MM - 10.0, z_offset))
            cutters.append(m4_hole)
    
    return normalize_mesh(boolean_difference(body, cutters))


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
    """Calculate two-level layout for long wall."""
    
    spacing_1 = STUD_SPACING_MM[0]  # 393.7 mm
    spacing_2 = STUD_SPACING_MM[1]  # 406.4 mm
    
    effective_bay_width = BAY_WIDTH_MM + 5.0  # Gap for assembly
    
    bays_span_1 = int(spacing_1 / effective_bay_width)  # 2 bays
    bays_span_2 = int(spacing_2 / effective_bay_width)  # 2 bays
    
    bays_per_level = bays_span_1 + bays_span_2  # 4 bays per level
    total_bays = bays_per_level * 2  # 8 bays total (two levels)
    
    filler_1 = spacing_1 - bays_span_1 * effective_bay_width
    filler_2 = spacing_2 - bays_span_2 * effective_bay_width
    
    # Deck count per level
    total_span = spacing_1 + spacing_2 + SPINE_WIDTH_MM * 3
    deck_per_level = int(total_span / DECK_LENGTH_MM) + 1
    total_deck = deck_per_level * 2  # Two levels
    
    # Spine count: 3 studs × 2 levels = 6 spine sections
    spine_sections = 3 * 2
    
    return {
        "levels": 2,
        "stud_spacing_mm": STUD_SPACING_MM,
        "bays_per_span": [bays_span_1, bays_span_2],
        "bays_per_level": bays_per_level,
        "total_bays": total_bays,
        "filler_widths_mm": [filler_1, filler_2],
        "deck_per_level": deck_per_level,
        "total_deck": total_deck,
        "spine_sections": spine_sections,
        "studs": 3,
        "level_height_mm": LEVEL_HEIGHT_MM,
        "total_arcade_height_mm": TWO_LEVEL_HEIGHT_MM,
    }


def main():
    print("=" * 70)
    print("STORAGE ARCADE GENERATOR — TWO-LEVEL EDITION")
    print("100% PETG • Every gram stores or carries • No decorative air")
    print("=" * 70)
    print()
    print("HEIGHT ASSUMPTION (UNVERIFIED):")
    print(f"  Outlet-top to ceiling: {OUTLET_TO_CEILING_IN} in ({OUTLET_TO_CEILING_MM:.1f} mm)")
    print("  THIS IS USER-REPORTED, NOT FIELD-VERIFIED.")
    print(f"  Ceiling clearance: {CEILING_CLEARANCE_MM} mm")
    print(f"  Outlet clearance: {OUTLET_CLEARANCE_MM} mm")
    print(f"  Available for two levels: {AVAILABLE_HEIGHT_MM:.1f} mm")
    print()
    
    OUT.mkdir(parents=True, exist_ok=True)
    
    print("[1] Generating stud spine (print 6 for two levels)...")
    spine = build_stud_spine()
    spine_ok = check_fits_bed(spine, "stud_spine")
    if spine_ok:
        write_stl(spine, OUT / "stud_spine.stl")
        write_3mf(spine, OUT / "stud_spine.3mf", "stud_spine")
    
    print("\n[2] Generating arch-bay module (print 8 for two levels)...")
    arch_bay = build_arch_bay()
    bay_ok = check_fits_bed(arch_bay, "arch_bay")
    if bay_ok:
        write_stl(arch_bay, OUT / "arch_bay.stl")
        write_3mf(arch_bay, OUT / "arch_bay.3mf", "arch_bay")
    
    print("\n[3] Generating deck module (print 12 for two levels)...")
    deck = build_deck_module()
    deck_ok = check_fits_bed(deck, "deck_module")
    if deck_ok:
        write_stl(deck, OUT / "deck_module.stl")
        write_3mf(deck, OUT / "deck_module.3mf", "deck_module")
    
    print("\n[4] Generating cable insert...")
    cable_insert = build_cable_insert()
    cable_ok = check_fits_bed(cable_insert, "cable_insert")
    if cable_ok:
        write_stl(cable_insert, OUT / "cable_insert.stl")
        write_3mf(cable_insert, OUT / "cable_insert.3mf", "cable_insert")
    
    print("\n[5] Generating string cassette...")
    string_cassette = build_string_cassette()
    string_ok = check_fits_bed(string_cassette, "string_cassette")
    if string_ok:
        write_stl(string_cassette, OUT / "string_cassette.stl")
        write_3mf(string_cassette, OUT / "string_cassette.3mf", "string_cassette")
    
    print("\n[6] Generating guitar hanger...")
    guitar_hanger = build_guitar_hanger()
    guitar_ok = check_fits_bed(guitar_hanger, "guitar_hanger")
    if guitar_ok:
        write_stl(guitar_hanger, OUT / "guitar_hanger.stl")
        write_3mf(guitar_hanger, OUT / "guitar_hanger.3mf", "guitar_hanger")
    
    layout = calculate_layout()
    
    manifest = {
        "description": "Elon-style 100% PETG storage arcade - TWO LEVELS on long wall",
        "height_assumption": {
            "outlet_to_ceiling_in": OUTLET_TO_CEILING_IN,
            "outlet_to_ceiling_mm": OUTLET_TO_CEILING_MM,
            "verified": False,
            "note": "USER-REPORTED, NOT FIELD-VERIFIED. Measure before printing spines."
        },
        "clearances": {
            "ceiling_clearance_mm": CEILING_CLEARANCE_MM,
            "outlet_clearance_mm": OUTLET_CLEARANCE_MM,
            "inter_level_gap_mm": INTER_LEVEL_GAP_MM,
            "available_height_mm": AVAILABLE_HEIGHT_MM,
        },
        "architecture": {
            "stud_spine": "Wall-mount backplate. Stack 2 per stud for two levels.",
            "arch_bay": "Roman arch opening IS the storage bay.",
            "deck_module": "Ribbed box section on top of each level.",
            "cable_insert": "Hook/trough insert for pier hollow.",
            "string_cassette": "Drawer for strings/picks in pier hollow.",
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
            "note": "~36 in nominal. NEEDS FIELD MEASUREMENT before print."
        },
        "calculated_layout": layout,
        "parts": {
            "stud_spine": {
                "file": "stud_spine.stl",
                "quantity_for_two_levels": 6,
                "note": "2 per stud × 3 studs",
                "dimensions_mm": [round(x, 1) for x in spine.bounding_box.extents],
            },
            "arch_bay": {
                "file": "arch_bay.stl",
                "quantity_for_two_levels": 8,
                "note": "4 per level × 2 levels",
                "dimensions_mm": [round(x, 1) for x in arch_bay.bounding_box.extents],
            },
            "deck_module": {
                "file": "deck_module.stl",
                "quantity_for_two_levels": 12,
                "note": "6 per level × 2 levels",
                "dimensions_mm": [round(x, 1) for x in deck.bounding_box.extents],
            },
            "cable_insert": {
                "file": "cable_insert.stl",
                "quantity": "As needed",
                "dimensions_mm": [round(x, 1) for x in cable_insert.bounding_box.extents],
            },
            "string_cassette": {
                "file": "string_cassette.stl",
                "quantity": "As needed",
                "dimensions_mm": [round(x, 1) for x in string_cassette.bounding_box.extents],
            },
            "guitar_hanger": {
                "file": "guitar_hanger.stl",
                "quantity": 1,
                "dimensions_mm": [round(x, 1) for x in guitar_hanger.bounding_box.extents],
            },
        },
        "hardware": {
            "wood_screws": {"spec": "#10 × 3 in", "quantity": 18, "note": "3 per spine × 6 spines"},
            "m4_bolts": {"spec": "M4 × 25mm socket head", "quantity": 100},
            "m4_nuts": {"spec": "M4 nylock", "quantity": 100},
            "washers": {"spec": "M4 flat", "quantity": 200},
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
    print("TWO-LEVEL STORAGE ARCADE SUMMARY")
    print("=" * 70)
    print(f"\nLONG WALL: {LONG_WALL_LENGTH_IN} in with studs at {STUD_POSITIONS_IN}")
    print(f"  Two stacked shelf levels above electric box")
    print(f"  Bays per level: {layout['bays_per_level']} → Total: {layout['total_bays']} bays")
    print(f"  Deck per level: {layout['deck_per_level']} → Total: {layout['total_deck']} deck modules")
    print(f"  Spines: {layout['spine_sections']} (2 per stud × 3 studs)")
    print(f"\nSHORT WALL: ~{SHORT_WALL_LENGTH_IN} in (nominal)")
    print("  STATUS: ON HOLD — needs field measurement")
    print("  Same bay/spine language; ready when measured")
    print(f"\nHEIGHT: {OUTLET_TO_CEILING_IN} in outlet-to-ceiling (UNVERIFIED)")
    print("  FIELD-MEASURE BEFORE PRINTING SPINES")
    print("=" * 70)


if __name__ == "__main__":
    main()
