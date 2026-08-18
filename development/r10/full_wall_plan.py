#!/usr/bin/env python3
"""Deterministic, zero-rated R10 first-wall topology and qualification plan.

This module turns the measured 61.25-inch wall into exact supports, bays,
cassette halves, splice logs, retention keys, and hardware quantities.  It is
not a drilling schedule, load rating, or production release.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

try:
    from . import capacity_study
except ImportError:  # pragma: no cover - direct script/test execution
    import capacity_study  # type: ignore[no-redef]


G_STANDARD_M_S2 = 9.80665


@dataclass(frozen=True)
class SupportStation:
    index: int
    center_mm: float
    role: str
    visible_corbel_drop_mm: float
    full_structural_strap_drop_mm: float
    cable_receiver_present: bool
    wall_bore_candidates: int


@dataclass(frozen=True)
class BayStation:
    index: int
    left_support_index: int
    right_support_index: int
    left_support_center_mm: float
    right_support_center_mm: float
    midpoint_seam_mm: float
    midpoint_seam_gap_mm: float
    left_half_kind: str
    left_half_length_mm: float
    right_half_kind: str
    right_half_length_mm: float
    splice_log_count: int
    splice_log_span_mm: tuple[float, float]
    midpoint_retention_key_count: int


def _support_drop(role: str, arcade: dict[str, Any]) -> float:
    if role == "outer_bookend_with_cable_receiver":
        return float(arcade["outer_bookend_visible_corbel_drop_mm"])
    if role == "compact_arcade":
        return float(arcade["compact_visible_corbel_drop_mm"])
    if role == "through_side_terminal_corner_placeholder":
        return 0.0
    raise capacity_study.CapacityStudyError(f"unknown support role: {role}")


def derive_supports(config: dict[str, Any]) -> tuple[SupportStation, ...]:
    capacity_study.validate_config(config)
    layout = capacity_study.derive_layout(config)
    arcade = config["printed_arcade"]
    roles = config["field_reference"]["support_roles_left_to_right"]
    if len(layout.centers_mm) != len(roles):
        raise capacity_study.CapacityStudyError("support centers and roles differ in length")
    result = tuple(
        SupportStation(
            index=index,
            center_mm=center,
            role=role,
            visible_corbel_drop_mm=_support_drop(role, arcade),
            full_structural_strap_drop_mm=float(
                arcade["wall_strap_total_drop_from_shelf_underside_mm"]
            ),
            cable_receiver_present=role == "outer_bookend_with_cable_receiver",
            wall_bore_candidates=int(arcade["wall_bore_candidate"]["count_per_support"]),
        )
        for index, (center, role) in enumerate(zip(layout.centers_mm, roles))
    )
    if sum(item.cable_receiver_present for item in result) != 1:
        raise capacity_study.CapacityStudyError("first wall requires exactly one cable bookend")
    return result


def derive_bays(config: dict[str, Any]) -> tuple[BayStation, ...]:
    supports = derive_supports(config)
    wall = float(config["field_reference"]["clear_wall_length_mm"])
    log_length = float(config["printed_arcade"]["splice_log"]["length_mm"])
    cassette = config["printed_arcade"]["cassette_half"]
    midpoint_gap = float(cassette["midpoint_seam_gap_mm"])
    support_gap = float(cassette["support_line_seam_gap_mm"])
    end_clearance = float(cassette["endpoint_clearance_per_end_mm"])
    result: list[BayStation] = []
    for index, (left, right) in enumerate(zip(supports, supports[1:])):
        seam = (left.center_mm + right.center_mm) / 2.0
        left_boundary = end_clearance if index == 0 else left.center_mm + support_gap / 2.0
        right_boundary = (
            wall - end_clearance
            if index == len(supports) - 2
            else right.center_mm - support_gap / 2.0
        )
        left_length = seam - midpoint_gap / 2.0 - left_boundary
        right_length = right_boundary - (seam + midpoint_gap / 2.0)
        result.append(
            BayStation(
                index=index,
                left_support_index=left.index,
                right_support_index=right.index,
                left_support_center_mm=left.center_mm,
                right_support_center_mm=right.center_mm,
                midpoint_seam_mm=round(seam, 6),
                midpoint_seam_gap_mm=midpoint_gap,
                left_half_kind="terminal_outer" if index == 0 else "regular",
                left_half_length_mm=round(left_length, 6),
                right_half_kind=(
                    "terminal_corner" if index == len(supports) - 2 else "regular"
                ),
                right_half_length_mm=round(right_length, 6),
                splice_log_count=3,
                splice_log_span_mm=(
                    round(seam - log_length / 2.0, 6),
                    round(seam + log_length / 2.0, 6),
                ),
                midpoint_retention_key_count=3,
            )
        )
    return tuple(result)


def _validate_topology(config: dict[str, Any]) -> None:
    bays = derive_bays(config)
    if len(bays) != 6:
        raise capacity_study.CapacityStudyError("exactly six independent bays are required")
    cassette = config["printed_arcade"]["cassette_half"]
    regular = float(cassette["regular_printed_length_mm"])
    terminal = float(cassette["terminal_printed_length_mm"])
    for bay in bays:
        expected_left = terminal if bay.left_half_kind == "terminal_outer" else regular
        expected_right = terminal if bay.right_half_kind == "terminal_corner" else regular
        if bay.left_half_length_mm != expected_left or bay.right_half_length_mm != expected_right:
            raise capacity_study.CapacityStudyError("cassette halves no longer close the wall")
        left_log, right_log = bay.splice_log_span_mm
        if left_log <= bay.left_support_center_mm or right_log >= bay.right_support_center_mm:
            raise capacity_study.CapacityStudyError("a midpoint log escaped its independent bay")


def build_plan(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = capacity_study.load_config() if config is None else config
    capacity_study.validate_config(cfg)
    _validate_topology(cfg)
    supports = derive_supports(cfg)
    bays = derive_bays(cfg)
    arcade = cfg["printed_arcade"]
    target = cfg["qualification_target"]
    distributed_force = float(target["distributed_contents_mass_kg"]) * G_STANDARD_M_S2
    point_force = float(target["front_edge_point_mass_kg"]) * G_STANDARD_M_S2
    depth = float(cfg["field_reference"]["shelf_depth_mm"])
    conservative_support_reaction = distributed_force / 6.0 + point_force
    conservative_wall_moment = distributed_force / 6.0 * depth / 2.0 + point_force * depth
    first_wall_article_count = 70
    measurement_station_count = len(bays) * 2 + len(supports)
    minimum_full_size_article_demand = (
        first_wall_article_count
        + int(arcade["hardware_procurement_plan"]["gate5_sacrificial_support_groups"])
        + 3 * first_wall_article_count
    )
    return {
        "schema_version": cfg["schema_version"],
        "scope": "first lower 61.25-inch wall; tabletop qualification only",
        "rating_kg": 0.0,
        "rating_lb": 0.0,
        "drilling_authorized": False,
        "wall_installation_authorized": False,
        "support_stations": [asdict(item) for item in supports],
        "bay_stations": [asdict(item) for item in bays],
        "printed_part_counts": {
            "load_bearing_supports": 7,
            "cassette_halves": 12,
            "splice_logs": 18,
            "independent_log_retainers": 18,
            "bay_local_support_retainers": 12,
            "first_wall_cable_modules": 3,
            "total_first_wall_articles_including_cable_modules": (
                first_wall_article_count
            ),
        },
        "hardware_candidate_counts": {
            "grk_90306_installed": arcade["wall_fastener_candidate"]["quantity_installed"],
            "grk_90306_initial_controlled_lot_buy": arcade[
                "hardware_procurement_plan"
            ]["initial_controlled_lot_purchase_quantity"],
            "dottie_fw14_installed": arcade["washer_candidate"][
                "quantity_installed"
            ],
            "dottie_fw14_initial_controlled_lot_buy": arcade[
                "hardware_procurement_plan"
            ]["initial_controlled_lot_purchase_quantity"],
            "minimum_reserved_before_retests": arcade[
                "hardware_procurement_plan"
            ]["minimum_reserved_quantity_before_retests"],
            "initial_unallocated_spares": arcade["hardware_procurement_plan"][
                "initial_unallocated_spare_quantity"
            ],
        },
        "qualification_scale_counts": {
            "measurement_stations": measurement_station_count,
            "measurement_station_formula": "2 * 6 bay midpoints + 7 supports",
            "minimum_full_size_articles_before_coupons_retests_or_spares": (
                minimum_full_size_article_demand
            ),
            "minimum_full_size_article_formula": "70 + 4 + 3 * 70",
        },
        "assembly_order": (
            "qualify the exact PETG lot, saved orientations, and actual midpoint "
            "interface articles",
            "for each bay slide three logs into the left cassette half to their shoulders",
            "with the right half absent lower one independent retainer through each "
            "left-half top access into its exposed log notch",
            "slide the right cassette half over the logs and captured retainer ends without force",
            "seat each independent bay on the two adjacent broad support half-lands",
            "insert one bay-local retainer straight from the front at each "
            "cassette/support contact, leave its hand paddle 4.0 mm proud, and "
            "shift it 2.4 mm toward that bay",
            "fit the outer-bookend blank and comb/hook through ten service cycles",
            "test the complete set on a flat tabletop and then a framed mock wall",
        ),
        "target_demand_not_capacity": {
            "distributed_contents_force_n": round(distributed_force, 6),
            "front_edge_point_force_n": round(point_force, 6),
            "conservative_support_reaction_n_excluding_dead_mass": round(
                conservative_support_reaction, 6
            ),
            "conservative_wall_moment_n_mm_excluding_dead_mass": round(
                conservative_wall_moment, 6
            ),
            "dead_mass_measured": False,
            "capacity_comparison_permitted": False,
            "external_proof_ballast_formula": (
                "1.5 * (measured shelf dead mass + contents target) "
                "- measured shelf dead mass"
            ),
            "external_point_proof_ballast_formula": (
                "0.5 * measured shelf dead mass, distributed representatively, "
                "+ 1.5 * 9 kg at one front-edge bay"
            ),
        },
        "release_blockers": tuple(sorted(cfg["physical_gates"])),
    }


def main() -> None:
    print(json.dumps(build_plan(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
