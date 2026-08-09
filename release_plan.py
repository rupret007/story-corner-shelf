#!/usr/bin/env python3
"""Exact baseline cassette planning plus an isolated optional rail study.

This module contains no mesh code.  It turns the authoritative r6 configuration
and :mod:`design_math` plan into named logical instances used by the generator,
drawings, schedules, and release tests.  Values remain nominal until the field
measurement gates in ``config.json`` are satisfied.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from design_math import PlanGeometry, RunPlan, calculate_plan


EPSILON = 1e-7


@dataclass(frozen=True)
class CassetteInstancePlan:
    logical_id: str
    run_id: str
    run_role: str
    index: int
    variant_id: str
    spring_side: str
    left_joint_class: str
    right_joint_class: str
    nominal_start_local_mm: float
    nominal_end_local_mm: float
    physical_start_local_mm: float
    physical_end_local_mm: float
    physical_width_mm: float
    support_center_local_mm: float
    support_offset_from_physical_left_mm: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RailJointPlan:
    logical_id: str
    run_id: str
    line_role: str
    index: int
    center_local_mm: float
    joint_class: str
    related_pier_seam_local_mm: float | None
    offset_from_related_seam_mm: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RailSegmentPlan:
    logical_id: str
    run_id: str
    line_role: str
    index: int
    start_local_mm: float
    end_local_mm: float
    length_mm: float
    left_joint_class: str
    right_joint_class: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RailLinePlan:
    run_id: str
    line_role: str
    joints: tuple[RailJointPlan, ...]
    segments: tuple[RailSegmentPlan, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "line_role": self.line_role,
            "joints": [item.to_dict() for item in self.joints],
            "segments": [item.to_dict() for item in self.segments],
        }


def _joint_class(boundary_index: int, module_count: int) -> str:
    if boundary_index == 0:
        return "free_run_start"
    if boundary_index == module_count:
        return "free_run_end"
    return "fixed_crown" if boundary_index % 2 == 1 else "floating_supported_pier"


def enumerate_cassette_instances(
    cfg: dict[str, Any],
    plan: PlanGeometry | None = None,
) -> tuple[CassetteInstancePlan, ...]:
    """Return all 18 logical half-bay cassettes for one L-shaped level."""

    plan = plan or calculate_plan(cfg)
    seam = float(cfg["structure"]["cassette_between_module_seam_mm"])
    output: list[CassetteInstancePlan] = []
    for run in (plan.through, plan.return_run):
        boundaries = run.cassette_boundary_stations_local_mm
        module_count = len(boundaries) - 1
        if module_count != 2 * run.bay_count:
            raise ValueError(f"{run.run_id}: expected two cassettes per bay")
        for index in range(module_count):
            left_class = _joint_class(index, module_count)
            right_class = _joint_class(index + 1, module_count)
            nominal_start = float(boundaries[index])
            nominal_end = float(boundaries[index + 1])
            physical_start = nominal_start + (0.0 if index == 0 else seam / 2.0)
            physical_end = nominal_end - (0.0 if index + 1 == module_count else seam / 2.0)
            spring_side = "left" if index % 2 == 0 else "right"
            if index == 0:
                support = run.start_pier_inset_mm
                width_class = "start_outer"
            elif index + 1 == module_count:
                support = run.length_mm - run.end_pier_inset_mm
                width_class = "end_outer"
            elif spring_side == "left":
                support = nominal_start
                width_class = "internal_pier_to_crown"
            else:
                support = nominal_end
                width_class = "internal_crown_to_pier"
            variant = f"{run.role}_{width_class}"
            output.append(
                CassetteInstancePlan(
                    logical_id=f"{run.run_id}_cassette_{index + 1:02d}",
                    run_id=run.run_id,
                    run_role=run.role,
                    index=index,
                    variant_id=variant,
                    spring_side=spring_side,
                    left_joint_class=left_class,
                    right_joint_class=right_class,
                    nominal_start_local_mm=nominal_start,
                    nominal_end_local_mm=nominal_end,
                    physical_start_local_mm=physical_start,
                    physical_end_local_mm=physical_end,
                    physical_width_mm=physical_end - physical_start,
                    support_center_local_mm=float(support),
                    support_offset_from_physical_left_mm=float(support - physical_start),
                )
            )
    if len(output) != 18 or len({item.logical_id for item in output}) != 18:
        raise AssertionError("The selected 3/6 L must contain 18 unique logical cassettes")
    return tuple(output)


def group_cassette_variants(
    instances: Iterable[CassetteInstancePlan],
) -> dict[str, tuple[CassetteInstancePlan, ...]]:
    groups: dict[str, list[CassetteInstancePlan]] = {}
    for instance in instances:
        groups.setdefault(instance.variant_id, []).append(instance)
    return {key: tuple(value) for key, value in sorted(groups.items())}


def _interior_points_between(left: float, right: float, maximum_gap: float) -> list[float]:
    distance = right - left
    if distance <= maximum_gap + EPSILON:
        return []
    gap_count = int(math.ceil((distance - EPSILON) / maximum_gap))
    step = distance / gap_count
    return [left + step * index for index in range(1, gap_count)]


def _start_points(anchor: float, maximum_gap: float, edge_limit: float) -> list[float]:
    if anchor <= edge_limit + EPSILON:
        return []
    count = int(math.ceil((anchor - edge_limit - EPSILON) / maximum_gap))
    return [anchor - maximum_gap * index for index in range(count, 0, -1)]


def _end_points(
    anchor: float,
    length: float,
    maximum_gap: float,
    edge_limit: float,
) -> list[float]:
    remainder = length - anchor
    if remainder <= edge_limit + EPSILON:
        return []
    count = int(math.ceil((remainder - edge_limit - EPSILON) / maximum_gap))
    return [anchor + maximum_gap * index for index in range(1, count + 1)]


def _configured_floating_offsets(
    cfg: dict[str, Any], run_id: str, line_role: str, count: int
) -> tuple[float, ...]:
    planner = cfg["structure"]["stitch_rail_planner"]
    key = f"{line_role}_floating_offsets_from_supported_pier_seam_mm"
    values = tuple(float(value) for value in planner[key][run_id])
    if len(values) != count:
        raise ValueError(f"{key}.{run_id} must contain {count} offsets")
    zone = float(planner["pier_zone_half_width_mm"])
    minimum = float(planner["minimum_overlap_plane_offset_from_cassette_seam_mm"])
    if any(abs(value) > zone + EPSILON or abs(value) < minimum - EPSILON for value in values):
        raise ValueError(f"{key}.{run_id} leaves the supported pier zone or seam keepout")
    return values


def _snap_fixed_points_outside_cassette_seam_keepouts(
    points: Iterable[float],
    seams: Iterable[float],
    minimum_offset_mm: float,
) -> list[float]:
    """Move research-only fixed joints to the nearest keepout boundary.

    The optional rail study is not installed, but its reproducible geometry
    must still honor the configured cassette-seam keepout after a fitted-plan
    change. Each violating point stays on its original side of the nearest
    seam; no tolerance or structural threshold is reduced.
    """

    seam_values = tuple(float(value) for value in seams)
    output: list[float] = []
    for point in points:
        center = float(point)
        if seam_values:
            seam = min(seam_values, key=lambda value: abs(center - value))
            delta = center - seam
            if abs(delta) < minimum_offset_mm - EPSILON:
                center = seam + (minimum_offset_mm if delta >= 0.0 else -minimum_offset_mm)
        output.append(center)
    if any(left >= right - EPSILON for left, right in zip(output, output[1:])):
        raise ValueError("Snapped fixed rail-study joints are not strictly increasing")
    return output


def _repair_optional_fixed_joint_spacing(
    fixed: Iterable[float],
    floating: Iterable[float],
    maximum_gap_mm: float,
    run_length_mm: float,
) -> list[float]:
    """Preserve segment length after a fixed joint is snapped from a seam.

    Only automatically generated research joints may move. When two adjacent
    fixed joints exceed the center-spacing limit, the joint nearer the free
    run end is moved inward until the exact limit is restored. Floating pier
    joints remain immutable.
    """

    records = [[float(value), False] for value in fixed]
    records.extend([float(value), True] for value in floating)
    records.sort(key=lambda item: item[0])
    for index in range(len(records) - 1):
        left, right = records[index], records[index + 1]
        if right[0] - left[0] <= maximum_gap_mm + EPSILON:
            continue
        if left[1] and right[1]:
            raise ValueError("Immutable floating rail-study joints exceed maximum spacing")
        midpoint = (left[0] + right[0]) / 2.0
        if not left[1] and (right[1] or midpoint <= run_length_mm / 2.0):
            left[0] = right[0] - maximum_gap_mm
        elif not right[1]:
            right[0] = left[0] + maximum_gap_mm
        else:
            raise ValueError("Rail-study joint spacing cannot be repaired fail-closed")
    repaired = sorted(item[0] for item in records if not item[1])
    if any(left >= right - EPSILON for left, right in zip(repaired, repaired[1:])):
        raise ValueError("Repaired fixed rail-study joints are not strictly increasing")
    return repaired


def plan_stitch_rail_line(
    cfg: dict[str, Any],
    run: RunPlan,
    line_role: str,
) -> RailLinePlan:
    """Plan one rail train with every floating joint inside its pier zone.

    A rail segment overlaps its neighbour by 45 mm.  Therefore adjacent joint
    centers may be at most ``max_segment - overlap`` apart.  End segments gain
    only half an overlap beyond their first/last joint, so their edge limit is
    ``max_segment - overlap/2``.
    """

    if line_role not in {"front", "rear"}:
        raise ValueError("line_role must be 'front' or 'rear'")
    planner = cfg["structure"]["stitch_rail_planner"]
    maximum_length = float(planner["maximum_segment_length_mm"])
    overlap = float(planner["overlap_length_mm"])
    maximum_gap = float(planner["maximum_joint_center_spacing_mm"])
    if abs(maximum_gap - (maximum_length - overlap)) > EPSILON:
        raise ValueError("maximum joint spacing must equal segment maximum minus overlap")
    edge_limit = maximum_length - overlap / 2.0
    offsets = _configured_floating_offsets(
        cfg, run.run_id, line_role, len(run.pier_seam_stations_local_mm)
    )
    floating = [
        float(seam) + offset
        for seam, offset in zip(run.pier_seam_stations_local_mm, offsets)
    ]
    if any(left >= right for left, right in zip(floating, floating[1:])):
        raise ValueError(f"{run.run_id}/{line_role}: floating rail joints are not increasing")

    fixed: list[float] = []
    if floating:
        fixed.extend(_start_points(floating[0], maximum_gap, edge_limit))
        for left, right in zip(floating, floating[1:]):
            fixed.extend(_interior_points_between(left, right, maximum_gap))
        fixed.extend(_end_points(floating[-1], run.length_mm, maximum_gap, edge_limit))
    else:
        # Not used by the selected 3/6 plan, but fail safely for a one-bay run.
        gap_count = max(1, int(math.ceil(run.length_mm / maximum_length)))
        step = run.length_mm / gap_count
        fixed.extend(step * index for index in range(1, gap_count))

    fixed = _snap_fixed_points_outside_cassette_seam_keepouts(
        fixed,
        run.cassette_boundary_stations_local_mm[1:-1],
        float(planner["minimum_overlap_plane_offset_from_cassette_seam_mm"]),
    )
    fixed = _repair_optional_fixed_joint_spacing(
        fixed,
        floating,
        maximum_gap,
        run.length_mm,
    )

    joint_data: list[tuple[float, str, float | None, float | None]] = []
    for seam, offset, center in zip(run.pier_seam_stations_local_mm, offsets, floating):
        joint_data.append((center, "floating_supported_pier", float(seam), offset))
    joint_data.extend((center, "fixed_staggered", None, None) for center in fixed)
    joint_data.sort(key=lambda value: value[0])
    joints = tuple(
        RailJointPlan(
            logical_id=f"{run.run_id}_{line_role}_rail_joint_{index + 1:02d}",
            run_id=run.run_id,
            line_role=line_role,
            index=index,
            center_local_mm=center,
            joint_class=joint_class,
            related_pier_seam_local_mm=related,
            offset_from_related_seam_mm=offset,
        )
        for index, (center, joint_class, related, offset) in enumerate(joint_data)
    )

    half_overlap = overlap / 2.0
    segments: list[RailSegmentPlan] = []
    centers = [joint.center_local_mm for joint in joints]
    for index in range(len(centers) + 1):
        start = 0.0 if index == 0 else centers[index - 1] - half_overlap
        end = run.length_mm if index == len(centers) else centers[index] + half_overlap
        left_class = "free_run_start" if index == 0 else joints[index - 1].joint_class
        right_class = "free_run_end" if index == len(centers) else joints[index].joint_class
        length = end - start
        if length <= 0.0 or length > maximum_length + EPSILON:
            raise ValueError(
                f"{run.run_id}/{line_role} rail segment {index + 1} length {length:.6f} mm"
            )
        segments.append(
            RailSegmentPlan(
                logical_id=f"{run.run_id}_{line_role}_rail_segment_{index + 1:02d}",
                run_id=run.run_id,
                line_role=line_role,
                index=index,
                start_local_mm=start,
                end_local_mm=end,
                length_mm=length,
                left_joint_class=left_class,
                right_joint_class=right_class,
            )
        )

    return RailLinePlan(run.run_id, line_role, joints, tuple(segments))


def plan_optional_stitch_rail_study(
    cfg: dict[str, Any], plan: PlanGeometry | None = None
) -> tuple[RailLinePlan, ...]:
    """Plan the excluded rail-on research specimen, never baseline parts."""

    policy = cfg["structure"]["stitch_rail_baseline_policy"]
    if policy["installed_in_release_candidate"]:
        raise ValueError("Optional rail-study planner cannot define installed baseline parts")
    plan = plan or calculate_plan(cfg)
    lines = tuple(
        plan_stitch_rail_line(cfg, run, line_role)
        for run in (plan.through, plan.return_run)
        for line_role in ("front", "rear")
    )
    expected = cfg["structure"]["stitch_rail_planner"]["expected_per_level"]
    segment_count = sum(len(line.segments) for line in lines)
    joint_count = sum(len(line.joints) for line in lines)
    floating_count = sum(
        joint.joint_class == "floating_supported_pier"
        for line in lines
        for joint in line.joints
    )
    fixed_count = joint_count - floating_count
    pin_count = joint_count * int(cfg["structure"]["stitch_rail_joint_pins_per_overlap"])
    actual = {
        "rail_segments": segment_count,
        "overlap_joints": joint_count,
        "floating_pier_overlap_joints": floating_count,
        "fixed_overlap_joints": fixed_count,
        "joint_pins": pin_count,
    }
    if any(int(expected[key]) != value for key, value in actual.items()):
        raise AssertionError(f"Rail topology drift: expected {expected}, got {actual}")

    minimum_stagger = float(
        cfg["structure"]["stitch_rail_planner"]["minimum_front_rear_joint_stagger_mm"]
    )
    for run in (plan.through, plan.return_run):
        front = next(line for line in lines if line.run_id == run.run_id and line.line_role == "front")
        rear = next(line for line in lines if line.run_id == run.run_id and line.line_role == "rear")
        front_float = [joint.center_local_mm for joint in front.joints if joint.related_pier_seam_local_mm is not None]
        rear_float = [joint.center_local_mm for joint in rear.joints if joint.related_pier_seam_local_mm is not None]
        if any(abs(left - right) < minimum_stagger - EPSILON for left, right in zip(front_float, rear_float)):
            raise AssertionError(f"{run.run_id}: front/rear floating rail joints are not staggered")
    return lines


def plan_all_stitch_rails(
    cfg: dict[str, Any], plan: PlanGeometry | None = None
) -> tuple[RailLinePlan, ...]:
    """Compatibility alias for the explicitly optional rail research study.

    Release generators and inventories must not call this function. It remains
    only so prior experiment notebooks can be reproduced while the rail-on /
    rail-off question is unqualified.
    """

    return plan_optional_stitch_rail_study(cfg, plan)


def per_level_topology(cfg: dict[str, Any], plan: PlanGeometry | None = None) -> dict[str, int]:
    # The active release topology is rail-free. Optional study geometry must
    # never leak into its physical-object counts.
    plan = plan or calculate_plan(cfg)
    _ = plan
    topology = {
        key: int(value)
        for key, value in cfg["nominal_geometry_snapshot"]["nominal_part_topology"].items()
        if isinstance(value, int) and not isinstance(value, bool)
    }
    for key in (
        "stitch_rail_segments",
        "stitch_rail_overlap_joints",
        "stitch_rail_joint_pins",
        "run_end_tie_blocks",
    ):
        if topology.get(key) != 0:
            raise AssertionError(f"Rail-free release topology requires {key}=0")
    return topology
