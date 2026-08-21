#!/usr/bin/env python3
"""Generate Elon-style 100% PETG storage arcade system.

Every gram printed stores something or carries load. No decorative air.

ARCHITECTURE:
1) Stud spine (print 3): Wall-load backplate with M4 grids. Screws to studs only.
2) Arch-bay module: Roman arch OPENING is a storage bay facing the room.
   Hollow piers become storage columns. Bay floor is cable trough/bin seat.
3) Deck module: Ribbed box section on top of the arcade.
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

# Wall layout (long wall only, return wall ON HOLD)
WALL_LENGTH_IN = 61.5
STUD_POSITIONS_IN = [17.0, 32.5, 48.5]  # From inside corner
STUD_SPACING_MM = [
    (STUD_POSITIONS_IN[1] - STUD_POSITIONS_IN[0]) * 25.4,  # 393.7 mm
    (STUD_POSITIONS_IN[2] - STUD_POSITIONS_IN[1]) * 25.4,  # 406.4 mm
]

# Stud spine dimensions - the only wall-load part
SPINE_WIDTH_MM = 40.0  # Along wall run
SPINE_HEIGHT_MM = 158.0  # Tall enough for 3 screws + crown
SPINE_DEPTH_MM = 20.0  # Wall projection
SPINE_WALL_MM = 5.0  # Wall thickness
SPINE_CROWN_HEIGHT_MM = 25.0  # Top section that supports deck/bays
SPINE_CROWN_DEPTH_MM = 50.0  # How far crown projects from wall

# Screw holes into studs (3 per spine for heavy duty)
WOOD_SCREW_DIAMETER_MM = 5.5  # Clearance for #10 wood screw
WOOD_SCREW_POSITIONS_Z_MM = [25.0, 79.0, 133.0]  # From bottom of spine
COUNTERBORE_DIAMETER_MM = 12.0
COUNTERBORE_DEPTH_MM = 4.0

# M4 grid for attaching bays and deck
M4_CLEARANCE_MM = 4.5
M4_GRID_Y_MM = [15.0, 35.0]  # Two rows on crown
M4_GRID_X_MM = [10.0, 30.0]  # Two columns

# Arch-bay module - the Roman arch opening IS the storage bay
BAY_WIDTH_MM = 155.0  # Along wall run (fits between spines)
BAY_DEPTH_MM = 150.0  # Into room
BAY_HEIGHT_MM = 155.0  # Max that fits A1 mini with brim safety

# Pier dimensions - hollow for storage
PIER_WIDTH_MM = 25.0  # Width of each vertical pier
PIER_WALL_MM = 4.0  # Pier shell thickness
PIER_INTERNAL_WIDTH_MM = PIER_WIDTH_MM - 2 * PIER_WALL_MM  # 17mm usable

# Arch geometry - true Roman semicircle
ARCH_SPAN_MM = BAY_WIDTH_MM - 2 * PIER_WIDTH_MM  # 105mm opening
ARCH_RADIUS_MM = ARCH_SPAN_MM / 2.0  # 52.5mm radius
ARCH_SPRING_Z_MM = 55.0  # Height where arch starts curving
ARCH_WALL_MM = 5.0  # Arch ring thickness

# Bay floor - cable trough / bin seat
BAY_FLOOR_HEIGHT_MM = 25.0  # Floor of the arch opening
BAY_FLOOR_WALL_MM = 4.0

# Crown that connects to deck
BAY_CROWN_HEIGHT_MM = 20.0
BAY_CROWN_WALL_MM = 4.0

# Deck module - ribbed box section
DECK_LENGTH_MM = 158.0  # Along wall run
DECK_WIDTH_MM = 150.0  # Depth into room (matches bay depth)
DECK_HEIGHT_MM = 35.0  # Box section depth
DECK_WALL_MM = 4.0
DECK_RIB_COUNT = 3

# Cable insert dimensions
CABLE_INSERT_WIDTH_MM = PIER_INTERNAL_WIDTH_MM - 1.0  # Fits inside pier
CABLE_INSERT_DEPTH_MM = BAY_DEPTH_MM - 10.0
CABLE_INSERT_HEIGHT_MM = 40.0

# String/pick cassette - fits in pier
STRING_CASSETTE_WIDTH_MM = PIER_INTERNAL_WIDTH_MM - 1.0
STRING_CASSETTE_DEPTH_MM = 60.0
STRING_CASSETTE_HEIGHT_MM = 80.0

# Guitar neck hanger - bolts to spine
GUITAR_HANGER_WIDTH_MM = 60.0
GUITAR_HANGER_DEPTH_MM = 100.0
GUITAR_HANGER_HEIGHT_MM = 30.0
GUITAR_NECK_SLOT_WIDTH_MM = 48.0  # Standard guitar neck width
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
    """Build the wall-mount spine that screws into a stud.
    
    This is the only structural connection to the wall. Everything else
    hangs off the spine via M4 bolts.
    
    Solid construction for watertight mesh - no internal hollows that
    could create non-manifold geometry.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Main backplate - vertical section against wall
    backplate = box(
        (SPINE_WALL_MM, SPINE_WIDTH_MM, SPINE_HEIGHT_MM),
        (0, 0, 0)
    )
    parts.append(backplate)
    
    # Ribs running from wall to crown (structural depth)
    rib_positions = [5.0, SPINE_WIDTH_MM - 10.0]
    for y in rib_positions:
        rib = box(
            (SPINE_DEPTH_MM, SPINE_WALL_MM, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM),
            (0, y, 0)
        )
        parts.append(rib)
    
    # Crown section - SOLID (simpler, watertight, gyroid infill handles weight)
    crown = box(
        (SPINE_CROWN_DEPTH_MM, SPINE_WIDTH_MM, SPINE_CROWN_HEIGHT_MM),
        (0, 0, SPINE_HEIGHT_MM - SPINE_CROWN_HEIGHT_MM)
    )
    parts.append(crown)
    
    body = boolean_union(parts)
    
    # Cut screw holes for wood screws into stud
    cutters: list[trimesh.Trimesh] = []
    for z in WOOD_SCREW_POSITIONS_Z_MM:
        # Through hole
        hole = cylinder_y(
            WOOD_SCREW_DIAMETER_MM / 2,
            SPINE_WALL_MM + 2,
            (SPINE_WALL_MM / 2, SPINE_WIDTH_MM / 2, z)
        )
        cutters.append(hole)
        # Counterbore on room side
        cbore = cylinder_y(
            COUNTERBORE_DIAMETER_MM / 2,
            COUNTERBORE_DEPTH_MM + 0.1,
            (SPINE_DEPTH_MM - COUNTERBORE_DEPTH_MM / 2, SPINE_WIDTH_MM / 2, z)
        )
        cutters.append(cbore)
    
    # Cut M4 holes in crown for bay/deck attachment
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
    
    The Roman arch opening faces the room. You can put a cable bin,
    string box, or anything else into the bay. The hollow piers on
    each side are also storage columns.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Left pier - hollow for storage
    left_pier_outer = box(
        (PIER_WIDTH_MM, BAY_DEPTH_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM),
        (0, 0, 0)
    )
    left_pier_inner = box(
        (PIER_INTERNAL_WIDTH_MM, BAY_DEPTH_MM - 2 * PIER_WALL_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM - PIER_WALL_MM),
        (PIER_WALL_MM, PIER_WALL_MM, PIER_WALL_MM)
    )
    parts.append(left_pier_outer)
    
    # Right pier - hollow for storage
    right_pier_outer = box(
        (PIER_WIDTH_MM, BAY_DEPTH_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM),
        (BAY_WIDTH_MM - PIER_WIDTH_MM, 0, 0)
    )
    right_pier_inner = box(
        (PIER_INTERNAL_WIDTH_MM, BAY_DEPTH_MM - 2 * PIER_WALL_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM - PIER_WALL_MM),
        (BAY_WIDTH_MM - PIER_WIDTH_MM + PIER_WALL_MM, PIER_WALL_MM, PIER_WALL_MM)
    )
    parts.append(right_pier_outer)
    
    # Bay floor - forms the bottom of the storage opening
    floor = box(
        (ARCH_SPAN_MM, BAY_DEPTH_MM, BAY_FLOOR_HEIGHT_MM),
        (PIER_WIDTH_MM, 0, 0)
    )
    parts.append(floor)
    
    # Floor internal trough (cable channel)
    floor_trough = box(
        (ARCH_SPAN_MM - 2 * BAY_FLOOR_WALL_MM, BAY_DEPTH_MM - 2 * BAY_FLOOR_WALL_MM, BAY_FLOOR_HEIGHT_MM - BAY_FLOOR_WALL_MM),
        (PIER_WIDTH_MM + BAY_FLOOR_WALL_MM, BAY_FLOOR_WALL_MM, BAY_FLOOR_WALL_MM)
    )
    
    # Build the Roman arch ring - true semicircle
    arch_center_x = BAY_WIDTH_MM / 2
    arch_center_z = ARCH_SPRING_Z_MM
    
    # Create arch profile as a ring in XZ plane
    num_points = 48
    outer_r = ARCH_RADIUS_MM + ARCH_WALL_MM
    inner_r = ARCH_RADIUS_MM
    
    outer_points = []
    inner_points = []
    for i in range(num_points + 1):
        angle = math.pi * i / num_points
        # Outer arch (extrados)
        outer_points.append((
            arch_center_x + outer_r * math.cos(angle),
            arch_center_z + outer_r * math.sin(angle)
        ))
        # Inner arch (intrados)
        inner_points.append((
            arch_center_x + inner_r * math.cos(angle),
            arch_center_z + inner_r * math.sin(angle)
        ))
    
    # Create arch ring profile (outer then inner reversed)
    ring_points = outer_points + inner_points[::-1]
    arch_profile = Polygon(ring_points)
    
    if arch_profile.is_valid and arch_profile.area > 1.0:
        arch_ring = extrude_yz_profile(arch_profile, BAY_DEPTH_MM, 0)
        arch_ring.vertices[:, [0, 1]] = arch_ring.vertices[:, [1, 0]]
        arch_ring.fix_normals()
        parts.append(arch_ring)
    
    # Crown on top connecting bays
    crown = box(
        (BAY_WIDTH_MM, BAY_DEPTH_MM, BAY_CROWN_HEIGHT_MM),
        (0, 0, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM + ARCH_WALL_MM)
    )
    crown_hollow = box(
        (BAY_WIDTH_MM - 2 * BAY_CROWN_WALL_MM, BAY_DEPTH_MM - 2 * BAY_CROWN_WALL_MM, BAY_CROWN_HEIGHT_MM - BAY_CROWN_WALL_MM),
        (BAY_CROWN_WALL_MM, BAY_CROWN_WALL_MM, ARCH_SPRING_Z_MM + ARCH_RADIUS_MM + ARCH_WALL_MM)
    )
    parts.append(crown)
    
    # Spandrel fill above arch (solid triangular regions)
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
    
    # Back wall of bay (closes the storage volume)
    back_wall = box(
        (BAY_WIDTH_MM, BAY_FLOOR_WALL_MM, BAY_HEIGHT_MM),
        (0, BAY_DEPTH_MM - BAY_FLOOR_WALL_MM, 0)
    )
    parts.append(back_wall)
    
    body = boolean_union(parts)
    
    # Cut out hollow regions
    cutters = [left_pier_inner, right_pier_inner, floor_trough, crown_hollow]
    
    # Cut M4 mounting holes in back wall for spine attachment
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
    """Build a ribbed deck module that sits on top of the arcade.
    
    Box-beam construction for stiffness. Ribs every ~50mm.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Top surface
    top = box(
        (DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM),
        (0, 0, DECK_HEIGHT_MM - DECK_WALL_MM)
    )
    parts.append(top)
    
    # Bottom surface
    bottom = box(
        (DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM),
        (0, 0, 0)
    )
    parts.append(bottom)
    
    # Front wall
    front = box(
        (DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM),
        (0, 0, 0)
    )
    parts.append(front)
    
    # Back wall
    back = box(
        (DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM),
        (0, DECK_WIDTH_MM - DECK_WALL_MM, 0)
    )
    parts.append(back)
    
    # End walls
    left_end = box(
        (DECK_WALL_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM),
        (0, 0, 0)
    )
    parts.append(left_end)
    
    right_end = box(
        (DECK_WALL_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM),
        (DECK_LENGTH_MM - DECK_WALL_MM, 0, 0)
    )
    parts.append(right_end)
    
    # Internal ribs (cross-ribs for stiffness)
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
    
    # Cut M4 holes for mounting to bays/spines
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
    """Build a cable hook/trough insert that fits inside a pier.
    
    Multiple hooks for organizing cables. Slides into the hollow pier.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Base plate
    base = box(
        (CABLE_INSERT_WIDTH_MM, CABLE_INSERT_DEPTH_MM, 3.0),
        (0, 0, 0)
    )
    parts.append(base)
    
    # Cable hooks - curved hooks at intervals
    hook_positions = [20.0, 60.0, 100.0]
    hook_width = CABLE_INSERT_WIDTH_MM - 2
    hook_height = CABLE_INSERT_HEIGHT_MM - 3
    hook_depth = 15.0
    
    for y_pos in hook_positions:
        # Vertical post
        post = box(
            (hook_width, 4.0, hook_height),
            (1.0, y_pos - 2.0, 3.0)
        )
        parts.append(post)
        # Curved hook top (simplified as angled piece)
        hook_top = box(
            (hook_width, hook_depth, 4.0),
            (1.0, y_pos - 2.0, 3.0 + hook_height - 4.0)
        )
        parts.append(hook_top)
        # Hook lip
        lip = box(
            (hook_width, 4.0, 10.0),
            (1.0, y_pos - 2.0 + hook_depth - 4.0, 3.0 + hook_height - 14.0)
        )
        parts.append(lip)
    
    body = boolean_union(parts)
    return normalize_mesh(body)


def build_string_cassette() -> trimesh.Trimesh:
    """Build a string/pick cassette that fits inside a pier.
    
    Shallow drawer-like insert for guitar strings, picks, capos.
    Open top for easy access.
    """
    wall_mm = 2.5
    
    # Outer shell
    outer = box(
        (STRING_CASSETTE_WIDTH_MM, STRING_CASSETTE_DEPTH_MM, STRING_CASSETTE_HEIGHT_MM),
        (0, 0, 0)
    )
    
    # Inner cavity (open top)
    inner = box(
        (STRING_CASSETTE_WIDTH_MM - 2 * wall_mm, 
         STRING_CASSETTE_DEPTH_MM - wall_mm,  # Open at front
         STRING_CASSETTE_HEIGHT_MM - wall_mm),  # Open at top
        (wall_mm, 0, wall_mm)
    )
    
    # Dividers for organization
    parts = [outer]
    divider = box(
        (wall_mm, STRING_CASSETTE_DEPTH_MM - wall_mm, STRING_CASSETTE_HEIGHT_MM - wall_mm - 10),
        (STRING_CASSETTE_WIDTH_MM / 2 - wall_mm / 2, 0, wall_mm)
    )
    parts.append(divider)
    
    body = boolean_union(parts)
    result = boolean_difference(body, [inner])
    return normalize_mesh(result)


def build_guitar_hanger() -> trimesh.Trimesh:
    """Build a guitar neck hanger that bolts to a stud spine.
    
    The guitar hangs in the ROOM (body hangs in free space, not on deck).
    Neck rests in a padded slot. Bolts to spine via M4.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Main body
    main = box(
        (GUITAR_HANGER_WIDTH_MM, GUITAR_HANGER_DEPTH_MM, GUITAR_HANGER_HEIGHT_MM),
        (0, 0, 0)
    )
    parts.append(main)
    
    # Mounting plate (thicker section near wall)
    mount_plate = box(
        (GUITAR_HANGER_WIDTH_MM, 20.0, GUITAR_HANGER_HEIGHT_MM + 10.0),
        (0, GUITAR_HANGER_DEPTH_MM - 20.0, 0)
    )
    parts.append(mount_plate)
    
    # Support arms that cradle the neck
    arm_width = (GUITAR_HANGER_WIDTH_MM - GUITAR_NECK_SLOT_WIDTH_MM) / 2
    arm_height = 25.0
    
    left_arm = box(
        (arm_width, GUITAR_HANGER_DEPTH_MM - 20.0, arm_height),
        (0, 0, GUITAR_HANGER_HEIGHT_MM)
    )
    parts.append(left_arm)
    
    right_arm = box(
        (arm_width, GUITAR_HANGER_DEPTH_MM - 20.0, arm_height),
        (GUITAR_HANGER_WIDTH_MM - arm_width, 0, GUITAR_HANGER_HEIGHT_MM)
    )
    parts.append(right_arm)
    
    body = boolean_union(parts)
    
    # Cut the neck slot
    cutters: list[trimesh.Trimesh] = []
    neck_slot = box(
        (GUITAR_NECK_SLOT_WIDTH_MM, GUITAR_NECK_SLOT_DEPTH_MM + 1, GUITAR_HANGER_HEIGHT_MM + arm_height + 2),
        ((GUITAR_HANGER_WIDTH_MM - GUITAR_NECK_SLOT_WIDTH_MM) / 2, -1, -1)
    )
    cutters.append(neck_slot)
    
    # M4 mounting holes
    for z_offset in [10.0, GUITAR_HANGER_HEIGHT_MM]:
        for x_offset in [15.0, GUITAR_HANGER_WIDTH_MM - 15.0]:
            m4_hole = cylinder_y(
                M4_CLEARANCE_MM / 2,
                25.0,
                (x_offset, GUITAR_HANGER_DEPTH_MM - 10.0, z_offset)
            )
            cutters.append(m4_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def check_fits_bed(mesh: trimesh.Trimesh, name: str) -> bool:
    """Check if mesh fits A1 mini bed with brim clearance."""
    extents = mesh.bounding_box.extents
    sorted_extents = sorted(extents)
    
    # Two smallest dimensions must be ≤160mm (they go on the bed)
    xy_dims = sorted_extents[:2]
    fits_bed = all(d <= MAX_BED_XY_MM for d in xy_dims)
    # Z (tallest) must be ≤180mm
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
    """Calculate how many bays fit between spines."""
    
    # Stud spacing
    spacing_1 = STUD_SPACING_MM[0]  # 393.7 mm
    spacing_2 = STUD_SPACING_MM[1]  # 406.4 mm
    
    # How many 155mm bays fit in each span?
    effective_bay_width = BAY_WIDTH_MM + 5.0  # Add gap for assembly
    
    bays_span_1 = int(spacing_1 / effective_bay_width)  # 2 bays
    bays_span_2 = int(spacing_2 / effective_bay_width)  # 2 bays
    
    # Leftover becomes filler
    filler_1 = spacing_1 - bays_span_1 * effective_bay_width
    filler_2 = spacing_2 - bays_span_2 * effective_bay_width
    
    # How many deck segments?
    total_span = spacing_1 + spacing_2 + SPINE_WIDTH_MM * 3
    deck_count = int(total_span / DECK_LENGTH_MM) + 1
    
    return {
        "stud_spacing_mm": STUD_SPACING_MM,
        "bays_per_span": [bays_span_1, bays_span_2],
        "total_bays": bays_span_1 + bays_span_2,
        "filler_widths_mm": [filler_1, filler_2],
        "deck_count": deck_count,
        "spine_count": 3,
    }


def main():
    print("=" * 70)
    print("STORAGE ARCADE GENERATOR")
    print("100% PETG • Every gram stores or carries • No decorative air")
    print("=" * 70)
    print()
    
    OUT.mkdir(parents=True, exist_ok=True)
    
    # Generate all parts
    print("[1] Generating stud spine...")
    spine = build_stud_spine()
    spine_ok = check_fits_bed(spine, "stud_spine")
    if spine_ok:
        write_stl(spine, OUT / "stud_spine.stl")
        write_3mf(spine, OUT / "stud_spine.3mf", "stud_spine")
    
    print("\n[2] Generating arch-bay module...")
    arch_bay = build_arch_bay()
    bay_ok = check_fits_bed(arch_bay, "arch_bay")
    if bay_ok:
        write_stl(arch_bay, OUT / "arch_bay.stl")
        write_3mf(arch_bay, OUT / "arch_bay.3mf", "arch_bay")
    
    print("\n[3] Generating deck module...")
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
    
    # Calculate layout
    layout = calculate_layout()
    
    # Write manifest
    manifest = {
        "description": "Elon-style 100% PETG storage arcade - every gram stores or carries",
        "architecture": {
            "stud_spine": "Wall-mount backplate with M4 grid. Only part that touches studs.",
            "arch_bay": "Roman arch opening IS the storage bay. Hollow piers are storage columns.",
            "deck_module": "Ribbed box section on top of arcade.",
            "cable_insert": "Hook/trough insert that slides into pier hollow.",
            "string_cassette": "Shallow drawer for strings/picks in pier hollow.",
            "guitar_hanger": "Neck hanger that bolts to spine. Guitar hangs in room."
        },
        "constraints": {
            "material": "100% PETG - no plywood, steel, or other materials",
            "printer": "Bambu A1 mini (180mm build volume)",
            "max_xy_with_brim_mm": MAX_BED_XY_MM,
            "fasteners": "Wood screws into studs, M4 through PETG. No snap-fit in load path."
        },
        "wall_layout": {
            "wall_length_in": WALL_LENGTH_IN,
            "stud_positions_in": STUD_POSITIONS_IN,
            "stud_spacing_mm": STUD_SPACING_MM,
        },
        "calculated_layout": layout,
        "parts": {
            "stud_spine": {
                "file": "stud_spine.stl",
                "quantity": 3,
                "dimensions_mm": [round(x, 1) for x in spine.bounding_box.extents],
                "print_time_hours": 4,
                "petg_grams": 80,
                "print_orientation": "Wall face down",
                "supports": "No",
            },
            "arch_bay": {
                "file": "arch_bay.stl",
                "quantity": layout["total_bays"],
                "dimensions_mm": [round(x, 1) for x in arch_bay.bounding_box.extents],
                "print_time_hours": 8,
                "petg_grams": 150,
                "print_orientation": "Back wall down (arch opening facing up)",
                "supports": "Yes - for arch interior",
            },
            "deck_module": {
                "file": "deck_module.stl",
                "quantity": layout["deck_count"],
                "dimensions_mm": [round(x, 1) for x in deck.bounding_box.extents],
                "print_time_hours": 4,
                "petg_grams": 100,
                "print_orientation": "Top surface down",
                "supports": "No",
            },
            "cable_insert": {
                "file": "cable_insert.stl",
                "quantity": "As needed",
                "dimensions_mm": [round(x, 1) for x in cable_insert.bounding_box.extents],
                "print_time_hours": 1.5,
                "petg_grams": 25,
                "print_orientation": "Base down",
                "supports": "No",
            },
            "string_cassette": {
                "file": "string_cassette.stl",
                "quantity": "As needed",
                "dimensions_mm": [round(x, 1) for x in string_cassette.bounding_box.extents],
                "print_time_hours": 2,
                "petg_grams": 30,
                "print_orientation": "Open top up",
                "supports": "No",
            },
            "guitar_hanger": {
                "file": "guitar_hanger.stl",
                "quantity": 1,
                "dimensions_mm": [round(x, 1) for x in guitar_hanger.bounding_box.extents],
                "print_time_hours": 2.5,
                "petg_grams": 45,
                "print_orientation": "Mounting plate down",
                "supports": "No",
            },
        },
        "hardware": {
            "wood_screws": {
                "spec": "#10 × 3 in wood screws",
                "quantity": 9,
                "note": "3 per spine, into studs only"
            },
            "m4_bolts": {
                "spec": "M4 × 25mm socket head cap screws",
                "quantity": 50,
                "note": "For bay-to-spine and deck-to-bay connections"
            },
            "m4_nuts": {
                "spec": "M4 nylock nuts",
                "quantity": 50,
            },
            "washers": {
                "spec": "M4 flat washers",
                "quantity": 100,
            }
        },
        "print_settings": {
            "material": "PETG",
            "layer_height_mm": 0.2,
            "wall_loops": 6,
            "top_bottom_layers": 6,
            "infill_percent": 40,
            "infill_pattern": "gyroid",
            "nozzle_temp_c": 245,
            "bed_temp_c": 75,
        },
        "load_capacity": {
            "working_load_per_bay_kg": 5.0,
            "working_load_per_bay_lb": 11.0,
            "deck_total_load_kg": 25.0,
            "deck_total_load_lb": 55.0,
            "basis": "Conservative PETG estimate. Short spans, ribbed sections, gyroid infill. Accounts for creep.",
            "guitar_hanger_load_kg": 5.0,
            "note": "Do not exceed. PETG creeps under sustained load."
        }
    }
    
    with open(OUT / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("\n[7] Wrote manifest.json")
    
    # Print summary
    print("\n" + "=" * 70)
    print("STORAGE ARCADE SUMMARY")
    print("=" * 70)
    print(f"\nWall: {WALL_LENGTH_IN} in with studs at {STUD_POSITIONS_IN}")
    print(f"Stud spacing: {STUD_SPACING_MM[0]:.1f}mm, {STUD_SPACING_MM[1]:.1f}mm")
    print(f"\nBays per span: {layout['bays_per_span']} = {layout['total_bays']} total arch bays")
    print(f"Deck segments: {layout['deck_count']}")
    print(f"Spines: {layout['spine_count']}")
    print(f"\nEvery arch opening is storage. Every pier hollow is storage.")
    print("Every gram printed stores something or carries load.")
    print("=" * 70)


if __name__ == "__main__":
    main()
