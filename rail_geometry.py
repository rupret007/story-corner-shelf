#!/usr/bin/env python3
"""Printable staggered stitch-rail geometry for the r6 fit/test set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import trimesh
from shapely.geometry import LineString

from model_io import boolean_difference, boolean_union, cuboid, normalize_mesh
from release_plan import RailSegmentPlan


@dataclass(frozen=True)
class RailMeshResult:
    mesh: trimesh.Trimesh
    round_hole_count: int
    elongated_hole_count: int
    left_half_lap: bool
    right_half_lap: bool


def _cylinder_along_z(
    diameter: float,
    length: float,
    *,
    center_x: float,
    center_y: float,
    z0: float,
) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=diameter / 2.0, height=length, sections=32)
    mesh.apply_translation((center_x, center_y, z0 + length / 2.0))
    return mesh


def _slot_along_x(
    length: float,
    width: float,
    depth: float,
    *,
    center_x: float,
    center_y: float,
    z0: float,
) -> trimesh.Trimesh:
    if length <= width:
        raise ValueError("An elongated rail hole must be longer than it is wide")
    half_straight = (length - width) / 2.0
    outline = LineString(
        [
            (center_x - half_straight, center_y),
            (center_x + half_straight, center_y),
        ]
    ).buffer(width / 2.0, cap_style=1, quad_segs=10)
    mesh = trimesh.creation.extrude_polygon(outline, height=depth, engine="earcut")
    mesh.apply_translation((0.0, 0.0, z0))
    return mesh


def _ibeam_zone(
    *,
    x0: float,
    length: float,
    height: float,
    depth: float,
    chord: float,
    web: float,
    z0: float,
) -> list[trimesh.Trimesh]:
    if length <= 1e-7:
        return []
    return [
        cuboid((length, chord, depth), origin=(x0, 0.0, z0)),
        cuboid((length, chord, depth), origin=(x0, height - chord, z0)),
        cuboid(
            (length, height - 2.0 * chord, web),
            origin=(x0, chord, z0 + (depth - web) / 2.0),
        ),
    ]


def stitch_rail_segment_mesh(
    cfg: dict[str, Any], segment: RailSegmentPlan
) -> RailMeshResult:
    structure = cfg["structure"]
    length = float(segment.length_mm)
    height = float(structure["stitch_rail_height_mm"])
    depth = float(structure["stitch_rail_depth_mm"])
    chord = float(structure["stitch_rail_chord_mm"])
    web = float(structure["stitch_rail_web_mm"])
    overlap = float(structure["stitch_rail_overlap_mm"])
    diameter = float(structure["stitch_rail_joint_hole_diameter_mm"])
    pins = int(structure["stitch_rail_joint_pins_per_overlap"])
    if pins != 2:
        raise ValueError("The current rail overlap geometry requires exactly two pins")
    if not (0.0 < web <= depth / 2.0 and 0.0 < chord < height / 2.0):
        raise ValueError("Rail chord/web dimensions do not leave an I-beam opening")

    left = segment.left_joint_class != "free_run_start"
    right = segment.right_joint_class != "free_run_end"
    left_length = overlap if left else 0.0
    right_length = overlap if right else 0.0
    if left_length + right_length > length + 1e-7:
        raise ValueError(f"{segment.logical_id}: half-lap zones overlap")

    pieces: list[trimesh.Trimesh] = []
    if left:
        pieces.extend(
            _ibeam_zone(
                x0=0.0,
                length=overlap + 0.02,
                height=height,
                depth=depth / 2.0,
                chord=chord,
                web=min(web, depth / 2.0 - 0.8),
                z0=0.0,
            )
        )
    center_start = overlap if left else 0.0
    center_end = length - overlap if right else length
    center_x0 = center_start - (0.02 if left else 0.0)
    center_x1 = center_end + (0.02 if right else 0.0)
    pieces.extend(
        _ibeam_zone(
            x0=center_x0,
            length=max(0.0, center_x1 - center_x0),
            height=height,
            depth=depth,
            chord=chord,
            web=web,
            z0=0.0,
        )
    )
    if right:
        pieces.extend(
            _ibeam_zone(
                x0=length - overlap - 0.02,
                length=overlap + 0.02,
                height=height,
                depth=depth / 2.0,
                chord=chord,
                web=min(web, depth / 2.0 - 0.8),
                z0=depth / 2.0,
            )
        )
    body = boolean_union(pieces)

    cutters: list[trimesh.Trimesh] = []
    round_count = 0
    slot_count = 0
    y = height / 2.0
    pin_offsets = (12.0, overlap - 12.0)
    if left:
        for x in pin_offsets:
            if segment.left_joint_class == "floating_supported_pier":
                cutters.append(
                    _slot_along_x(
                        diameter + 1.2,
                        diameter,
                        depth / 2.0 + 0.4,
                        center_x=x,
                        center_y=y,
                        z0=-0.2,
                    )
                )
                slot_count += 1
            else:
                cutters.append(
                    _cylinder_along_z(
                        diameter,
                        depth / 2.0 + 0.4,
                        center_x=x,
                        center_y=y,
                        z0=-0.2,
                    )
                )
                round_count += 1
    if right:
        for offset in pin_offsets:
            cutters.append(
                _cylinder_along_z(
                    diameter,
                    depth / 2.0 + 0.4,
                    center_x=length - overlap + offset,
                    center_y=y,
                    z0=depth / 2.0 - 0.2,
                )
            )
            round_count += 1
    mesh = boolean_difference(body, cutters)
    normalize_mesh(mesh)
    return RailMeshResult(mesh, round_count, slot_count, left, right)


def stitch_rail_pin_mesh(cfg: dict[str, Any]) -> trimesh.Trimesh:
    structure = cfg["structure"]
    diameter = float(structure["stitch_rail_joint_pin_diameter_mm"])
    depth = float(structure["stitch_rail_depth_mm"])
    head = float(structure["stitch_rail_joint_pin_head_mm"])
    shaft = _cylinder_along_z(
        diameter,
        depth + 1.0,
        center_x=0.0,
        center_y=0.0,
        z0=0.0,
    )
    pull_head = _cylinder_along_z(
        head,
        2.4,
        center_x=0.0,
        center_y=0.0,
        z0=depth + 0.95,
    )
    mesh = boolean_union([shaft, pull_head])
    normalize_mesh(mesh)
    return mesh


def run_end_tie_block_mesh(cfg: dict[str, Any]) -> trimesh.Trimesh:
    """One run-local X tie between rear and front rail ends; never crosses the L."""

    depth = float(cfg["closet"]["shelf_depth_in"]) * 25.4
    height = float(cfg["structure"]["stitch_rail_height_mm"])
    extrusion = float(cfg["structure"]["stitch_rail_depth_mm"])
    pad_depth = 18.0
    web = float(cfg["structure"]["stitch_rail_web_mm"])
    footprints = [
        LineString([(pad_depth, 7.0), (depth - pad_depth, height - 7.0)]).buffer(
            web / 2.0, cap_style=1, join_style=1, quad_segs=8
        ),
        LineString([(pad_depth, height - 7.0), (depth - pad_depth, 7.0)]).buffer(
            web / 2.0, cap_style=1, join_style=1, quad_segs=8
        ),
    ]
    from shapely.geometry import box as shapely_box
    from shapely.ops import unary_union

    footprints.extend(
        [
            shapely_box(0.0, 0.0, pad_depth + 2.0, height),
            shapely_box(depth - pad_depth - 2.0, 0.0, depth, height),
        ]
    )
    outline = unary_union(footprints)
    mesh = trimesh.creation.extrude_polygon(outline, height=extrusion, engine="earcut")
    normalize_mesh(mesh)
    return mesh
