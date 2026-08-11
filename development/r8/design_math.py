#!/usr/bin/env python3
"""Pure layout and readiness calculations for the R8 shelf scaffold.

This module emits no geometry and writes no files.  Its dimensions are
nominal millimetres.  The results are layout checks only: they are not a load
rating and do not authorize an installed print.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


EPSILON = 1.0e-9


@dataclass(frozen=True)
class RunLayout:
    """One run's exact nominal corbel, seam, and cassette stationing."""

    run_id: str
    length_mm: float
    cassette_module_count: int
    corbel_count: int
    terminal_corbel_center_inset_mm: float
    equal_corbel_pitch_mm: float
    corbel_centers_mm: tuple[float, ...]
    corbel_cap_bounds_mm: tuple[tuple[float, float], ...]
    seam_centers_mm: tuple[float, ...]
    nominal_module_bounds_mm: tuple[tuple[float, float], ...]
    physical_module_bounds_mm: tuple[tuple[float, float], ...]
    nominal_module_widths_mm: tuple[float, ...]
    physical_module_widths_mm: tuple[float, ...]
    minimum_cap_bearing_each_side_of_seam_mm: float
    accessory_eligible_corbel_indices: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrintEnvelope:
    """Axis-aligned envelope in a declared saved print orientation."""

    part_mm: tuple[float, float, float]
    with_brim_mm: tuple[float, float, float]
    printable_volume_mm: tuple[float, float, float]
    fits: bool


@dataclass(frozen=True)
class ShelfPlan:
    """The exact R8 nominal scaffold derived from ``config.json``."""

    depth_mm: float
    cassette_height_mm: float
    selected_level_count: int
    d_frame_envelope_mm: tuple[float, float, float]
    d_frame_saved_print_envelope: PrintEnvelope
    through: RunLayout
    return_run: RunLayout
    accessory_sockets_per_eligible_corbel: int
    accessory_eligible_corbels_per_level: int
    accessory_eligible_corbels_selected_levels: int
    accessory_socket_count_per_level: int
    accessory_socket_count_selected_levels: int
    accessory_default_rails_per_level: int
    accessory_default_rails_selected_levels: int
    accessory_default_socket_count_per_level: int
    accessory_default_socket_count_selected_levels: int
    cassette_flat_plate_fit_by_run: tuple[tuple[str, bool], ...]
    cassette_edge_yaw_envelope_by_run: tuple[tuple[str, PrintEnvelope], ...]
    structural_corbels_per_level: int
    structural_corbels_selected_levels: int
    minimum_metal_screws_per_corbel: int
    minimum_metal_screws_per_level: int
    minimum_metal_screws_selected_levels: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_by_id(cfg: dict[str, Any], run_id: str) -> dict[str, Any]:
    matches = [run for run in cfg["runs"] if run["id"] == run_id]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {run_id!r} run; found {len(matches)}")
    return matches[0]


def _as_three_floats(values: list[float] | tuple[float, ...], label: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{label} must contain exactly three dimensions")
    result = tuple(float(value) for value in values)
    if any(value <= 0.0 for value in result):
        raise ValueError(f"{label} dimensions must all be positive")
    return result  # type: ignore[return-value]


def _physical_bounds(
    nominal_bounds: tuple[tuple[float, float], ...], seam_mm: float
) -> tuple[tuple[float, float], ...]:
    """Reserve half of each configured seam from each adjacent cassette."""

    last = len(nominal_bounds) - 1
    physical: list[tuple[float, float]] = []
    for index, (left, right) in enumerate(nominal_bounds):
        physical_left = left + (seam_mm / 2.0 if index > 0 else 0.0)
        physical_right = right - (seam_mm / 2.0 if index < last else 0.0)
        if physical_right <= physical_left:
            raise ValueError("A cassette is too narrow for the configured seam")
        physical.append((physical_left, physical_right))
    return tuple(physical)


def calculate_run_layout(
    run: dict[str, Any], *, seam_mm: float, terminal_inset_mm: float, cap_width_mm: float
) -> RunLayout:
    """Derive a run whose every internal cassette seam lands on a corbel cap."""

    run_id = str(run["id"])
    length = float(run["nominal_length_mm"])
    modules = int(run["cassette_module_count"])
    corbels = int(run["corbel_count"])
    if length <= 0.0 or modules < 1:
        raise ValueError(f"{run_id}: run length and module count must be positive")
    if corbels != modules + 1:
        raise ValueError(
            f"{run_id}: {modules} modules require exactly {modules + 1} corbels"
        )
    if seam_mm <= 0.0 or seam_mm >= cap_width_mm:
        raise ValueError(f"{run_id}: seam must be positive and narrower than the cap")
    if terminal_inset_mm <= 0.0 or 2.0 * terminal_inset_mm >= length:
        raise ValueError(f"{run_id}: invalid terminal corbel inset")
    if abs(cap_width_mm - 2.0 * terminal_inset_mm) > EPSILON:
        raise ValueError(
            f"{run_id}: the frozen cap must finish flush with both run ends"
        )

    pitch = (length - 2.0 * terminal_inset_mm) / modules
    centers = tuple(terminal_inset_mm + index * pitch for index in range(corbels))
    caps = tuple(
        (center - cap_width_mm / 2.0, center + cap_width_mm / 2.0)
        for center in centers
    )
    seams = centers[1:-1]
    boundaries = (0.0, *seams, length)
    nominal_bounds = tuple(zip(boundaries, boundaries[1:]))
    physical_bounds = _physical_bounds(nominal_bounds, seam_mm)

    for seam, cap in zip(seams, caps[1:-1]):
        if seam < cap[0] - EPSILON or seam > cap[1] + EPSILON:
            raise AssertionError(f"{run_id}: seam is not carried by its corbel cap")

    return RunLayout(
        run_id=run_id,
        length_mm=length,
        cassette_module_count=modules,
        corbel_count=corbels,
        terminal_corbel_center_inset_mm=terminal_inset_mm,
        equal_corbel_pitch_mm=pitch,
        corbel_centers_mm=centers,
        corbel_cap_bounds_mm=caps,
        seam_centers_mm=seams,
        nominal_module_bounds_mm=nominal_bounds,
        physical_module_bounds_mm=physical_bounds,
        nominal_module_widths_mm=tuple(right - left for left, right in nominal_bounds),
        physical_module_widths_mm=tuple(right - left for left, right in physical_bounds),
        minimum_cap_bearing_each_side_of_seam_mm=(cap_width_mm - seam_mm) / 2.0,
        accessory_eligible_corbel_indices=tuple(range(1, corbels - 1)),
    )


def print_envelope(
    part_mm: tuple[float, float, float],
    *,
    printable_volume_mm: tuple[float, float, float],
    brim_mm: float,
    brim_object_gap_mm: float,
) -> PrintEnvelope:
    """Check an XYZ part envelope with the complete outer brim margin.

    Bambu Studio's configured brim-object gap lies between the part and the
    brim.  It therefore consumes bed footprint on both sides just as the brim
    itself does.  ``part_mm`` may already include a separately declared plate
    edge reserve; this helper adds only the brim plus its object gap.
    """

    if not math.isfinite(brim_mm) or brim_mm < 0.0:
        raise ValueError("Brim width must be finite and nonnegative")
    if not math.isfinite(brim_object_gap_mm) or brim_object_gap_mm < 0.0:
        raise ValueError("Brim-object gap must be finite and nonnegative")
    outer_margin = brim_mm + brim_object_gap_mm
    with_brim = (
        part_mm[0] + 2.0 * outer_margin,
        part_mm[1] + 2.0 * outer_margin,
        part_mm[2],
    )
    return PrintEnvelope(
        part_mm=part_mm,
        with_brim_mm=with_brim,
        printable_volume_mm=printable_volume_mm,
        fits=all(
            needed <= available + EPSILON
            for needed, available in zip(with_brim, printable_volume_mm)
        ),
    )


def calculate_plan(cfg: dict[str, Any]) -> ShelfPlan:
    """Calculate the complete frozen nominal R8 scaffold."""

    shelf = cfg["shelf"]
    d_frame = cfg["d_frame"]
    printer = cfg["printer"]
    seam = float(shelf["between_module_seam_mm"])
    terminal_inset = float(shelf["terminal_corbel_center_inset_mm"])
    cap_width = float(d_frame["shelf_bearing_cap_width_across_run_mm"])
    through = calculate_run_layout(
        _run_by_id(cfg, "through"),
        seam_mm=seam,
        terminal_inset_mm=terminal_inset,
        cap_width_mm=cap_width,
    )
    return_run = calculate_run_layout(
        _run_by_id(cfg, "return"),
        seam_mm=seam,
        terminal_inset_mm=terminal_inset,
        cap_width_mm=cap_width,
    )

    d_frame_envelope = _as_three_floats(
        d_frame["prototype_envelope_mm"], "d_frame.prototype_envelope_mm"
    )
    declared_d_frame = (
        float(d_frame["shelf_projection_mm"]),
        float(d_frame["installed_height_mm"]),
        float(d_frame["body_thickness_across_run_mm"]),
    )
    if any(
        abs(left - right) > EPSILON
        for left, right in zip(d_frame_envelope, declared_d_frame)
    ):
        raise ValueError("D-frame envelope disagrees with its named dimensions")
    printable_volume = _as_three_floats(
        printer["printable_volume_mm"], "printer.printable_volume_mm"
    )
    d_frame_print = print_envelope(
        (
            d_frame_envelope[0]
            + 2.0 * float(d_frame["saved_edge_reserve_each_side_mm"]),
            d_frame_envelope[1]
            + 2.0 * float(d_frame["saved_edge_reserve_each_side_mm"]),
            d_frame_envelope[2],
        ),
        printable_volume_mm=printable_volume,
        brim_mm=float(printer["brim_mm"]),
        brim_object_gap_mm=float(printer["brim_object_gap_mm"]),
    )

    sockets_per_corbel = int(cfg["accessory_system"]["sockets_per_eligible_corbel"])
    if sockets_per_corbel < 1:
        raise ValueError("At least one socket is required on an accessory-eligible corbel")
    eligible_per_level = sum(
        len(run.accessory_eligible_corbel_indices) for run in (through, return_run)
    )
    level_count = int(shelf["selected_level_count"])
    if level_count < 1:
        raise ValueError("At least one shelf level is required")
    structural_corbels_per_level = through.corbel_count + return_run.corbel_count
    minimum_screws = int(
        cfg["wall_attachment"]["minimum_metal_structural_screws_per_corbel"]
    )
    if minimum_screws < 3:
        raise ValueError("R8 requires at least three metal structural screws per corbel")
    defaults = cfg["accessory_system"]["default_equipped_station_indices"]
    default_count = 0
    for run in (through, return_run):
        indices = tuple(int(index) for index in defaults[run.run_id])
        if len(indices) != len(set(indices)):
            raise ValueError(f"{run.run_id}: default accessory stations repeat")
        if any(index not in run.accessory_eligible_corbel_indices for index in indices):
            raise ValueError(
                f"{run.run_id}: a default accessory station is not safely eligible"
            )
        default_count += len(indices)

    depth = float(shelf["depth_mm"])
    flat_fit: list[tuple[str, bool]] = []
    edge_yaw_fit: list[tuple[str, PrintEnvelope]] = []
    orientation = shelf["cassette_saved_orientation_candidate"]
    yaw_deg = float(orientation["bed_yaw_deg"])
    if abs(yaw_deg - 45.0) > EPSILON:
        raise ValueError("The current exact cassette envelope proof requires 45 degree yaw")
    edge_reserve = float(orientation["edge_reserve_each_side_mm"])
    if edge_reserve < 0.0:
        raise ValueError("Cassette edge reserve cannot be negative")
    for run in (through, return_run):
        maximum_width = max(run.physical_module_widths_mm)
        envelope = print_envelope(
            (maximum_width, depth, float(shelf["cassette_total_height_mm"])),
            printable_volume_mm=printable_volume,
            brim_mm=float(printer["brim_mm"]),
            brim_object_gap_mm=float(printer["brim_object_gap_mm"]),
        )
        flat_fit.append((run.run_id, envelope.fits))
        rotated_bed_axis = (
            maximum_width + float(shelf["cassette_total_height_mm"])
        ) / math.sqrt(2.0)
        edge_envelope = print_envelope(
            (
                rotated_bed_axis + 2.0 * edge_reserve,
                rotated_bed_axis + 2.0 * edge_reserve,
                depth,
            ),
            printable_volume_mm=printable_volume,
            brim_mm=float(printer["brim_mm"]),
            brim_object_gap_mm=float(printer["brim_object_gap_mm"]),
        )
        edge_yaw_fit.append((run.run_id, edge_envelope))

    return ShelfPlan(
        depth_mm=depth,
        cassette_height_mm=float(shelf["cassette_total_height_mm"]),
        selected_level_count=level_count,
        d_frame_envelope_mm=d_frame_envelope,
        d_frame_saved_print_envelope=d_frame_print,
        through=through,
        return_run=return_run,
        accessory_sockets_per_eligible_corbel=sockets_per_corbel,
        accessory_eligible_corbels_per_level=eligible_per_level,
        accessory_eligible_corbels_selected_levels=eligible_per_level * level_count,
        accessory_socket_count_per_level=eligible_per_level * sockets_per_corbel,
        accessory_socket_count_selected_levels=(
            eligible_per_level * sockets_per_corbel * level_count
        ),
        accessory_default_rails_per_level=default_count,
        accessory_default_rails_selected_levels=default_count * level_count,
        accessory_default_socket_count_per_level=default_count * sockets_per_corbel,
        accessory_default_socket_count_selected_levels=(
            default_count * sockets_per_corbel * level_count
        ),
        cassette_flat_plate_fit_by_run=tuple(flat_fit),
        cassette_edge_yaw_envelope_by_run=tuple(edge_yaw_fit),
        structural_corbels_per_level=structural_corbels_per_level,
        structural_corbels_selected_levels=structural_corbels_per_level * level_count,
        minimum_metal_screws_per_corbel=minimum_screws,
        minimum_metal_screws_per_level=structural_corbels_per_level * minimum_screws,
        minimum_metal_screws_selected_levels=(
            structural_corbels_per_level * minimum_screws * level_count
        ),
    )


def _null_leaf_paths(value: Any, prefix: str) -> tuple[str, ...]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key in sorted(value):
            paths.extend(_null_leaf_paths(value[key], f"{prefix}.{key}"))
        return tuple(paths)
    return (prefix,) if value is None else ()


def production_blockers(cfg: dict[str, Any]) -> tuple[str, ...]:
    """Return deterministic reasons this nominal scaffold cannot be released."""

    project = cfg["project"]
    blockers: list[str] = []
    boolean_gates = (
        ("qualification_only", True),
        ("installed_release_allowed", False),
        ("physical_qualification_complete", False),
        ("production_ready", False),
        ("load_rating_allowed", False),
        ("tested_load_rating_exists", False),
        ("wall_bores_emitted", False),
    )
    for key, blocked_value in boolean_gates:
        if project[key] is blocked_value:
            blockers.append(f"project.{key}")
    if float(project["rated_load_kg"]) <= 0.0 or float(project["rated_load_lb"]) <= 0.0:
        blockers.append("project.zero_rated_load")
    for group in ("wall", "hardware", "field"):
        blockers.extend(
            _null_leaf_paths(
                cfg["unresolved_inputs"][group], f"unresolved_inputs.{group}"
            )
        )
    blockers.extend(_null_leaf_paths(cfg["qualification"], "qualification"))
    blockers.extend(_null_leaf_paths(cfg["printer"], "printer"))

    plan = calculate_plan(cfg)
    if not plan.d_frame_saved_print_envelope.fits:
        blockers.append("printer.d_frame_saved_orientation_does_not_fit")
    orientation = cfg["shelf"]["cassette_saved_orientation_candidate"]
    if not bool(orientation["physical_printability_qualified"]):
        blockers.append(
            "shelf.cassette_saved_orientation_candidate.physical_printability_qualified"
        )
    if not bool(orientation["software_envelope_proven"]):
        blockers.append(
            "shelf.cassette_saved_orientation_candidate.software_envelope_proven"
        )
    if any(not envelope.fits for _, envelope in plan.cassette_edge_yaw_envelope_by_run):
        blockers.append("shelf.cassette_edge_yaw_envelope_exceeds_a1_mini")
    if not bool(cfg["shelf"]["selected_cassette_physical_qualification_complete"]):
        blockers.append("shelf.selected_cassette_physical_qualification_complete")
    if not bool(
        cfg["wall_attachment"][
            "continuous_blocking_or_verified_equivalent_confirmed"
        ]
    ):
        blockers.append(
            "wall_attachment.continuous_blocking_or_verified_equivalent_confirmed"
        )
    return tuple(blockers)
