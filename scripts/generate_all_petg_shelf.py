#!/usr/bin/env python3
"""Generate structural all-PETG shelf parts: Roman arch brackets and ribbed deck segments.

This is NOT the 102-piece Palatine ornamental pipeline. This generates real
structural parts that carry load through printed PETG arches screwed into studs.

Output: STL files ready to slice on Bambu A1 mini (180mm build volume).
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


# === Design Parameters ===

# A1 mini build volume
BUILD_VOLUME_MM = (180.0, 180.0, 180.0)

# Arch bracket dimensions (fits in 180mm cube when printed on side)
ARCH_THICKNESS_MM = 32.0          # Thickness across the run (Z in print orientation)
ARCH_HEIGHT_MM = 160.0            # Total height from shelf top to bottom of wall mount
ARCH_DEPTH_MM = 152.0             # Projection from wall (shelf depth = 6 inches)
WALL_MOUNT_WIDTH_MM = 20.0        # Width of wall-hugging section
WALL_MOUNT_THICKNESS_MM = 16.0    # Thickness of wall mount plate

# Structural arch geometry
ARCH_RIB_THICKNESS_MM = 12.0      # Thickness of arch ribs
TOP_PLATE_THICKNESS_MM = 16.0     # Thickness of shelf-supporting top plate
ARCH_INNER_RADIUS_MM = 50.0       # Inner radius of the Roman arch opening

# Screw holes for wall mounting (3 holes per bracket)
SCREW_HOLE_DIAMETER_MM = 6.0      # Clearance for #10 or 1/4" screw
SCREW_HOLE_POSITIONS_MM = [30.0, 80.0, 130.0]  # Distance from top of bracket
COUNTERBORE_DIAMETER_MM = 14.0    # For washer seating
COUNTERBORE_DEPTH_MM = 3.0        # Depth of counterbore

# Deck segment dimensions
DECK_LENGTH_MM = 160.0            # Length of one deck segment (printable)
DECK_WIDTH_MM = 152.0             # Same as arch depth (6 inches)
DECK_THICKNESS_MM = 24.0          # Total deck thickness
DECK_TOP_THICKNESS_MM = 3.0       # Top surface thickness
DECK_BOTTOM_THICKNESS_MM = 3.0    # Bottom surface thickness
DECK_RIB_THICKNESS_MM = 3.0       # Internal rib thickness
DECK_RIB_COUNT = 4                # Number of longitudinal ribs

# Deck-to-arch attachment
DECK_BOLT_HOLE_DIAMETER_MM = 5.0  # M4 or #8 bolt clearance
DECK_BOLT_HOLE_INSET_MM = 10.0    # Distance from deck edge to bolt hole


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


def boolean_union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    """Union multiple meshes."""
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


def build_roman_arch_bracket() -> trimesh.Trimesh:
    """Build a structural Roman arch bracket for wall mounting.
    
    The arch shape provides:
    - Compression-friendly load path from shelf to wall
    - Visual Roman arch aesthetic
    - Thick ribs for PETG structural integrity
    - Screw holes for stud mounting
    
    Print orientation: On its side (arch opening facing up) so layers
    are perpendicular to the primary load direction, not in peel.
    """
    parts: list[trimesh.Trimesh] = []
    
    # Wall mount plate - the vertical section that screws to the wall
    wall_plate = cuboid(
        (WALL_MOUNT_THICKNESS_MM, ARCH_THICKNESS_MM, ARCH_HEIGHT_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(wall_plate)
    
    # Top plate - horizontal shelf support
    top_plate = cuboid(
        (ARCH_DEPTH_MM, ARCH_THICKNESS_MM, TOP_PLATE_THICKNESS_MM),
        (0.0, 0.0, ARCH_HEIGHT_MM - TOP_PLATE_THICKNESS_MM)
    )
    parts.append(top_plate)
    
    # Front arch rib (Y = 0 side)
    front_rib = build_arch_rib_profile(y_offset=0.0)
    parts.append(front_rib)
    
    # Back arch rib (Y = ARCH_THICKNESS side)
    back_rib = build_arch_rib_profile(y_offset=ARCH_THICKNESS_MM - ARCH_RIB_THICKNESS_MM)
    parts.append(back_rib)
    
    # Center rib for extra strength
    center_rib = build_arch_rib_profile(y_offset=(ARCH_THICKNESS_MM - ARCH_RIB_THICKNESS_MM) / 2.0)
    parts.append(center_rib)
    
    # Bottom plate connecting the arch to the wall mount
    bottom_plate_height = 20.0
    bottom_plate = cuboid(
        (ARCH_DEPTH_MM * 0.6, ARCH_THICKNESS_MM, bottom_plate_height),
        (WALL_MOUNT_THICKNESS_MM, 0.0, 0.0)
    )
    parts.append(bottom_plate)
    
    # Union all parts
    body = boolean_union(parts)
    
    # Cut screw holes through the wall mount plate
    cutters: list[trimesh.Trimesh] = []
    for z_pos in SCREW_HOLE_POSITIONS_MM:
        # Main screw hole
        hole = cylinder_z(
            SCREW_HOLE_DIAMETER_MM / 2.0,
            WALL_MOUNT_THICKNESS_MM + 2.0,
            (WALL_MOUNT_THICKNESS_MM / 2.0, ARCH_THICKNESS_MM / 2.0, z_pos)
        )
        # Rotate to X-axis
        hole.vertices = hole.vertices[:, [2, 1, 0]]
        hole.vertices[:, 2] = z_pos
        hole.vertices[:, 0] = WALL_MOUNT_THICKNESS_MM / 2.0
        hole.vertices[:, 1] = ARCH_THICKNESS_MM / 2.0
        hole = cylinder_z(SCREW_HOLE_DIAMETER_MM / 2.0, WALL_MOUNT_THICKNESS_MM + 2.0, (0, 0, 0))
        rot = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])
        hole.apply_transform(rot)
        hole.apply_translation([WALL_MOUNT_THICKNESS_MM / 2.0, ARCH_THICKNESS_MM / 2.0, z_pos])
        cutters.append(hole)
        
        # Counterbore on the front face
        counterbore = cylinder_z(COUNTERBORE_DIAMETER_MM / 2.0, COUNTERBORE_DEPTH_MM + 0.1, (0, 0, 0))
        rot = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])
        counterbore.apply_transform(rot)
        counterbore.apply_translation([WALL_MOUNT_THICKNESS_MM - COUNTERBORE_DEPTH_MM / 2.0 + 0.05, ARCH_THICKNESS_MM / 2.0, z_pos])
        cutters.append(counterbore)
    
    # Cut bolt holes in top plate for deck attachment (2 holes)
    for x_offset in [DECK_BOLT_HOLE_INSET_MM + 20, ARCH_DEPTH_MM - DECK_BOLT_HOLE_INSET_MM - 20]:
        bolt_hole = cylinder_z(
            DECK_BOLT_HOLE_DIAMETER_MM / 2.0,
            TOP_PLATE_THICKNESS_MM + 2.0,
            (x_offset, ARCH_THICKNESS_MM / 2.0, ARCH_HEIGHT_MM - TOP_PLATE_THICKNESS_MM / 2.0)
        )
        cutters.append(bolt_hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_arch_rib_profile(y_offset: float) -> trimesh.Trimesh:
    """Build one arch rib - the curved structural member.
    
    Creates a Roman semicircular arch profile that transfers load
    from the shelf down to the wall mount through compression.
    """
    # Define the arch profile as a 2D shape, then extrude
    # The arch rises from the bottom plate to meet the top plate
    
    arch_start_z = 20.0  # Above the bottom plate
    arch_end_z = ARCH_HEIGHT_MM - TOP_PLATE_THICKNESS_MM
    arch_span_z = arch_end_z - arch_start_z
    
    # Create the arch rib as a series of boxes approximating the curve
    parts: list[trimesh.Trimesh] = []
    
    # Diagonal rib from wall to front edge of shelf
    # This is the main load-carrying member
    
    # Calculate the arch curve points
    num_segments = 12
    arch_center_x = WALL_MOUNT_THICKNESS_MM + ARCH_INNER_RADIUS_MM
    arch_center_z = arch_start_z + ARCH_INNER_RADIUS_MM
    
    # Outer curved section
    for i in range(num_segments):
        angle_start = math.pi / 2 + (math.pi / 2) * i / num_segments
        angle_end = math.pi / 2 + (math.pi / 2) * (i + 1) / num_segments
        
        # Inner radius points
        x1_inner = arch_center_x + ARCH_INNER_RADIUS_MM * math.cos(angle_start)
        z1_inner = arch_center_z + ARCH_INNER_RADIUS_MM * math.sin(angle_start)
        x2_inner = arch_center_x + ARCH_INNER_RADIUS_MM * math.cos(angle_end)
        z2_inner = arch_center_z + ARCH_INNER_RADIUS_MM * math.sin(angle_end)
        
        # Outer radius points
        outer_radius = ARCH_INNER_RADIUS_MM + ARCH_RIB_THICKNESS_MM
        x1_outer = arch_center_x + outer_radius * math.cos(angle_start)
        z1_outer = arch_center_z + outer_radius * math.sin(angle_start)
        x2_outer = arch_center_x + outer_radius * math.cos(angle_end)
        z2_outer = arch_center_z + outer_radius * math.sin(angle_end)
        
        # Create a prism for this segment
        points = [
            (x1_inner, z1_inner),
            (x2_inner, z2_inner),
            (x2_outer, z2_outer),
            (x1_outer, z1_outer),
        ]
        poly = Polygon(points)
        if poly.is_valid and poly.area > 0:
            segment = trimesh.creation.extrude_polygon(poly, height=ARCH_RIB_THICKNESS_MM, engine="earcut")
            segment.vertices = segment.vertices[:, [0, 2, 1]]
            segment.vertices[:, 1] += y_offset
            parts.append(clean_mesh(segment))
    
    # Vertical section from arch top to shelf
    vert_section = cuboid(
        (ARCH_RIB_THICKNESS_MM, ARCH_RIB_THICKNESS_MM, arch_end_z - (arch_center_z + ARCH_INNER_RADIUS_MM)),
        (arch_center_x - ARCH_RIB_THICKNESS_MM / 2, y_offset, arch_center_z + ARCH_INNER_RADIUS_MM)
    )
    if arch_end_z > arch_center_z + ARCH_INNER_RADIUS_MM:
        parts.append(vert_section)
    
    # Horizontal section from arch to front
    horiz_start_x = arch_center_x + ARCH_INNER_RADIUS_MM
    horiz_section = cuboid(
        (ARCH_DEPTH_MM - horiz_start_x, ARCH_RIB_THICKNESS_MM, ARCH_RIB_THICKNESS_MM),
        (horiz_start_x, y_offset, arch_start_z)
    )
    parts.append(horiz_section)
    
    # Diagonal brace from mid-arch to front-bottom for extra rigidity
    diag_length = math.sqrt((ARCH_DEPTH_MM - arch_center_x) ** 2 + (arch_start_z) ** 2)
    diag_angle = math.atan2(arch_start_z, ARCH_DEPTH_MM - arch_center_x)
    
    if parts:
        return boolean_union(parts)
    else:
        return cuboid((1, 1, 1), (0, 0, 0))


def build_deck_segment() -> trimesh.Trimesh:
    """Build a ribbed deck segment that spans between arch brackets.
    
    The deck is a hollow box with internal ribs for stiffness.
    Bolt holes at each end attach to the arch bracket top plates.
    
    Print orientation: Top face down (so top surface is smooth).
    """
    parts: list[trimesh.Trimesh] = []
    
    # Top surface
    top = cuboid(
        (DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_TOP_THICKNESS_MM),
        (0.0, 0.0, DECK_THICKNESS_MM - DECK_TOP_THICKNESS_MM)
    )
    parts.append(top)
    
    # Bottom surface
    bottom = cuboid(
        (DECK_LENGTH_MM, DECK_WIDTH_MM, DECK_BOTTOM_THICKNESS_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(bottom)
    
    # Front and back walls
    front_wall = cuboid(
        (DECK_LENGTH_MM, DECK_RIB_THICKNESS_MM, DECK_THICKNESS_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(front_wall)
    
    back_wall = cuboid(
        (DECK_LENGTH_MM, DECK_RIB_THICKNESS_MM, DECK_THICKNESS_MM),
        (0.0, DECK_WIDTH_MM - DECK_RIB_THICKNESS_MM, 0.0)
    )
    parts.append(back_wall)
    
    # End walls
    left_wall = cuboid(
        (DECK_RIB_THICKNESS_MM, DECK_WIDTH_MM, DECK_THICKNESS_MM),
        (0.0, 0.0, 0.0)
    )
    parts.append(left_wall)
    
    right_wall = cuboid(
        (DECK_RIB_THICKNESS_MM, DECK_WIDTH_MM, DECK_THICKNESS_MM),
        (DECK_LENGTH_MM - DECK_RIB_THICKNESS_MM, 0.0, 0.0)
    )
    parts.append(right_wall)
    
    # Internal longitudinal ribs
    rib_spacing = (DECK_WIDTH_MM - 2 * DECK_RIB_THICKNESS_MM) / (DECK_RIB_COUNT + 1)
    for i in range(1, DECK_RIB_COUNT + 1):
        y_pos = DECK_RIB_THICKNESS_MM + i * rib_spacing - DECK_RIB_THICKNESS_MM / 2
        rib = cuboid(
            (DECK_LENGTH_MM, DECK_RIB_THICKNESS_MM, DECK_THICKNESS_MM - DECK_TOP_THICKNESS_MM - DECK_BOTTOM_THICKNESS_MM),
            (0.0, y_pos, DECK_BOTTOM_THICKNESS_MM)
        )
        parts.append(rib)
    
    # Internal cross ribs (2 in the middle)
    cross_positions = [DECK_LENGTH_MM / 3, 2 * DECK_LENGTH_MM / 3]
    for x_pos in cross_positions:
        cross_rib = cuboid(
            (DECK_RIB_THICKNESS_MM, DECK_WIDTH_MM, DECK_THICKNESS_MM - DECK_TOP_THICKNESS_MM - DECK_BOTTOM_THICKNESS_MM),
            (x_pos - DECK_RIB_THICKNESS_MM / 2, 0.0, DECK_BOTTOM_THICKNESS_MM)
        )
        parts.append(cross_rib)
    
    body = boolean_union(parts)
    
    # Cut bolt holes at each end for attachment to brackets
    cutters: list[trimesh.Trimesh] = []
    bolt_y_positions = [DECK_WIDTH_MM / 3, 2 * DECK_WIDTH_MM / 3]
    
    for x_pos in [DECK_BOLT_HOLE_INSET_MM, DECK_LENGTH_MM - DECK_BOLT_HOLE_INSET_MM]:
        for y_pos in bolt_y_positions:
            hole = cylinder_z(
                DECK_BOLT_HOLE_DIAMETER_MM / 2.0,
                DECK_THICKNESS_MM + 2.0,
                (x_pos, y_pos, DECK_THICKNESS_MM / 2.0)
            )
            cutters.append(hole)
    
    result = boolean_difference(body, cutters)
    return normalize_mesh(result)


def build_end_cap() -> trimesh.Trimesh:
    """Build an end cap for the deck ends that don't meet another segment.
    
    Simple cover plate that attaches to the last deck segment.
    """
    cap = cuboid(
        (DECK_RIB_THICKNESS_MM * 2, DECK_WIDTH_MM, DECK_THICKNESS_MM),
        (0.0, 0.0, 0.0)
    )
    return normalize_mesh(cap)


def check_fits_build_volume(mesh: trimesh.Trimesh, name: str) -> bool:
    """Check if mesh fits in A1 mini build volume."""
    extents = mesh.bounding_box.extents
    fits = all(e <= b for e, b in zip(sorted(extents), sorted(BUILD_VOLUME_MM)))
    print(f"  {name}: {extents[0]:.1f} x {extents[1]:.1f} x {extents[2]:.1f} mm", end="")
    if fits:
        print(" ✓ fits A1 mini")
    else:
        print(" ✗ TOO BIG")
    return fits


def write_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    """Write mesh to STL file."""
    mesh.export(str(path), file_type="stl")
    print(f"  Wrote: {path.name} ({path.stat().st_size / 1024:.1f} KB)")


def write_3mf(mesh: trimesh.Trimesh, path: Path, name: str) -> None:
    """Write mesh to 3MF file."""
    try:
        scene = trimesh.Scene()
        scene.add_geometry(mesh, node_name=name)
        scene.export(str(path), file_type="3mf")
        print(f"  Wrote: {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"  Warning: Could not write 3MF: {e}")


def main():
    print("=" * 60)
    print("All-PETG Structural Shelf Generator")
    print("Roman arch brackets + ribbed deck segments")
    print("=" * 60)
    
    OUT.mkdir(parents=True, exist_ok=True)
    
    # Generate arch bracket
    print("\nGenerating Roman arch bracket...")
    bracket = build_roman_arch_bracket()
    check_fits_build_volume(bracket, "arch_bracket")
    write_stl(bracket, OUT / "arch_bracket.stl")
    write_3mf(bracket, OUT / "arch_bracket.3mf", "arch_bracket")
    
    # Generate deck segment
    print("\nGenerating ribbed deck segment...")
    deck = build_deck_segment()
    check_fits_build_volume(deck, "deck_segment")
    write_stl(deck, OUT / "deck_segment.stl")
    write_3mf(deck, OUT / "deck_segment.3mf", "deck_segment")
    
    # Generate end cap
    print("\nGenerating end cap...")
    end_cap = build_end_cap()
    check_fits_build_volume(end_cap, "end_cap")
    write_stl(end_cap, OUT / "end_cap.stl")
    write_3mf(end_cap, OUT / "end_cap.3mf", "end_cap")
    
    # Write manifest
    manifest = {
        "description": "All-PETG structural shelf parts",
        "target_wall": {
            "length_in": 61.5,
            "stud_positions_in": [17.0, 32.5, 48.5],
        },
        "parts": {
            "arch_bracket": {
                "file": "arch_bracket.stl",
                "quantity_needed": 3,
                "dimensions_mm": list(bracket.bounding_box.extents),
                "print_time_hours_estimate": 6,
                "print_orientation": "On side, arch opening facing up",
                "description": "Structural Roman arch wall bracket, screws into stud",
            },
            "deck_segment": {
                "file": "deck_segment.stl",
                "quantity_needed": 9,
                "dimensions_mm": list(deck.bounding_box.extents),
                "print_time_hours_estimate": 4,
                "print_orientation": "Top face down for smooth surface",
                "description": "Ribbed deck segment, bolts to bracket tops",
            },
            "end_cap": {
                "file": "end_cap.stl",
                "quantity_needed": 2,
                "dimensions_mm": list(end_cap.bounding_box.extents),
                "print_time_hours_estimate": 1,
                "print_orientation": "Flat",
                "description": "End cap for exposed deck ends",
            },
        },
        "hardware": {
            "wall_screws": "#10 x 2.5 in wood screws, 9 total (3 per bracket)",
            "wall_washers": "1/4 in flat washers, 9 total",
            "deck_bolts": "M4 x 20mm bolts, 36 total (4 per deck-bracket joint)",
            "deck_nuts": "M4 nuts, 36 total",
        },
        "total_print_time_hours_estimate": 3 * 6 + 9 * 4 + 2 * 1,
        "total_petg_kg_estimate": 2.5,
    }
    
    manifest_path = OUT / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote: {manifest_path.name}")
    
    print("\n" + "=" * 60)
    print("SUMMARY - Parts for 61.5 in wall (studs at 17, 32.5, 48.5 in)")
    print("=" * 60)
    print(f"  Arch brackets:  3  (one per stud)")
    print(f"  Deck segments:  9  (fills ~1440mm / 56.7in)")
    print(f"  End caps:       2  (one each end)")
    print(f"  Total print time: ~{manifest['total_print_time_hours_estimate']} hours")
    print(f"  PETG needed: ~{manifest['total_petg_kg_estimate']} kg")
    print("=" * 60)


if __name__ == "__main__":
    main()
