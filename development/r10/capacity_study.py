#!/usr/bin/env python3
"""Fail-closed R10 predominantly printed architecture study.

The report compares exact topology and section *geometry*. It never converts
those proxies, a catalog screw value, or the 45 kg physical target into a load
rating. R10 remains 0 kg / 0 lb until the complete qualification sequence and
independent structural review pass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any


R10_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = R10_ROOT.parents[1]
CONFIG_PATH = R10_ROOT / "config.json"
MM_PER_INCH = 25.4
EXPECTED_CONFIG_CANONICAL_SHA256 = (
    "f800b4ef27a6fbdca02594b5fab37e31861199789b196ef34017f3e8f19d9cef"
)


class CapacityStudyError(ValueError):
    """Raised when the predominantly printed study stops being fail-closed."""


@dataclass(frozen=True)
class LayoutEvidence:
    wall_length_mm: float
    support_count: int
    bay_count: int
    centers_mm: tuple[float, ...]
    support_pitch_mm: float
    support_pitch_in: float
    support_faces_flush_with_wall_ends: bool
    r9_pitch_mm: float
    pitch_reduction_percent: float
    nominal_support_share_reduction_percent: float
    support_roles_left_to_right: tuple[str, ...]


@dataclass(frozen=True)
class PrintedArchitectureEvidence:
    support_raw_envelope_mm: tuple[float, float, float]
    support_required_envelope_mm: tuple[float, float, float]
    largest_cassette_half_raw_envelope_mm: tuple[float, float, float]
    largest_cassette_half_required_envelope_mm: tuple[float, float, float]
    splice_log_raw_envelope_mm: tuple[float, float, float]
    splice_log_required_envelope_mm: tuple[float, float, float]
    nominal_core_envelopes_fit_with_margins: bool
    actual_saved_mesh_release_fit_proven: bool
    splice_logs_per_bay: int
    independent_bays: int
    printed_primary_bearing_piece_count: int
    printed_retention_key_count: int
    printed_load_path_piece_count: int
    per_log_gross_area_mm2: float
    per_log_gross_second_moment_mm4: float
    per_log_gross_section_modulus_mm3: float
    per_log_net_area_mm2: float
    per_log_net_second_moment_mm4: float
    per_log_net_section_modulus_mm3: float
    net_to_gross_area_ratio: float
    net_to_gross_second_moment_ratio: float
    net_to_gross_section_modulus_ratio: float
    three_log_net_second_moment_geometry_proxy_mm4: float
    midpoint_section_material_capacity_claimed: bool
    metal_shelf_chassis_present: bool


def _reject_constant(value: str) -> None:
    raise CapacityStudyError(f"non-finite JSON constant is forbidden: {value}")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CapacityStudyError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_object_pairs,
        parse_constant=_reject_constant,
    )


def canonical_config_sha256(config: dict[str, Any]) -> str:
    try:
        payload = json.dumps(
            config,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CapacityStudyError("config is not canonical finite JSON") from error
    return hashlib.sha256(payload).hexdigest()


def _exact_number(value: Any, expected: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapacityStudyError(f"{name} must be an exact numeric value")
    result = float(value)
    if not math.isfinite(result) or not math.isclose(
        result, expected, rel_tol=0.0, abs_tol=1.0e-9
    ):
        raise CapacityStudyError(f"{name} drifted: {result} != {expected}")
    return result


def _exact_int(value: Any, expected: int, name: str) -> int:
    if type(value) is not int or value != expected:
        raise CapacityStudyError(f"{name} drifted: {value!r} != {expected}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_reference_hashes(config: dict[str, Any]) -> None:
    records = config["frozen_r9_inputs"]
    if not isinstance(records, dict) or not records:
        raise CapacityStudyError("frozen R9 input hashes are required")
    for relative, expected in records.items():
        path = REPOSITORY_ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            raise CapacityStudyError(f"frozen R9 input changed: {relative}")


def validate_config(config: dict[str, Any]) -> None:
    identity = canonical_config_sha256(config)
    if identity != EXPECTED_CONFIG_CANONICAL_SHA256:
        raise CapacityStudyError(
            "R10 fixed-design config changed without a versioned contract update: "
            f"{identity}"
        )
    if config.get("schema_version") != "r10_printed_arcade_study_v1":
        raise CapacityStudyError("R10 schema changed")
    project = config["project"]
    if project.get("qualification_only") is not True:
        raise CapacityStudyError("R10 must remain qualification-only")
    for key in (
        "production_ready",
        "wall_installation_authorized",
        "physical_qualification_complete",
        "tested_load_rating_exists",
    ):
        if project.get(key) is not False:
            raise CapacityStudyError(f"project.{key} must remain false")
    _exact_number(project["rated_load_kg"], 0.0, "rated kg")
    _exact_number(project["rated_load_lb"], 0.0, "rated lb")

    field = config["field_reference"]
    _exact_number(field["clear_wall_length_mm"], 1555.75, "wall length")
    _exact_number(field["shelf_top_elevation_in"], 68.0, "shelf elevation")
    _exact_number(field["shelf_depth_mm"], 152.4, "shelf depth")
    _exact_number(field["first_support_center_from_left_mm"], 15.875, "first center")
    _exact_number(field["last_support_center_from_left_mm"], 1539.875, "last center")
    _exact_int(field["support_count"], 7, "support count")
    _exact_int(field["bay_count"], 6, "bay count")
    expected_roles = [
        "outer_bookend_with_cable_receiver",
        "compact_arcade",
        "compact_arcade",
        "compact_arcade",
        "compact_arcade",
        "compact_arcade",
        "through_side_terminal_corner_placeholder",
    ]
    if field.get("support_roles_left_to_right") != expected_roles:
        raise CapacityStudyError("support roles or cable/corner endpoints drifted")
    if field.get("supports_evenly_spaced") is not True:
        raise CapacityStudyError("supports must remain evenly spaced")
    if field.get("continuous_blocking_required") is not True:
        raise CapacityStudyError("continuous blocking must remain required")
    if field.get("hollow_wall_anchor_primary_load_path_allowed") is not False:
        raise CapacityStudyError("generic hollow-wall anchors remain forbidden")
    _exact_number(field["outlet_top_elevation_in"], 53.5, "outlet top")
    unresolved = field.get("unresolved_inputs")
    expected_unresolved = {
        "outlet_horizontal_bounds_mm",
        "plug_and_cord_service_envelope_mm",
        "door_and_trim_service_envelope_mm",
        "wall_bow_profile_mm",
        "inside_corner_angle_deg",
        "wall_substrate_material",
        "wall_substrate_thickness_mm",
        "blocking_species_grade_and_thickness",
    }
    if not isinstance(unresolved, dict) or set(unresolved) != expected_unresolved:
        raise CapacityStudyError("field unresolved-input schema drifted")
    if any(value is not None for value in unresolved.values()):
        raise CapacityStudyError("field inputs require a versioned measured-data revision")

    target = config["qualification_target"]
    _exact_number(target["distributed_contents_mass_kg"], 45.0, "target kg")
    _exact_number(target["distributed_contents_mass_lb"], 99.208018, "target lb")
    _exact_number(target["front_edge_point_mass_kg"], 9.0, "point target kg")
    _exact_number(target["proof_multiplier"], 1.5, "proof multiplier")
    _exact_int(target["sustained_creep_hours"], 1000, "creep hours")
    _exact_number(
        target["temperature_qualification_margin_c"], 5.0, "temperature margin"
    )
    if target.get("maximum_service_temperature_c") is not None:
        raise CapacityStudyError("service temperature must remain unresolved before survey")
    if (
        target.get(
            "dead_mass_must_be_measured_and_included_in_total_fixture_demand"
        )
        is not True
    ):
        raise CapacityStudyError(
            "dead mass must remain included exactly once in total fixture demand"
        )
    if target.get("rating_created_by_target") is not False:
        raise CapacityStudyError("a physical target may not become a rating")

    arcade = config["printed_arcade"]
    if arcade.get("architecture_id") != "r10_palatine_lincoln_arcade_v1":
        raise CapacityStudyError("printed arcade identity changed")
    if arcade.get("metal_shelf_chassis_present") is not False:
        raise CapacityStudyError("the active R10 shelf chassis must remain printed")
    if arcade.get("printed_material") != "SUNLU standard black PETG, ASIN B0D1KC72YP":
        raise CapacityStudyError("exact printed material identity changed")
    _exact_number(arcade["support_run_width_mm"], 31.75, "support width")
    _exact_number(arcade["wall_chord_mm"], 19.05, "wall chord")
    _exact_number(
        arcade["wall_strap_total_drop_from_shelf_underside_mm"],
        158.75,
        "wall-strap drop",
    )
    _exact_number(arcade["support_top_chord_mm"], 19.05, "top chord")
    _exact_number(arcade["compression_web_mm"], 19.05, "compression web")
    _exact_number(arcade["front_nose_mm"], 31.75, "front nose")
    _exact_number(arcade["compact_visible_corbel_drop_mm"], 76.2, "compact drop")
    _exact_number(
        arcade["outer_bookend_visible_corbel_drop_mm"], 120.65, "bookend drop"
    )
    if arcade.get("full_structural_wall_strap_hidden_behind_shorter_corbel") is not True:
        raise CapacityStudyError("the shorter corbel may not shorten the structural wall strap")
    if arcade.get("roman_recess_receives_structural_credit") is not False:
        raise CapacityStudyError("ornamental Roman recess may not receive credit")
    _exact_number(arcade["shelf_total_thickness_mm"], 32.0, "shelf thickness")

    log = arcade["splice_log"]
    _exact_int(log["quantity"], 18, "splice log quantity")
    _exact_int(log["per_bay"], 3, "splice logs per bay")
    if log.get("stations") != ["rear", "center", "front"]:
        raise CapacityStudyError("three independent splice-log stations are required")
    _exact_number(log["length_mm"], 159.1, "splice log length")
    _exact_number(log["width_in_shelf_depth_mm"], 20.0, "splice log width")
    _exact_number(log["height_mm"], 24.0, "splice log height")
    _exact_number(log["engagement_per_cassette_half_mm"], 79.375, "log engagement")
    _exact_number(log["clearance_per_face_mm"], 0.4, "splice clearance")
    if log.get("captured_dovetail_channel") is not True:
        raise CapacityStudyError("captured dovetail channels are required")
    if log.get("positive_body_shoulder") is not True:
        raise CapacityStudyError("positive log shoulders are required")
    if log.get("structural_credit_from_friction_or_snap") is not False:
        raise CapacityStudyError("friction and snap retention receive no credit")
    section = log.get("midpoint_section_geometry_proxy")
    if not isinstance(section, dict):
        raise CapacityStudyError("mesh-derived midpoint section evidence is required")
    expected_section = {
        "gross_area_mm2": 464.0,
        "gross_centroid_z_mm": 11.863505747126437,
        "gross_second_moment_about_y_mm4": 22428.688697,
        "gross_governing_section_modulus_mm3": 1848.036857,
        "net_area_mm2": 334.8000145,
        "net_centroid_z_mm": 8.492075247596894,
        "net_second_moment_about_y_mm4": 8263.957405,
        "net_governing_section_modulus_mm3": 949.015628,
        "net_to_gross_area_ratio": 0.721551755,
        "net_to_gross_second_moment_ratio": 0.368454773,
        "net_to_gross_section_modulus_ratio": 0.513526353,
    }
    if set(section) != {*expected_section, "material_capacity_claimed"}:
        raise CapacityStudyError("midpoint section evidence schema drifted")
    for key, expected in expected_section.items():
        _exact_number(section[key], expected, f"midpoint section {key}")
    if section.get("material_capacity_claimed") is not False:
        raise CapacityStudyError("section geometry may not create a material capacity")

    midpoint_key = arcade["transverse_lock_key"]
    _exact_int(midpoint_key["quantity"], 18, "log-retainer quantity")
    _exact_int(midpoint_key["per_bay"], 3, "log retainers per bay")
    if midpoint_key.get("stations") != ["rear", "center", "front"]:
        raise CapacityStudyError("each log station requires an independent retainer")
    for key in ("one_log_per_key", "single_key_cannot_release_all_three_logs"):
        if midpoint_key.get(key) is not True:
            raise CapacityStudyError(f"log-retainer redundancy drifted: {key}")
    if midpoint_key.get("structural_capacity_credit") is not False:
        raise CapacityStudyError("log retainers remain retention-only")
    _exact_number(midpoint_key["width_along_run_mm"], 12.0, "log-retainer width")
    _exact_number(
        midpoint_key["length_across_one_log_station_mm"], 28.0, "log-retainer length"
    )
    _exact_number(midpoint_key["height_mm"], 6.0, "log-retainer height")
    if midpoint_key.get("integrated_flush_access_cap") is not True:
        raise CapacityStudyError("each log retainer requires its integrated flush cap")
    _exact_number(midpoint_key["flush_cap_run_length_mm"], 6.0, "log-retainer cap run")
    _exact_number(
        midpoint_key["flush_cap_additional_height_mm"], 4.8, "log-retainer cap height"
    )
    if midpoint_key.get("saved_print_envelope_mm") != [12.4, 28.0, 10.8]:
        raise CapacityStudyError("log-retainer saved envelope drifted")
    if midpoint_key.get("loose_access_closure_present") is not False:
        raise CapacityStudyError("a separate loose log-access closure is forbidden")
    support_key = arcade["support_capture_key"]
    _exact_int(support_key["quantity"], 12, "support-retainer quantity")
    _exact_int(support_key["per_bay"], 2, "support retainers per bay")
    _exact_number(support_key["width_along_run_mm"], 8.0, "support-retainer width")
    _exact_number(support_key["shelf_depth_mm"], 136.0, "support-retainer depth")
    _exact_number(support_key["height_mm"], 6.0, "support-retainer height")
    for key, expected in (
        ("front_inserted", True),
        ("one_cassette_support_contact_per_key", True),
        ("interior_left_and_right_functions_separate", True),
        ("gravity_or_bending_capacity_credit", False),
        ("retention_only", True),
        ("bearing_land_must_remain_uninterrupted_above_key", True),
    ):
        if support_key.get(key) is not expected:
            raise CapacityStudyError(f"support-capture key rule drifted: {key}")
    for key, expected in (
        ("shaft_width_along_run_mm", 3.8),
        ("rear_dog_depth_mm", 8.0),
        ("front_handle_depth_mm", 12.0),
        ("front_hand_grip_protrusion_mm", 4.0),
        ("bayonet_shift_toward_bay_mm", 2.4),
        ("support_capture_lug_width_along_run_mm", 12.0),
    ):
        _exact_number(support_key[key], expected, f"support-capture {key}")
    if support_key.get("positive_no_friction_walkout_stop") is not True:
        raise CapacityStudyError("support retainers require a positive walkout stop")
    if support_key.get("retention_depends_on_friction_or_snap") is not False:
        raise CapacityStudyError("support retention may not depend on friction or snap")

    cassette = arcade["cassette_half"]
    _exact_int(cassette["regular_quantity"], 10, "regular halves")
    _exact_int(cassette["terminal_quantity"], 2, "terminal halves")
    _exact_number(cassette["regular_nominal_length_mm"], 127.0, "regular nominal")
    _exact_number(cassette["terminal_nominal_length_mm"], 142.875, "terminal nominal")
    _exact_number(cassette["regular_printed_length_mm"], 126.65, "regular printed")
    _exact_number(cassette["terminal_printed_length_mm"], 142.35, "terminal printed")
    _exact_number(cassette["midpoint_seam_gap_mm"], 0.35, "midpoint seam")
    _exact_number(cassette["support_line_seam_gap_mm"], 0.35, "support seam")
    _exact_number(cassette["endpoint_clearance_per_end_mm"], 0.35, "end clearance")
    _exact_number(cassette["depth_mm"], 152.4, "cassette depth")
    _exact_number(cassette["total_height_mm"], 32.0, "cassette height")
    _exact_number(cassette["top_skin_mm"], 4.0, "top skin")
    _exact_number(cassette["bottom_skin_mm"], 3.2, "bottom skin")
    _exact_number(cassette["load_web_thickness_mm"], 4.0, "load-web thickness")
    _exact_number(cassette["support_half_land_nominal_mm"], 15.875, "nominal land")
    _exact_number(
        cassette["minimum_cassette_bearing_contact_mm"], 15.7, "bearing contact"
    )
    if not math.isclose(
        float(log["length_mm"]),
        2.0 * float(log["engagement_per_cassette_half_mm"])
        + float(cassette["midpoint_seam_gap_mm"]),
        abs_tol=1.0e-9,
    ):
        raise CapacityStudyError("log length no longer bridges seam at exact engagement")
    if cassette.get("midpoint_seam_bridged_by_three_logs") is not True:
        raise CapacityStudyError("all three logs must bridge the midpoint seam")
    channel_height = float(log["height_mm"]) + 2.0 * float(
        log["clearance_per_face_mm"]
    )
    available_height = (
        float(cassette["total_height_mm"])
        - float(cassette["top_skin_mm"])
        - float(cassette["bottom_skin_mm"])
    )
    if not math.isclose(channel_height, available_height, abs_tol=1.0e-9):
        raise CapacityStudyError("cassette skins no longer close the cleared log channel")
    if cassette.get("load_web_stations") != ["rear", "center", "front"]:
        raise CapacityStudyError("cassette must retain three load-web stations")
    if cassette.get("support_locator_receives_structural_credit") is not False:
        raise CapacityStudyError("shallow locators may not receive load credit")

    bore = arcade["wall_bore_candidate"]
    _exact_int(bore["count_per_support"], 3, "bores per support")
    _exact_number(bore["diameter_mm"], 7.0, "bore diameter")
    expected_drops = [19.05, 79.375, 139.7]
    if bore.get("drops_below_shelf_underside_mm") != expected_drops:
        raise CapacityStudyError("wall-bore candidate spacing drifted")
    _exact_number(
        bore["washer_bearing_land_outer_diameter_mm"], 27.025, "washer land"
    )
    for key, expected in (
        ("surface_bearing_only", True),
        ("counterbore_allowed", False),
        ("candidate_geometry_is_not_a_drilling_schedule", True),
    ):
        if bore.get(key) is not expected:
            raise CapacityStudyError(f"wall-bore safety rule drifted: {key}")

    cable = arcade["cable_system"]
    _exact_int(cable["full_l_outer_bookends_per_level"], 2, "outer bookends")
    _exact_int(cable["first_wall_active_bookends"], 1, "first-wall bookend")
    if cable.get("active_first_wall_support_indices") != [0]:
        raise CapacityStudyError("cable receiver moved away from the outer bookend")
    _exact_int(cable["sockets_per_bookend"], 2, "sockets per bookend")
    _exact_int(cable["first_wall_flush_blank_quantity"], 2, "first-wall blanks")
    _exact_int(cable["first_wall_comb_hook_quantity"], 1, "first-wall combs")
    _exact_int(
        cable["eventual_full_l_flush_blank_quantity_per_level"], 4, "full-L blanks"
    )
    _exact_int(
        cable["eventual_full_l_comb_hook_quantity_per_level"], 2, "full-L combs"
    )
    _exact_number(cable["socket_clearance_per_face_mm"], 0.4, "socket clearance")
    _exact_number(cable["service_lift_mm"], 8.0, "socket service lift")
    for key, expected in (
        ("inward_facing", True),
        ("flush_blank_required_when_unused", True),
        ("multi_cable_comb_hook_required", True),
        ("allowed_on_intermediate_supports", False),
        ("allowed_at_inside_corner", False),
        ("structural_credit", False),
    ):
        if cable.get(key) is not expected:
            raise CapacityStudyError(f"cable-system rule drifted: {key}")

    fastener = arcade["wall_fastener_candidate"]
    _exact_int(fastener["quantity_installed"], 21, "installed screws")
    _exact_int(fastener["fasteners_per_support"], 3, "screws per support")
    if fastener.get("product") != (
        "GRK RSS Rugged Structural Screw, Climatek, 1/4 in x 3-1/2 in, "
        "T25, part 90306"
    ):
        raise CapacityStudyError("exact GRK candidate changed")
    for key, expected in (
        ("printed_or_drywall_fastener_substitution_allowed", False),
        ("final_schedule_requires_actual_blocking_and_substrate", True),
        ("esr_2442_covers_petg_or_loose_washer_stack", False),
        ("independent_connection_qualification_required", True),
        ("manufacturer_thread_length_documents_conflict", True),
        ("received_dimensions_control_fixture", True),
        ("pilot_spacing_and_screw_group_review_required", True),
    ):
        if fastener.get(key) is not expected:
            raise CapacityStudyError(f"fastener safety rule drifted: {key}")
    if fastener.get("received_thread_length_mm") is not None:
        raise CapacityStudyError("received screw thread length remains unresolved")
    washer = arcade["washer_candidate"]
    if washer.get("product") != (
        "L.H. Dottie FW14 1/4 in USS flat washer, unhardened carbon steel, "
        "zinc plated, ASME B18.21.1"
    ):
        raise CapacityStudyError("exact washer candidate changed")
    if (
        washer.get("manufacturer") != "L.H. Dottie"
        or washer.get("part_number") != "FW14"
    ):
        raise CapacityStudyError("washer manufacturer or part number changed")
    _exact_int(washer["standard_package_quantity"], 100, "washer pack quantity")
    _exact_int(washer["quantity_installed"], 21, "installed washers")
    for key, expected in (
        ("minimum_inner_diameter_mm", 7.7978),
        ("maximum_inner_diameter_mm", 8.3058),
        ("minimum_outer_diameter_mm", 18.4658),
        ("maximum_outer_diameter_mm", 19.0246),
        ("minimum_thickness_mm", 1.2954),
        ("maximum_thickness_mm", 2.032),
    ):
        _exact_number(washer[key], expected, f"washer {key}")
    if washer.get("stacking_allowed") is not False:
        raise CapacityStudyError("washers may not be stacked")
    if washer.get("certificate_or_received_lot_record_required") is not True:
        raise CapacityStudyError("washer lot or certificate record remains required")
    if washer.get("loose_washer_stack_is_outside_esr_2442") is not True:
        raise CapacityStudyError("loose washer stack must remain outside ESR-2442")

    procurement = arcade["hardware_procurement_plan"]
    expected_procurement = {
        "gate5_sacrificial_support_groups": 4,
        "gate5_screw_and_washer_quantity": 12,
        "gate6_and_gate7_mock_wall_quantity": 21,
        "gate8_fresh_creep_wall_quantity": 21,
        "gate9_fresh_destructive_wall_quantity": 21,
        "released_final_installation_reserve_quantity": 21,
        "minimum_reserved_quantity_before_retests": 96,
        "initial_controlled_lot_purchase_quantity": 100,
        "initial_unallocated_spare_quantity": 4,
        "replenish_same_candidate_before_final_install_if_reserve_is_consumed": True,
        "purchase_requires_field_stack_and_reviewed_fixture_plan": True,
    }
    if procurement != expected_procurement:
        raise CapacityStudyError("hardware procurement allocation drifted")
    allocated = sum(
        procurement[key]
        for key in (
            "gate5_screw_and_washer_quantity",
            "gate6_and_gate7_mock_wall_quantity",
            "gate8_fresh_creep_wall_quantity",
            "gate9_fresh_destructive_wall_quantity",
            "released_final_installation_reserve_quantity",
        )
    )
    if allocated != procurement["minimum_reserved_quantity_before_retests"]:
        raise CapacityStudyError("hardware reserve no longer reconciles")
    if (
        allocated + procurement["initial_unallocated_spare_quantity"]
        != procurement["initial_controlled_lot_purchase_quantity"]
    ):
        raise CapacityStudyError("hardware purchase no longer covers reserve plus spares")

    gates = config["physical_gates"]
    if not gates or any(value is not False for value in gates.values()):
        raise CapacityStudyError("all physical gates must start fail-closed")
    _validate_reference_hashes(config)


def derive_layout(config: dict[str, Any]) -> LayoutEvidence:
    field = config["field_reference"]
    first = float(field["first_support_center_from_left_mm"])
    last = float(field["last_support_center_from_left_mm"])
    count = int(field["support_count"])
    pitch = (last - first) / (count - 1)
    centers = tuple(round(first + index * pitch, 6) for index in range(count))
    r9_pitch = 304.75
    width = float(config["printed_arcade"]["support_run_width_mm"])
    faces_flush = math.isclose(first - width / 2.0, 0.0, abs_tol=1.0e-9) and math.isclose(
        last + width / 2.0, float(field["clear_wall_length_mm"]), abs_tol=1.0e-9
    )
    return LayoutEvidence(
        wall_length_mm=float(field["clear_wall_length_mm"]),
        support_count=count,
        bay_count=int(field["bay_count"]),
        centers_mm=centers,
        support_pitch_mm=round(pitch, 6),
        support_pitch_in=round(pitch / MM_PER_INCH, 6),
        support_faces_flush_with_wall_ends=faces_flush,
        r9_pitch_mm=r9_pitch,
        pitch_reduction_percent=round((1.0 - pitch / r9_pitch) * 100.0, 6),
        nominal_support_share_reduction_percent=round((1.0 - 6.0 / 7.0) * 100.0, 6),
        support_roles_left_to_right=tuple(field["support_roles_left_to_right"]),
    )


def _required(raw: tuple[float, float, float]) -> tuple[float, float, float]:
    radial = 5.0 + 0.1 + 2.0
    return (round(raw[0] + 2.0 * radial, 6), round(raw[1] + 2.0 * radial, 6), raw[2])


def derive_printed_architecture(config: dict[str, Any]) -> PrintedArchitectureEvidence:
    arcade = config["printed_arcade"]
    cassette = arcade["cassette_half"]
    log = arcade["splice_log"]
    support_raw = (152.4, 158.75, 31.75)
    cassette_raw = (
        float(cassette["terminal_printed_length_mm"]),
        float(cassette["total_height_mm"]),
        float(cassette["depth_mm"]),
    )
    log_raw = (
        float(log["length_mm"]),
        float(log["width_in_shelf_depth_mm"]),
        float(log["height_mm"]),
    )
    required = tuple(_required(item) for item in (support_raw, cassette_raw, log_raw))
    fits = all(
        all(value <= 180.0 + 1.0e-9 for value in envelope)
        for envelope in required
    )
    section = log["midpoint_section_geometry_proxy"]
    primary_bearing_pieces = 7 + 12 + 18
    retention_keys = 18 + 12
    return PrintedArchitectureEvidence(
        support_raw_envelope_mm=support_raw,
        support_required_envelope_mm=required[0],
        largest_cassette_half_raw_envelope_mm=cassette_raw,
        largest_cassette_half_required_envelope_mm=required[1],
        splice_log_raw_envelope_mm=log_raw,
        splice_log_required_envelope_mm=required[2],
        nominal_core_envelopes_fit_with_margins=fits,
        actual_saved_mesh_release_fit_proven=False,
        splice_logs_per_bay=int(log["per_bay"]),
        independent_bays=int(config["field_reference"]["bay_count"]),
        printed_primary_bearing_piece_count=primary_bearing_pieces,
        printed_retention_key_count=retention_keys,
        printed_load_path_piece_count=primary_bearing_pieces + retention_keys,
        per_log_gross_area_mm2=round(float(section["gross_area_mm2"]), 6),
        per_log_gross_second_moment_mm4=round(
            float(section["gross_second_moment_about_y_mm4"]), 6
        ),
        per_log_gross_section_modulus_mm3=round(
            float(section["gross_governing_section_modulus_mm3"]), 6
        ),
        per_log_net_area_mm2=round(float(section["net_area_mm2"]), 6),
        per_log_net_second_moment_mm4=round(
            float(section["net_second_moment_about_y_mm4"]), 6
        ),
        per_log_net_section_modulus_mm3=round(
            float(section["net_governing_section_modulus_mm3"]), 6
        ),
        net_to_gross_area_ratio=round(float(section["net_to_gross_area_ratio"]), 9),
        net_to_gross_second_moment_ratio=round(
            float(section["net_to_gross_second_moment_ratio"]), 9
        ),
        net_to_gross_section_modulus_ratio=round(
            float(section["net_to_gross_section_modulus_ratio"]), 9
        ),
        three_log_net_second_moment_geometry_proxy_mm4=round(
            3.0 * float(section["net_second_moment_about_y_mm4"]), 6
        ),
        midpoint_section_material_capacity_claimed=bool(
            section["material_capacity_claimed"]
        ),
        metal_shelf_chassis_present=bool(arcade["metal_shelf_chassis_present"]),
    )


def build_report(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config() if config is None else config
    validate_config(cfg)
    layout = derive_layout(cfg)
    architecture = derive_printed_architecture(cfg)
    target = cfg["qualification_target"]
    cable = cfg["printed_arcade"]["cable_system"]
    field = cfg["field_reference"]
    arcade = cfg["printed_arcade"]
    shelf_underside_in = float(field["shelf_top_elevation_in"]) - (
        float(arcade["shelf_total_thickness_mm"]) / MM_PER_INCH
    )
    strap_bottom_in = shelf_underside_in - (
        float(arcade["wall_strap_total_drop_from_shelf_underside_mm"]) / MM_PER_INCH
    )
    return {
        "schema_version": cfg["schema_version"],
        "qualification_only": True,
        "production_ready": False,
        "wall_installation_authorized": False,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "critical_correction": (
            "The prior 16.000337 kg figure is CAD-solid mass context, not capacity. "
            "R10 has no load rating."
        ),
        "layout": asdict(layout),
        "printed_architecture": asdict(architecture),
        "envelope_evidence_boundary": (
            "Current envelopes screen nominal cores only. Release fit must be derived "
            "from every final saved mesh, including receiver, ornament, locators, and keys."
        ),
        "load_path": (
            "stored contents -> printed cassette skins/webs -> three captured PETG "
            "splice logs plus direct support-capital bearing -> seven Palatine PETG "
            "supports -> 21 GRK/washer candidates -> verified continuous blocking"
        ),
        "cable_memory": {
            "full_l_outer_bookends_per_level": cable["full_l_outer_bookends_per_level"],
            "first_wall_active_bookends": cable["first_wall_active_bookends"],
            "sockets_per_bookend": cable["sockets_per_bookend"],
            "first_wall_flush_blank_quantity": cable["first_wall_flush_blank_quantity"],
            "first_wall_comb_hook_quantity": cable["first_wall_comb_hook_quantity"],
            "flush_blank_and_comb_hook_required": True,
            "intermediate_and_corner_hardware_forbidden": True,
            "structural_credit": False,
        },
        "physical_target": {
            "distributed_contents_mass_kg": target["distributed_contents_mass_kg"],
            "front_edge_point_mass_kg": target["front_edge_point_mass_kg"],
            "proof_multiplier": target["proof_multiplier"],
            "target_is_not_a_rating": True,
            "dead_mass_included_in_tests": True,
            "sustained_creep_hours": target["sustained_creep_hours"],
            "maximum_service_temperature_c": target["maximum_service_temperature_c"],
            "qualification_temperature_c": None,
            "external_proof_ballast_formula": (
                "1.5 * (measured shelf dead mass + contents target) "
                "- measured shelf dead mass"
            ),
            "external_point_proof_ballast_formula": (
                "0.5 * measured shelf dead mass, distributed representatively, "
                "+ 1.5 * 9 kg at one front-edge bay"
            ),
        },
        "field_clearance_screen": {
            "shelf_underside_elevation_in": round(shelf_underside_in, 6),
            "structural_strap_bottom_elevation_in": round(strap_bottom_in, 6),
            "vertical_gap_above_outlet_top_in": round(
                strap_bottom_in - float(field["outlet_top_elevation_in"]), 6
            ),
            "vertical_only": True,
            "horizontal_outlet_plug_cord_trim_clearance_verified": False,
        },
        "wall_bore_candidate": {
            **cfg["printed_arcade"]["wall_bore_candidate"],
            "drilling_authorized": False,
        },
        "release_blockers": tuple(sorted(cfg["physical_gates"])),
    }


def main() -> None:
    print(json.dumps(build_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
