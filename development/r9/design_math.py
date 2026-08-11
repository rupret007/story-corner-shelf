"""Fail-closed layout math for the R9 compact-bookend design scaffold."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
BASELINES_PATH = ROOT / "FROZEN_BASELINES.json"


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_constant,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(root: Path) -> tuple[int, int, str]:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and path.name != ".DS_Store"
    )
    aggregate = hashlib.sha256()
    total_bytes = 0
    for path in files:
        payload = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(payload).hexdigest()
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(len(payload)).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        total_bytes += len(payload)
    return len(files), total_bytes, aggregate.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a non-boolean number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _positive(value: Any, name: str) -> float:
    number = _finite_number(value, name)
    if number <= 0.0:
        raise ValueError(f"{name} must be positive")
    return number


def _exact_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _exact_zero(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric zero")
    if float(value) != 0.0:
        raise ValueError(f"{name} must remain zero")


@dataclass(frozen=True)
class SupportStation:
    run_id: str
    index: int
    source_r8_index: int
    center_mm: float
    role: str
    visible: bool
    cable_rail_allowed: bool


@dataclass(frozen=True)
class RunLayout:
    run_id: str
    coordinate_scope: str
    coordinate_datum: str
    positive_direction: str
    length_mm: float
    pitch_mm: float
    stations: tuple[SupportStation, ...]


@dataclass(frozen=True)
class RunFieldFit:
    run_id: str
    clear_length_lower_mm: float
    clear_length_upper_mm: float
    scaffold_length_mm: float
    minimum_unallocated_clear_length_mm: float


@dataclass(frozen=True)
class ClearanceMetrics:
    shelf_thickness_in: float
    open_clearance_between_shelves_in: float
    upper_shelf_to_ceiling_in: float
    outlet_to_lower_wall_strap_bottom_in: float
    lower_shelf_to_upper_feature_bottom_in: float
    lower_shelf_to_upper_compact_arch_bottom_in: float


@dataclass(frozen=True)
class R9Layout:
    runs: tuple[RunLayout, ...]
    field_fits: tuple[RunFieldFit, ...]
    levels: int
    structural_stations_per_level: int
    visible_supports_per_level: int
    outer_feature_columns_per_level: int
    ordinary_compact_supports_per_level: int
    hidden_corner_halves_per_level: int
    visible_inside_corner_columns_per_level: int
    cable_rails_per_level: int
    cable_sockets_per_level: int
    clearances: ClearanceMetrics


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("unsupported R9 schema_version")

    project = config["project"]
    if project["revision"] != "R9-COMPACT-BOOKEND-SCAFFOLD-1":
        raise ValueError("unexpected R9 revision")
    for field in (
        "qualification_only",
        "installed_release_allowed",
        "physical_qualification_complete",
        "tested_load_rating_exists",
        "production_ready",
        "load_rating_allowed",
        "wall_bores_emitted",
        "full_shelf_set_emitted",
        "embedded_gcode_allowed",
    ):
        expected = field == "qualification_only"
        if type(project[field]) is not bool or project[field] is not expected:
            raise ValueError(f"project.{field} violates fail-closed state")
    _exact_zero(project["rated_load_kg"], "project.rated_load_kg")
    _exact_zero(project["rated_load_lb"], "project.rated_load_lb")

    material = config["material"]
    if material["printed_material"] != "PETG only":
        raise ValueError("R9 printed material must remain PETG only")
    if material["primary_part_material"] != "PETG":
        raise ValueError("R9 primary material must remain PETG")
    for field in (
        "pla_allowed_in_primary_or_load_path_parts",
        "structural_credit_from_accessories_allowed",
        "printed_wall_anchors_allowed",
        "hollow_wall_anchors_allowed_in_primary_load_path",
        "printed_fastener_or_anchor_substitution_allowed",
    ):
        if material[field] is not False:
            raise ValueError(f"material.{field} must remain false")
    if material.get("required_wall_fastener_material") != (
        "metal structural screws and compatible washers"
    ):
        raise ValueError("wall fasteners must remain structural metal screws")

    printer = config["printer"]
    exact_printer_values = {
        "manufacturer": "Bambu Lab",
        "model": "A1 mini",
        "machine_preset": "Bambu Lab A1 mini 0.4 nozzle",
        "plate_type": "Textured PEI Plate",
        "process_preset": "0.20mm Strength @BBL A1M",
        "printable_volume_mm": [180.0, 180.0, 180.0],
        "filament_manufacturer": "SUNLU",
        "filament_product": "PETG",
        "filament_color": "black",
        "filament_asin": "B0D1KC72YP",
        "filament_preset": "SUNLU PETG @BBL A1M 0.4 nozzle",
        "nozzle_mm": 0.4,
        "layer_height_mm": 0.2,
        "wall_loops": 6,
        "top_shell_layers": 5,
        "bottom_shell_layers": 3,
        "infill_percent": 25,
        "infill_pattern": "grid",
        "first_layer_nozzle_temperature_c": 250.0,
        "other_layer_nozzle_temperature_c": 245.0,
        "textured_pei_bed_temperature_c": 60.0,
        "flow_ratio": 0.94,
        "maximum_volumetric_speed_mm3_s": 9.0,
        "fan_min_percent": 10,
        "fan_max_percent": 30,
        "overhang_fan_percent": 90,
        "drying_temperature_c": 50.0,
        "drying_duration_range_h": [6.0, 8.0],
        "brim_mm": 5.0,
        "brim_object_gap_mm": 0.1,
        "minimum_brim_to_brim_gap_mm": 2.0,
        "edge_reserve_each_side_mm": 2.0,
    }
    for field, expected in exact_printer_values.items():
        if printer.get(field) != expected:
            raise ValueError(f"printer.{field} drifted from R9 PETG contract")
    if printer["received_spool_and_dryer_lower_limit_controls"] is not True:
        raise ValueError("received spool and dryer limit must control drying")
    if printer["filament_lot_record_required"] is not True:
        raise ValueError("filament lot record must remain required")
    if printer["drying_record_required"] is not True:
        raise ValueError("drying record must remain required")

    shelf = config["shelf"]
    if _exact_int(shelf["selected_level_count"], "shelf levels", minimum=1) != 2:
        raise ValueError("R9 is frozen to two shelf levels")
    elevations = shelf["shelf_top_elevations_in"]
    if elevations != [68.0, 84.0]:
        raise ValueError("R9 shelf-top elevations must remain 68/84 inches")
    if _positive(shelf["depth_mm"], "shelf depth") != 152.4:
        raise ValueError("shelf depth must remain 152.4 mm")
    if _positive(shelf["cassette_total_height_mm"], "cassette height") != 30.0:
        raise ValueError("cassette height must remain 30.0 mm")
    if shelf.get("between_module_seam_mm") != 0.35:
        raise ValueError("cassette seam must remain 0.35 mm")
    if shelf.get("selected_cassette_candidate") != (
        "front_first_open_back_u_box_3_web"
    ):
        raise ValueError("selected cassette candidate drifted")
    if shelf.get("selected_cassette_physical_qualification_complete") is not False:
        raise ValueError("cassette physical qualification must remain incomplete")

    field = config["field_reference"]
    exact_field_values = {
        "ceiling_height_in": 96.0,
        "outlet_faceplate_top_elevation_in": 53.5,
        "lower_shelf_top_elevation_in": 68.0,
        "upper_shelf_top_elevation_in": 84.0,
        "through_wall_clear_length_in": 61.25,
        "return_wall_clear_length_in": 36.75,
        "through_wall_clear_length_at_lower_shelf_in": 61.25,
        "through_wall_clear_length_at_upper_shelf_in": 61.25,
        "return_wall_clear_length_at_lower_shelf_in": 36.75,
        "return_wall_clear_length_at_upper_shelf_in": 36.75,
    }
    for name, expected in exact_field_values.items():
        observed = _finite_number(field.get(name), f"field_reference.{name}")
        if observed != expected:
            raise ValueError(f"field_reference.{name} drifted from the scaffold")
    if field.get("outlet_measurement_is_approximate") is not True:
        raise ValueError("outlet measurement must remain marked approximate")
    exact_measurement_provenance = {
        "through_wall_length_basis": (
            "field-reported clear length at both 68 in and 84 in shelf-top "
            "elevations"
        ),
        "return_wall_length_basis": (
            "photo-derived conservative working clear length at both 68 in and "
            "84 in shelf-top elevations"
        ),
    }
    for name, expected in exact_measurement_provenance.items():
        if field.get(name) != expected:
            raise ValueError(f"field_reference.{name} provenance drifted")
    if field.get("return_wall_length_is_conservative_working_value") is not True:
        raise ValueError("return wall length must remain marked conservative")
    if field.get("wall_length_measurements_authorize_installed_cad") is not False:
        raise ValueError("wall lengths alone may not authorize installed CAD")
    for run_id in ("through", "return"):
        accepted = field[f"{run_id}_wall_clear_length_in"]
        lower = field[f"{run_id}_wall_clear_length_at_lower_shelf_in"]
        upper = field[f"{run_id}_wall_clear_length_at_upper_shelf_in"]
        if accepted != min(lower, upper):
            raise ValueError(
                f"{run_id} accepted clear length must be the shorter level value"
            )
    for unresolved in (
        "outlet_center_from_through_datum_in",
        "inside_corner_angle_deg",
        "stud_or_blocking_locations_in",
        "wall_substrate_thickness_in",
    ):
        if field.get(unresolved) is not None:
            raise ValueError(f"field_reference.{unresolved} must remain unresolved")

    topology = config["support_topology"]
    expected_counts = {
        "structural_station_count_per_level": 8,
        "visible_support_count_per_level": 6,
        "outer_feature_columns_per_level": 2,
        "ordinary_compact_supports_per_level": 4,
        "hidden_corner_halves_per_level": 2,
        "visible_inside_corner_columns_per_level": 0,
    }
    for field, expected in expected_counts.items():
        if _exact_int(topology[field], field) != expected:
            raise ValueError(f"support_topology.{field} must equal {expected}")
    exact_topology_dimensions = {
        "shelf_projection_mm": 152.4,
        "support_body_thickness_across_run_mm": 32.0,
        "wall_hugging_strap_total_drop_mm": 160.0,
        "wall_hugging_strap_projection_mm": 16.0,
        "outer_feature_visible_drop_mm": 120.65,
        "compact_arch_visible_drop_mm": 76.2,
    }
    for field, expected in exact_topology_dimensions.items():
        if _finite_number(topology.get(field), f"support_topology.{field}") != expected:
            raise ValueError(f"support_topology.{field} drifted")
    strap = _positive(
        topology["wall_hugging_strap_total_drop_mm"], "wall strap drop"
    )
    feature = _positive(
        topology["outer_feature_visible_drop_mm"], "feature drop"
    )
    compact = _positive(
        topology["compact_arch_visible_drop_mm"], "compact drop"
    )
    if not strap > feature > compact:
        raise ValueError("support drops must satisfy strap > feature > compact")
    if topology["continuous_blocking_or_verified_equivalent_confirmed"] is not False:
        raise ValueError("framing confirmation must remain false")
    if topology.get("continuous_blocking_or_verified_equivalent_required") is not True:
        raise ValueError("continuous blocking or verified equivalent remains required")
    if _exact_int(
        topology.get("minimum_metal_structural_screws_per_station"),
        "metal screws per station",
        minimum=1,
    ) != 3:
        raise ValueError("R9 remains frozen to three metal screws per station")
    if topology["structural_capacity_credit_allowed"] is not False:
        raise ValueError("structural capacity credit must remain false")

    bridging = config["span_bridging_system"]
    for field in (
        "rear_ledger_required",
        "rear_ledger_joint_coupon_required",
        "front_beam_or_fascia_splice_required_at_unsupported_cassette_seams",
        "front_beam_splice_coupon_required",
        "support_every_second_r8_station_only",
    ):
        if bridging[field] is not True:
            raise ValueError(f"span_bridging_system.{field} must remain true")
    for field in (
        "ledger_or_splice_structural_capacity_credit_allowed",
        "physical_qualification_complete",
    ):
        if bridging[field] is not False:
            raise ValueError(f"span_bridging_system.{field} must remain false")
    if _positive(
        bridging["rear_ledger_segment_max_length_mm"],
        "rear ledger segment maximum",
    ) != 165.0:
        raise ValueError("rear ledger segment maximum must remain 165 mm")
    if bridging.get("rear_ledger_joint_tongue_length_mm") != 12.0:
        raise ValueError("rear ledger tongue must remain 12 mm")
    if bridging.get("rear_ledger_complete_part_max_build_height_mm") != 177.0:
        raise ValueError("rear ledger complete-part build height must remain 177 mm")
    if bridging.get("rear_ledger_saved_orientation") != (
        "member end on plate; member length builds in Z"
    ):
        raise ValueError("rear ledger saved orientation drifted")
    complete_height = (
        bridging["rear_ledger_segment_max_length_mm"]
        + bridging["rear_ledger_joint_tongue_length_mm"]
    )
    if complete_height != bridging["rear_ledger_complete_part_max_build_height_mm"]:
        raise ValueError("rear ledger body and tongue do not match complete height")
    if complete_height > printer["printable_volume_mm"][2]:
        raise ValueError("complete rear ledger part exceeds A1 mini build height")
    if bridging.get("maximum_nominal_through_support_pitch_mm") != 370.61875:
        raise ValueError("through support pitch contract drifted")
    if bridging.get("maximum_nominal_return_support_pitch_mm") != 359.6375:
        raise ValueError("return support pitch contract drifted")

    accessory = config["accessory_system"]
    if accessory["rails_allowed_on_outer_feature_columns_only"] is not True:
        raise ValueError("rails must remain limited to outer feature columns")
    if accessory["rails_or_pegs_at_inside_corner_allowed"] is not False:
        raise ValueError("corner rails and pegs are prohibited")
    if accessory["rails_or_pegs_on_compact_supports_allowed"] is not False:
        raise ValueError("compact supports must remain smooth")
    if _exact_int(accessory["rails_per_level"], "rails per level") != 2:
        raise ValueError("R9 requires two cable rails per level")
    if _exact_int(accessory["sockets_per_rail"], "sockets per rail") != 2:
        raise ValueError("R9 requires two sockets per outer rail")
    if _exact_int(accessory["sockets_per_level"], "sockets per level") != 4:
        raise ValueError("R9 requires four sockets per level")
    if accessory.get("service_direction") != (
        "inward toward shelf field and away from door openings"
    ):
        raise ValueError("outer cable service direction drifted")
    _exact_zero(accessory["rated_load_kg"], "accessory rated_load_kg")
    _exact_zero(accessory["rated_load_lb"], "accessory rated_load_lb")

    corner = config["corner_system"]
    if corner["visible_column_pair_allowed"] is not False:
        raise ValueError("visible inside-corner columns are prohibited")
    if corner["corner_load_path_authored"] is not False:
        raise ValueError("corner load path must remain unauthored")
    if corner["corner_physical_qualification_complete"] is not False:
        raise ValueError("corner qualification must remain incomplete")
    for field_name in (
        "independent_hidden_half_per_wall",
        "under_shelf_shear_key_candidate",
        "single_cosmetic_cover_candidate",
    ):
        if corner.get(field_name) is not True:
            raise ValueError(f"corner_system.{field_name} must remain true")

    if accessory.get("structural_or_shelf_load_credit") is not False:
        raise ValueError("cable accessories must receive no structural credit")

    qualification = config["qualification"]
    for field_name in (
        "compact_support_vs_r8_control_required",
        "one_bay_compact_support_ledger_fixture_required",
        "two_wall_hidden_corner_fixture_required",
        "handed_outer_feature_column_service_test_required",
        "framed_wall_hardware_test_required",
        "proof_creep_and_destructive_tests_required",
    ):
        if qualification.get(field_name) is not True:
            raise ValueError(f"qualification.{field_name} must remain true")
    if qualification.get("target_contents_load_kg") is not None:
        raise ValueError("target contents load must remain unresolved")
    if qualification.get("test_report") is not None:
        raise ValueError("qualification test report must remain unresolved")

    visual = config["visual_reference"]
    if visual.get("visual_intent_only") is not True:
        raise ValueError("artist rendering must remain visual intent only")

    unresolved = config.get("unresolved_inputs")
    expected_unresolved_keys = {
        "field": {
            "inside_corner_angle_lower_level_deg",
            "inside_corner_angle_upper_level_deg",
            "wall_bow_profile_lower_level_mm",
            "wall_bow_profile_upper_level_mm",
            "outlet_center_from_through_datum_mm",
            "outlet_faceplate_envelope_mm",
            "door_trim_and_service_envelope_mm",
            "ceiling_and_faceplate_elevations_verified",
        },
        "framing": {
            "stud_or_blocking_map_lower_level_mm",
            "stud_or_blocking_map_upper_level_mm",
            "continuous_blocking_or_verified_equivalent_record",
            "wall_substrate_material",
            "wall_substrate_thickness_mm",
            "framing_scan_method_and_reviewer",
        },
        "hardware": {
            "structural_screw_product_and_material",
            "structural_screw_body_diameter_mm",
            "structural_screw_head_diameter_mm",
            "structural_screw_head_height_mm",
            "structural_screw_length_mm",
            "washer_inner_diameter_mm",
            "washer_outer_diameter_mm",
            "washer_thickness_mm",
            "pilot_diameter_mm",
            "verified_embedment_mm",
            "driver_envelope_mm",
            "approved_fastener_schedule",
        },
        "load_and_physical_tests": {
            "target_contents_and_load_kg",
            "distributed_and_point_load_cases",
            "proof_test_record",
            "creep_test_record",
            "recovery_test_record",
            "destructive_test_record",
            "final_reviewer_and_release_record",
        },
    }
    if not isinstance(unresolved, dict) or set(unresolved) != set(expected_unresolved_keys):
        raise ValueError("unresolved-input groups drifted")
    for group, keys in expected_unresolved_keys.items():
        values = unresolved.get(group)
        if not isinstance(values, dict) or set(values) != keys:
            raise ValueError(f"unresolved-input schema drifted: {group}")
        if any(value is not None for value in values.values()):
            raise ValueError(f"unresolved inputs must remain null: {group}")


def _run_layout(run: dict[str, Any]) -> RunLayout:
    run_id = run["id"]
    if run_id not in ("through", "return"):
        raise ValueError(f"unknown run id: {run_id}")
    expected_coordinates = {
        "through": (
            "run-local qualification scaffold; not an R8 global or field drilling datum",
            "far-left outer wall end",
            "toward the inside corner",
        ),
        "return": (
            "run-local qualification scaffold; not an R8 global or field drilling datum",
            "inside corner",
            "toward the far-right outer wall end",
        ),
    }
    observed_coordinates = (
        run.get("coordinate_scope"),
        run.get("coordinate_datum"),
        run.get("positive_direction"),
    )
    if observed_coordinates != expected_coordinates[run_id]:
        raise ValueError(f"{run_id} run-local coordinate contract drifted")
    length = _positive(run["nominal_length_mm"], f"{run_id} length")
    inset = _positive(run["terminal_center_inset_mm"], f"{run_id} inset")
    count = _exact_int(run["support_count"], f"{run_id} support count", minimum=2)
    source_indices = run["source_r8_station_indices"]
    if (
        len(source_indices) != count
        or any(type(value) is not int for value in source_indices)
        or source_indices != list(range(0, source_indices[-1] + 1, 2))
    ):
        raise ValueError(f"{run_id} must retain every second R8 support station")
    outer = _exact_int(run["outer_feature_index"], f"{run_id} outer index")
    hidden = _exact_int(run["hidden_corner_index"], f"{run_id} corner index")
    compact_values = run["compact_support_indices"]
    if any(type(value) is not int for value in compact_values):
        raise ValueError(f"{run_id} compact indices must be integers")
    compact = set(compact_values)
    if len(compact) != len(compact_values):
        raise ValueError(f"{run_id} compact indices must be unique")
    roles = {outer: "outer_feature", hidden: "hidden_corner"}
    if outer == hidden:
        raise ValueError(f"{run_id} outer and corner indices overlap")
    for index in compact:
        if index in roles:
            raise ValueError(f"{run_id} support roles overlap at {index}")
        roles[index] = "compact"
    if set(roles) != set(range(count)):
        raise ValueError(f"{run_id} roles must partition every support index")
    pitch = (length - 2.0 * inset) / (count - 1)
    if pitch <= 0.0:
        raise ValueError(f"{run_id} support pitch must be positive")
    stations = tuple(
        SupportStation(
            run_id=run_id,
            index=index,
            source_r8_index=source_indices[index],
            center_mm=inset + pitch * index,
            role=roles[index],
            visible=roles[index] != "hidden_corner",
            cable_rail_allowed=roles[index] == "outer_feature",
        )
        for index in range(count)
    )
    return RunLayout(
        run_id=run_id,
        coordinate_scope=observed_coordinates[0],
        coordinate_datum=observed_coordinates[1],
        positive_direction=observed_coordinates[2],
        length_mm=length,
        pitch_mm=pitch,
        stations=stations,
    )


def calculate_layout(config: dict[str, Any] | None = None) -> R9Layout:
    cfg = load_config() if config is None else config
    validate_config(cfg)
    runs = tuple(_run_layout(run) for run in cfg["runs"])
    if tuple(run.run_id for run in runs) != ("through", "return"):
        raise ValueError("R9 requires through then return run order")
    bridging = cfg["span_bridging_system"]
    if not math.isclose(
        runs[0].pitch_mm,
        bridging["maximum_nominal_through_support_pitch_mm"],
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise ValueError("through support pitch contradicts bridging contract")
    if not math.isclose(
        runs[1].pitch_mm,
        bridging["maximum_nominal_return_support_pitch_mm"],
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise ValueError("return support pitch contradicts bridging contract")

    field = cfg["field_reference"]
    field_fit_records: list[RunFieldFit] = []
    for run in runs:
        lower_mm = round(
            field[f"{run.run_id}_wall_clear_length_at_lower_shelf_in"] * 25.4,
            6,
        )
        upper_mm = round(
            field[f"{run.run_id}_wall_clear_length_at_upper_shelf_in"] * 25.4,
            6,
        )
        field_fit_records.append(
            RunFieldFit(
                run_id=run.run_id,
                clear_length_lower_mm=lower_mm,
                clear_length_upper_mm=upper_mm,
                scaffold_length_mm=run.length_mm,
                minimum_unallocated_clear_length_mm=round(
                    min(lower_mm, upper_mm) - run.length_mm,
                    6,
                ),
            )
        )
    field_fits = tuple(field_fit_records)
    for fit in field_fits:
        if fit.minimum_unallocated_clear_length_mm <= 0.0:
            raise ValueError(
                f"{fit.run_id} scaffold does not fit the accepted field clear length"
            )
    stations = tuple(station for run in runs for station in run.stations)
    role_counts = {
        role: sum(station.role == role for station in stations)
        for role in ("outer_feature", "compact", "hidden_corner")
    }
    topology = cfg["support_topology"]
    expected = (
        topology["outer_feature_columns_per_level"],
        topology["ordinary_compact_supports_per_level"],
        topology["hidden_corner_halves_per_level"],
    )
    actual = (
        role_counts["outer_feature"],
        role_counts["compact"],
        role_counts["hidden_corner"],
    )
    if actual != expected:
        raise ValueError(f"derived support roles {actual} do not match {expected}")
    if sum(actual) != topology["structural_station_count_per_level"]:
        raise ValueError("derived support station total is inconsistent")
    visible = sum(station.visible for station in stations)
    if visible != topology["visible_support_count_per_level"]:
        raise ValueError("derived visible support total is inconsistent")
    rails = sum(station.cable_rail_allowed for station in stations)
    accessory = cfg["accessory_system"]
    if rails != accessory["rails_per_level"]:
        raise ValueError("derived rail total is inconsistent")

    shelf = cfg["shelf"]
    cassette_in = shelf["cassette_total_height_mm"] / 25.4
    lower, upper = shelf["shelf_top_elevations_in"]
    strap_drop = (shelf["cassette_total_height_mm"] + topology[
        "wall_hugging_strap_total_drop_mm"
    ]) / 25.4
    feature_drop = (shelf["cassette_total_height_mm"] + topology[
        "outer_feature_visible_drop_mm"
    ]) / 25.4
    compact_drop = (shelf["cassette_total_height_mm"] + topology[
        "compact_arch_visible_drop_mm"
    ]) / 25.4
    clearances = ClearanceMetrics(
        shelf_thickness_in=cassette_in,
        open_clearance_between_shelves_in=upper - cassette_in - lower,
        upper_shelf_to_ceiling_in=field["ceiling_height_in"] - upper,
        outlet_to_lower_wall_strap_bottom_in=(
            lower - strap_drop - field["outlet_faceplate_top_elevation_in"]
        ),
        lower_shelf_to_upper_feature_bottom_in=upper - feature_drop - lower,
        lower_shelf_to_upper_compact_arch_bottom_in=upper - compact_drop - lower,
    )
    if min(clearances.__dict__.values()) <= 0.0:
        raise ValueError("all R9 vertical clearances must be positive")

    levels = shelf["selected_level_count"]
    return R9Layout(
        runs=runs,
        field_fits=field_fits,
        levels=levels,
        structural_stations_per_level=len(stations),
        visible_supports_per_level=visible,
        outer_feature_columns_per_level=role_counts["outer_feature"],
        ordinary_compact_supports_per_level=role_counts["compact"],
        hidden_corner_halves_per_level=role_counts["hidden_corner"],
        visible_inside_corner_columns_per_level=(
            topology["visible_inside_corner_columns_per_level"]
        ),
        cable_rails_per_level=rails,
        cable_sockets_per_level=(
            rails * accessory["sockets_per_rail"]
        ),
        clearances=clearances,
    )


def resolve_relative(path_text: str) -> Path:
    return (ROOT / path_text).resolve()


def validate_bound_files(config: dict[str, Any] | None = None) -> None:
    cfg = load_config() if config is None else config
    visual = cfg["visual_reference"]
    visual_path = resolve_relative(visual["path"])
    if sha256_file(visual_path) != visual["sha256"]:
        raise ValueError("R9 visual reference hash mismatch")
    if png_dimensions(visual_path) != (visual["width_px"], visual["height_px"]):
        raise ValueError("R9 visual reference dimensions mismatch")
    for name, record in cfg["predecessor_evidence"].items():
        path = resolve_relative(record["path"])
        if sha256_file(path) != record["sha256"]:
            raise ValueError(f"predecessor evidence hash mismatch: {name}")


def validate_frozen_baselines() -> None:
    baselines = load_config(BASELINES_PATH)
    if baselines.get("schema_version") != 1:
        raise ValueError("unsupported frozen-baseline schema")
    for revision, record in baselines["baselines"].items():
        root = resolve_relative(record["path"])
        observed = tree_digest(root)
        expected = (
            record["file_count"],
            record["byte_count"],
            record["tree_sha256"],
        )
        if observed != expected:
            raise ValueError(f"frozen predecessor tree changed: {revision}")
        if sha256_file(root / "config.json") != record["config_sha256"]:
            raise ValueError(f"frozen predecessor config changed: {revision}")


if __name__ == "__main__":
    layout = calculate_layout()
    validate_bound_files()
    validate_frozen_baselines()
    print(
        json.dumps(
            {
                "levels": layout.levels,
                "structural_stations_per_level": layout.structural_stations_per_level,
                "visible_supports_per_level": layout.visible_supports_per_level,
                "outer_feature_columns_per_level": (
                    layout.outer_feature_columns_per_level
                ),
                "ordinary_compact_supports_per_level": (
                    layout.ordinary_compact_supports_per_level
                ),
                "hidden_corner_halves_per_level": layout.hidden_corner_halves_per_level,
                "cable_sockets_per_level": layout.cable_sockets_per_level,
                "field_fit_mm": {
                    fit.run_id: {
                        "clear_length_lower": fit.clear_length_lower_mm,
                        "clear_length_upper": fit.clear_length_upper_mm,
                        "scaffold_length": fit.scaffold_length_mm,
                        "minimum_unallocated_clear_length": (
                            fit.minimum_unallocated_clear_length_mm
                        ),
                    }
                    for fit in layout.field_fits
                },
                "clearances_in": layout.clearances.__dict__,
            },
            indent=2,
            sort_keys=True,
        )
    )
