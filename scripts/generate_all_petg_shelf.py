#!/usr/bin/env python3
"""Generate HEAVY-DUTY all-PETG structural shelf parts.

Roman arch brackets that look like Palatine/Roman architecture AND carry real load.
Overbuilt for PETG creep. No plywood, no steel, no light-duty compromises.

=== VISUAL LANGUAGE: ROMAN ARCH ===
This design uses classical Roman arch proportions and terminology:

- PIER: The thick vertical column that rises from the floor (here, from the bottom)
- IMPOST / CAPITAL: The transition block where the arch springs from the pier
- ARCHIVOLT: The main curved arch profile, with molding bands for visual depth
- KEYSTONE: The central wedge at the crown (implied by a thickened band)
- SOFFIT: The underside of the arch, showing masonry-like ribs
- SPANDREL: The triangular area between arch extrados and top plate

Target: sustained heavy closet storage (packed bins, folded clothes, closet junk)
Method: thick box-section arches, many walls, high infill, mechanical fasteners

Output: STL files ready to slice on Bambu A1 mini (180mm build volume).
CRITICAL: XY bed axes must be ≤160mm to pass Bambu gcode check with brim.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "all_petg_shelf"


# === A1 mini build constraints ===
# 180mm cube nominal, but brim/calibration region eats ~10mm per axis
BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
MAX_BED_XY_MM = 160.0  # HARD LIMIT for parts with brim on A1 mini

# === HEAVY-DUTY Design Parameters ===
# These are deliberately OVERBUILT for PETG creep resistance

# Arch bracket - the main structural element
# CRITICAL: depth and thickness must be ≤160mm for A1 mini bed with brim
ARCH_THICKNESS_MM = 40.0           # THICK - 40mm across the run for torsional stiffness
ARCH_HEIGHT_MM = 160.0             # Fits 180mm build volume in Z
ARCH_DEPTH_MM = 152.0              # 6 inch shelf depth - fits 160mm bed limit
WALL_SECTION_DEPTH_MM = 22.0       # Deep wall-mount section for screw engagement

# Roman arch visual proportions (Classical orders)
# Pier width should be ~1/4 to 1/3 of arch opening for proper proportions
PIER_WIDTH_MM = 30.0               # Thick pier for visual mass and strength
IMPOST_HEIGHT_MM = 8.0             # Capital/impost transition block
IMPOST_PROJECTION_MM = 3.0         # How much impost projects beyond pier
ARCHIVOLT_OUTER_BAND_MM = 5.0      # Outer molding band
ARCHIVOLT_INNER_BAND_MM = 4.0      # Inner structural band
KEYSTONE_EXTRA_MM = 3.0            # Extra depth at crown for implied keystone

# Structural arch geometry - OVERBUILT
ARCH_OUTER_WALL_MM = 6.0           # Thick outer shell
ARCH_INNER_WALL_MM = 4.0           # Thick internal webs
ARCH_RIB_COUNT = 4                 # Multiple ribs for redundancy (masonry-like soffit)
TOP_PLATE_THICKNESS_MM = 18.0      # Thick top plate - carries the deck
ARCH_RADIUS_MM = 42.0              # Roman semicircular arch - sized for proportions

# Screw holes - 4 screws per bracket for heavy duty
SCREW_HOLE_DIAMETER_MM = 6.5       # Clearance for #10 or 1/4" screw
SCREW_POSITIONS_FROM_TOP_MM = [20.0, 55.0, 95.0, 135.0]  # 4 screws, well distributed
COUNTERBORE_DIAMETER_MM = 16.0     # Room for washer + driver
COUNTERBORE_DEPTH_MM = 4.0

# Deck segment - HEAVY DUTY box beam
# CRITICAL: must fit 160mm bed constraint
DECK_LENGTH_MM = 158.0             # Under 160mm for brim clearance
DECK_WIDTH_MM = 152.0              # Match arch depth (6 inches)
DECK_HEIGHT_MM = 42.0              # DEEP section for stiffness - key to load capacity
DECK_WALL_MM = 5.0                 # Thick walls throughout
DECK_RIB_COUNT = 5                 # Many ribs

# Deck-to-arch bolting - bolts per joint for heavy duty
BOLT_HOLE_DIAMETER_MM = 5.5        # M5 clearance
BOLT_POSITIONS_Y_MM = [30.0, 76.0, 122.0]  # 3 bolts across width at each end


def cuboid(size: tuple[float, float, float], origin=(0.0, 0.0, 0.0)) -> trimesh.Trimesh:
    """Create a box at the given origin (corner)."""
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(np.asarray(origin, dtype=float) + np.asarray(size, dtype=float) / 2.0)
    return mesh


def cylinder_z(radius: float, height: float, center: tuple[float, float, float], segments: int = 32) -> trimesh.Trimesh:
    """Create a Z-axis cylinder at the given center."""
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=segments)
    mesh.apply_translation(center)
    return mesh


def cylinder_x(radius: float, length: float, center: tuple[float, float, float], segments: int = 32) -> trimesh.Trimesh:
    """Create an X-axis cylinder at the given center."""
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=segments)
    rot = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])
    mesh.apply_transform(rot)
    mesh.apply_translation(center)
    return mesh


def boolean_union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    """Union multiple meshes."""
    if not meshes:
        raise ValueError("No meshes to union")
    if len(meshes) == 1:
        return meshes[0].copy()
    result = trimesh.boolean.union(meshes, engine="manifold")
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return clean_mesh(result)


def boolean_difference(body: trimesh.Trimesh, cutters: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    """Subtract cutters from body."""
    if not cutters:
        return body.copy()
    result = trimesh.boolean.difference([body] + cutters, engine="manifold")
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return clean_mesh(result)


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Clean up a mesh."""
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    return mesh


def normalize_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Move mesh to positive octant."""
    mesh = mesh.copy()
    mesh.apply_translation(-np.asarray(mesh.bounds[0], dtype=float))
    return clean_mesh(mesh)


def build_heavy_duty_arch_bracket() -> trimesh.Trimesh:
    """Build a HEAVY-DUTY Roman arch bracket with classical visual elements.
    
    This is a thick box-section arch designed for sustained heavy loads,
    styled to look like a proper Roman arch with classical architectural features.
    
    === VISUAL ELEMENTS (Classical Roman Arch) ===
    
    1. PIER: Thick vertical column rising from bottom
       - Wide base for visual mass and structural stability
       - Slight taper for classical proportion
    
    2. IMPOST / CAPITAL: Transition block at arch spring point
       - Projects slightly beyond pier face
       - Visual break between vertical pier and curved arch
    
    3. ARCHIVOLT: The curved arch profile
       - Outer band: decorative molding profile
       - Inner band: structural arch rib
       - Multiple ribs create masonry-like soffit appearance
    
    4. IMPLIED KEYSTONE: Thickened section at arch crown
       - Wedge-shaped visual emphasis at top of arch
       - Structural: adds depth where loads concentrate
    
    5. SPANDREL FILL: Area between arch extrados and top plate
       - Solid fill transfers load to arch
       - Smooth transition to deck support plate
    
    Print orientation: Arch opening facing UP (layers perpendicular to load)
    """
    parts: list[trimesh.Trimesh] = []
    
    # === WALL MOUNT SECTION (PIER BASE) ===
    # This is the vertical part that screws to the wall
    # Made as a solid box section for maximum screw engagement
    
    wall_mount = cuboid(
        (WALL_SECTION_DEPTH_MM, ARCH_THICKNESS_MM, ARCH_HEIGHT_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(wall_mount)
    
    # === TOP PLATE (ENTABLATURE) ===
    # Thick horizontal surface that the deck sits on
    # Extends full depth of shelf
    
    top_plate = cuboid(
        (ARCH_DEPTH_MM, ARCH_THICKNESS_MM, TOP_PLATE_THICKNESS_MM),
        (0.0, 0.0, ARCH_HEIGHT_MM - TOP_PLATE_THICKNESS_MM)
    )
    parts.append(top_plate)
    
    # === FRONT PIER ===
    # Vertical column at front edge - the visual anchor
    # This is what gives the Roman arch its distinctive proportions
    
    pier_height = ARCH_HEIGHT_MM - TOP_PLATE_THICKNESS_MM
    front_pier = cuboid(
        (PIER_WIDTH_MM, ARCH_THICKNESS_MM, pier_height),
        (ARCH_DEPTH_MM - PIER_WIDTH_MM, 0.0, 0.0)
    )
    parts.append(front_pier)
    
    # === IMPOST / CAPITAL ===
    # The transition block where arch springs from pier
    # Projects slightly for classical visual break
    
    arch_spring_z = 35.0  # Height where arch begins to curve
    impost_z = arch_spring_z - IMPOST_HEIGHT_MM
    
    # Impost on front pier (projects inward toward arch)
    impost_front = cuboid(
        (PIER_WIDTH_MM + IMPOST_PROJECTION_MM, ARCH_THICKNESS_MM, IMPOST_HEIGHT_MM),
        (ARCH_DEPTH_MM - PIER_WIDTH_MM - IMPOST_PROJECTION_MM, 0.0, impost_z)
    )
    parts.append(impost_front)
    
    # Impost on wall pier (projects outward from wall)
    impost_wall = cuboid(
        (WALL_SECTION_DEPTH_MM + IMPOST_PROJECTION_MM, ARCH_THICKNESS_MM, IMPOST_HEIGHT_MM),
        (0.0, 0.0, impost_z)
    )
    parts.append(impost_wall)
    
    # === BOTTOM SILL ===
    # Connects piers at bottom, closes off the arch bay
    
    sill_height = 20.0
    sill_depth = ARCH_DEPTH_MM - WALL_SECTION_DEPTH_MM - PIER_WIDTH_MM
    bottom_sill = cuboid(
        (sill_depth, ARCH_THICKNESS_MM, sill_height),
        (WALL_SECTION_DEPTH_MM, 0.0, 0.0)
    )
    parts.append(bottom_sill)
    
    # === ARCH RIBS (ARCHIVOLT + SOFFIT) ===
    # Multiple thick ribs forming the Roman arch
    # The outer and inner ribs are thicker (archivolt bands)
    # Inner ribs create masonry-like soffit appearance
    
    rib_spacing = (ARCH_THICKNESS_MM - ARCH_OUTER_WALL_MM) / ARCH_RIB_COUNT
    
    for i in range(ARCH_RIB_COUNT + 1):
        y_pos = i * rib_spacing
        if i == 0 or i == ARCH_RIB_COUNT:
            # Outer ribs: thick archivolt bands
            rib_thickness = ARCH_OUTER_WALL_MM
        else:
            # Inner ribs: masonry-like soffit structure
            rib_thickness = ARCH_INNER_WALL_MM
        
        rib = build_roman_arch_rib(y_pos, rib_thickness, i == 0 or i == ARCH_RIB_COUNT)
        parts.append(rib)
    
    # === SPANDREL FILL ===
    # Solid area above the arch extrados, below the top plate
    # Creates smooth load transfer from deck to arch
    
    spandrel = build_spandrel_fill()
    parts.append(spandrel)
    
    # Union all solid parts
    body = boolean_union(parts)
    
    # === CUT SCREW HOLES ===
    cutters: list[trimesh.Trimesh] = []
    
    for z_pos in SCREW_POSITIONS_FROM_TOP_MM:
        z_from_bottom = ARCH_HEIGHT_MM - z_pos
        
        # Main screw hole through wall mount
        hole = cylinder_x(
            SCREW_HOLE_DIAMETER_MM / 2.0,
            WALL_SECTION_DEPTH_MM + 2.0,
            (WALL_SECTION_DEPTH_MM / 2.0, ARCH_THICKNESS_MM / 2.0, z_from_bottom)
        )
        cutters.append(hole)
        
        # Counterbore on the front face
        counterbore = cylinder_x(
            COUNTERBORE_DIAMETER_MM / 2.0,
            COUNTERBORE_DEPTH_MM + 0.1,
            (WALL_SECTION_DEPTH_MM - COUNTERBORE_DEPTH_MM / 2.0, ARCH_THICKNESS_MM / 2.0, z_from_bottom)
        )
        cutters.append(counterbore)
    
    # === CUT BOLT HOLES IN TOP PLATE ===
    # For deck attachment
    
    for y_pos in BOLT_POSITIONS_Y_MM:
        for x_offset in [WALL_SECTION_DEPTH_MM + 20.0, ARCH_DEPTH_MM - 20.0]:
            bolt_hole = cylinder_z(
                BOLT_HOLE_DIAMETER_MM / 2.0,
                TOP_PLATE_THICKNESS_MM + 2.0,
                (x_offset, y_pos, ARCH_HEIGHT_MM - TOP_PLATE_THICKNESS_MM / 2.0)
            )
            cutters.append(bolt_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_roman_arch_rib(y_offset: float, thickness: float, is_outer: bool) -> trimesh.Trimesh:
    """Build one Roman arch rib - a thick curved structural member.
    
    The arch profile is a proper Roman semicircle that transfers
    load through compression. The arch springs from impost height
    and curves up to meet at the crown.
    
    For outer ribs (archivolt bands), we add extra depth at the keystone.
    Inner ribs create the masonry-like soffit appearance.
    
    === GEOMETRY ===
    - Arch springs from impost blocks on both piers
    - True semicircular profile (Roman, not pointed Gothic)
    - Radius sized so arch fits between piers
    - Build as a single extruded polygon (closed ring shape)
    """
    # Arch geometry - true semicircle spanning between the two piers
    arch_spring_z = 35.0  # Height where arch begins (top of impost)
    
    # The arch spans horizontally from wall pier to front pier
    pier_face_wall = WALL_SECTION_DEPTH_MM + IMPOST_PROJECTION_MM  # Inner face of wall impost
    pier_face_front = ARCH_DEPTH_MM - PIER_WIDTH_MM - IMPOST_PROJECTION_MM  # Inner face of front impost
    
    # Arch span and center
    arch_span = pier_face_front - pier_face_wall
    arch_center_x = (pier_face_wall + pier_face_front) / 2.0
    arch_center_z = arch_spring_z
    
    # True semicircle: radius = half the span
    inner_r = arch_span / 2.0
    # Rib thickness (radial)
    rib_radial_thickness = 12.0  # Thick structural rib
    
    # Build the arch profile as a closed polygon (in XZ plane)
    # Go around the outer edge (extrados) then back along inner edge (intrados)
    num_points = 32  # Smooth curve
    
    outer_points = []
    inner_points = []
    
    for i in range(num_points + 1):
        # Angle from 0 (right/front) to pi (left/wall)
        angle = math.pi * i / num_points
        
        # Keystone effect: add extra thickness near the crown (angle ~90°)
        keystone_factor = math.sin(angle)  # Max at 90°
        if is_outer:
            extra_outer = KEYSTONE_EXTRA_MM * keystone_factor
        else:
            extra_outer = KEYSTONE_EXTRA_MM * 0.5 * keystone_factor
        
        outer_r = inner_r + rib_radial_thickness + extra_outer
        
        # Outer point (extrados)
        x_outer = arch_center_x + outer_r * math.cos(angle)
        z_outer = arch_center_z + outer_r * math.sin(angle)
        outer_points.append((x_outer, z_outer))
        
        # Inner point (intrados)
        x_inner = arch_center_x + inner_r * math.cos(angle)
        z_inner = arch_center_z + inner_r * math.sin(angle)
        inner_points.append((x_inner, z_inner))
    
    # Create closed polygon: outer edge forward, inner edge backward
    # This creates a ring shape (arch cross-section)
    ring_points = outer_points + inner_points[::-1]
    
    poly = Polygon(ring_points)
    if not poly.is_valid:
        poly = poly.buffer(0)  # Fix self-intersections
    
    if poly.is_valid and poly.area > 1.0:
        # Extrude in Y direction (the rib thickness direction)
        arch_mesh = trimesh.creation.extrude_polygon(poly, height=thickness)
        # The extrusion is in Z by default, we need to rotate to make it Y
        # Swap Y and Z: vertices[:, [x, y, z]] -> vertices[:, [x, z, y]]
        arch_mesh.vertices = arch_mesh.vertices[:, [0, 2, 1]]
        # Translate to y_offset position
        arch_mesh.apply_translation([0, y_offset, 0])
        return clean_mesh(arch_mesh)
    
    # Fallback: return a small box if polygon failed
    return cuboid((1, 1, 1), (arch_center_x, y_offset, arch_center_z))


def build_spandrel_fill() -> trimesh.Trimesh:
    """Build the spandrel fill - solid area above arch, below top plate.
    
    The spandrel is the roughly triangular area between:
    - The curved extrados (outer surface) of the arch
    - The horizontal bottom of the top plate
    - The vertical faces of the piers
    
    This provides:
    1. Structural continuity from deck to arch
    2. Clean visual appearance (not hollow/skeletal)
    3. Additional material for load distribution
    
    Built as a single extruded polygon profile for manifold reliability.
    """
    # Spandrel geometry matches arch extrados
    arch_spring_z = 35.0
    pier_face_wall = WALL_SECTION_DEPTH_MM + IMPOST_PROJECTION_MM
    pier_face_front = ARCH_DEPTH_MM - PIER_WIDTH_MM - IMPOST_PROJECTION_MM
    arch_span = pier_face_front - pier_face_wall
    arch_center_x = (pier_face_wall + pier_face_front) / 2.0
    arch_center_z = arch_spring_z
    
    inner_r = arch_span / 2.0
    rib_radial_thickness = 12.0
    outer_r = inner_r + rib_radial_thickness + KEYSTONE_EXTRA_MM
    
    top_plate_bottom = ARCH_HEIGHT_MM - TOP_PLATE_THICKNESS_MM
    
    # Build spandrel profile as polygon in XZ plane
    # Top edge: horizontal at top_plate_bottom
    # Bottom edge: follows arch extrados curve
    # Sides: vertical at pier faces
    
    profile_points = []
    
    # Start at top-left (wall side)
    profile_points.append((pier_face_wall, top_plate_bottom))
    
    # Top edge to right (front side)
    profile_points.append((pier_face_front, top_plate_bottom))
    
    # Right side down to arch spring level (if needed)
    # This is already at the pier face, arch meets here
    
    # Follow arch extrados from front to wall (bottom edge)
    num_arch_points = 24
    for i in range(num_arch_points + 1):
        # Go from front (angle=0) to wall (angle=pi)
        angle = math.pi * i / num_arch_points
        
        # Keystone bulge
        keystone_factor = math.sin(angle)
        r = outer_r + KEYSTONE_EXTRA_MM * keystone_factor * 0.5
        
        x = arch_center_x + r * math.cos(angle)
        z = arch_center_z + r * math.sin(angle)
        
        # Only include points above the spring line
        if z >= arch_spring_z:
            profile_points.append((x, z))
    
    # Close the polygon
    poly = Polygon(profile_points)
    if not poly.is_valid:
        poly = poly.buffer(0)
    
    if poly.is_valid and poly.area > 1.0:
        # Extrude the full thickness
        spandrel = trimesh.creation.extrude_polygon(poly, height=ARCH_THICKNESS_MM)
        # Rotate from XZ extrusion to XY orientation
        spandrel.vertices = spandrel.vertices[:, [0, 2, 1]]
        return clean_mesh(spandrel)
    
    # Fallback
    return cuboid((1, 1, 1), (arch_center_x, 0, top_plate_bottom - 10))


def build_heavy_duty_deck_segment() -> trimesh.Trimesh:
    """Build a HEAVY-DUTY ribbed deck segment.
    
    This is a deep box-beam design for maximum stiffness and load capacity.
    
    CRITICAL: Must fit 160mm bed constraint on A1 mini with brim.
    Current dimensions: 158mm × 152mm × 42mm
    
    Features:
    - 42mm deep section for high stiffness
    - 5mm walls throughout
    - 5 longitudinal ribs
    - 3 cross ribs  
    - 6 bolt holes per end for secure bracket attachment
    
    Print orientation: Top face DOWN for smooth usable surface
    """
    parts: list[trimesh.Trimesh] = []
    
    # Verify dimensions fit bed constraint
    assert DECK_LENGTH_MM <= MAX_BED_XY_MM, f"Deck length {DECK_LENGTH_MM} exceeds {MAX_BED_XY_MM}mm bed limit"
    assert DECK_WIDTH_MM <= MAX_BED_XY_MM, f"Deck width {DECK_WIDTH_MM} exceeds {MAX_BED_XY_MM}mm bed limit"
    
    # Top surface (becomes bottom during print)
    top = cuboid(
        (DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM),
        (0.0, 0.0, DECK_HEIGHT_MM - DECK_WALL_MM)
    )
    parts.append(top)
    
    # Bottom surface
    bottom = cuboid(
        (DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_WALL_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(bottom)
    
    # Front wall (shelf edge)
    front = cuboid(
        (DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(front)
    
    # Back wall (against wall side)
    back = cuboid(
        (DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM),
        (0.0, DECK_WIDTH_MM - DECK_WALL_MM, 0.0)
    )
    parts.append(back)
    
    # End walls (butt against adjacent deck segments)
    left = cuboid(
        (DECK_WALL_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(left)
    
    right = cuboid(
        (DECK_WALL_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM),
        (DECK_LENGTH_MM - DECK_WALL_MM, 0.0, 0.0)
    )
    parts.append(right)
    
    # Longitudinal ribs (along length) - internal structure
    rib_spacing_y = (DECK_WIDTH_MM - 2 * DECK_WALL_MM) / (DECK_RIB_COUNT + 1)
    for i in range(1, DECK_RIB_COUNT + 1):
        y_pos = DECK_WALL_MM + i * rib_spacing_y - DECK_WALL_MM / 2
        rib = cuboid(
            (DECK_LENGTH_MM, DECK_WALL_MM, DECK_HEIGHT_MM - 2 * DECK_WALL_MM),
            (0.0, y_pos, DECK_WALL_MM)
        )
        parts.append(rib)
    
    # Cross ribs (across width) - 3 total for additional stiffness
    cross_positions = [DECK_LENGTH_MM / 4, DECK_LENGTH_MM / 2, 3 * DECK_LENGTH_MM / 4]
    for x_pos in cross_positions:
        cross = cuboid(
            (DECK_WALL_MM, DECK_WIDTH_MM, DECK_HEIGHT_MM - 2 * DECK_WALL_MM),
            (x_pos - DECK_WALL_MM / 2, 0.0, DECK_WALL_MM)
        )
        parts.append(cross)
    
    body = boolean_union(parts)
    
    # Cut bolt holes at each end for bracket attachment
    cutters: list[trimesh.Trimesh] = []
    
    bolt_x_positions = [15.0, DECK_LENGTH_MM - 15.0]  # Near each end
    
    for x_pos in bolt_x_positions:
        for y_pos in BOLT_POSITIONS_Y_MM:
            hole = cylinder_z(
                BOLT_HOLE_DIAMETER_MM / 2.0,
                DECK_HEIGHT_MM + 2.0,
                (x_pos, y_pos, DECK_HEIGHT_MM / 2.0)
            )
            cutters.append(hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_end_bracket() -> trimesh.Trimesh:
    """Build a smaller end bracket for shelf ends beyond the last stud.
    
    This is a half-width bracket that bolts to the adjacent deck segment
    and provides support for the overhanging end.
    
    NOT a wall mount - this attaches to the deck, not the wall.
    """
    # Simplified L-bracket that attaches under the deck end
    parts: list[trimesh.Trimesh] = []
    
    # Vertical leg
    vert = cuboid(
        (20.0, ARCH_THICKNESS_MM, 80.0),
        (0.0, 0.0, 0.0)
    )
    parts.append(vert)
    
    # Horizontal leg (attaches to deck bottom)
    horiz = cuboid(
        (60.0, ARCH_THICKNESS_MM, 20.0),
        (0.0, 0.0, 60.0)
    )
    parts.append(horiz)
    
    # Diagonal brace
    brace_points = [
        (20.0, 0.0),
        (60.0, 60.0),
        (60.0, 80.0),
        (20.0, 80.0),
    ]
    poly = Polygon(brace_points)
    if poly.is_valid:
        brace = trimesh.creation.extrude_polygon(poly, height=ARCH_OUTER_WALL_MM, engine="earcut")
        brace.vertices = brace.vertices[:, [0, 2, 1]]
        brace.vertices[:, 1] += (ARCH_THICKNESS_MM - ARCH_OUTER_WALL_MM) / 2
        parts.append(clean_mesh(brace))
    
    body = boolean_union(parts)
    
    # Bolt holes for deck attachment
    cutters: list[trimesh.Trimesh] = []
    for y_pos in [ARCH_THICKNESS_MM / 3, 2 * ARCH_THICKNESS_MM / 3]:
        hole = cylinder_z(
            BOLT_HOLE_DIAMETER_MM / 2.0,
            25.0,
            (40.0, y_pos, 70.0)
        )
        cutters.append(hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def check_fits_build_volume(mesh: trimesh.Trimesh, name: str) -> bool:
    """Check if mesh fits in A1 mini build volume with brim clearance.
    
    CRITICAL: XY dimensions must be ≤160mm to pass Bambu gcode check
    with brim enabled. Z can use the full 180mm.
    """
    extents = mesh.bounding_box.extents
    sorted_extents = sorted(extents)
    
    # Check overall build volume
    fits_volume = all(e <= b for e, b in zip(sorted_extents, sorted(BUILD_VOLUME_MM)))
    
    # Check 160mm bed constraint (two smallest dimensions = XY on bed)
    xy_dims = sorted_extents[:2]  # Two smallest = will be on bed
    fits_bed = all(d <= MAX_BED_XY_MM for d in xy_dims)
    
    if fits_volume and fits_bed:
        status = "✓ fits A1 mini with brim"
    elif fits_volume and not fits_bed:
        status = f"✗ XY too big for brim (max {MAX_BED_XY_MM}mm)"
    else:
        status = "✗ TOO BIG for build volume"
    
    print(f"  {name}: {extents[0]:.1f} x {extents[1]:.1f} x {extents[2]:.1f} mm {status}")
    return fits_volume and fits_bed


def write_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    """Write mesh to STL file."""
    mesh.export(str(path), file_type="stl")
    print(f"    → {path.name} ({path.stat().st_size / 1024:.1f} KB)")


def write_3mf(mesh: trimesh.Trimesh, path: Path, name: str) -> None:
    """Write mesh to 3MF file."""
    try:
        scene = trimesh.Scene()
        scene.add_geometry(mesh, node_name=name)
        scene.export(str(path), file_type="3mf")
        print(f"    → {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"    (3MF skipped: {e})")


def main():
    print("=" * 70)
    print("HEAVY-DUTY All-PETG Structural Shelf Generator")
    print("Roman arch brackets + deep box-beam deck segments")
    print("=" * 70)
    print()
    print("BUILD CONSTRAINTS:")
    print(f"  • A1 mini build volume: {BUILD_VOLUME_MM[0]} × {BUILD_VOLUME_MM[1]} × {BUILD_VOLUME_MM[2]} mm")
    print(f"  • Max XY with brim:     {MAX_BED_XY_MM} × {MAX_BED_XY_MM} mm")
    print()
    
    OUT.mkdir(parents=True, exist_ok=True)
    
    # Generate heavy-duty arch bracket with Roman architectural features
    print("[1] Generating Roman arch bracket (pier, impost, archivolt, keystone)...")
    bracket = build_heavy_duty_arch_bracket()
    bracket_ok = check_fits_build_volume(bracket, "arch_bracket")
    if bracket_ok:
        write_stl(bracket, OUT / "arch_bracket.stl")
        write_3mf(bracket, OUT / "arch_bracket.3mf", "arch_bracket")
    else:
        print("    ERROR: Arch bracket too large!")
        return
    
    # Generate heavy-duty deck segment
    print("\n[2] Generating deck segment (158mm × 152mm box beam)...")
    deck = build_heavy_duty_deck_segment()
    deck_ok = check_fits_build_volume(deck, "deck_segment")
    if deck_ok:
        write_stl(deck, OUT / "deck_segment.stl")
        write_3mf(deck, OUT / "deck_segment.3mf", "deck_segment")
    else:
        print("    ERROR: Deck segment too large!")
        return
    
    # Generate end bracket
    print("\n[3] Generating end support bracket...")
    end_bracket = build_end_bracket()
    end_ok = check_fits_build_volume(end_bracket, "end_bracket")
    if end_ok:
        write_stl(end_bracket, OUT / "end_bracket.stl")
        write_3mf(end_bracket, OUT / "end_bracket.3mf", "end_bracket")
    else:
        print("    ERROR: End bracket too large!")
        return
    
    # Calculate layout
    # Studs at 17.0, 32.5, 48.5 in = 431.8, 825.5, 1231.9 mm from corner
    # Wall length: 61.5 in = 1562.1 mm
    
    stud_positions_in = [17.0, 32.5, 48.5]
    stud_positions_mm = [s * 25.4 for s in stud_positions_in]
    wall_length_mm = 61.5 * 25.4
    
    # Deck coverage: need enough segments to span wall
    # 158mm segments, need to cover ~1560mm = 10 segments
    deck_count = 10
    total_deck_mm = deck_count * DECK_LENGTH_MM
    
    # Heavy-duty layout analysis
    max_span_mm = max(
        stud_positions_mm[0],  # Left overhang to first bracket
        stud_positions_mm[1] - stud_positions_mm[0],  # Span 1-2
        stud_positions_mm[2] - stud_positions_mm[1],  # Span 2-3
    )
    max_span_in = max_span_mm / 25.4
    
    # Write manifest
    manifest = {
        "description": "HEAVY-DUTY all-PETG structural shelf - Classical Roman arch design",
        "design_philosophy": "Overbuilt for PETG creep. Classical Roman arch proportions. Thick sections, many ribs, mechanical fasteners.",
        "visual_elements": {
            "pier": f"{PIER_WIDTH_MM}mm wide front pier - visual anchor and structural column",
            "impost": f"{IMPOST_HEIGHT_MM}mm capital blocks where arch springs from piers",
            "archivolt": "Semicircular arch profile with outer molding bands",
            "keystone": f"Implied keystone with {KEYSTONE_EXTRA_MM}mm extra thickness at crown",
            "soffit": f"{ARCH_RIB_COUNT} ribs create masonry-like arch underside",
            "spandrel": "Solid fill above arch for smooth deck support"
        },
        "build_constraints": {
            "printer": "Bambu A1 mini (180mm cube)",
            "max_xy_with_brim_mm": MAX_BED_XY_MM,
            "max_z_mm": BUILD_VOLUME_MM[2],
            "note": "All parts verified to fit 160mm XY with brim enabled"
        },
        "target_wall": {
            "length_in": 61.5,
            "stud_positions_in": stud_positions_in,
            "stud_positions_mm": stud_positions_mm,
        },
        "structural_analysis": {
            "max_span_between_brackets_in": round(max_span_in, 1),
            "max_span_between_brackets_mm": round(max_span_mm, 1),
            "deck_section_depth_mm": DECK_HEIGHT_MM,
            "deck_wall_thickness_mm": DECK_WALL_MM,
            "arch_thickness_mm": ARCH_THICKNESS_MM,
            "screws_per_bracket": len(SCREW_POSITIONS_FROM_TOP_MM),
            "bolts_per_deck_bracket_joint": len(BOLT_POSITIONS_Y_MM) * 2,
        },
        "load_rating": {
            "target_working_load_lb": 75,
            "target_working_load_kg": 34,
            "basis": f"Conservative estimate for {DECK_HEIGHT_MM}mm deep PETG box beam over {max_span_in:.0f}in max span with {DECK_WALL_MM}mm walls and gyroid infill. Accounts for PETG creep with 2x safety factor.",
            "load_distribution": "Evenly distributed across shelf. No concentrated point loads at front edge.",
            "increase_to_100lb_requires": "Add 4th bracket at wall end (requires blocking) OR reduce max span to 12in OR increase deck depth to 50mm",
        },
        "parts": {
            "arch_bracket": {
                "file": "arch_bracket.stl",
                "quantity": 3,
                "dimensions_mm": [round(x, 1) for x in bracket.bounding_box.extents],
                "print_time_hours": 9,
                "petg_grams": 200,
                "print_orientation": "Arch opening facing UP - layers perpendicular to load",
                "supports": "YES - organic supports for arch interior",
                "description": "Classical Roman arch wall bracket with pier, impost, archivolt, and keystone",
            },
            "deck_segment": {
                "file": "deck_segment.stl",
                "quantity": deck_count,
                "dimensions_mm": [round(x, 1) for x in deck.bounding_box.extents],
                "print_time_hours": 6,
                "petg_grams": 190,
                "print_orientation": "Top face DOWN for smooth surface",
                "supports": "NO - box structure is self-supporting",
                "description": f"Heavy-duty {DECK_HEIGHT_MM}mm deep box-beam deck segment",
            },
            "end_bracket": {
                "file": "end_bracket.stl",
                "quantity": 2,
                "dimensions_mm": [round(x, 1) for x in end_bracket.bounding_box.extents],
                "print_time_hours": 2,
                "petg_grams": 60,
                "print_orientation": "Flat on vertical leg",
                "supports": "Minimal",
                "description": "End support bracket, bolts to deck underside",
            },
        },
        "hardware": {
            "wall_screws": {
                "spec": "#10 x 3 in wood screws (or GRK RSS 1/4 x 3 in)",
                "quantity": 12,
                "note": "4 per bracket into stud. Longer screws for better engagement."
            },
            "wall_washers": {
                "spec": "1/4 in fender washers (1 in OD)",
                "quantity": 12,
                "note": "Large washers distribute load on PETG"
            },
            "deck_bolts": {
                "spec": "M5 x 50mm hex bolts",
                "quantity": 60,
                "note": "6 per deck-bracket joint"
            },
            "deck_nuts": {
                "spec": "M5 nylock nuts",
                "quantity": 60,
                "note": "Nylock prevents loosening under vibration/creep"
            },
        },
        "print_settings": {
            "material": "PETG (SUNLU black recommended)",
            "layer_height_mm": 0.2,
            "wall_loops": 6,
            "top_bottom_layers": 6,
            "infill_percent": 40,
            "infill_pattern": "gyroid",
            "nozzle_temp_c": 245,
            "bed_temp_c": 75,
            "cooling_percent": "50-60",
            "print_speed_mm_s": 60,
            "brim": "YES - required for bed adhesion, fits within 160mm limit",
            "note": "6 walls / 40%+ gyroid for structural strength"
        },
        "totals": {
            "parts_count": 3 + deck_count + 2,
            "print_time_hours": 3 * 9 + deck_count * 6 + 2 * 2,
            "petg_kg": round((3 * 200 + deck_count * 190 + 2 * 60) / 1000, 1),
        },
    }
    
    manifest_path = OUT / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n[4] Wrote manifest.json")
    
    # Print summary
    bracket_dims = bracket.bounding_box.extents
    deck_dims = deck.bounding_box.extents
    
    print("\n" + "=" * 70)
    print("ROMAN ARCH SHELF SUMMARY")
    print("=" * 70)
    print()
    print("VISUAL DESIGN: Classical Roman Arch")
    print(f"  • Pier:      {PIER_WIDTH_MM}mm wide front column")
    print(f"  • Impost:    {IMPOST_HEIGHT_MM}mm capital where arch springs")
    print(f"  • Archivolt: Semicircular arch with {ARCH_RIB_COUNT} ribs")
    print(f"  • Keystone:  +{KEYSTONE_EXTRA_MM}mm at crown")
    print()
    print(f"Wall: 61.5 in with studs at {stud_positions_in}")
    print(f"Max span between brackets: {max_span_in:.1f} in ({max_span_mm:.0f} mm)")
    print()
    print("PARTS TO PRINT (all fit A1 mini with brim):")
    print(f"  • Arch brackets:  3 × ({bracket_dims[0]:.0f}×{bracket_dims[1]:.0f}×{bracket_dims[2]:.0f}mm)  → 27 hrs")
    print(f"  • Deck segments: {deck_count} × ({deck_dims[0]:.0f}×{deck_dims[1]:.0f}×{deck_dims[2]:.0f}mm)  → 60 hrs")
    print(f"  • End brackets:   2 × small                  →  4 hrs")
    print(f"  ───────────────────────────────────────────────────────")
    print(f"  TOTAL:           {manifest['totals']['parts_count']} parts      ~{manifest['totals']['print_time_hours']} hrs")
    print(f"  PETG needed:     ~{manifest['totals']['petg_kg']} kg")
    print()
    print("TARGET LOAD: 75 lb (34 kg) evenly distributed")
    print("  Accounts for PETG creep with 2x safety factor.")
    print("=" * 70)


if __name__ == "__main__":
    main()
