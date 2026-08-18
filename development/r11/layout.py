#!/usr/bin/env python3
"""Fail-closed R11 wall layout and print-envelope contract.

The module performs exact topology arithmetic for the integrated Lincoln-log
candidate.  It does not create geometry, a drilling schedule, or a load
rating.  R11 v1 is deliberately qualification-only: configuration values may
add evidence and blockers, but cannot authorize printing, drilling,
installation, production, or load use.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


CONFIG_PATH = Path(__file__).with_name("config.json")
BASELINE_PATH = Path(__file__).with_name("FROZEN_BASELINES.json")
SCHEMA_VERSION = "r11_integrated_lincoln_layout_v1"
EPSILON_MM = Decimal("0.000001")
MM_PER_INCH = Decimal("25.4")

ROOT_KEYS = {
    "schema_version",
    "project",
    "wall_input",
    "field_measurement_input",
    "environment_input",
    "joinery_candidate",
    "piece_contract",
    "printer_input",
    "keepout_input",
    "blocking_input",
    "hardware_candidate",
    "cable_system",
}

SECTION_KEYS = {
    "project": {
        "name", "scope", "qualification_only", "print_authorized",
        "production_ready", "wall_installation_authorized",
        "drilling_coordinates_released", "test_load_authorized",
        "geometry_release_complete",
        "independent_engineering_review_approved",
        "physical_load_qualification_passed", "tested_load_rating_exists",
        "rated_load_kg", "rated_load_lb",
    },
    "wall_input": {
        "clear_length_mm", "support_run_width_mm", "maximum_bay_pitch_mm",
        "supports_evenly_spaced", "support_end_faces_flush_with_wall_ends",
    },
    "field_measurement_input": {
        "measurement_reference", "height_samples_in",
        "clear_length_samples_mm", "measurement_uncertainty_mm",
        "wall_plane_bow_mm", "endpoint_trim_clearance_mm",
        "measurement_instrument", "instrument_resolution_mm",
        "measurement_date", "observer",
    },
    "environment_input": {
        "maximum_expected_service_temperature_c",
        "minimum_expected_service_temperature_c",
        "minimum_expected_relative_humidity_percent",
        "maximum_expected_relative_humidity_percent",
        "measurement_instrument", "measurement_start_date",
        "measurement_end_date",
        "direct_sun_exposure_assessed", "nearby_heat_sources_assessed",
        "service_environment_record_complete",
    },
    "joinery_candidate": {
        "architecture_id", "shelf_depth_mm", "shelf_total_thickness_mm",
        "support_wall_strap_drop_mm", "integrated_reciprocal_overlap_mm",
        "joint_clearance_mm", "minimum_bearing_per_support_side_mm",
        "terminal_extension_formula",
        "overlap_is_initial_candidate_only", "overlap_physical_gate_passed",
        "integral_bay_local_support_capture_required",
        "integral_bay_local_support_capture_validated",
        "positive_bay_wedge_required", "gravity_bearing_surfaces_validated",
        "structural_credit_from_friction_snap_glue_or_wedge",
    },
    "piece_contract": {
        "supports_per_station", "integrated_half_decks_per_bay",
        "positive_bay_wedges_per_bay", "first_wall_cable_modules_supplied",
        "first_wall_cable_modules_simultaneously_installed",
        "candidate_wedges_per_plate", "candidate_cable_modules_per_plate",
        "wedge_plate_nesting_verified", "cable_plate_nesting_verified",
        "individual_supports_and_half_decks_are_not_copacked_for_start_estimate",
    },
    "printer_input": {
        "printer", "build_volume_mm", "brim_width_mm", "brim_object_gap_mm",
        "edge_reserve_mm", "required_xy_allowance_formula",
        "saved_orientation_required", "actual_saved_mesh_envelopes_verified",
        "all_auxiliary_plate_envelopes_verified",
    },
    "keepout_input": {
        "measurement_complete", "explicit_no_keepouts_confirmed",
        "required_classes", "zones",
    },
    "blocking_input": {
        "survey_complete", "continuous_blocking_confirmed",
        "utilities_scan_complete", "exact_screw_axes_clear_of_utilities",
        "wall_substrate_material", "wall_substrate_thickness_mm",
        "blocking_material_species_grade", "blocking_thickness_mm", "segments",
        "blocking_vertical_start_mm", "blocking_vertical_end_mm",
        "shelf_top_elevation_mm", "screw_axis_elevations_mm",
        "exact_fastener_schedule_approved",
    },
    "hardware_candidate": {
        "wall_fasteners_per_support", "washers_per_fastener",
        "fastener_product", "washer_product",
        "hardware_is_a_candidate_not_a_drilling_schedule",
        "hollow_wall_anchor_primary_load_path_allowed",
    },
    "cable_system": {
        "receiver_support_indices", "receiver_sockets_per_support",
        "flush_blanks_supplied", "comb_hooks_supplied",
        "simultaneously_installed_modules", "module_clearance_per_face_mm",
        "service_lift_drop_mm", "structural_credit_allowed",
        "intermediate_support_receivers_allowed",
        "corner_support_receivers_allowed",
    },
}

REQUIRED_KEEPOUT_CLASSES = (
    "outlet_plug_and_cord",
    "door_and_trim",
    "inside_corner",
    "wall_bow",
    "human_access",
)
FASTENER_PRODUCT = (
    "GRK RSS Rugged Structural Screw, Climatek, 1/4 in x 3-1/2 in, "
    "T25, part 90306"
)
WASHER_PRODUCT = "L.H. Dottie FW14 1/4 in USS flat washer"
R10_SOURCE_COMMIT = "9a36df75ac1979193fbd56637c0dfa0aff1ce285"
R10_GIT_TREE_SHA1 = "c4989cebcd990011f6255d00fea15060d00c6c85"


class LayoutContractError(ValueError):
    """Raised when an input cannot be interpreted without guessing."""


class InstallationRefused(LayoutContractError):
    """Raised when installation is requested before every release gate passes."""

    def __init__(self, blockers: Sequence[str], plan: Mapping[str, Any]) -> None:
        self.blockers = tuple(blockers)
        self.plan = dict(plan)
        super().__init__(
            "R11 installation refused: " + "; ".join(self.blockers)
        )


@dataclass(frozen=True)
class SupportStation:
    index: int
    center_mm: float
    footprint_start_mm: float
    footprint_end_mm: float
    role: str


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load the checked-in R11 candidate contract."""

    source = CONFIG_PATH if path is None else path
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise LayoutContractError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_nonfinite(value: str) -> None:
        raise LayoutContractError(f"non-finite JSON value: {value}")

    try:
        loaded = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except json.JSONDecodeError as error:
        raise LayoutContractError(f"invalid config JSON: {error}") from None
    if not isinstance(loaded, dict):
        raise LayoutContractError("config root must be an object")
    return loaded


def compute_tree_evidence(root: Path) -> dict[str, Any]:
    """Compute the frozen-tree record used to prove R10 byte immutability."""

    if not root.is_dir():
        raise LayoutContractError(f"frozen tree is missing: {root}")
    records: list[bytes] = []
    file_count = 0
    byte_count = 0
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or path.suffix == ".pyc"
            or path.name == ".DS_Store"
        ):
            continue
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        records.append(
            f"{relative}\0{len(content)}\0{digest}\n".encode("utf-8")
        )
        file_count += 1
        byte_count += len(content)
    config_path = root / "config.json"
    if not config_path.is_file():
        raise LayoutContractError(f"frozen tree has no config.json: {root}")
    return {
        "file_count": file_count,
        "byte_count": byte_count,
        "tree_sha256": hashlib.sha256(b"".join(records)).hexdigest(),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
    }


def verify_frozen_r10(r10_root: Path | None = None) -> dict[str, Any]:
    """Raise on any non-cache byte drift in the frozen R10 predecessor."""

    baseline_document = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if baseline_document.get("schema_version") != 1:
        raise LayoutContractError("frozen baseline schema drifted")
    if baseline_document.get("hash_algorithm") != "sha256":
        raise LayoutContractError("frozen baseline hash algorithm drifted")
    baseline = baseline_document["baselines"]["r10"]
    fixed_identity = {
        "path": "../r10",
        "source_commit": R10_SOURCE_COMMIT,
        "git_tree_sha1": R10_GIT_TREE_SHA1,
    }
    actual_identity = {key: baseline.get(key) for key in fixed_identity}
    if actual_identity != fixed_identity:
        raise LayoutContractError(
            "frozen R10 identity record drifted: "
            + json.dumps(
                {"expected": fixed_identity, "actual": actual_identity},
                sort_keys=True,
            )
        )
    root = Path(__file__).resolve().parent.parent / "r10" if r10_root is None else r10_root
    actual = compute_tree_evidence(root)
    expected = {
        key: baseline[key]
        for key in ("file_count", "byte_count", "tree_sha256", "config_sha256")
    }
    if actual != expected:
        raise LayoutContractError(
            "frozen R10 tree drifted: "
            + json.dumps({"expected": expected, "actual": actual}, sort_keys=True)
        )
    return {
        "verified": True,
        "path": str(root),
        "source_commit": baseline["source_commit"],
        "git_tree_sha1": baseline["git_tree_sha1"],
        **actual,
    }


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LayoutContractError(f"{name} must be an object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], path: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise LayoutContractError(
            f"{path} keys drifted: missing={missing}, unknown={unknown}"
        )


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LayoutContractError(f"{name} must be an array")
    return value


def _decimal(
    source: Mapping[str, Any],
    key: str,
    path: str,
    *,
    positive: bool = True,
) -> Decimal:
    if key not in source or isinstance(source[key], bool) or not isinstance(
        source[key], (int, float, Decimal)
    ):
        raise LayoutContractError(f"{path}.{key} must be a finite number")
    try:
        value = Decimal(str(source[key]))
    except (InvalidOperation, ValueError):
        raise LayoutContractError(f"{path}.{key} must be a finite number") from None
    if not value.is_finite() or (positive and value <= 0):
        qualifier = "positive and finite" if positive else "finite"
        raise LayoutContractError(f"{path}.{key} must be {qualifier}")
    return value


def _optional_positive_decimal(
    source: Mapping[str, Any], key: str, path: str
) -> Decimal | None:
    if source.get(key) is None:
        return None
    return _decimal(source, key, path)


def _optional_nonnegative_decimal(
    source: Mapping[str, Any], key: str, path: str
) -> Decimal | None:
    if source.get(key) is None:
        return None
    value = _decimal(source, key, path, positive=False)
    if value < 0:
        raise LayoutContractError(f"{path}.{key} must be nonnegative and finite")
    return value


def _optional_finite_decimal(
    source: Mapping[str, Any], key: str, path: str
) -> Decimal | None:
    if source.get(key) is None:
        return None
    return _decimal(source, key, path, positive=False)


def _optional_percentage(
    source: Mapping[str, Any], key: str, path: str
) -> Decimal | None:
    value = _optional_nonnegative_decimal(source, key, path)
    if value is not None and value > 100:
        raise LayoutContractError(f"{path}.{key} must be between 0 and 100")
    return value


def _integer(source: Mapping[str, Any], key: str, path: str, *, minimum: int) -> int:
    if key not in source or isinstance(source[key], bool):
        raise LayoutContractError(f"{path}.{key} must be an integer")
    value = source[key]
    if not isinstance(value, int) or value < minimum:
        raise LayoutContractError(
            f"{path}.{key} must be an integer greater than or equal to {minimum}"
        )
    return value


def _boolean(source: Mapping[str, Any], key: str, path: str) -> bool:
    if key not in source or not isinstance(source[key], bool):
        raise LayoutContractError(f"{path}.{key} must be true or false")
    return bool(source[key])


def _text_or_none(source: Mapping[str, Any], key: str, path: str) -> str | None:
    value = source.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise LayoutContractError(f"{path}.{key} must be null or non-empty text")
    return value.strip()


def _out(value: Decimal) -> float:
    return float(value.quantize(EPSILON_MM))


def _ceil_ratio(numerator: Decimal, denominator: Decimal) -> int:
    return int((numerator / denominator).to_integral_value(rounding=ROUND_CEILING))


def _unique(items: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def validate_config(config: Mapping[str, Any]) -> None:
    """Reject schema or invariant drift before deriving any candidate result."""

    cfg = _mapping(config, "config")
    _require_exact_keys(cfg, ROOT_KEYS, "config")
    if cfg.get("schema_version") != SCHEMA_VERSION:
        raise LayoutContractError(f"schema_version must be {SCHEMA_VERSION}")
    for key in (
        "project",
        "wall_input",
        "field_measurement_input",
        "environment_input",
        "joinery_candidate",
        "piece_contract",
        "printer_input",
        "keepout_input",
        "blocking_input",
        "hardware_candidate",
        "cable_system",
    ):
        section = _mapping(cfg.get(key), key)
        _require_exact_keys(section, SECTION_KEYS[key], key)

    project = _mapping(cfg["project"], "project")
    for key in ("name", "scope"):
        if _text_or_none(project, key, "project") is None:
            raise LayoutContractError(f"project.{key} is required")
    exact_release_values = {
        "qualification_only": True,
        "print_authorized": False,
        "production_ready": False,
        "wall_installation_authorized": False,
        "drilling_coordinates_released": False,
        "test_load_authorized": False,
        "independent_engineering_review_approved": False,
        "physical_load_qualification_passed": False,
        "tested_load_rating_exists": False,
    }
    for key, expected in exact_release_values.items():
        if _boolean(project, key, "project") is not expected:
            raise LayoutContractError(
                f"project.{key} must remain {str(expected).lower()} in R11 v1"
            )
    for key in ("rated_load_kg", "rated_load_lb"):
        if _decimal(project, key, "project", positive=False) != 0:
            raise LayoutContractError(f"project.{key} must remain zero in R11 v1")

    wall = _mapping(cfg["wall_input"], "wall_input")
    if not _boolean(wall, "supports_evenly_spaced", "wall_input"):
        raise LayoutContractError("R11 requires evenly spaced supports")
    if not _boolean(wall, "support_end_faces_flush_with_wall_ends", "wall_input"):
        raise LayoutContractError("R11 requires terminal support faces flush with wall ends")

    field = _mapping(cfg["field_measurement_input"], "field_measurement_input")
    if _text_or_none(field, "measurement_reference", "field_measurement_input") is None:
        raise LayoutContractError("field measurement reference is required")
    heights = _sequence(field["height_samples_in"], "field_measurement_input.height_samples_in")
    lengths = _sequence(
        field["clear_length_samples_mm"],
        "field_measurement_input.clear_length_samples_mm",
    )
    if len(heights) < 2 or len(heights) != len(lengths):
        raise LayoutContractError("field samples require two or more paired heights and lengths")
    parsed_lengths: list[Decimal] = []
    for index, (height, length) in enumerate(zip(heights, lengths)):
        sample = {"height": height, "length": length}
        _decimal(sample, "height", f"field sample {index}")
        parsed_lengths.append(_decimal(sample, "length", f"field sample {index}"))
    if min(parsed_lengths) != _decimal(wall, "clear_length_mm", "wall_input"):
        raise LayoutContractError(
            "wall_input.clear_length_mm must equal the shortest field sample"
        )
    for key in (
        "measurement_uncertainty_mm", "wall_plane_bow_mm",
        "endpoint_trim_clearance_mm",
    ):
        _optional_nonnegative_decimal(field, key, "field_measurement_input")
    _optional_positive_decimal(
        field, "instrument_resolution_mm", "field_measurement_input"
    )
    for key in ("measurement_instrument", "measurement_date", "observer"):
        _text_or_none(field, key, "field_measurement_input")

    environment = _mapping(cfg["environment_input"], "environment_input")
    maximum_temperature = _optional_finite_decimal(
        environment, "maximum_expected_service_temperature_c", "environment_input"
    )
    minimum_temperature = _optional_finite_decimal(
        environment, "minimum_expected_service_temperature_c", "environment_input"
    )
    if (
        maximum_temperature is not None
        and minimum_temperature is not None
        and minimum_temperature > maximum_temperature
    ):
        raise LayoutContractError(
            "environment minimum service temperature cannot exceed maximum"
        )
    minimum_humidity = _optional_percentage(
        environment,
        "minimum_expected_relative_humidity_percent",
        "environment_input",
    )
    maximum_humidity = _optional_percentage(
        environment,
        "maximum_expected_relative_humidity_percent",
        "environment_input",
    )
    if (
        minimum_humidity is not None
        and maximum_humidity is not None
        and minimum_humidity > maximum_humidity
    ):
        raise LayoutContractError(
            "environment minimum relative humidity cannot exceed maximum"
        )
    for key in (
        "measurement_instrument",
        "measurement_start_date",
        "measurement_end_date",
    ):
        _text_or_none(environment, key, "environment_input")
    for key in (
        "direct_sun_exposure_assessed", "nearby_heat_sources_assessed",
        "service_environment_record_complete",
    ):
        _boolean(environment, key, "environment_input")

    joinery = _mapping(cfg["joinery_candidate"], "joinery_candidate")
    if joinery.get("architecture_id") != "r11_integrated_reciprocal_lincoln_v1":
        raise LayoutContractError("R11 joinery architecture identity drifted")
    if joinery.get("terminal_extension_formula") != (
        "(support_run_width_mm - joint_clearance_mm) / 4"
    ):
        raise LayoutContractError("terminal extension formula drifted")
    if not _boolean(
        joinery, "overlap_is_initial_candidate_only", "joinery_candidate"
    ):
        raise LayoutContractError("the 55 mm overlap must remain a candidate")
    if _boolean(
        joinery,
        "structural_credit_from_friction_snap_glue_or_wedge",
        "joinery_candidate",
    ):
        raise LayoutContractError("friction, snap, glue, and wedge cannot receive structural credit")
    for key in (
        "integral_bay_local_support_capture_required", "positive_bay_wedge_required",
    ):
        if not _boolean(joinery, key, "joinery_candidate"):
            raise LayoutContractError(f"joinery_candidate.{key} must remain true")

    printer = _mapping(cfg["printer_input"], "printer_input")
    if _text_or_none(printer, "printer", "printer_input") is None:
        raise LayoutContractError("printer_input.printer is required")
    if printer.get("required_xy_allowance_formula") != (
        "2 * (brim_width_mm + brim_object_gap_mm + edge_reserve_mm)"
    ):
        raise LayoutContractError("print-envelope allowance formula drifted")
    if not _boolean(printer, "saved_orientation_required", "printer_input"):
        raise LayoutContractError("saved print orientation must remain required")

    pieces = _mapping(cfg["piece_contract"], "piece_contract")
    exact_piece_values = {
        "supports_per_station": 1,
        "integrated_half_decks_per_bay": 2,
        "positive_bay_wedges_per_bay": 1,
        "first_wall_cable_modules_supplied": 3,
        "first_wall_cable_modules_simultaneously_installed": 2,
    }
    for key, expected in exact_piece_values.items():
        if _integer(pieces, key, "piece_contract", minimum=0) != expected:
            raise LayoutContractError(f"piece_contract.{key} must remain {expected}")
    if not _boolean(
        pieces,
        "individual_supports_and_half_decks_are_not_copacked_for_start_estimate",
        "piece_contract",
    ):
        raise LayoutContractError("structural article start estimates must remain one per plate")

    hardware = _mapping(cfg["hardware_candidate"], "hardware_candidate")
    if _integer(hardware, "wall_fasteners_per_support", "hardware_candidate", minimum=1) != 3:
        raise LayoutContractError("R11 retains exactly three wall fasteners per support")
    if _integer(hardware, "washers_per_fastener", "hardware_candidate", minimum=1) != 1:
        raise LayoutContractError("R11 retains exactly one washer per wall fastener")
    if hardware.get("fastener_product") != FASTENER_PRODUCT:
        raise LayoutContractError("exact GRK 90306 candidate identity drifted")
    if hardware.get("washer_product") != WASHER_PRODUCT:
        raise LayoutContractError("exact Dottie FW14 candidate identity drifted")
    if not _boolean(
        hardware,
        "hardware_is_a_candidate_not_a_drilling_schedule",
        "hardware_candidate",
    ):
        raise LayoutContractError("hardware must remain candidate-only")
    if _boolean(
        hardware,
        "hollow_wall_anchor_primary_load_path_allowed",
        "hardware_candidate",
    ):
        raise LayoutContractError("hollow-wall anchors cannot be the primary load path")

    keepouts = _mapping(cfg["keepout_input"], "keepout_input")
    required_classes = tuple(
        _sequence(keepouts["required_classes"], "keepout_input.required_classes")
    )
    if required_classes != REQUIRED_KEEPOUT_CLASSES:
        raise LayoutContractError("required keepout classes drifted")
    for index, raw in enumerate(_sequence(keepouts["zones"], "keepout_input.zones")):
        zone = _mapping(raw, f"keepout_input.zones[{index}]")
        _require_exact_keys(
            zone,
            {"name", "start_mm", "end_mm", "clearance_mm", "verified", "applies_to"},
            f"keepout_input.zones[{index}]",
        )

    blocking = _mapping(cfg["blocking_input"], "blocking_input")
    for index, raw in enumerate(_sequence(blocking["segments"], "blocking_input.segments")):
        segment = _mapping(raw, f"blocking_input.segments[{index}]")
        _require_exact_keys(
            segment, {"start_mm", "end_mm", "verified"},
            f"blocking_input.segments[{index}]",
        )

    cable = _mapping(cfg["cable_system"], "cable_system")
    if list(_sequence(cable["receiver_support_indices"], "cable_system.receiver_support_indices")) != [0]:
        raise LayoutContractError("the first wall has a cable receiver only at S0")
    exact_cable_integers = {
        "receiver_sockets_per_support": 2,
        "flush_blanks_supplied": 2,
        "comb_hooks_supplied": 1,
        "simultaneously_installed_modules": 2,
    }
    for key, expected in exact_cable_integers.items():
        if _integer(cable, key, "cable_system", minimum=0) != expected:
            raise LayoutContractError(f"cable_system.{key} must remain {expected}")
    if _decimal(cable, "module_clearance_per_face_mm", "cable_system") != Decimal("0.4"):
        raise LayoutContractError("cable module clearance must remain 0.4 mm per face")
    if _decimal(cable, "service_lift_drop_mm", "cable_system") != Decimal("8.0"):
        raise LayoutContractError("cable service lift/drop must remain 8 mm")
    for key in (
        "structural_credit_allowed", "intermediate_support_receivers_allowed",
        "corner_support_receivers_allowed",
    ):
        if _boolean(cable, key, "cable_system"):
            raise LayoutContractError(f"cable_system.{key} must remain false")


def _support_stations(
    wall_length: Decimal, support_width: Decimal, bay_count: int, pitch: Decimal
) -> tuple[SupportStation, ...]:
    stations: list[SupportStation] = []
    half_width = support_width / 2
    for index in range(bay_count + 1):
        center = half_width + pitch * index
        start = center - half_width
        end = center + half_width
        if start < -EPSILON_MM or end > wall_length + EPSILON_MM:
            raise LayoutContractError("a derived support escaped the measured wall")
        role = (
            "outer_bookend_with_cable_receiver"
            if index == 0
            else "through_side_terminal_corner_placeholder"
            if index == bay_count
            else "compact_arcade"
        )
        stations.append(
            SupportStation(
                index=index,
                center_mm=_out(center),
                footprint_start_mm=_out(start),
                footprint_end_mm=_out(end),
                role=role,
            )
        )
    if Decimal(str(stations[0].footprint_start_mm)) != Decimal("0.000000"):
        raise LayoutContractError("first support face is not flush with the wall datum")
    if Decimal(str(stations[-1].footprint_end_mm)) != wall_length.quantize(EPSILON_MM):
        raise LayoutContractError("last support face is not flush with the wall end")
    return tuple(stations)


def _fit_xy(required: tuple[Decimal, Decimal, Decimal], build: tuple[Decimal, Decimal, Decimal]) -> bool:
    x, y, z = required
    bx, by, bz = build
    return z <= bz + EPSILON_MM and (
        (x <= bx + EPSILON_MM and y <= by + EPSILON_MM)
        or (y <= bx + EPSILON_MM and x <= by + EPSILON_MM)
    )


def _printer_evidence(
    printer: Mapping[str, Any],
    *,
    support_width: Decimal,
    shelf_depth: Decimal,
    shelf_thickness: Decimal,
    support_drop: Decimal,
    regular_length: Decimal,
    terminal_length: Decimal,
) -> tuple[dict[str, Any], list[str]]:
    build_raw = _sequence(printer.get("build_volume_mm"), "printer.build_volume_mm")
    if len(build_raw) != 3:
        raise LayoutContractError("printer.build_volume_mm must contain x, y, and z")
    build_map = {str(index): value for index, value in enumerate(build_raw)}
    build = tuple(
        _decimal(build_map, str(index), "printer.build_volume_mm")
        for index in range(3)
    )
    brim = _decimal(printer, "brim_width_mm", "printer")
    gap = _decimal(printer, "brim_object_gap_mm", "printer", positive=False)
    reserve = _decimal(printer, "edge_reserve_mm", "printer", positive=False)
    if gap < 0 or reserve < 0:
        raise LayoutContractError("printer gap and edge reserve cannot be negative")
    allowance = 2 * (brim + gap + reserve)

    bodies = {
        "support": (shelf_depth, support_drop, support_width),
        "regular_integrated_half_deck": (regular_length, shelf_depth, shelf_thickness),
        "terminal_integrated_half_deck": (terminal_length, shelf_depth, shelf_thickness),
    }
    evidence: dict[str, Any] = {}
    blockers: list[str] = []
    for name, body in bodies.items():
        required = (body[0] + allowance, body[1] + allowance, body[2])
        fits = _fit_xy(required, build) and all(value > 0 for value in body)
        evidence[name] = {
            "candidate_body_envelope_mm": [_out(value) for value in body],
            "required_build_envelope_mm": [_out(value) for value in required],
            "fits_declared_build_volume_with_xy_rotation": fits,
        }
        if not fits:
            blockers.append(f"{name} does not fit the declared printer envelope")

    saved_verified = _boolean(
        printer, "actual_saved_mesh_envelopes_verified", "printer"
    )
    auxiliary_verified = _boolean(
        printer, "all_auxiliary_plate_envelopes_verified", "printer"
    )
    if not saved_verified:
        blockers.append("actual R11 saved-mesh print envelopes are not verified")
    if not auxiliary_verified:
        blockers.append("bay-wedge and cable-module plate envelopes are not verified")
    return (
        {
            "build_volume_mm": [_out(value) for value in build],
            "xy_allowance_each_axis_mm": _out(allowance),
            "xy_allowance_formula": (
                "2 * (brim width + object gap + edge reserve)"
            ),
            "parts": evidence,
            "all_declared_candidate_envelopes_fit": all(
                item["fits_declared_build_volume_with_xy_rotation"]
                for item in evidence.values()
            ),
            "actual_saved_mesh_envelopes_verified": saved_verified,
            "all_auxiliary_plate_envelopes_verified": auxiliary_verified,
            "release_fit_proven": (
                saved_verified
                and auxiliary_verified
                and all(
                    item["fits_declared_build_volume_with_xy_rotation"]
                    for item in evidence.values()
                )
            ),
        },
        blockers,
    )


def _keepout_evidence(
    keepouts: Mapping[str, Any],
    stations: Sequence[SupportStation],
    wall_length: Decimal,
) -> tuple[dict[str, Any], list[str]]:
    complete = _boolean(keepouts, "measurement_complete", "keepouts")
    no_keepouts = _boolean(
        keepouts, "explicit_no_keepouts_confirmed", "keepouts"
    )
    required_classes = _sequence(
        keepouts.get("required_classes"), "keepouts.required_classes"
    )
    if not required_classes or any(
        not isinstance(item, str) or not item.strip() for item in required_classes
    ):
        raise LayoutContractError("keepouts.required_classes must contain labels")
    zones_raw = _sequence(keepouts.get("zones"), "keepouts.zones")
    blockers: list[str] = []
    if not complete:
        blockers.append("keepout survey is incomplete")
    if complete and not zones_raw and not no_keepouts:
        blockers.append("keepout survey has neither zones nor an explicit no-keepout record")
    if zones_raw and no_keepouts:
        raise LayoutContractError("keepouts cannot declare zones and no keepouts simultaneously")

    normalized: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    for index, raw in enumerate(zones_raw):
        zone = _mapping(raw, f"keepouts.zones[{index}]")
        name = _text_or_none(zone, "name", f"keepouts.zones[{index}]")
        if name is None:
            raise LayoutContractError(f"keepouts.zones[{index}].name is required")
        start = _decimal(zone, "start_mm", f"keepouts.zones[{index}]", positive=False)
        end = _decimal(zone, "end_mm", f"keepouts.zones[{index}]", positive=False)
        clearance = _decimal(
            zone, "clearance_mm", f"keepouts.zones[{index}]", positive=False
        )
        if start < 0 or end <= start or end > wall_length or clearance < 0:
            raise LayoutContractError(
                f"keepouts.zones[{index}] must be ordered within the measured wall"
            )
        verified = _boolean(zone, "verified", f"keepouts.zones[{index}]")
        applies_to = _sequence(
            zone.get("applies_to"), f"keepouts.zones[{index}].applies_to"
        )
        if not applies_to or any(item not in {"support", "shelf"} for item in applies_to):
            raise LayoutContractError(
                f"keepouts.zones[{index}].applies_to must use support and/or shelf"
            )
        if not verified:
            blockers.append(f"keepout {name} is not field verified")
        effective_start = start - clearance
        effective_end = end + clearance
        hit_supports = [
            station.index
            for station in stations
            if "support" in applies_to
            and not (
                Decimal(str(station.footprint_end_mm)) < effective_start
                or Decimal(str(station.footprint_start_mm)) > effective_end
            )
        ]
        shelf_collision = "shelf" in applies_to
        if hit_supports or shelf_collision:
            collision = {
                "zone": name,
                "support_indices": hit_supports,
                "continuous_shelf_collision": shelf_collision,
            }
            collisions.append(collision)
            blockers.append(f"keepout {name} collides with the equal-pitch candidate")
        normalized.append(
            {
                "name": name,
                "start_mm": _out(start),
                "end_mm": _out(end),
                "clearance_mm": _out(clearance),
                "verified": verified,
                "applies_to": list(applies_to),
            }
        )
    return (
        {
            "measurement_complete": complete,
            "explicit_no_keepouts_confirmed": no_keepouts,
            "required_classes": list(required_classes),
            "zones": normalized,
            "collisions": collisions,
            "candidate_clear": bool(
                complete
                and not collisions
                and (no_keepouts or all(item["verified"] for item in normalized))
            ),
        },
        blockers,
    )


def _merge_intervals(
    intervals: Sequence[tuple[Decimal, Decimal]],
) -> tuple[tuple[Decimal, Decimal], ...]:
    merged: list[list[Decimal]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + EPSILON_MM:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return tuple((start, end) for start, end in merged)


def _blocking_evidence(
    blocking: Mapping[str, Any],
    stations: Sequence[SupportStation],
    wall_length: Decimal,
    fasteners_per_support: int,
) -> tuple[dict[str, Any], list[str]]:
    survey_complete = _boolean(blocking, "survey_complete", "blocking")
    continuous_confirmed = _boolean(
        blocking, "continuous_blocking_confirmed", "blocking"
    )
    fastener_approved = _boolean(
        blocking, "exact_fastener_schedule_approved", "blocking"
    )
    utilities_complete = _boolean(
        blocking, "utilities_scan_complete", "blocking"
    )
    screw_axes_clear = _boolean(
        blocking, "exact_screw_axes_clear_of_utilities", "blocking"
    )
    substrate = _text_or_none(blocking, "wall_substrate_material", "blocking")
    substrate_thickness = _optional_positive_decimal(
        blocking, "wall_substrate_thickness_mm", "blocking"
    )
    blocking_material = _text_or_none(
        blocking, "blocking_material_species_grade", "blocking"
    )
    blocking_thickness = _optional_positive_decimal(
        blocking, "blocking_thickness_mm", "blocking"
    )
    vertical_start = _optional_positive_decimal(
        blocking, "blocking_vertical_start_mm", "blocking"
    )
    vertical_end = _optional_positive_decimal(
        blocking, "blocking_vertical_end_mm", "blocking"
    )
    shelf_top = _decimal(blocking, "shelf_top_elevation_mm", "blocking")
    screw_axes_raw = _sequence(
        blocking.get("screw_axis_elevations_mm"),
        "blocking.screw_axis_elevations_mm",
    )
    screw_axes: list[Decimal] = []
    for index, value in enumerate(screw_axes_raw):
        screw_axes.append(
            _decimal({"value": value}, "value", f"blocking screw axis {index}")
        )
    segments_raw = _sequence(blocking.get("segments"), "blocking.segments")
    blockers: list[str] = []
    if not survey_complete:
        blockers.append("blocking and substrate survey is incomplete")
    if not continuous_confirmed:
        blockers.append("continuous blocking is not confirmed")
    if substrate is None or substrate_thickness is None:
        blockers.append("wall substrate material and thickness are unresolved")
    if blocking_material is None or blocking_thickness is None:
        blockers.append("blocking material, grade, and thickness are unresolved")
    if not fastener_approved:
        blockers.append("exact fastener schedule is not approved")
    if not utilities_complete:
        blockers.append("utilities scan is incomplete")
    if not screw_axes_clear:
        blockers.append("exact screw axes are not cleared of utilities")
    if vertical_start is None or vertical_end is None:
        blockers.append("blocking vertical extent is unresolved")
    elif vertical_end <= vertical_start:
        raise LayoutContractError("blocking vertical extent must be ordered")
    if not screw_axes:
        blockers.append("exact screw-axis elevations are unresolved")
    elif len(screw_axes) != fasteners_per_support:
        blockers.append(
            "exactly three distinct screw-axis elevations are required per support"
        )
    elif len(set(screw_axes)) != fasteners_per_support:
        blockers.append("screw-axis elevations must be distinct")
    elif vertical_start is not None and vertical_end is not None and any(
        axis < vertical_start or axis > vertical_end for axis in screw_axes
    ):
        blockers.append("one or more screw axes fall outside verified blocking height")

    normalized: list[dict[str, Any]] = []
    verified_intervals: list[tuple[Decimal, Decimal]] = []
    for index, raw in enumerate(segments_raw):
        segment = _mapping(raw, f"blocking.segments[{index}]")
        start = _decimal(
            segment, "start_mm", f"blocking.segments[{index}]", positive=False
        )
        end = _decimal(
            segment, "end_mm", f"blocking.segments[{index}]", positive=False
        )
        if start < 0 or end <= start or end > wall_length:
            raise LayoutContractError(
                f"blocking.segments[{index}] must be ordered within the measured wall"
            )
        verified = _boolean(segment, "verified", f"blocking.segments[{index}]")
        normalized.append(
            {"start_mm": _out(start), "end_mm": _out(end), "verified": verified}
        )
        if verified:
            verified_intervals.append((start, end))
        else:
            blockers.append(f"blocking segment {index} is not field verified")
    merged = _merge_intervals(verified_intervals)
    continuous_coverage = bool(merged) and (
        merged[0][0] <= EPSILON_MM
        and merged[-1][1] >= wall_length - EPSILON_MM
        and len(merged) == 1
    )
    if continuous_confirmed and not continuous_coverage:
        blockers.append("blocking segments do not prove continuous full-run coverage")
    uncovered_supports = [
        station.index
        for station in stations
        if not any(
            start <= Decimal(str(station.footprint_start_mm)) + EPSILON_MM
            and end >= Decimal(str(station.footprint_end_mm)) - EPSILON_MM
            for start, end in merged
        )
    ]
    if uncovered_supports:
        blockers.append("one or more support footprints lack verified blocking")
    candidate_axes = [
        {
            "support_index": station.index,
            "wall_x_mm": station.center_mm,
            "elevation_mm": _out(axis),
        }
        for station in stations
        for axis in screw_axes
    ]
    return (
        {
            "survey_complete": survey_complete,
            "continuous_blocking_confirmed": continuous_confirmed,
            "verified_segments": normalized,
            "merged_verified_segments_mm": [
                [_out(start), _out(end)] for start, end in merged
            ],
            "continuous_full_run_coverage_proven": continuous_coverage,
            "uncovered_support_indices": uncovered_supports,
            "wall_substrate_material": substrate,
            "wall_substrate_thickness_mm": (
                None if substrate_thickness is None else _out(substrate_thickness)
            ),
            "blocking_material_species_grade": blocking_material,
            "blocking_thickness_mm": (
                None if blocking_thickness is None else _out(blocking_thickness)
            ),
            "exact_fastener_schedule_approved": fastener_approved,
            "utilities_scan_complete": utilities_complete,
            "exact_screw_axes_clear_of_utilities": screw_axes_clear,
            "blocking_vertical_start_mm": (
                None if vertical_start is None else _out(vertical_start)
            ),
            "blocking_vertical_end_mm": (
                None if vertical_end is None else _out(vertical_end)
            ),
            "shelf_top_elevation_mm": _out(shelf_top),
            "screw_axis_elevations_mm": [_out(value) for value in screw_axes],
            "candidate_screw_axes": candidate_axes,
            "candidate_screw_axis_count": len(candidate_axes),
            "required_candidate_screw_axis_count": (
                len(stations) * fasteners_per_support
            ),
        },
        blockers,
    )


def solve_layout(
    *,
    wall: Mapping[str, Any],
    field: Mapping[str, Any],
    environment: Mapping[str, Any],
    printer: Mapping[str, Any],
    keepouts: Mapping[str, Any],
    blocking: Mapping[str, Any],
    joinery: Mapping[str, Any],
    pieces: Mapping[str, Any],
    hardware: Mapping[str, Any],
    cable: Mapping[str, Any],
    project: Mapping[str, Any],
    request_install: bool = False,
) -> dict[str, Any]:
    """Solve one wall while refusing guesses and incomplete installation inputs."""

    for value, name in (
        (wall, "wall"),
        (field, "field"),
        (environment, "environment"),
        (printer, "printer"),
        (keepouts, "keepouts"),
        (blocking, "blocking"),
        (joinery, "joinery"),
        (pieces, "pieces"),
        (hardware, "hardware"),
        (cable, "cable"),
        (project, "project"),
    ):
        _mapping(value, name)
    if not isinstance(request_install, bool):
        raise LayoutContractError("request_install must be true or false")

    wall_length = _decimal(wall, "clear_length_mm", "wall")
    support_width = _decimal(wall, "support_run_width_mm", "wall")
    maximum_pitch = _decimal(wall, "maximum_bay_pitch_mm", "wall")
    if wall_length <= support_width:
        raise LayoutContractError("wall must be longer than one support")
    if not _boolean(wall, "supports_evenly_spaced", "wall"):
        raise LayoutContractError("solver only accepts the equal-pitch R11 contract")
    if not _boolean(wall, "support_end_faces_flush_with_wall_ends", "wall"):
        raise LayoutContractError("terminal support faces must remain flush with wall ends")

    overlap = _decimal(joinery, "integrated_reciprocal_overlap_mm", "joinery")
    clearance = _decimal(joinery, "joint_clearance_mm", "joinery", positive=False)
    minimum_bearing = _decimal(
        joinery, "minimum_bearing_per_support_side_mm", "joinery"
    )
    shelf_depth = _decimal(joinery, "shelf_depth_mm", "joinery")
    shelf_thickness = _decimal(joinery, "shelf_total_thickness_mm", "joinery")
    support_drop = _decimal(joinery, "support_wall_strap_drop_mm", "joinery")
    if clearance < 0 or clearance >= support_width:
        raise LayoutContractError("joint clearance must be nonnegative and below support width")
    if joinery.get("terminal_extension_formula") != (
        "(support_run_width_mm - joint_clearance_mm) / 4"
    ):
        raise LayoutContractError("terminal extension formula drifted")

    usable_span = wall_length - support_width
    bay_count = max(1, _ceil_ratio(usable_span, maximum_pitch))
    if bay_count < 2:
        raise LayoutContractError(
            "the current R11 terminal-load distribution requires at least two bays"
        )
    support_count = bay_count + 1
    pitch = usable_span / bay_count
    if pitch > maximum_pitch + EPSILON_MM:
        raise LayoutContractError("derived equal pitch exceeds its ceiling")
    if pitch <= support_width + EPSILON_MM:
        raise LayoutContractError(
            "derived pitch must exceed support width and leave a positive clear bay"
        )
    bearing_per_side = (support_width - clearance) / 2
    if bearing_per_side < minimum_bearing:
        raise LayoutContractError(
            "derived bearing per support side is below the configured minimum"
        )
    stations = _support_stations(wall_length, support_width, bay_count, pitch)

    regular_length = pitch / 2 + overlap / 2 - clearance / 2
    terminal_extension = (support_width - clearance) / 4
    terminal_length = regular_length + terminal_extension
    if regular_length <= 0 or terminal_length <= regular_length:
        raise LayoutContractError("integrated half-deck candidate lengths are invalid")
    regular_physical_span = 2 * regular_length - overlap
    if overlap >= regular_physical_span - EPSILON_MM:
        raise LayoutContractError(
            "integrated overlap must remain below the physical bay span"
        )

    bay_stations: list[dict[str, Any]] = []
    for index, (left, right) in enumerate(zip(stations, stations[1:])):
        bay_stations.append(
            {
                "index": index,
                "left_support_index": left.index,
                "right_support_index": right.index,
                "left_support_center_mm": left.center_mm,
                "right_support_center_mm": right.center_mm,
                "pitch_mm": _out(pitch),
                "midpoint_mm": _out(
                    (Decimal(str(left.center_mm)) + Decimal(str(right.center_mm))) / 2
                ),
                # The outer extension is deliberately shared between both
                # halves of an end bay.  Making only the outer half longer
                # would require a 170.025 mm raw run on the default layout,
                # which cannot meet the A1-mini brim/reserve contract.
                "left_half_kind": (
                    "terminal" if index in {0, bay_count - 1} else "regular"
                ),
                "right_half_kind": (
                    "terminal" if index in {0, bay_count - 1} else "regular"
                ),
                "integrated_overlap_candidate_mm": _out(overlap),
                "positive_wedge_count": 1,
            }
        )

    supports_per_station = _integer(
        pieces, "supports_per_station", "pieces", minimum=1
    )
    halves_per_bay = _integer(
        pieces, "integrated_half_decks_per_bay", "pieces", minimum=1
    )
    wedges_per_bay = _integer(
        pieces, "positive_bay_wedges_per_bay", "pieces", minimum=1
    )
    cable_modules = _integer(
        pieces, "first_wall_cable_modules_supplied", "pieces", minimum=0
    )
    installed_cable_modules = _integer(
        pieces,
        "first_wall_cable_modules_simultaneously_installed",
        "pieces",
        minimum=0,
    )
    if (supports_per_station, halves_per_bay, wedges_per_bay, cable_modules) != (
        1,
        2,
        1,
        3,
    ):
        raise LayoutContractError("R11 piece-family multiplicities drifted")
    if installed_cable_modules != 2:
        raise LayoutContractError("R11 has exactly two simultaneously installed cable modules")
    support_articles = support_count * supports_per_station
    half_articles = bay_count * halves_per_bay
    wedge_articles = bay_count * wedges_per_bay
    kit_articles = support_articles + half_articles + wedge_articles + cable_modules
    simultaneously_installed_articles = (
        support_articles + half_articles + wedge_articles + installed_cable_modules
    )
    terminal_half_articles = 4
    regular_half_articles = half_articles - terminal_half_articles

    terminal_physical_span = 2 * terminal_length - overlap
    module_body_total = (
        2 * terminal_physical_span
        + Decimal(bay_count - 2) * regular_physical_span
    )
    module_gap_total = Decimal(bay_count - 1) * clearance + 2 * clearance
    module_closure = module_body_total + module_gap_total
    if abs(module_closure - wall_length) > EPSILON_MM:
        raise LayoutContractError(
            "terminal/regular half-deck identities do not close the measured wall"
        )

    wedges_per_plate = _integer(
        pieces, "candidate_wedges_per_plate", "pieces", minimum=1
    )
    cables_per_plate = _integer(
        pieces, "candidate_cable_modules_per_plate", "pieces", minimum=1
    )
    wedge_plate_starts = math.ceil(wedge_articles / wedges_per_plate)
    cable_plate_starts = math.ceil(cable_modules / cables_per_plate) if cable_modules else 0
    target_batched_starts = (
        support_articles + half_articles + wedge_plate_starts + cable_plate_starts
    )
    safe_unbatched_starts = kit_articles

    fasteners_per_support = _integer(
        hardware, "wall_fasteners_per_support", "hardware", minimum=1
    )
    washers_per_fastener = _integer(
        hardware, "washers_per_fastener", "hardware", minimum=1
    )
    if fasteners_per_support != 3 or washers_per_fastener != 1:
        raise LayoutContractError("R11 hardware multiplicities must remain 3 screws and 3 washers per support")
    wall_fasteners = support_count * fasteners_per_support
    washers = wall_fasteners * washers_per_fastener

    printer_evidence, printer_blockers = _printer_evidence(
        printer,
        support_width=support_width,
        shelf_depth=shelf_depth,
        shelf_thickness=shelf_thickness,
        support_drop=support_drop,
        regular_length=regular_length,
        terminal_length=terminal_length,
    )
    keepout_evidence, keepout_blockers = _keepout_evidence(
        keepouts, stations, wall_length
    )
    blocking_evidence, blocking_blockers = _blocking_evidence(
        blocking, stations, wall_length, fasteners_per_support
    )

    field_blockers: list[str] = []
    field_evidence = {
        "measurement_reference": field["measurement_reference"],
        "height_samples_in": list(field["height_samples_in"]),
        "clear_length_samples_mm": list(field["clear_length_samples_mm"]),
        "measurement_uncertainty_mm": field["measurement_uncertainty_mm"],
        "wall_plane_bow_mm": field["wall_plane_bow_mm"],
        "endpoint_trim_clearance_mm": field["endpoint_trim_clearance_mm"],
        "measurement_instrument": field["measurement_instrument"],
        "instrument_resolution_mm": field["instrument_resolution_mm"],
        "measurement_date": field["measurement_date"],
        "observer": field["observer"],
    }
    for key, label in (
        ("measurement_uncertainty_mm", "field measurement uncertainty is unresolved"),
        ("wall_plane_bow_mm", "wall-plane bow is unresolved"),
        ("endpoint_trim_clearance_mm", "endpoint trim clearance is unresolved"),
    ):
        if field[key] is None:
            field_blockers.append(label)
    for key, label in (
        ("measurement_instrument", "field measurement instrument is unresolved"),
        ("instrument_resolution_mm", "field instrument resolution is unresolved"),
        ("measurement_date", "field measurement date is unresolved"),
        ("observer", "field measurement observer is unresolved"),
    ):
        if field[key] is None:
            field_blockers.append(label)

    environment_blockers: list[str] = []
    environment_evidence = {
        key: environment[key]
        for key in SECTION_KEYS["environment_input"]
    }
    if environment["maximum_expected_service_temperature_c"] is None:
        environment_blockers.append("maximum service temperature is unresolved")
    if environment["minimum_expected_service_temperature_c"] is None:
        environment_blockers.append("minimum service temperature is unresolved")
    if environment["minimum_expected_relative_humidity_percent"] is None:
        environment_blockers.append("minimum relative humidity is unresolved")
    if environment["maximum_expected_relative_humidity_percent"] is None:
        environment_blockers.append("maximum relative humidity is unresolved")
    for key, label in (
        ("measurement_instrument", "environment measurement instrument is unresolved"),
        ("measurement_start_date", "environment measurement start date is unresolved"),
        ("measurement_end_date", "environment measurement end date is unresolved"),
    ):
        if environment[key] is None:
            environment_blockers.append(label)
    for key, label in (
        ("direct_sun_exposure_assessed", "direct-sun exposure is not assessed"),
        ("nearby_heat_sources_assessed", "nearby heat sources are not assessed"),
        ("service_environment_record_complete", "service environment record is incomplete"),
    ):
        if not _boolean(environment, key, "environment"):
            environment_blockers.append(label)

    blockers: list[str] = [
        *printer_blockers,
        *keepout_blockers,
        *blocking_blockers,
        *field_blockers,
        *environment_blockers,
    ]
    project_gates = {
        "qualification_only": _boolean(project, "qualification_only", "project"),
        "print_authorized": _boolean(project, "print_authorized", "project"),
        "production_ready": _boolean(project, "production_ready", "project"),
        "wall_installation_authorized": _boolean(
            project, "wall_installation_authorized", "project"
        ),
        "drilling_coordinates_released": _boolean(
            project, "drilling_coordinates_released", "project"
        ),
        "test_load_authorized": _boolean(
            project, "test_load_authorized", "project"
        ),
        "geometry_release_complete": _boolean(
            project, "geometry_release_complete", "project"
        ),
        "independent_engineering_review_approved": _boolean(
            project, "independent_engineering_review_approved", "project"
        ),
        "physical_load_qualification_passed": _boolean(
            project, "physical_load_qualification_passed", "project"
        ),
        "tested_load_rating_exists": _boolean(
            project, "tested_load_rating_exists", "project"
        ),
    }
    if project_gates["qualification_only"]:
        blockers.append("R11 is qualification-only")
    for gate in (
        "print_authorized",
        "production_ready",
        "wall_installation_authorized",
        "drilling_coordinates_released",
        "test_load_authorized",
        "geometry_release_complete",
        "independent_engineering_review_approved",
        "physical_load_qualification_passed",
        "tested_load_rating_exists",
    ):
        if not project_gates[gate]:
            blockers.append(f"project gate {gate} is false")

    overlap_qualified = _boolean(
        joinery, "overlap_physical_gate_passed", "joinery"
    )
    capture_validated = _boolean(
        joinery, "integral_bay_local_support_capture_validated", "joinery"
    )
    bearing_validated = _boolean(
        joinery, "gravity_bearing_surfaces_validated", "joinery"
    )
    if not overlap_qualified:
        blockers.append("55 mm integrated overlap is not physically qualified")
    if not capture_validated:
        blockers.append("integral bay-local support capture is not validated")
    if not bearing_validated:
        blockers.append("gravity-bearing surfaces are not validated")
    wedge_nesting = _boolean(
        pieces, "wedge_plate_nesting_verified", "pieces"
    )
    cable_nesting = _boolean(
        pieces, "cable_plate_nesting_verified", "pieces"
    )
    blockers_tuple = _unique(blockers)

    rated_kg = _decimal(project, "rated_load_kg", "project", positive=False)
    rated_lb = _decimal(project, "rated_load_lb", "project", positive=False)
    if rated_kg < 0 or rated_lb < 0:
        raise LayoutContractError("rated loads cannot be negative")
    if not project_gates["tested_load_rating_exists"] and (rated_kg != 0 or rated_lb != 0):
        raise LayoutContractError("an untested candidate must remain zero-rated")

    closure_reconstructed = support_width + Decimal(bay_count) * pitch
    closure_residual = wall_length - closure_reconstructed
    if abs(closure_residual) > EPSILON_MM:
        raise LayoutContractError("equal-pitch decomposition no longer closes the wall")

    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scope": project.get("scope"),
        "qualification_only": project_gates["qualification_only"],
        "rated_load_kg": _out(rated_kg),
        "rated_load_lb": _out(rated_lb),
        "layout": {
            "clear_wall_length_mm": _out(wall_length),
            "support_run_width_mm": _out(support_width),
            "maximum_bay_pitch_mm": _out(maximum_pitch),
            "usable_center_span_mm": _out(usable_span),
            "bay_count": bay_count,
            "support_count": support_count,
            "actual_pitch_mm": _out(pitch),
            "support_stations": [station.__dict__ for station in stations],
            "bay_stations": bay_stations,
            "exact_wall_closure": {
                "clear_wall_length_in": _out(wall_length / MM_PER_INCH),
                "decomposition": "L = W + bay_count * actual_pitch",
                "support_width_term_mm": _out(support_width),
                "bay_pitch_term_count": bay_count,
                "bay_pitch_term_mm": _out(pitch),
                "reconstructed_wall_length_mm": _out(closure_reconstructed),
                "closure_residual_mm": _out(closure_residual),
                "regular_physical_bay_span_mm": _out(regular_physical_span),
                "terminal_physical_bay_span_mm": _out(terminal_physical_span),
                "terminal_bay_count": 2,
                "regular_bay_count": bay_count - 2,
                "inter_bay_gap_count": bay_count - 1,
                "endpoint_gap_count": 2,
                "module_reconstructed_wall_length_mm": _out(module_closure),
                "module_closure_residual_mm": _out(wall_length - module_closure),
            },
        },
        "joinery_candidate": {
            "integrated_reciprocal_overlap_mm": _out(overlap),
            "joint_clearance_mm": _out(clearance),
            "regular_half_deck_length_mm": _out(regular_length),
            "terminal_extension_mm": _out(terminal_extension),
            "terminal_half_deck_length_mm": _out(terminal_length),
            "bearing_per_support_side_mm": _out(bearing_per_side),
            "minimum_bearing_per_support_side_mm": _out(minimum_bearing),
            "overlap_is_initial_candidate_only": True,
            "overlap_physical_gate_passed": overlap_qualified,
            "integral_bay_local_support_capture_validated": capture_validated,
            "gravity_bearing_surfaces_validated": bearing_validated,
            "piece_reduction_contingent_on_capture_validation": True,
            "structural_credit_from_friction_snap_glue_or_wedge": False,
        },
        "exact_formulas": {
            "bay_count": "ceil((L - W) / Pmax)",
            "support_count": "bay_count + 1",
            "actual_pitch": "(L - W) / bay_count",
            "support_center_i": "W / 2 + i * actual_pitch",
            "regular_half_length": "actual_pitch / 2 + overlap / 2 - joint_clearance / 2",
            "terminal_extension": "(W - joint_clearance) / 4",
            "terminal_half_length": "regular_half_length + terminal_extension",
            "kit_articles": "supports + 2 * bays + 1 * bays + supplied_cable_modules",
            "simultaneously_installed_articles": (
                "supports + 2 * bays + 1 * bays + installed_cable_modules"
            ),
            "wall_fasteners": "3 * supports",
            "washers": "1 * wall_fasteners",
            "target_batched_starts": (
                "supports + half_decks + ceil(wedges / wedge_plate_capacity) "
                "+ ceil(cable_modules / cable_plate_capacity)"
            ),
        },
        "printed_piece_counts": {
            "supports": support_articles,
            "integrated_half_decks": half_articles,
            "terminal_integrated_half_decks": terminal_half_articles,
            "regular_integrated_half_decks": regular_half_articles,
            "positive_bay_wedges": wedge_articles,
            "cable_modules": cable_modules,
            "kit_articles": kit_articles,
            "simultaneously_installed_articles": simultaneously_installed_articles,
            "count_is_releasable": capture_validated,
        },
        "print_start_estimate": {
            "individual_support_starts": support_articles,
            "individual_half_deck_starts": half_articles,
            "candidate_wedge_plate_starts": wedge_plate_starts,
            "candidate_cable_plate_starts": cable_plate_starts,
            "target_batched_starts": target_batched_starts,
            "safe_unbatched_starts": safe_unbatched_starts,
            "verified_production_starts": (
                target_batched_starts if wedge_nesting and cable_nesting else None
            ),
            "formula": (
                "supports + half_decks + ceil(wedges / wedge_plate_capacity) "
                "+ ceil(cable_modules / cable_plate_capacity)"
            ),
            "plate_nesting_verified": wedge_nesting and cable_nesting,
        },
        "hardware_candidate_counts": {
            "wall_fasteners": wall_fasteners,
            "washers": washers,
            "fasteners_per_support": fasteners_per_support,
            "washers_per_fastener": washers_per_fastener,
            "drilling_schedule_created": False,
            "hollow_wall_anchor_primary_load_path_allowed": False,
        },
        "printer_evidence": printer_evidence,
        "field_measurement_evidence": field_evidence,
        "environment_evidence": environment_evidence,
        "cable_system": {
            "receiver_support_indices": list(cable["receiver_support_indices"]),
            "receiver_sockets_per_support": cable["receiver_sockets_per_support"],
            "flush_blanks_supplied": cable["flush_blanks_supplied"],
            "comb_hooks_supplied": cable["comb_hooks_supplied"],
            "simultaneously_installed_modules": cable["simultaneously_installed_modules"],
            "module_clearance_per_face_mm": cable["module_clearance_per_face_mm"],
            "service_lift_drop_mm": cable["service_lift_drop_mm"],
            "structural_credit_allowed": False,
        },
        "keepout_evidence": keepout_evidence,
        "blocking_evidence": blocking_evidence,
        "release": {
            "checked_neutral_qualification_artifact_generation_allowed": True,
            "print_authorized": False,
            "installation_ready": False,
            "wall_installation_authorized": False,
            "drilling_coordinates_released": False,
            "test_load_authorized": False,
            "production_ready": False,
            "blockers": list(blockers_tuple),
        },
    }
    if request_install:
        hard_blockers = _unique(
            (*blockers_tuple, "R11 v1 never releases drilling or installation")
        )
        raise InstallationRefused(hard_blockers, plan)
    return plan


def build_plan(
    config: Mapping[str, Any] | None = None, *, request_install: bool = False
) -> dict[str, Any]:
    """Validate a complete R11 config and solve its wall candidate."""

    cfg = load_config() if config is None else dict(config)
    validate_config(cfg)
    return solve_layout(
        wall=cfg["wall_input"],
        field=cfg["field_measurement_input"],
        environment=cfg["environment_input"],
        printer=cfg["printer_input"],
        keepouts=cfg["keepout_input"],
        blocking=cfg["blocking_input"],
        joinery=cfg["joinery_candidate"],
        pieces=cfg["piece_contract"],
        hardware=cfg["hardware_candidate"],
        cable=cfg["cable_system"],
        project=cfg["project"],
        request_install=request_install,
    )


def main() -> None:
    print(json.dumps(build_plan(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
