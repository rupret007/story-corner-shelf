#!/usr/bin/env python3
"""Exact source contract for the shared fixed-crown quarter-turn pin family.

This module deliberately proves only the dimensioned source contract and its
rigid service kinematics.  It requires software-model mapping, but does not
claim that generated parent solids or their Boolean motion sweeps exist; only
the runtime generator may report mapping complete after testing both receiver
variants.  Physical installation and production remain unqualified.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


EPSILON = 1.0e-7


Matrix4 = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]


@dataclass(frozen=True)
class PinVariantContract:
    variant_id: str
    center_u_q_mm: tuple[float, float]
    entry_gate_u_q_mm: tuple[tuple[float, float], tuple[float, float]]
    chamber_u_q_mm: tuple[tuple[float, float], tuple[float, float]]
    entry_throat_e_mm: tuple[float, float]
    index_pocket_e_mm: tuple[float, float]
    chamber_e_mm: tuple[float, float]
    roof_e_mm: tuple[float, float]
    tail_body_e_mm: tuple[float, float]
    index_nub_e_mm: tuple[float, float]
    handle_e_mm: tuple[float, float]
    shaft_e_mm: tuple[float, float]
    clear_approach_translation_e_mm: float
    insertion_translation_e_mm: float
    minimum_parent_floor_after_pocket_mm: float
    minimum_external_collision_clearance_mm: float
    bare_saved_envelope_mm: tuple[float, float, float]
    kinematic_stage_matrices: dict[str, Matrix4]


@dataclass(frozen=True)
class FrontTiePinVariantContract:
    variant_id: str
    center_u_e_mm: tuple[float, float]
    tie_eye_u_e_mm: tuple[tuple[float, float], tuple[float, float]]
    tie_eye_q_mm: tuple[float, float]
    receiver_eye_u_e_mm: tuple[tuple[float, float], tuple[float, float]]
    receiver_eye_q_mm: tuple[float, float]
    receiver_parent_boss_u_e_q_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    original_tie_trim_u_e_q_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    entry_gate_u_e_mm: tuple[tuple[float, float], tuple[float, float]]
    chamber_u_e_mm: tuple[tuple[float, float], tuple[float, float]]
    chamber_q_mm: tuple[float, float]
    rear_capture_wall_q_mm: tuple[float, float]
    entry_throat_q_mm: tuple[float, float]
    tail_body_u_e_q_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    index_nub_u_e_q_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    index_pocket_u_e_q_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    shaft_q_mm: tuple[float, float]
    pull_bar_u_e_q_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    clear_approach_translation_q_mm: float
    insertion_to_rotation_translation_q_mm: float
    minimum_external_collision_clearance_mm: float
    bare_saved_envelope_mm: tuple[float, float, float]
    kinematic_stage_matrices: dict[str, Matrix4]


@dataclass(frozen=True)
class SharedCrownRetentionPinContract:
    family_id: str
    shaft_diameter_mm: float
    shaft_bore_diameter_mm: float
    tail_long_short_axial_mm: tuple[float, float, float]
    entry_gate_long_short_mm: tuple[float, float]
    chamber_u_q_axial_mm: tuple[float, float, float]
    capture_roof_thickness_mm: float
    locked_capture_overlap_each_side_mm: float
    entry_clearance_each_face_mm: float
    shaft_radial_clearance_mm: float
    maximum_rotating_half_extent_mm: float
    minimum_rotation_chamber_clearance_mm: float
    unlock_push_e_mm: float
    index_nub_height_mm: float
    index_pocket_depth_mm: float
    index_clearance_after_push_mm: float
    tail_ceiling_clearance_during_rotation_mm: float
    flat_pull_bar_long_short_axial_mm: tuple[float, float, float]
    keeper: PinVariantContract
    front_tie: FrontTiePinVariantContract
    additional_objects_per_level: int
    additional_objects_two_levels: int
    projected_complete_objects_per_level: int
    projected_complete_objects_two_levels: int
    physical_cycle_count_each_variant: int
    migration_dwell_days: tuple[int, int]
    software_model_mapping_contract_required: bool
    physical_installation_mapping_qualified: bool
    production_release_eligible: bool


def pin_transform_e(rotation_deg: float, translation_e_mm: float) -> Matrix4:
    """Return a rigid transform in the local ``(u, q, e)`` coordinates."""

    radians = math.radians(float(rotation_deg))
    cosine = _zero_small(math.cos(radians))
    sine = _zero_small(math.sin(radians))
    return (
        (cosine, -sine, 0.0, 0.0),
        (sine, cosine, 0.0, 0.0),
        (0.0, 0.0, 1.0, float(translation_e_mm)),
        (0.0, 0.0, 0.0, 1.0),
    )


def pin_transform_q(rotation_deg: float, translation_q_mm: float) -> Matrix4:
    """Return a rigid transform about/along q in local ``(u, q, e)`` space."""

    radians = math.radians(float(rotation_deg))
    cosine = _zero_small(math.cos(radians))
    sine = _zero_small(math.sin(radians))
    return (
        (cosine, 0.0, sine, 0.0),
        (0.0, 1.0, 0.0, float(translation_q_mm)),
        (-sine, 0.0, cosine, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _zero_small(value: float) -> float:
    return 0.0 if abs(value) <= EPSILON else float(value)


def _pair(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label} must be a two-value envelope")
    pair = (float(value[0]), float(value[1]))
    if pair[1] <= pair[0]:
        raise ValueError(f"{label} is empty or reversed")
    return pair


def _pair_of_pairs(value: Any, label: str) -> tuple[tuple[float, float], tuple[float, float]]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label} must contain u and q envelopes")
    return (_pair(value[0], f"{label}.u"), _pair(value[1], f"{label}.q"))


def _triple_of_pairs(
    value: Any, label: str
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must contain three axis envelopes")
    return (
        _pair(value[0], f"{label}.0"),
        _pair(value[1], f"{label}.1"),
        _pair(value[2], f"{label}.2"),
    )


def _close(actual: float, expected: float, label: str) -> None:
    if abs(float(actual) - float(expected)) > EPSILON:
        raise ValueError(f"{label} disagrees with exact derived geometry")


def _span(envelope: tuple[float, float]) -> float:
    return envelope[1] - envelope[0]


def _variant_contract(
    raw: dict[str, Any],
    *,
    variant_id: str,
    entry_key: str,
    push_e: float,
    tail_thickness: float,
    handle_thickness: float,
    handle_long_span: float,
    pocket_depth: float,
    nub_height: float,
    minimum_wall: float,
    saved_envelope: tuple[float, float, float],
) -> PinVariantContract:
    if raw.get("variant_id") != variant_id:
        raise ValueError(f"{variant_id} variant identity drifted")
    center_raw = raw.get("pin_center_inward_u_q_mm")
    if not isinstance(center_raw, list) or len(center_raw) != 2:
        raise ValueError(f"{variant_id} pin center is incomplete")
    center = (float(center_raw[0]), float(center_raw[1]))
    entry = _pair_of_pairs(raw[entry_key], f"{variant_id}.entry_gate")
    chamber_plan = _pair_of_pairs(
        raw["rotation_chamber_u_q_envelopes_mm"],
        f"{variant_id}.rotation_chamber",
    )
    throat_e = _pair(raw["entry_throat_e_envelope_mm"], f"{variant_id}.entry_throat_e")
    pocket_e = _pair(raw["index_pocket_e_envelope_mm"], f"{variant_id}.index_pocket_e")
    chamber_e = _pair(raw["rotation_chamber_e_envelope_mm"], f"{variant_id}.chamber_e")
    roof_e = _pair(raw["capture_roof_e_envelope_mm"], f"{variant_id}.roof_e")
    tail_e = _pair(raw["installed_tail_body_e_envelope_mm"], f"{variant_id}.tail_e")
    nub_e = _pair(raw["installed_index_nub_e_envelope_mm"], f"{variant_id}.nub_e")
    handle_e = _pair(raw["installed_handle_e_envelope_mm"], f"{variant_id}.handle_e")
    shaft_e = _pair(
        raw["shaft_e_envelope_including_0_4_mm_end_unions_mm"],
        f"{variant_id}.shaft_e",
    )

    for axis, axis_name in enumerate(("u", "q")):
        _close((entry[axis][0] + entry[axis][1]) / 2.0, center[axis], f"{variant_id} entry {axis_name} center")
        _close((chamber_plan[axis][0] + chamber_plan[axis][1]) / 2.0, center[axis], f"{variant_id} chamber {axis_name} center")
    _close(throat_e[1], chamber_e[0], f"{variant_id} throat-to-chamber continuity")
    _close(chamber_e[1], roof_e[0], f"{variant_id} chamber-to-roof continuity")
    _close(_span(chamber_e), 3.6, f"{variant_id} chamber axial height")
    _close(_span(roof_e), minimum_wall, f"{variant_id} capture roof")
    _close(_span(tail_e), tail_thickness, f"{variant_id} tail thickness")
    _close(tail_e[0], chamber_e[0], f"{variant_id} seated tail floor")
    _close(nub_e[1], chamber_e[0], f"{variant_id} seated index datum")
    _close(_span(nub_e), nub_height, f"{variant_id} index nub height")
    _close(_span(pocket_e), pocket_depth, f"{variant_id} index pocket depth")
    _close(pocket_e[1], chamber_e[0], f"{variant_id} pocket-to-chamber datum")
    parent_floor_start = float(raw["parent_floor_solid_start_e_mm"])
    _close(pocket_e[0] - parent_floor_start, minimum_wall, f"{variant_id} residual parent floor")
    _close(
        float(raw["minimum_parent_floor_after_index_pocket_mm"]),
        minimum_wall,
        f"{variant_id} configured residual floor",
    )
    _close(_span(handle_e), handle_thickness, f"{variant_id} handle thickness")
    _close(shaft_e[0], handle_e[1] - 0.4, f"{variant_id} handle union")
    _close(shaft_e[1], tail_e[0] + 0.4, f"{variant_id} tail union")

    handle_gap_key = (
        "installed_handle_to_keeper_bottom_clearance_mm"
        if variant_id == "keeper_reach"
        else "installed_handle_to_cassette_underside_clearance_mm"
    )
    lowest_parent = float(raw["lowest_crossed_parent_bottom_e_mm"])
    handle_gap = lowest_parent - handle_e[1]
    _close(handle_gap, float(raw[handle_gap_key]), f"{variant_id} installed handle gap")
    if handle_gap - push_e < 0.2 - EPSILON:
        raise ValueError(f"{variant_id} handle collides during its unlock push")

    clear_tail_top = float(raw["clear_approach_tail_top_e_mm"])
    if lowest_parent - clear_tail_top < 0.4 - EPSILON:
        raise ValueError(f"{variant_id} clear approach lacks 0.4 mm parent clearance")
    clear_translation = float(raw["clear_approach_translation_from_locked_e_mm"])
    insertion = float(raw["insertion_translation_e_mm"])
    _close(clear_translation, clear_tail_top - tail_e[1], f"{variant_id} clear approach transform")
    _close(insertion, push_e - clear_translation, f"{variant_id} insertion stroke")

    unlocked_tail_top = tail_e[1] + push_e
    if chamber_e[1] - unlocked_tail_top < 0.4 - EPSILON:
        raise ValueError(f"{variant_id} tail crowds the chamber ceiling during rotation")

    overall_length = tail_e[1] - handle_e[0]
    _close(overall_length, saved_envelope[0], f"{variant_id} saved axial envelope")
    _close(saved_envelope[1], handle_long_span, f"{variant_id} saved handle envelope")

    minimum_external_clearance = min(
        float(raw.get("minimum_chamber_to_diaphragm_mouth_ligament_mm", math.inf)),
        float(raw.get("minimum_chamber_to_owned_seam_run_ligament_mm", math.inf)),
        float(raw.get("minimum_chamber_to_crown_ear_q_clearance_mm", math.inf)),
        float(raw.get("minimum_chamber_to_shelf_front_wall_mm", math.inf)),
        float(raw.get("minimum_chamber_to_crown_keyway_u_clearance_mm", math.inf)),
        float(raw.get("minimum_rotating_handle_to_crown_ear_q_clearance_mm", math.inf)),
    )

    matrices = {
        "clear_approach_entry_index": pin_transform_e(0.0, clear_translation),
        "inserted_unindexed": pin_transform_e(0.0, push_e),
        "rotated_unseated": pin_transform_e(90.0, push_e),
        "positively_indexed_locked": pin_transform_e(90.0, 0.0),
        "removal_push": pin_transform_e(90.0, push_e),
        "removal_entry_index": pin_transform_e(0.0, push_e),
        "removed_clear": pin_transform_e(0.0, clear_translation),
    }
    return PinVariantContract(
        variant_id=variant_id,
        center_u_q_mm=center,
        entry_gate_u_q_mm=entry,
        chamber_u_q_mm=chamber_plan,
        entry_throat_e_mm=throat_e,
        index_pocket_e_mm=pocket_e,
        chamber_e_mm=chamber_e,
        roof_e_mm=roof_e,
        tail_body_e_mm=tail_e,
        index_nub_e_mm=nub_e,
        handle_e_mm=handle_e,
        shaft_e_mm=shaft_e,
        clear_approach_translation_e_mm=clear_translation,
        insertion_translation_e_mm=insertion,
        minimum_parent_floor_after_pocket_mm=float(raw["minimum_parent_floor_after_index_pocket_mm"]),
        minimum_external_collision_clearance_mm=minimum_external_clearance,
        bare_saved_envelope_mm=saved_envelope,
        kinematic_stage_matrices=matrices,
    )


def _front_tie_q_variant_contract(
    raw: dict[str, Any],
    *,
    tail_long: float,
    tail_short: float,
    tail_axial: float,
    chamber_side: float,
    chamber_axial: float,
    minimum_wall: float,
    push: float,
    nub_dims: tuple[float, float, float],
    pocket_dims: tuple[float, float, float],
    pull_bar_dims: tuple[float, float, float],
    saved_envelope: tuple[float, float, float],
) -> FrontTiePinVariantContract:
    """Validate the visible-front, q-axis member of the shared pin family."""

    if raw.get("variant_id") != "front_tie_reach":
        raise ValueError("front_tie_reach variant identity drifted")
    if raw.get("service_axis") != "visible front toward wall along -q":
        raise ValueError("front-tie pin must remain visible-front q-axis serviceable")
    center_raw = raw.get("pin_center_u_e_mm")
    if not isinstance(center_raw, list) or len(center_raw) != 2:
        raise ValueError("front-tie q-axis center is incomplete")
    center = (float(center_raw[0]), float(center_raw[1]))
    tie_eye = _pair_of_pairs(raw["tie_integral_eye_u_e_envelopes_mm"], "front tie eye")
    tie_eye_q = _pair(raw["tie_integral_eye_q_envelope_mm"], "front tie eye q")
    receiver_eye = _pair_of_pairs(
        raw["cassette_receiver_eye_u_e_envelopes_mm"], "front tie receiver eye"
    )
    receiver_eye_q = _pair(raw["cassette_receiver_eye_q_envelope_mm"], "front tie receiver eye q")
    receiver_boss = _triple_of_pairs(
        raw["cassette_receiver_parent_boss_u_e_q_envelopes_mm"],
        "front tie receiver parent boss",
    )
    tie_trim = _triple_of_pairs(
        raw["local_original_tie_body_trim_u_e_q_envelopes_mm"],
        "front tie local original-body trim",
    )
    entry = _pair_of_pairs(
        raw["tie_and_cassette_entry_gate_u_e_envelopes_mm"], "front tie entry"
    )
    chamber = _pair_of_pairs(raw["rotation_chamber_u_e_envelopes_mm"], "front tie chamber")
    chamber_q = _pair(raw["rotation_chamber_q_envelope_mm"], "front tie chamber q")
    rear_wall_q = _pair(raw["rear_capture_wall_q_envelope_mm"], "front tie rear wall q")
    throat_q = _pair(raw["front_entry_throat_q_envelope_mm"], "front tie throat q")
    tail = _triple_of_pairs(raw["installed_tail_body_u_e_q_envelopes_mm"], "front tie tail")
    nub = _triple_of_pairs(raw["installed_index_nub_u_e_q_envelopes_mm"], "front tie nub")
    pocket = _triple_of_pairs(raw["index_pocket_u_e_q_envelopes_mm"], "front tie pocket")
    shaft_q = _pair(raw["shaft_q_envelope_including_0_4_mm_end_unions_mm"], "front tie shaft q")
    pull_bar = _triple_of_pairs(raw["installed_flat_pull_bar_u_e_q_envelopes_mm"], "front tie pull bar")

    for envelope, label in ((entry, "entry"), (chamber, "chamber")):
        _close((envelope[0][0] + envelope[0][1]) / 2.0, center[0], f"front tie {label} u center")
        _close((envelope[1][0] + envelope[1][1]) / 2.0, center[1], f"front tie {label} e center")
    _close(_span(entry[0]), tail_long + 0.8, "front tie entry long span")
    _close(_span(entry[1]), tail_short + 0.8, "front tie entry short span")
    _close(_span(chamber[0]), chamber_side, "front tie chamber u")
    _close(_span(chamber[1]), chamber_side, "front tie chamber e")
    _close(_span(chamber_q), chamber_axial, "front tie chamber q")
    _close(rear_wall_q[1], chamber_q[0], "front tie rear-wall continuity")
    _close(_span(rear_wall_q), minimum_wall, "front tie rear capture wall")
    _close(throat_q[0], chamber_q[1], "front tie throat continuity")
    _close(tie_eye_q[0], throat_q[0], "front tie eye-to-throat rear datum")
    _close(tie_eye_q[1], throat_q[1], "front tie eye-to-throat front datum")
    _close(tie_eye_q[0] - receiver_eye_q[0], 0.2, "front tie eye rear q fit")
    _close(tie_eye_q[1], receiver_eye_q[1], "front tie front-open eye datum")
    _close(receiver_boss[2][0], rear_wall_q[0], "front tie parent boss rear datum")
    _close(receiver_boss[2][1], throat_q[1], "front tie parent boss front datum")
    _close(tie_trim[2][0], 134.8, "front tie local trim rear datum")
    _close(tie_trim[2][1], tie_eye_q[0], "front tie local trim-to-eye datum")
    if tie_trim[0] != tie_eye[0] or tie_trim[1] != tie_eye[1]:
        raise ValueError("front tie local trim no longer matches its eye footprint")

    eye_walls = (
        entry[0][0] - tie_eye[0][0],
        tie_eye[0][1] - entry[0][1],
        entry[1][0] - tie_eye[1][0],
        tie_eye[1][1] - entry[1][1],
    )
    if min(eye_walls) < minimum_wall - EPSILON:
        raise ValueError("front tie local eye wall fell below the 3.2 mm minimum")
    for actual in eye_walls:
        _close(actual, float(raw["minimum_tie_eye_wall_mm"]), "front tie eye wall")
    for axis in range(2):
        _close(tie_eye[axis][0] - receiver_eye[axis][0], 0.2, "front tie receiver low fit")
        _close(receiver_eye[axis][1] - tie_eye[axis][1], 0.2, "front tie receiver high fit")
    parent_walls = (
        chamber[0][0] - receiver_boss[0][0],
        receiver_boss[0][1] - chamber[0][1],
        chamber[1][0] - receiver_boss[1][0],
        receiver_boss[1][1] - chamber[1][1],
    )
    for actual in parent_walls:
        _close(actual, minimum_wall, "front tie receiver-parent wall")

    _close(_span(tail[0]), tail_short, "front tie locked tail u")
    _close(_span(tail[1]), tail_long, "front tie locked tail e")
    _close(_span(tail[2]), tail_axial, "front tie tail axial q")
    _close((tail[0][0] + tail[0][1]) / 2.0, center[0], "front tie tail u center")
    _close((tail[1][0] + tail[1][1]) / 2.0, center[1], "front tie tail e center")
    if tail[2][0] - chamber_q[0] < 0.4 - EPSILON or chamber_q[1] - tail[2][1] < -EPSILON:
        raise ValueError("front tie seated tail leaves its rotation chamber")

    expected_nub_spans = (nub_dims[1], nub_dims[0], nub_dims[2])
    expected_pocket_spans = (pocket_dims[1], pocket_dims[0], pocket_dims[2])
    for axis in range(3):
        _close(_span(nub[axis]), expected_nub_spans[axis], f"front tie nub axis {axis}")
        _close(_span(pocket[axis]), expected_pocket_spans[axis], f"front tie pocket axis {axis}")
        _close(
            (pocket[axis][0] + pocket[axis][1]) / 2.0,
            (nub[axis][0] + nub[axis][1]) / 2.0 + (0.1 if axis == 2 else 0.0),
            f"front tie pocket center axis {axis}",
        )
    _close(pocket[2][1] - pocket[2][0] - (nub[2][1] - nub[2][0]), 0.2, "front tie nub axial pocket reserve")

    _close(shaft_q[0], tail[2][1] - 0.4, "front tie tail-shaft union")
    _close(shaft_q[1], pull_bar[2][0] + 0.4, "front tie shaft-bar union")
    _close(_span(pull_bar[0]), pull_bar_dims[1], "front tie pull bar short span")
    _close(_span(pull_bar[1]), pull_bar_dims[0], "front tie pull bar long span")
    _close(_span(pull_bar[2]), pull_bar_dims[2], "front tie pull bar axial span")
    _close(pull_bar[2][0] - float(raw["shelf_front_q_mm"]), float(raw["installed_head_to_shelf_front_gap_mm"]), "front tie visible bar gap")

    ear_gap = chamber_q[0] - float(raw["front_crown_ear_max_q_mm"])
    keyway_gap = float(raw["nearest_crown_keyway_inner_u_mm"]) - chamber[0][1]
    arch_gap = chamber[1][0] - float(raw["maximum_arch_extrados_at_pin_u_mm"])
    _close(ear_gap, float(raw["minimum_chamber_to_crown_ear_q_clearance_mm"]), "front tie crown-ear clearance")
    _close(keyway_gap, float(raw["minimum_chamber_to_crown_keyway_u_clearance_mm"]), "front tie crown-keyway clearance")
    _close(arch_gap, float(raw["minimum_chamber_bottom_to_arch_extrados_mm"]), "front tie arch clearance")
    minimum_clearance = min(ear_gap, keyway_gap, arch_gap, *eye_walls, *parent_walls)

    unlock = float(raw["unlock_push_q_mm"])
    if unlock != -push:
        raise ValueError("front tie unlock push must be 0.8 mm toward the wall")
    clear_translation = float(raw["clear_approach_translation_from_locked_q_mm"])
    clear_tail = _pair(raw["clear_approach_tail_q_envelope_mm"], "front tie clear tail q")
    _close(clear_tail[0], tail[2][0] + clear_translation, "front tie clear tail rear")
    _close(clear_tail[1], tail[2][1] + clear_translation, "front tie clear tail front")
    _close(clear_tail[0] - float(raw["shelf_front_q_mm"]), float(raw["minimum_clear_approach_beyond_shelf_front_mm"]), "front tie clear approach")
    insertion = float(raw["clear_approach_to_rotation_translation_q_mm"])
    _close(insertion, unlock - clear_translation, "front tie insertion translation")
    unlocked_tail_q = (tail[2][0] + unlock, tail[2][1] + unlock)
    _close(unlocked_tail_q[0] - chamber_q[0], 0.4, "front tie rotation rear clearance")
    if chamber_q[1] - unlocked_tail_q[1] < 0.4 - EPSILON:
        raise ValueError("front tie tail crowds the rotation chamber front")
    unlocked_nub_q = (nub[2][0] + unlock, nub[2][1] + unlock)
    _close(pocket[2][0] - unlocked_nub_q[1], 0.2, "front tie index release clearance")

    overall_axial = pull_bar[2][1] - tail[2][0]
    _close(saved_envelope[0], overall_axial, "front tie saved axial envelope")
    _close(saved_envelope[1], pull_bar_dims[0], "front tie saved pull-bar envelope")
    _close(saved_envelope[2], pull_bar_dims[1], "front tie saved build height")
    matrices = {
        "clear_approach_entry_index": pin_transform_q(0.0, clear_translation),
        "inserted_unindexed": pin_transform_q(0.0, unlock),
        "rotated_unseated": pin_transform_q(-90.0, unlock),
        "positively_indexed_locked": pin_transform_q(-90.0, 0.0),
        "removal_push": pin_transform_q(-90.0, unlock),
        "removal_entry_index": pin_transform_q(0.0, unlock),
        "removed_clear": pin_transform_q(0.0, clear_translation),
    }
    return FrontTiePinVariantContract(
        variant_id="front_tie_reach",
        center_u_e_mm=center,
        tie_eye_u_e_mm=tie_eye,
        tie_eye_q_mm=tie_eye_q,
        receiver_eye_u_e_mm=receiver_eye,
        receiver_eye_q_mm=receiver_eye_q,
        receiver_parent_boss_u_e_q_mm=receiver_boss,
        original_tie_trim_u_e_q_mm=tie_trim,
        entry_gate_u_e_mm=entry,
        chamber_u_e_mm=chamber,
        chamber_q_mm=chamber_q,
        rear_capture_wall_q_mm=rear_wall_q,
        entry_throat_q_mm=throat_q,
        tail_body_u_e_q_mm=tail,
        index_nub_u_e_q_mm=nub,
        index_pocket_u_e_q_mm=pocket,
        shaft_q_mm=shaft_q,
        pull_bar_u_e_q_mm=pull_bar,
        clear_approach_translation_q_mm=clear_translation,
        insertion_to_rotation_translation_q_mm=insertion,
        minimum_external_collision_clearance_mm=minimum_clearance,
        bare_saved_envelope_mm=saved_envelope,
        kinematic_stage_matrices=matrices,
    )


def crown_retention_pin_contract(cfg: dict[str, Any]) -> SharedCrownRetentionPinContract:
    """Validate both reach variants of the one source-controlled pin family."""

    joinery = cfg["joinery"]
    minimum_wall = float(joinery["minimum_wall_mm"])
    if minimum_wall < 3.2 - EPSILON:
        raise ValueError("Shared crown pins require the frozen 3.2 mm minimum wall")
    contract = joinery["shared_keeper_and_front_tie_quarter_turn_pin"]
    family_id = str(contract["family_id"])
    if family_id != "indexed_vertical_quarter_turn_pin":
        raise ValueError("Shared crown pin family identity drifted")
    retain = joinery["diaphragm_bowtie"]["positive_retention"]
    front = joinery["front_entablature_joint"]["fixed_crown_tie_key"]
    if retain.get("positive_retention_pin_family_id") != family_id or front.get("positive_retention_pin_family_id") != family_id:
        raise ValueError("Keeper and front tie do not reference the same pin family")
    if retain["internal_upward_bayonet_track"].get("front_track_status", "").startswith("RETIRED_AS_A_TONGUE") is False:
        raise ValueError("The colliding second keeper tongue was not retired")

    geometry = contract["shared_pin_geometry"]
    shaft = float(geometry["shaft_diameter_mm"])
    bore = float(geometry["shaft_bore_diameter_mm"])
    tail_long = float(geometry["tail_long_span_mm"])
    tail_short = float(geometry["tail_short_span_mm"])
    tail_axial = float(geometry["tail_axial_thickness_mm"])
    entry_long = float(geometry["entry_gate_long_q_mm"])
    entry_short = float(geometry["entry_gate_short_u_mm"])
    chamber_u, chamber_q = (float(value) for value in geometry["rotation_chamber_u_q_mm"])
    chamber_axial = float(geometry["rotation_chamber_axial_height_mm"])
    roof = float(geometry["capture_roof_thickness_mm"])

    if not (shaft > 0.0 and shaft <= tail_short + EPSILON and tail_short < entry_short and tail_long < entry_long):
        raise ValueError("T-tail or shaft cannot pass the entry gate")
    entry_clearance = min((entry_long - tail_long) / 2.0, (entry_short - tail_short) / 2.0)
    shaft_clearance = (bore - shaft) / 2.0
    capture_overlap = (tail_long - entry_short) / 2.0
    half_extent = math.hypot(tail_long / 2.0, tail_short / 2.0)
    chamber_clearance = min(chamber_u, chamber_q) / 2.0 - half_extent
    _close(entry_clearance, float(geometry["entry_clearance_each_tail_face_mm"]), "tail entry clearance")
    _close(shaft_clearance, float(geometry["shaft_bore_radial_clearance_mm"]), "shaft bore clearance")
    _close(capture_overlap, float(geometry["locked_gate_overlap_each_u_side_mm"]), "locked gate overlap")
    _close(half_extent, float(geometry["maximum_rotating_tail_half_extent_mm"]), "tail rotational half extent")
    _close(chamber_clearance, float(geometry["minimum_rotation_chamber_side_clearance_mm"]), "tail rotation clearance")
    if min(entry_clearance, shaft_clearance, chamber_clearance, capture_overlap) <= 0.0:
        raise ValueError("Shared pin has no positive fit or capture reserve")
    _close(roof, minimum_wall, "shared capture roof")

    pull_bar_dims = (
        float(geometry["flat_pull_bar_long_span_mm"]),
        float(geometry["flat_pull_bar_short_span_mm"]),
        float(geometry["flat_pull_bar_axial_thickness_mm"]),
    )
    if geometry.get("round_handle_disk_allowed") or pull_bar_dims != (8.0, 3.2, 3.2):
        raise ValueError("Shared crown pins require the frozen flat 8 x 3.2 mm pull bar")
    service = contract["exact_service_kinematics"]
    push_e = float(service["unlock_push_along_insertion_axis_mm"])
    if (
        float(service["keeper_entry_orientation_deg"]) != 0.0
        or float(service["keeper_locked_orientation_deg"]) != 90.0
        or float(service["front_tie_entry_orientation_deg"]) != 0.0
        or float(service["front_tie_locked_orientation_deg"]) != -90.0
    ):
        raise ValueError("Shared crown pin variants lost their exact quarter-turn directions")
    if float(service["minimum_external_straight_service_access_mm"]) < 75.0:
        raise ValueError("Shared crown pin lacks straight external service access")
    forbidden = set(str(value) for value in service["forbidden_access"])
    if {"wall/rear", "top/above cassette", "friction-only retention"} - forbidden:
        raise ValueError("Shared crown pin permits forbidden access or friction retention")

    nub = geometry["single_index_nub"]
    nub_dims = tuple(float(value) for value in nub["long_by_short_by_axial_mm"])
    pocket_dims = tuple(float(value) for value in nub["locked_pocket_long_by_short_by_depth_mm"])
    nub_height = nub_dims[2]
    pocket_depth = pocket_dims[2]
    _close((pocket_dims[0] - nub_dims[0]) / 2.0, float(nub["pocket_clearance_per_plan_face_mm"]), "index long clearance")
    _close((pocket_dims[1] - nub_dims[1]) / 2.0, float(nub["pocket_clearance_per_plan_face_mm"]), "index short clearance")
    _close(pocket_depth - nub_height, float(nub["pocket_bottom_clearance_mm"]), "index pocket bottom clearance")
    _close(push_e - nub_height, float(service["index_nub_clearance_after_unlock_push_mm"]), "index release clearance")
    _close(chamber_axial - tail_axial - push_e, float(service["tail_ceiling_clearance_during_rotation_mm"]), "tail rotation ceiling clearance")
    nub_center = float(nub["center_from_pin_axis_on_locked_positive_long_axis_mm"])
    nub_inner_u = nub_center - nub_dims[0] / 2.0
    nub_outer_u = nub_center + nub_dims[0] / 2.0
    pocket_inner_u = nub_inner_u - float(nub["pocket_clearance_per_plan_face_mm"])
    pocket_outer_u = nub_outer_u + float(nub["pocket_clearance_per_plan_face_mm"])
    _close(nub_inner_u, entry_short / 2.0, "index nub starts at locked gate edge")
    _close(nub_outer_u, tail_long / 2.0, "index nub ends at tail edge")
    if pocket_inner_u < entry_short / 2.0 - float(nub["pocket_clearance_per_plan_face_mm"]) - EPSILON or pocket_outer_u > chamber_u / 2.0 + EPSILON:
        raise ValueError("Index pocket leaves the positive-u chamber floor")
    if pocket_dims[1] / 2.0 > chamber_q / 2.0 + EPSILON:
        raise ValueError("Index pocket leaves the q chamber floor")
    if "only the positive locked long-axis position" not in str(nub["wrong_way_rule"]):
        raise ValueError("Index pocket does not reject the wrong-way orientation")

    assembly = contract["fixed_crown_interface_assembly_sequence"]
    if len(assembly) != 7 or "keeper-reach pin" not in assembly[2] or "front-tie-reach pin" not in assembly[4]:
        raise ValueError("Fixed-crown pin assembly order is incomplete")
    disassembly = str(contract["fixed_crown_interface_disassembly_rule"])
    if "fully unload" not in disassembly or "no wall/rear/top access" not in disassembly:
        raise ValueError("Fixed-crown pin disassembly is not safely bottom-serviceable")

    saved = contract["saved_print_orientation"]
    keeper_saved = tuple(float(value) for value in saved["keeper_reach_bare_envelope_mm"])
    tie_saved = tuple(float(value) for value in saved["front_tie_reach_bare_envelope_mm"])
    if saved["production_orientation_allowed"] or saved["support_free_claim_allowed"]:
        raise ValueError(
            "Unqualified pin print orientation was marked support-free or production-qualified"
        )

    keeper = _variant_contract(
        contract["keeper_reach_variant"],
        variant_id="keeper_reach",
        entry_key="cassette_entry_gate_u_q_envelopes_mm",
        push_e=push_e,
        tail_thickness=tail_axial,
        handle_thickness=pull_bar_dims[2],
        handle_long_span=pull_bar_dims[0],
        pocket_depth=pocket_depth,
        nub_height=nub_height,
        minimum_wall=minimum_wall,
        saved_envelope=keeper_saved,
    )
    tie = _front_tie_q_variant_contract(
        contract["front_tie_reach_variant"],
        tail_long=tail_long,
        tail_short=tail_short,
        tail_axial=tail_axial,
        chamber_side=chamber_u,
        chamber_axial=chamber_axial,
        minimum_wall=minimum_wall,
        push=push_e,
        nub_dims=nub_dims,
        pocket_dims=pocket_dims,
        pull_bar_dims=pull_bar_dims,
        saved_envelope=tie_saved,
    )

    keeper_raw = contract["keeper_reach_variant"]
    mouth_edges = tuple(float(value) for value in keeper_raw["adjacent_diaphragm_mouth_q_edges_mm"])
    keeper_q = keeper.chamber_u_q_mm[1]
    _close(keeper_q[0] - mouth_edges[0], float(keeper_raw["minimum_chamber_to_diaphragm_mouth_ligament_mm"]), "keeper rear mouth ligament")
    _close(mouth_edges[1] - keeper_q[1], float(keeper_raw["minimum_chamber_to_diaphragm_mouth_ligament_mm"]), "keeper front mouth ligament")
    if min(keeper_q[0] - mouth_edges[0], mouth_edges[1] - keeper_q[1]) < minimum_wall - EPSILON:
        raise ValueError("Keeper pin chamber crowds a diaphragm mouth")
    _close(keeper.chamber_u_q_mm[0][0], float(keeper_raw["minimum_chamber_to_owned_seam_run_ligament_mm"]), "keeper seam ligament")
    if keeper_raw["front_tongue_emitted"] or not keeper_raw["rear_bayonet_tongue_retained"]:
        raise ValueError("Keeper must use one rear tongue plus the pin, never two tongues")

    gate = contract["qualification_gate"]
    if int(gate["minimum_full_insert_push_rotate_seat_release_cycles_each_variant"]) < 100:
        raise ValueError("Shared crown pins require at least 100 complete cycles per variant")
    migration_days = tuple(int(value) for value in gate["migration_dwell_days"])
    if migration_days != (30, 90) or int(gate["release_migration_gate_days"]) != 90:
        raise ValueError("Shared crown pins require both 30- and 90-day migration gates")
    if not gate["both_actual_parent_receiver_coupons_required"] or not gate["same_actual_black_petg_required"]:
        raise ValueError("Shared crown pins are not tied to both actual-parent PETG coupons")

    counts = contract["object_count_impact_contract"]
    additional_per_level = int(counts["additional_pins_per_level"])
    additional_two = int(counts["additional_pins_selected_two_levels"])
    if (int(counts["keeper_pins_per_level"]), int(counts["front_tie_pins_per_level"])) != (9, 9) or additional_per_level != 18 or additional_two != 36:
        raise ValueError("Shared crown pin object-count impact is not exact")
    if int(counts["projected_complete_objects_per_level_after_inventory_integration"]) != 258 or int(counts["projected_complete_objects_selected_two_levels_after_inventory_integration"]) != 516:
        raise ValueError("Projected post-integration object totals are not 258/516")
    if not bool(contract["software_model_mapping_contract_required"]):
        raise ValueError("Shared crown pins must require runtime software-model mapping proof")
    if bool(contract["physical_installation_mapping_qualified"]):
        raise ValueError("Shared crown pins are not physically installation-qualified")
    if bool(contract["production_release_eligible"]):
        raise ValueError("Shared crown pins are not production-release eligible")
    gate_text = str(contract["software_model_mapping_completion_gate"])
    if (
        "runtime generator" not in gate_text
        or "solid insertion/rotation/removal booleans" not in gate_text
        or "software_model_mapping_complete true" not in gate_text
    ):
        raise ValueError("Shared crown pin software mapping gate omits runtime Boolean proof")

    return SharedCrownRetentionPinContract(
        family_id=family_id,
        shaft_diameter_mm=shaft,
        shaft_bore_diameter_mm=bore,
        tail_long_short_axial_mm=(tail_long, tail_short, tail_axial),
        entry_gate_long_short_mm=(entry_long, entry_short),
        chamber_u_q_axial_mm=(chamber_u, chamber_q, chamber_axial),
        capture_roof_thickness_mm=roof,
        locked_capture_overlap_each_side_mm=capture_overlap,
        entry_clearance_each_face_mm=entry_clearance,
        shaft_radial_clearance_mm=shaft_clearance,
        maximum_rotating_half_extent_mm=half_extent,
        minimum_rotation_chamber_clearance_mm=chamber_clearance,
        unlock_push_e_mm=push_e,
        index_nub_height_mm=nub_height,
        index_pocket_depth_mm=pocket_depth,
        index_clearance_after_push_mm=push_e - nub_height,
        tail_ceiling_clearance_during_rotation_mm=chamber_axial - tail_axial - push_e,
        flat_pull_bar_long_short_axial_mm=pull_bar_dims,
        keeper=keeper,
        front_tie=tie,
        additional_objects_per_level=additional_per_level,
        additional_objects_two_levels=additional_two,
        projected_complete_objects_per_level=int(counts["projected_complete_objects_per_level_after_inventory_integration"]),
        projected_complete_objects_two_levels=int(counts["projected_complete_objects_selected_two_levels_after_inventory_integration"]),
        physical_cycle_count_each_variant=int(gate["minimum_full_insert_push_rotate_seat_release_cycles_each_variant"]),
        migration_dwell_days=migration_days,
        software_model_mapping_contract_required=True,
        physical_installation_mapping_qualified=False,
        production_release_eligible=False,
    )
