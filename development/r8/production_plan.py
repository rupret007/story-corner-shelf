#!/usr/bin/env python3
"""Measurement-driven, fail-closed production planning for R8.

This module converts two *measured* clear wall lengths into a nominal parts
plan.  It deliberately does not create meshes, wall bores, toolpaths, a load
rating, or an installed-release authorization.  All dimensions are
millimetres and all calculated material masses are solid-CAD PETG proxies;
the slicer's filament estimate remains the purchasing value.

The planner preserves the frozen R8 seam architecture:

* a 0.35 mm physical gap between adjacent cassettes,
* every seam centred on a 32 mm D-frame cap, and
* terminal D-frame centres inset 16 mm from each run end.

The maximum cassette length is solved from the configured A1-mini build
volume, brim, edge reserve, cassette height, and 45-degree saved orientation.
It is never copied from the current nominal support layout.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Sequence

from design_math import EPSILON, RunLayout, calculate_run_layout


FROZEN_SEAM_MM = 0.35
FROZEN_CAP_WIDTH_MM = 32.0
FROZEN_TERMINAL_INSET_MM = 16.0
FROZEN_PRINTED_WALL_CHORD_MM = 16.0
DEFAULT_PETG_DENSITY_G_CM3 = 1.27

# Canonical JSON identity of the complete artifact-coupled R8 config.  This is
# intentionally stricter than the individual geometry checks below: the
# qualification artifacts publish printer/material/process instructions,
# nominal run records, safety state, and unresolved-input state as well as CAD.
# Canonical JSON (sorted keys, compact separators, no NaN) makes the identity
# independent of whitespace while retaining exact JSON scalar types and every
# key/list member.  Update this only alongside a deliberately versioned
# artifact contract and its mutation audit.
FROZEN_ARTIFACT_CONFIG_CANONICAL_SHA256 = (
    "56ce54aa078ff728efb7d989f5844d62bcf4e2e456bd7166f29e74868220e402"
)
FROZEN_ARTIFACT_CONFIG_CONTRACT_ID = "r8_16b_petg_artifact_config_v2"
ARTIFACT_CONFIG_IDENTITY_BLOCKER = (
    "artifact_config.complete_identity_must_match_r8_16b_petg_v2"
)

# The selected interface orientation rotates 180 degrees about local X, leaves
# local X/Y on the bed, and uses local negative Z as build direction.  These
# nominal dimensions are the final support-free retained-blank envelope; the
# interface's float32 serialization differs only below 1e-6 mm.
RETAINED_MODULE_SAVED_ORIENTATION = "local_xy_bed_local_negative_z_build"
RETAINED_BLANK_RAW_ENVELOPE_MM = (22.4, 11.7, 27.4)
RAIL_SAVED_ORIENTATION = "local_xz_bed_local_y_build_broad_rear_face"

# CAD-coupled nominal contracts.  The planner may vary measured cassette width,
# but it must never price or pack a coordinated config mutation using fixed
# canonical rail/accessory references or the non-parametric cassette builder.
FROZEN_SELECTED_LEVEL_COUNT = 2
FROZEN_PRINTER_MANUFACTURER = "Bambu Lab"
FROZEN_PRINTER_MODEL = "A1 mini"
FROZEN_PRINTABLE_VOLUME_MM = (180.0, 180.0, 180.0)
FROZEN_NOZZLE_MM = 0.4
FROZEN_SHELF_DEPTH_MM = 152.4
FROZEN_CASSETTE_HEIGHT_MM = 30.0
FROZEN_CASSETTE_CANDIDATE = "front_first_open_back_u_box_3_web"
FROZEN_CASSETTE_GEOMETRY_MM = (
    ("top_skin", 3.2),
    ("bottom_skin", 2.4),
    ("visible_front_wall", 4.0),
    ("full_depth_end_land", 6.4),
    ("internal_web", 2.4),
)
FROZEN_INTERNAL_WEB_COUNT = 3
FROZEN_D_FRAME_ENVELOPE_MM = (152.4, 160.0, 32.0)
FROZEN_D_FRAME_DIMENSIONS_MM = (
    ("shelf_projection_mm", 152.4),
    ("installed_height_mm", 160.0),
    ("body_thickness_across_run_mm", 32.0),
    ("top_chord_mm", 16.0),
    ("wall_chord_mm", FROZEN_PRINTED_WALL_CHORD_MM),
    ("curved_web_mm", 16.0),
    ("root_radius_mm", 10.0),
    ("front_nose_mm", 32.0),
    ("minimum_authored_web_normal_thickness_mm", 16.0),
    ("shelf_bearing_cap_width_across_run_mm", FROZEN_CAP_WIDTH_MM),
    ("saved_edge_reserve_each_side_mm", 2.0),
)
FROZEN_RAIL_ENVELOPE_MM = (36.0, 88.0, 8.8)
FROZEN_SOCKET_COUNT = 3
FROZEN_SOCKET_CENTERS_MM = (20.0, 46.0, 72.0)
FROZEN_RAIL_INSTALLED_LOWER_EDGE_MM = 48.0
FROZEN_MODULE_SERVICE_LIFT_MM = 8.0
FROZEN_RAIL_SERVICE_LIFT_MM = 4.0
FROZEN_ACCESSORY_CLEARANCE_MM = 0.4
FROZEN_CLEARANCE_LADDER_MM = (0.2, 0.3, 0.4, 0.5)
FROZEN_LATCH_STRAIN_PROXY = 0.024
FROZEN_AVAILABLE_MODULES = (
    "blank",
    "single cable peg",
    "three-position cable comb",
    "cable coil hook",
)
FROZEN_ACCESSORY_VOLUME_KEYS = (
    "blank",
    "single_peg",
    "three_cable_comb",
    "coil_j_hook",
)
FROZEN_DEFAULT_EQUIPPED_STATION_INDICES = (
    ("through", (1, 3, 5, 7)),
    ("return", (1, 3)),
)

# Registered production cassettes remove two shallow locator pockets and one
# open keeper slot from the selected U-box.  The dimensions mirror the assembly
# contract and remain analytic here so the planner has no mesh/runtime import.
REGISTRATION_POCKET_COUNT = 2
REGISTRATION_POCKET_X_MM = 4.0
REGISTRATION_POCKET_Y_MM = 12.8
REGISTRATION_POCKET_DEPTH_MM = 1.4
FROZEN_REGISTRATION_REMAINING_BOTTOM_SKIN_MM = 1.0
REGISTRATION_POCKET_END_CENTER_OFFSET_MM = 3.2
KEEPER_SLOT_END_CENTER_OFFSET_MM = 8.0
KEEPER_SLOT_X_MM = 4.8
KEEPER_SLOT_MATERIAL_Y_MM = 1.2
KEEPER_SLOT_Z_BOUNDS_MM = (1.2, 3.2)
GEOMETRY_FEASIBILITY_UNVALIDATED_BLOCKER = (
    "hardware.wall_bore_ligament_and_driver_geometry_fit_unvalidated"
)


class PlanningBlocked(ValueError):
    """Raised when a nominal plan would rely on missing or unsafe inputs."""

    def __init__(self, blockers: Sequence[str]):
        unique = tuple(dict.fromkeys(str(item) for item in blockers))
        if not unique:
            raise ValueError("PlanningBlocked requires at least one blocker")
        self.blockers = unique
        super().__init__("R8 planning blocked: " + "; ".join(unique))


@dataclass(frozen=True)
class HardwareEnvelopeInput:
    """Fastener inputs; driver envelope is cross-X, cross-Y, then axial."""

    structural_screw_diameter_mm: float | None = None
    structural_screw_length_mm: float | None = None
    structural_screw_head_diameter_mm: float | None = None
    structural_screw_head_height_mm: float | None = None
    washer_outer_diameter_mm: float | None = None
    washer_inner_diameter_mm: float | None = None
    washer_thickness_mm: float | None = None
    wall_substrate_thickness_mm: float | None = None
    minimum_verified_embedment_mm: float | None = None
    pilot_diameter_mm: float | None = None
    driver_access_envelope_mm: tuple[float, float, float] | None = None
    approved_fastener_schedule: str | None = None
    approval_confirmed: bool = False


@dataclass(frozen=True)
class WallBoreInputEnvelope:
    """Complete numeric inputs for a later geometry study, never bore approval."""

    structural_screw_diameter_mm: float
    structural_screw_length_mm: float
    structural_screw_head_diameter_mm: float
    structural_screw_head_height_mm: float
    washer_outer_diameter_mm: float
    washer_inner_diameter_mm: float
    washer_thickness_mm: float
    wall_substrate_thickness_mm: float
    minimum_verified_embedment_mm: float
    pilot_diameter_mm: float
    printed_wall_chord_mm: float
    minimum_required_screw_length_mm: float
    driver_access_envelope_mm: tuple[float, float, float]
    minimum_driver_cross_section_mm: float
    driver_required_approach_beyond_head_mm: float
    minimum_driver_axial_length_mm: float
    approved_fastener_schedule: str
    framing_confirmation_record: str
    geometric_fit_validated: bool = False
    geometry_emitted: bool = False


@dataclass(frozen=True)
class HardwareEnvelopeAssessment:
    """Input-completeness state; geometry feasibility remains a later gate."""

    recorded: HardwareEnvelopeInput
    framing_confirmed: bool
    framing_confirmation_record: str | None
    blockers: tuple[str, ...]
    inputs_complete_for_geometry_study: bool
    geometric_fit_validated: bool
    geometry_feasibility_release_blockers: tuple[str, ...]
    ready_for_wall_bore_authoring: bool
    wall_bore_input_envelope: WallBoreInputEnvelope | None
    wall_bore_geometry_emitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CassettePrintCeiling:
    """Exact 45-degree A1-mini physical cassette-width ceiling."""

    yaw_degrees: float
    printable_volume_mm: tuple[float, float, float]
    cassette_height_mm: float
    shelf_depth_mm: float
    brim_each_side_mm: float
    brim_object_gap_mm: float
    edge_reserve_each_side_mm: float
    raw_bed_budget_mm: tuple[float, float]
    maximum_physical_cassette_width_mm: float
    fits_build_height: bool


@dataclass(frozen=True)
class ProductionRunPlan:
    """One measured run and its minimum printable topology."""

    run_id: str
    measured_clear_length_mm: float
    layout: RunLayout
    longest_physical_cassette_mm: float
    printable_cassette_ceiling_mm: float
    module_count_is_minimum: bool
    accessory_eligible_support_indices: tuple[int, ...]
    accessory_default_alternating_support_indices: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BOMItem:
    """One deterministic line in the nominal two-level bill of materials."""

    item_id: str
    quantity: int
    material: str
    nominal_unit_solid_volume_mm3: float | None
    nominal_total_solid_volume_mm3: float | None
    included_in_petg_mass_budget: bool
    note: str


@dataclass(frozen=True)
class PlateObjectPlacement:
    """One raw part and its outer-brim rectangle on an XY build plate."""

    instance_id: str
    part_id: str
    saved_orientation: str
    support_required: bool
    raw_envelope_mm: tuple[float, float, float]
    brim_footprint_mm: tuple[float, float]
    brim_bounds_mm: tuple[float, float, float, float]


@dataclass(frozen=True)
class PlateGeometryProof:
    """Deterministic axis-aligned containment and brim-clearance evidence."""

    printable_volume_mm: tuple[float, float, float]
    brim_each_side_mm: float
    brim_object_gap_mm: float
    edge_reserve_each_side_mm: float
    edge_reserve_config_path: str
    minimum_brim_to_brim_gap_mm: float
    complete_kit_count: int
    retained_blank_count_per_kit: int
    placements: tuple[PlateObjectPlacement, ...]
    pairwise_brim_gaps_mm: tuple[tuple[str, str, float], ...]
    minimum_observed_brim_to_brim_gap_mm: float
    all_placements_contained: bool
    all_build_heights_contained: bool
    all_pairwise_gaps_satisfied: bool
    geometry_proven: bool


@dataclass(frozen=True)
class PlateRecipe:
    """Conservative, easy-to-operate nominal plate recipe."""

    recipe_id: str
    plate_count: int
    objects_per_plate: str
    note: str
    geometry_proof: PlateGeometryProof | None = None


@dataclass(frozen=True)
class RegisteredCassetteVolumeProof:
    """Analytic production-cassette cutout and PETG mass correction."""

    registration_pocket_count_per_cassette: int
    registration_pocket_volume_each_mm3: float
    keeper_slot_volume_each_mm3: float
    cutout_volume_per_cassette_mm3: float
    production_cassette_count: int
    total_cutout_volume_mm3: float
    solid_petg_mass_delta_g: float
    cutouts_pairwise_disjoint: bool
    cutout_volume_independent_of_cassette_width: bool


@dataclass(frozen=True)
class SupportTopologyProof:
    """Dynamic serialized-support families and integral keeper counts."""

    selected_level_count: int
    clean_one_key_terminal_start_count: int
    clean_one_key_terminal_end_count: int
    clean_one_key_terminal_count: int
    smooth_interior_one_keeper_count: int
    bossed_interior_one_keeper_count: int
    smooth_penultimate_two_keeper_count: int
    bossed_penultimate_two_keeper_count: int
    total_support_count: int
    total_integral_keeper_count: int
    penultimate_station_by_run: tuple[tuple[str, int, bool], ...]


@dataclass(frozen=True)
class SolidCadMassBudget:
    """PETG solid-volume proxies, not slicer or finished-part weights."""

    assumed_petg_density_g_cm3: float
    known_registered_cassette_volume_mm3: float
    known_registered_cassette_mass_g: float
    known_non_support_blank_configuration_volume_mm3: float | None
    known_non_support_blank_configuration_mass_g: float | None
    known_non_support_maximum_populated_volume_mm3: float | None
    known_non_support_maximum_populated_mass_g: float | None
    base_blank_configuration_volume_mm3: float | None
    base_blank_configuration_mass_g: float | None
    maximum_populated_configuration_volume_mm3: float | None
    maximum_populated_configuration_mass_g: float | None
    maximum_volume_accessory_kind: str | None
    rail_and_accessory_reference_volume_basis: str
    rail_and_accessory_reference_volumes_pending: bool
    registered_cassette_volume_proof: RegisteredCassetteVolumeProof
    support_reference_volumes_pending: bool
    hardware_mass_included: bool
    slicer_filament_mass_required_for_purchasing: bool
    caveat: str


@dataclass(frozen=True)
class MeasurementDrivenPlan:
    """Nominal measured R8 BOM that remains qualification-only and zero-rated."""

    qualification_only: bool
    production_ready: bool
    installed_release_allowed: bool
    wall_bore_geometry_emitted: bool
    rated_load_kg: float
    rated_load_lb: float
    level_count: int
    print_ceiling: CassettePrintCeiling
    through: ProductionRunPlan
    return_run: ProductionRunPlan
    hardware: HardwareEnvelopeAssessment
    support_topology: SupportTopologyProof
    bom: tuple[BOMItem, ...]
    plate_recipes: tuple[PlateRecipe, ...]
    nominal_plate_count: int
    mass_budget: SolidCadMassBudget
    release_blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _CadReferenceVolumes:
    clean_one_key_terminal_start_d_frame_mm3: float | None
    clean_one_key_terminal_end_d_frame_mm3: float | None
    smooth_interior_one_keeper_d_frame_mm3: float | None
    bossed_interior_one_keeper_d_frame_mm3: float | None
    smooth_penultimate_two_keeper_d_frame_mm3: float | None
    bossed_penultimate_two_keeper_d_frame_mm3: float | None
    retention_rail_mm3: float | None
    retained_accessory_mm3: tuple[tuple[str, float | None], ...]


_HARDWARE_SCALAR_FIELDS = (
    "structural_screw_diameter_mm",
    "structural_screw_length_mm",
    "structural_screw_head_diameter_mm",
    "structural_screw_head_height_mm",
    "washer_outer_diameter_mm",
    "washer_inner_diameter_mm",
    "washer_thickness_mm",
    "wall_substrate_thickness_mm",
    "minimum_verified_embedment_mm",
    "pilot_diameter_mm",
)


def _finite_positive(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) > 0.0
    )


def _finite_nonnegative(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) >= 0.0
    )


def _three_positive_floats(value: object) -> tuple[float, float, float] | None:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    if len(value) != 3 or any(not _finite_positive(item) for item in value):
        return None
    return tuple(float(item) for item in value)  # type: ignore[return-value]


def _nonempty_record(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _exact_numeric_zero(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) == 0.0
    )


def artifact_coupled_config_identity_sha256(cfg: dict[str, Any]) -> str:
    """Return the exact semantic identity used by every R8 v2 artifact.

    The full mapping is serialized rather than a hand-selected subset.  This
    freezes schema/project identity; the exact A1-mini and SUNLU PETG process;
    shelf, D-frame, run, and accessory contracts; wall/safety flags; and every
    qualification or unresolved-input null in one auditable value.
    """

    if not isinstance(cfg, dict):
        raise PlanningBlocked(("artifact_config.root_must_be_json_object",))
    try:
        canonical = json.dumps(
            cfg,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PlanningBlocked(
            ("artifact_config.must_be_finite_canonical_json",)
        ) from error
    return hashlib.sha256(canonical).hexdigest()


def validate_artifact_coupled_config_identity(cfg: dict[str, Any]) -> str:
    """Fail closed unless *every* artifact-coupled config value is frozen.

    Returns the verified digest so generators can record the exact identity in
    validation and manifest provenance without recomputing a parallel gate.
    """

    observed = artifact_coupled_config_identity_sha256(cfg)
    if observed != FROZEN_ARTIFACT_CONFIG_CANONICAL_SHA256:
        raise PlanningBlocked((ARTIFACT_CONFIG_IDENTITY_BLOCKER,))
    return observed


def _matches_positive_contract(value: object, expected: float) -> bool:
    return _finite_positive(value) and math.isclose(
        float(value), expected, rel_tol=0.0, abs_tol=EPSILON
    )


def _matches_positive_sequence(
    value: object, expected: tuple[float, ...]
) -> bool:
    return bool(
        not isinstance(value, (str, bytes))
        and isinstance(value, Sequence)
        and len(value) == len(expected)
        and all(
            _matches_positive_contract(observed, required)
            for observed, required in zip(value, expected)
        )
    )


def _matches_positive_integer_sequence(
    value: object, expected: tuple[int, ...]
) -> bool:
    return bool(
        not isinstance(value, (str, bytes))
        and isinstance(value, Sequence)
        and len(value) == len(expected)
        and all(
            type(observed) is int and observed > 0 and observed == required
            for observed, required in zip(value, expected)
        )
    )


def assess_hardware_envelope(
    hardware: HardwareEnvelopeInput | None,
    *,
    framing_confirmed: bool,
    framing_confirmation_record: str | None,
) -> HardwareEnvelopeAssessment:
    """Validate study inputs without claiming bore geometry feasibility.

    A complete assessment publishes a numeric study envelope only.  This
    module has no bore/ligament/driver-fit geometry validator, so geometric
    fit, bore-authoring readiness, and emitted geometry remain false.
    """

    recorded = hardware if hardware is not None else HardwareEnvelopeInput()
    blockers: list[str] = []
    valid_scalars: dict[str, float] = {}
    for field_name in _HARDWARE_SCALAR_FIELDS:
        value = getattr(recorded, field_name)
        if value is None:
            blockers.append(f"hardware.{field_name}.missing")
        elif not _finite_positive(value):
            blockers.append(f"hardware.{field_name}.must_be_positive_finite")
        else:
            valid_scalars[field_name] = float(value)

    driver = _three_positive_floats(recorded.driver_access_envelope_mm)
    if recorded.driver_access_envelope_mm is None:
        blockers.append("hardware.driver_access_envelope_mm.missing")
    elif driver is None:
        blockers.append(
            "hardware.driver_access_envelope_mm.must_be_three_positive_finite_values"
        )

    if not _nonempty_record(recorded.approved_fastener_schedule):
        blockers.append("hardware.approved_fastener_schedule.missing")
    if recorded.approval_confirmed is not True:
        blockers.append("hardware.approval_confirmed")
    if framing_confirmed is not True:
        blockers.append("framing.continuous_blocking_or_verified_equivalent_unconfirmed")
    if not _nonempty_record(framing_confirmation_record):
        blockers.append("framing.confirmation_record.missing")

    if all(
        key in valid_scalars
        for key in (
            "pilot_diameter_mm",
            "structural_screw_diameter_mm",
        )
    ) and not (
        valid_scalars["pilot_diameter_mm"]
        < valid_scalars["structural_screw_diameter_mm"]
    ):
        blockers.append("hardware.pilot_diameter_must_be_smaller_than_screw")
    if all(
        key in valid_scalars
        for key in (
            "structural_screw_diameter_mm",
            "structural_screw_head_diameter_mm",
            "washer_inner_diameter_mm",
            "washer_outer_diameter_mm",
        )
    ):
        if valid_scalars["structural_screw_head_diameter_mm"] <= valid_scalars[
            "structural_screw_diameter_mm"
        ]:
            blockers.append(
                "hardware.screw_head_diameter_must_exceed_screw_diameter"
            )
        if valid_scalars["washer_inner_diameter_mm"] <= valid_scalars[
            "structural_screw_diameter_mm"
        ]:
            blockers.append(
                "hardware.washer_inner_diameter_must_exceed_screw_diameter"
            )
        if valid_scalars["washer_inner_diameter_mm"] >= valid_scalars[
            "structural_screw_head_diameter_mm"
        ]:
            blockers.append(
                "hardware.washer_inner_diameter_must_be_smaller_than_screw_head"
            )
        if valid_scalars["washer_outer_diameter_mm"] <= valid_scalars[
            "washer_inner_diameter_mm"
        ]:
            blockers.append("hardware.washer_outer_diameter_not_larger_than_inner")
        if valid_scalars["washer_outer_diameter_mm"] <= valid_scalars[
            "structural_screw_head_diameter_mm"
        ]:
            blockers.append(
                "hardware.washer_outer_diameter_must_exceed_screw_head"
            )
    minimum_required_screw_length: float | None = None
    if all(
        key in valid_scalars
        for key in (
            "structural_screw_length_mm",
            "minimum_verified_embedment_mm",
            "washer_thickness_mm",
            "wall_substrate_thickness_mm",
        )
    ):
        minimum_required_screw_length = (
            valid_scalars["minimum_verified_embedment_mm"]
            + FROZEN_PRINTED_WALL_CHORD_MM
            + valid_scalars["washer_thickness_mm"]
            + valid_scalars["wall_substrate_thickness_mm"]
        )
        if (
            valid_scalars["structural_screw_length_mm"] + EPSILON
            < minimum_required_screw_length
        ):
            blockers.append(
                "hardware.screw_length_below_embedment_plus_wall_chord_washer_and_substrate"
            )

    minimum_driver_cross_section: float | None = None
    driver_required_approach: float | None = None
    minimum_driver_axial_length: float | None = None
    if driver is not None and all(
        key in valid_scalars
        for key in (
            "structural_screw_head_diameter_mm",
            "structural_screw_head_height_mm",
            "washer_outer_diameter_mm",
        )
    ):
        minimum_driver_cross_section = max(
            valid_scalars["structural_screw_head_diameter_mm"],
            valid_scalars["washer_outer_diameter_mm"],
        )
        # The study envelope reserves one maximum-hardware span beyond the
        # head as a deterministic minimum approach, with no tool-fit claim.
        driver_required_approach = minimum_driver_cross_section
        minimum_driver_axial_length = (
            valid_scalars["structural_screw_head_height_mm"]
            + driver_required_approach
        )
        if (
            driver[0] + EPSILON < minimum_driver_cross_section
            or driver[1] + EPSILON < minimum_driver_cross_section
        ):
            blockers.append(
                "hardware.driver_access_cross_section_below_head_or_washer"
            )
        if driver[2] + EPSILON < minimum_driver_axial_length:
            blockers.append(
                "hardware.driver_access_axial_below_head_plus_required_approach"
            )

    blockers_tuple = tuple(dict.fromkeys(blockers))
    bore_inputs: WallBoreInputEnvelope | None = None
    if not blockers_tuple:
        if driver is None:  # Defensive: the empty blocker set proves otherwise.
            raise AssertionError("Validated driver envelope was lost")
        if minimum_required_screw_length is None:
            raise AssertionError("Validated screw stack length was lost")
        if (
            minimum_driver_cross_section is None
            or driver_required_approach is None
            or minimum_driver_axial_length is None
        ):
            raise AssertionError("Validated driver-fit study dimensions were lost")
        bore_inputs = WallBoreInputEnvelope(
            **valid_scalars,
            printed_wall_chord_mm=FROZEN_PRINTED_WALL_CHORD_MM,
            minimum_required_screw_length_mm=minimum_required_screw_length,
            driver_access_envelope_mm=driver,
            minimum_driver_cross_section_mm=minimum_driver_cross_section,
            driver_required_approach_beyond_head_mm=driver_required_approach,
            minimum_driver_axial_length_mm=minimum_driver_axial_length,
            approved_fastener_schedule=str(recorded.approved_fastener_schedule).strip(),
            framing_confirmation_record=str(framing_confirmation_record).strip(),
        )
    return HardwareEnvelopeAssessment(
        recorded=recorded,
        framing_confirmed=framing_confirmed is True,
        framing_confirmation_record=framing_confirmation_record,
        blockers=blockers_tuple,
        inputs_complete_for_geometry_study=bore_inputs is not None,
        geometric_fit_validated=False,
        geometry_feasibility_release_blockers=(
            GEOMETRY_FEASIBILITY_UNVALIDATED_BLOCKER,
        ),
        ready_for_wall_bore_authoring=False,
        wall_bore_input_envelope=bore_inputs,
        wall_bore_geometry_emitted=False,
    )


def _positive_config_float(value: object, label: str) -> float:
    if not _finite_positive(value):
        raise ValueError(f"{label} must be a positive finite number")
    return float(value)


def _nonnegative_config_float(value: object, label: str) -> float:
    if not _finite_nonnegative(value):
        raise ValueError(f"{label} must be a nonnegative finite number")
    return float(value)


def _three_config_floats(value: object, label: str) -> tuple[float, float, float]:
    parsed = _three_positive_floats(value)
    if parsed is None:
        raise ValueError(f"{label} must contain three positive finite numbers")
    return parsed


def _rectangle_gap_mm(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    """Return the shortest Euclidean gap between two closed XY rectangles."""

    x_gap = max(left[0] - right[2], right[0] - left[2], 0.0)
    y_gap = max(left[1] - right[3], right[1] - left[3], 0.0)
    return math.hypot(x_gap, y_gap)


def _pairwise_plate_gaps(
    placements: Sequence[PlateObjectPlacement],
) -> tuple[tuple[str, str, float], ...]:
    return tuple(
        (
            first.instance_id,
            second.instance_id,
            _rectangle_gap_mm(first.brim_bounds_mm, second.brim_bounds_mm),
        )
        for index, first in enumerate(placements)
        for second in placements[index + 1 :]
    )


def validate_plate_geometry_proof(proof: PlateGeometryProof) -> None:
    """Recompute every rail-kit plate claim and reject stale or unsafe proof."""

    blockers: list[str] = []
    try:
        bed = _three_config_floats(
            proof.printable_volume_mm, "plate printable volume"
        )
        brim = _positive_config_float(proof.brim_each_side_mm, "plate brim")
        brim_object_gap = _nonnegative_config_float(
            proof.brim_object_gap_mm, "plate brim object gap"
        )
        reserve = _positive_config_float(
            proof.edge_reserve_each_side_mm, "plate edge reserve"
        )
        gap_required = _positive_config_float(
            proof.minimum_brim_to_brim_gap_mm, "minimum brim gap"
        )
    except ValueError as error:
        raise ValueError(f"Invalid rail-kit plate proof: {error}") from error

    if type(proof.complete_kit_count) is not int or proof.complete_kit_count != 1:
        blockers.append("exactly_one_complete_rail_kit_must_be_proven")
    if (
        type(proof.retained_blank_count_per_kit) is not int
        or proof.retained_blank_count_per_kit < 1
    ):
        blockers.append("retained_blank_count_per_kit_must_be_positive_integer")
    if not _nonempty_record(proof.edge_reserve_config_path):
        blockers.append("edge_reserve_config_path_missing")

    expected_count = 1 + proof.retained_blank_count_per_kit
    if len(proof.placements) != expected_count:
        blockers.append("placement_count_does_not_equal_one_rail_plus_blanks")
    ids = tuple(placement.instance_id for placement in proof.placements)
    if len(set(ids)) != len(ids):
        blockers.append("placement_instance_ids_not_unique")
    if sum(item.part_id == "mounted_retention_rail" for item in proof.placements) != 1:
        blockers.append("plate_must_contain_exactly_one_retention_rail")
    if (
        sum(item.part_id == "retained_socket_blank" for item in proof.placements)
        != proof.retained_blank_count_per_kit
    ):
        blockers.append("plate_blank_quantity_mismatch")

    contained = True
    height_contained = True
    for placement in proof.placements:
        raw = placement.raw_envelope_mm
        footprint = placement.brim_footprint_mm
        bounds = placement.brim_bounds_mm
        if len(raw) != 3 or any(not _finite_positive(value) for value in raw):
            blockers.append(f"{placement.instance_id}.raw_envelope_invalid")
            continue
        if placement.part_id == "mounted_retention_rail":
            if placement.saved_orientation != RAIL_SAVED_ORIENTATION:
                blockers.append("retention_rail.saved_orientation_mismatch")
            if placement.support_required is not False:
                blockers.append("retention_rail.support_classification_mismatch")
        elif placement.part_id == "retained_socket_blank":
            if placement.saved_orientation != RETAINED_MODULE_SAVED_ORIENTATION:
                blockers.append("retained_blank.saved_orientation_mismatch")
            if placement.support_required is not False:
                blockers.append("retained_blank.support_classification_mismatch")
            if any(
                not math.isclose(
                    observed, expected, rel_tol=0.0, abs_tol=EPSILON
                )
                for observed, expected in zip(
                    raw, RETAINED_BLANK_RAW_ENVELOPE_MM
                )
            ):
                blockers.append("retained_blank.raw_orientation_envelope_mismatch")
        if len(footprint) != 2 or any(
            not _finite_positive(value) for value in footprint
        ):
            blockers.append(f"{placement.instance_id}.brim_footprint_invalid")
            continue
        if len(bounds) != 4 or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in bounds
        ):
            blockers.append(f"{placement.instance_id}.brim_bounds_invalid")
            continue
        outer_margin = brim + brim_object_gap
        expected_footprint = (
            raw[0] + 2.0 * outer_margin,
            raw[1] + 2.0 * outer_margin,
        )
        if any(
            not math.isclose(observed, expected, rel_tol=0.0, abs_tol=EPSILON)
            for observed, expected in zip(footprint, expected_footprint)
        ):
            blockers.append(f"{placement.instance_id}.brim_footprint_not_derived")
        bounds_size = (bounds[2] - bounds[0], bounds[3] - bounds[1])
        if any(
            not math.isclose(observed, expected, rel_tol=0.0, abs_tol=EPSILON)
            for observed, expected in zip(bounds_size, footprint)
        ):
            blockers.append(f"{placement.instance_id}.bounds_footprint_mismatch")
        in_bounds = bool(
            bounds[0] >= reserve - EPSILON
            and bounds[1] >= reserve - EPSILON
            and bounds[2] <= bed[0] - reserve + EPSILON
            and bounds[3] <= bed[1] - reserve + EPSILON
        )
        contained = contained and in_bounds
        height_contained = height_contained and raw[2] <= bed[2] + EPSILON

    observed_pairs = _pairwise_plate_gaps(proof.placements)
    gap_satisfied = bool(
        observed_pairs
        and all(item[2] + EPSILON >= gap_required for item in observed_pairs)
    )
    minimum_observed = (
        min(item[2] for item in observed_pairs) if observed_pairs else math.nan
    )
    if len(proof.pairwise_brim_gaps_mm) != len(observed_pairs):
        blockers.append("pairwise_gap_record_count_mismatch")
    else:
        for recorded, observed in zip(proof.pairwise_brim_gaps_mm, observed_pairs):
            if recorded[:2] != observed[:2] or not math.isclose(
                recorded[2], observed[2], rel_tol=0.0, abs_tol=EPSILON
            ):
                blockers.append("pairwise_gap_record_stale")
                break
    if not math.isclose(
        proof.minimum_observed_brim_to_brim_gap_mm,
        minimum_observed,
        rel_tol=0.0,
        abs_tol=EPSILON,
    ):
        blockers.append("minimum_observed_gap_record_stale")
    if not contained:
        blockers.append("brim_footprint_outside_edge_reserve")
    if not height_contained:
        blockers.append("part_exceeds_build_height")
    if not gap_satisfied:
        blockers.append("brim_to_brim_gap_below_configured_minimum")
    if proof.all_placements_contained is not contained:
        blockers.append("containment_boolean_stale")
    if proof.all_build_heights_contained is not height_contained:
        blockers.append("build_height_boolean_stale")
    if proof.all_pairwise_gaps_satisfied is not gap_satisfied:
        blockers.append("gap_boolean_stale")
    if proof.geometry_proven is not bool(contained and height_contained and gap_satisfied):
        blockers.append("geometry_proven_boolean_stale")
    if blockers:
        raise ValueError("Invalid rail-kit plate proof: " + "; ".join(blockers))


def derive_rail_kit_plate_geometry(cfg: dict[str, Any]) -> PlateGeometryProof:
    """Place one configured rail and its retained blanks with explicit margins."""

    contract_blockers = _frozen_cad_contract_blockers(cfg)
    if contract_blockers:
        raise PlanningBlocked(contract_blockers)
    printer = cfg["printer"]
    accessory = cfg["accessory_system"]
    bed = _three_config_floats(
        printer["printable_volume_mm"], "printer.printable_volume_mm"
    )
    brim = _positive_config_float(printer["brim_mm"], "printer.brim_mm")
    brim_object_gap = _nonnegative_config_float(
        printer["brim_object_gap_mm"], "printer.brim_object_gap_mm"
    )
    gap = _positive_config_float(
        printer["minimum_brim_to_brim_gap_mm"],
        "printer.minimum_brim_to_brim_gap_mm",
    )
    reserve_path = (
        "shelf.cassette_saved_orientation_candidate.edge_reserve_each_side_mm"
    )
    reserve = _positive_config_float(
        cfg["shelf"]["cassette_saved_orientation_candidate"][
            "edge_reserve_each_side_mm"
        ],
        reserve_path,
    )
    rail_raw = _three_config_floats(
        accessory["rail_envelope_mm"], "accessory_system.rail_envelope_mm"
    )
    sockets = accessory["sockets_per_eligible_corbel"]
    if type(sockets) is not int or sockets < 1:
        raise ValueError("sockets_per_eligible_corbel must be a positive integer")
    centers = accessory["socket_centers_from_rail_bottom_mm"]
    if (
        isinstance(centers, (str, bytes))
        or not isinstance(centers, Sequence)
        or len(centers) != sockets
        or any(not _finite_positive(value) for value in centers)
    ):
        raise ValueError("socket center count/dimensions must match the rail sockets")
    parsed_centers = tuple(float(value) for value in centers)
    if any(
        right <= left + EPSILON
        for left, right in zip(parsed_centers, parsed_centers[1:])
    ):
        raise ValueError("socket centers must be strictly increasing")

    blank_raw = RETAINED_BLANK_RAW_ENVELOPE_MM
    outer_margin = brim + brim_object_gap
    rail_footprint = (
        rail_raw[0] + 2.0 * outer_margin,
        rail_raw[1] + 2.0 * outer_margin,
    )
    blank_footprint = (
        blank_raw[0] + 2.0 * outer_margin,
        blank_raw[1] + 2.0 * outer_margin,
    )
    rail_x = reserve
    rail_y = reserve
    placements: list[PlateObjectPlacement] = [
        PlateObjectPlacement(
            instance_id="retention_rail_01",
            part_id="mounted_retention_rail",
            saved_orientation=RAIL_SAVED_ORIENTATION,
            support_required=False,
            raw_envelope_mm=rail_raw,
            brim_footprint_mm=rail_footprint,
            brim_bounds_mm=(
                rail_x,
                rail_y,
                rail_x + rail_footprint[0],
                rail_y + rail_footprint[1],
            ),
        )
    ]
    blank_x = rail_x + rail_footprint[0] + gap
    for index in range(sockets):
        blank_y = reserve + index * (blank_footprint[1] + gap)
        placements.append(
            PlateObjectPlacement(
                instance_id=f"retained_blank_{index + 1:02d}",
                part_id="retained_socket_blank",
                saved_orientation=RETAINED_MODULE_SAVED_ORIENTATION,
                support_required=False,
                raw_envelope_mm=blank_raw,
                brim_footprint_mm=blank_footprint,
                brim_bounds_mm=(
                    blank_x,
                    blank_y,
                    blank_x + blank_footprint[0],
                    blank_y + blank_footprint[1],
                ),
            )
        )

    placement_tuple = tuple(placements)
    pairwise = _pairwise_plate_gaps(placement_tuple)
    contained = all(
        item.brim_bounds_mm[0] >= reserve - EPSILON
        and item.brim_bounds_mm[1] >= reserve - EPSILON
        and item.brim_bounds_mm[2] <= bed[0] - reserve + EPSILON
        and item.brim_bounds_mm[3] <= bed[1] - reserve + EPSILON
        for item in placement_tuple
    )
    height_contained = all(
        item.raw_envelope_mm[2] <= bed[2] + EPSILON for item in placement_tuple
    )
    gaps_satisfied = bool(
        pairwise and all(item[2] + EPSILON >= gap for item in pairwise)
    )
    proof = PlateGeometryProof(
        printable_volume_mm=bed,
        brim_each_side_mm=brim,
        brim_object_gap_mm=brim_object_gap,
        edge_reserve_each_side_mm=reserve,
        edge_reserve_config_path=reserve_path,
        minimum_brim_to_brim_gap_mm=gap,
        complete_kit_count=1,
        retained_blank_count_per_kit=sockets,
        placements=placement_tuple,
        pairwise_brim_gaps_mm=pairwise,
        minimum_observed_brim_to_brim_gap_mm=min(
            item[2] for item in pairwise
        ),
        all_placements_contained=contained,
        all_build_heights_contained=height_contained,
        all_pairwise_gaps_satisfied=gaps_satisfied,
        geometry_proven=bool(contained and height_contained and gaps_satisfied),
    )
    validate_plate_geometry_proof(proof)
    return proof


def _frozen_layout_dimensions(cfg: dict[str, Any]) -> tuple[float, float, float]:
    seam = _positive_config_float(
        cfg["shelf"]["between_module_seam_mm"], "shelf seam"
    )
    inset = _positive_config_float(
        cfg["shelf"]["terminal_corbel_center_inset_mm"], "terminal inset"
    )
    cap = _positive_config_float(
        cfg["d_frame"]["shelf_bearing_cap_width_across_run_mm"], "corbel cap"
    )
    frozen = (
        ("seam", seam, FROZEN_SEAM_MM),
        ("cap width", cap, FROZEN_CAP_WIDTH_MM),
        ("terminal inset", inset, FROZEN_TERMINAL_INSET_MM),
    )
    for label, observed, expected in frozen:
        if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=EPSILON):
            raise ValueError(
                f"R8 frozen {label} must remain {expected:g} mm; observed {observed:g}"
            )
    if not math.isclose(cap, 2.0 * inset, rel_tol=0.0, abs_tol=EPSILON):
        raise ValueError("The 32 mm terminal caps must finish flush with run ends")
    return seam, inset, cap


def derive_cassette_print_ceiling(cfg: dict[str, Any]) -> CassettePrintCeiling:
    """Solve the exact physical cassette-width limit in the saved orientation."""

    printer = cfg["printer"]
    shelf = cfg["shelf"]
    orientation = shelf["cassette_saved_orientation_candidate"]
    printable = _three_config_floats(
        printer["printable_volume_mm"], "printer.printable_volume_mm"
    )
    height = _positive_config_float(
        shelf["cassette_total_height_mm"], "cassette height"
    )
    depth = _positive_config_float(shelf["depth_mm"], "shelf depth")
    brim = _positive_config_float(printer["brim_mm"], "brim")
    brim_object_gap = _nonnegative_config_float(
        printer["brim_object_gap_mm"], "brim object gap"
    )
    reserve = _positive_config_float(
        orientation["edge_reserve_each_side_mm"], "cassette edge reserve"
    )
    yaw_degrees = float(orientation["bed_yaw_deg"])
    if not math.isfinite(yaw_degrees) or not math.isclose(
        yaw_degrees, 45.0, rel_tol=0.0, abs_tol=EPSILON
    ):
        raise ValueError("The exact R8 cassette ceiling requires the frozen 45-degree yaw")

    raw_x = printable[0] - 2.0 * (brim + brim_object_gap + reserve)
    raw_y = printable[1] - 2.0 * (brim + brim_object_gap + reserve)
    if raw_x <= 0.0 or raw_y <= 0.0:
        raise ValueError("Brim and edge reserve consume the printable bed")
    angle = math.radians(yaw_degrees)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    # A width-by-height rectangle yawed on the bed occupies
    # (w*cos+h*sin) by (w*sin+h*cos).  Solve both bed-axis inequalities for w.
    width_from_x = (raw_x - height * sine) / cosine
    width_from_y = (raw_y - height * cosine) / sine
    ceiling = min(width_from_x, width_from_y)
    if ceiling <= 0.0:
        raise ValueError("No positive cassette width fits the configured process envelope")
    fits_height = depth <= printable[2] + EPSILON
    if not fits_height:
        raise ValueError("Shelf depth exceeds saved-orientation build height")
    return CassettePrintCeiling(
        yaw_degrees=yaw_degrees,
        printable_volume_mm=printable,
        cassette_height_mm=height,
        shelf_depth_mm=depth,
        brim_each_side_mm=brim,
        brim_object_gap_mm=brim_object_gap,
        edge_reserve_each_side_mm=reserve,
        raw_bed_budget_mm=(raw_x, raw_y),
        maximum_physical_cassette_width_mm=ceiling,
        fits_build_height=True,
    )


def _run_layout(
    run_id: str,
    length_mm: float,
    module_count: int,
    *,
    seam_mm: float,
    terminal_inset_mm: float,
    cap_width_mm: float,
) -> RunLayout:
    return calculate_run_layout(
        {
            "id": run_id,
            "nominal_length_mm": length_mm,
            "cassette_module_count": module_count,
            "corbel_count": module_count + 1,
        },
        seam_mm=seam_mm,
        terminal_inset_mm=terminal_inset_mm,
        cap_width_mm=cap_width_mm,
    )


def derive_minimum_run_plan(
    run_id: str,
    measured_clear_length_mm: float,
    *,
    cassette_ceiling_mm: float,
    seam_mm: float = FROZEN_SEAM_MM,
    terminal_inset_mm: float = FROZEN_TERMINAL_INSET_MM,
    cap_width_mm: float = FROZEN_CAP_WIDTH_MM,
) -> ProductionRunPlan:
    """Return the fewest modules whose physical widths all fit the ceiling."""

    length = _positive_config_float(measured_clear_length_mm, f"{run_id} clear length")
    ceiling = _positive_config_float(cassette_ceiling_mm, "cassette ceiling")
    if length <= 2.0 * terminal_inset_mm + EPSILON:
        raise ValueError(
            f"{run_id}: clear length must exceed both 16 mm terminal insets"
        )

    # For n>1, the end cassette is longest and has width
    # (L-2t)/n + t - seam/2.  The closed-form value is only a starting point;
    # exact RunLayout checks below handle n=1 and floating-point boundaries.
    pitch_budget = ceiling - terminal_inset_mm + seam_mm / 2.0
    if pitch_budget <= 0.0:
        raise ValueError("Cassette ceiling cannot carry the terminal geometry")
    estimate = max(
        1,
        int(
            math.ceil(
                (length - 2.0 * terminal_inset_mm) / pitch_budget - EPSILON
            )
        ),
    )
    layout = _run_layout(
        run_id,
        length,
        estimate,
        seam_mm=seam_mm,
        terminal_inset_mm=terminal_inset_mm,
        cap_width_mm=cap_width_mm,
    )
    while max(layout.physical_module_widths_mm) > ceiling + EPSILON:
        estimate += 1
        layout = _run_layout(
            run_id,
            length,
            estimate,
            seam_mm=seam_mm,
            terminal_inset_mm=terminal_inset_mm,
            cap_width_mm=cap_width_mm,
        )

    # Prove minimality instead of trusting the closed-form estimate.
    while estimate > 1:
        previous = _run_layout(
            run_id,
            length,
            estimate - 1,
            seam_mm=seam_mm,
            terminal_inset_mm=terminal_inset_mm,
            cap_width_mm=cap_width_mm,
        )
        if max(previous.physical_module_widths_mm) > ceiling + EPSILON:
            break
        estimate -= 1
        layout = previous

    if estimate == 1:
        raise PlanningBlocked(
            ("retention.single_module_run_requires_unauthored_terminal_keeper",)
        )

    eligible = layout.accessory_eligible_corbel_indices
    defaults = eligible[::2]
    return ProductionRunPlan(
        run_id=run_id,
        measured_clear_length_mm=length,
        layout=layout,
        longest_physical_cassette_mm=max(layout.physical_module_widths_mm),
        printable_cassette_ceiling_mm=ceiling,
        module_count_is_minimum=True,
        accessory_eligible_support_indices=eligible,
        accessory_default_alternating_support_indices=defaults,
    )


def _measurement(value: object, label: str) -> float:
    if value is None:
        raise PlanningBlocked((f"field.{label}.missing",))
    if not _finite_positive(value):
        raise PlanningBlocked((f"field.{label}.must_be_positive_finite",))
    return float(value)


def _frozen_cad_contract_blockers(cfg: dict[str, Any]) -> tuple[str, ...]:
    """Reject config drift from every currently priced canonical CAD article."""

    shelf = cfg["shelf"]
    printer = cfg["printer"]
    d_frame = cfg["d_frame"]
    accessory = cfg["accessory_system"]
    geometry = shelf["selected_cassette_geometry_mm"]
    blockers: list[str] = []
    if printer.get("manufacturer") != FROZEN_PRINTER_MANUFACTURER:
        blockers.append("printer.manufacturer_must_match_bambu_lab")
    if printer.get("model") != FROZEN_PRINTER_MODEL:
        blockers.append("printer.model_must_match_a1_mini")
    if not _matches_positive_sequence(
        printer.get("printable_volume_mm"), FROZEN_PRINTABLE_VOLUME_MM
    ):
        blockers.append("printer.printable_volume_mm_must_match_a1_mini")
    if not _matches_positive_contract(
        printer.get("nozzle_mm"), FROZEN_NOZZLE_MM
    ):
        blockers.append("printer.nozzle_mm_must_match_authored_0_4_mm")
    levels = shelf.get("selected_level_count")
    if type(levels) is not int or levels != FROZEN_SELECTED_LEVEL_COUNT:
        blockers.append("shelf.selected_level_count_must_match_authored_two_levels")
    if not _matches_positive_contract(
        shelf.get("depth_mm"), FROZEN_SHELF_DEPTH_MM
    ):
        blockers.append("shelf.depth_mm_must_match_canonical_cassette")
    if not _matches_positive_contract(
        shelf.get("cassette_total_height_mm"), FROZEN_CASSETTE_HEIGHT_MM
    ):
        blockers.append(
            "shelf.cassette_total_height_mm_must_match_canonical_cassette"
        )
    if shelf.get("selected_cassette_candidate") != FROZEN_CASSETTE_CANDIDATE:
        blockers.append("shelf.selected_cassette_candidate_must_match_canonical")
    for field_name, expected in FROZEN_CASSETTE_GEOMETRY_MM:
        if not _matches_positive_contract(geometry.get(field_name), expected):
            blockers.append(
                f"shelf.selected_cassette_geometry_mm.{field_name}_must_match_canonical"
            )
    web_count = geometry.get("internal_web_count")
    if type(web_count) is not int or web_count != FROZEN_INTERNAL_WEB_COUNT:
        blockers.append(
            "shelf.selected_cassette_geometry_mm.internal_web_count_must_match_canonical"
        )

    if not _matches_positive_sequence(
        d_frame.get("prototype_envelope_mm"), FROZEN_D_FRAME_ENVELOPE_MM
    ):
        blockers.append("d_frame.prototype_envelope_mm_must_match_canonical")
    for field_name, expected in FROZEN_D_FRAME_DIMENSIONS_MM:
        if not _matches_positive_contract(d_frame.get(field_name), expected):
            blockers.append(f"d_frame.{field_name}_must_match_canonical")

    if not _matches_positive_sequence(
        accessory.get("rail_envelope_mm"), FROZEN_RAIL_ENVELOPE_MM
    ):
        blockers.append("accessory_system.rail_envelope_mm_must_match_canonical")
    socket_count = accessory.get("sockets_per_eligible_corbel")
    if type(socket_count) is not int or socket_count != FROZEN_SOCKET_COUNT:
        blockers.append("accessory_system.sockets_per_eligible_corbel_must_equal_3")
    if not _matches_positive_sequence(
        accessory.get("socket_centers_from_rail_bottom_mm"),
        FROZEN_SOCKET_CENTERS_MM,
    ):
        blockers.append("accessory_system.socket_centers_must_match_canonical")
    scalar_contracts = (
        (
            "rail_installed_lower_edge_mm_above_corbel_bottom",
            FROZEN_RAIL_INSTALLED_LOWER_EDGE_MM,
        ),
        ("module_service_lift_mm", FROZEN_MODULE_SERVICE_LIFT_MM),
        ("rail_service_lift_mm", FROZEN_RAIL_SERVICE_LIFT_MM),
        ("nominal_clearance_per_face_mm", FROZEN_ACCESSORY_CLEARANCE_MM),
        ("latch_comparison_strain_proxy", FROZEN_LATCH_STRAIN_PROXY),
    )
    for field_name, expected in scalar_contracts:
        if not _matches_positive_contract(accessory.get(field_name), expected):
            blockers.append(
                f"accessory_system.{field_name}_must_match_canonical"
            )
    if not _matches_positive_sequence(
        accessory.get("clearance_ladder_per_face_mm"),
        FROZEN_CLEARANCE_LADDER_MM,
    ):
        blockers.append(
            "accessory_system.clearance_ladder_per_face_mm_must_match_canonical"
        )
    if accessory.get("positive_release_latch_authored") is not True:
        blockers.append(
            "accessory_system.positive_release_latch_authored_must_remain_true"
        )
    modules = accessory.get("available_modules")
    if (
        isinstance(modules, (str, bytes))
        or not isinstance(modules, Sequence)
        or tuple(modules) != FROZEN_AVAILABLE_MODULES
    ):
        blockers.append("accessory_system.available_modules_must_match_canonical")
    default_stations = accessory.get("default_equipped_station_indices")
    expected_station_runs = dict(FROZEN_DEFAULT_EQUIPPED_STATION_INDICES)
    if (
        not isinstance(default_stations, dict)
        or set(default_stations) != set(expected_station_runs)
        or any(
            not _matches_positive_integer_sequence(
                default_stations.get(run_id), expected_indices
            )
            for run_id, expected_indices in expected_station_runs.items()
        )
    ):
        blockers.append(
            "accessory_system.default_equipped_station_indices_must_match_canonical"
        )
    return tuple(blockers)


def _validate_project_scope(cfg: dict[str, Any]) -> None:
    identity_blockers: tuple[str, ...] = ()
    try:
        validate_artifact_coupled_config_identity(cfg)
    except PlanningBlocked as error:
        identity_blockers = error.blockers
    project = cfg["project"]
    shelf = cfg["shelf"]
    orientation = shelf["cassette_saved_orientation_candidate"]
    d_frame = cfg["d_frame"]
    material = cfg["material"]
    printer = cfg["printer"]
    accessory = cfg["accessory_system"]
    wall_attachment = cfg["wall_attachment"]
    blockers: list[str] = [
        *identity_blockers,
        *_frozen_cad_contract_blockers(cfg),
    ]
    if project.get("qualification_only") is not True:
        blockers.append("project.qualification_only_must_remain_true")
    for key in (
        "installed_release_allowed",
        "physical_qualification_complete",
        "production_ready",
        "load_rating_allowed",
        "tested_load_rating_exists",
        "wall_bores_emitted",
        "embedded_gcode_allowed",
    ):
        if project.get(key) is not False:
            blockers.append(f"project.{key}_must_remain_false")
    if not _exact_numeric_zero(project.get("rated_load_kg")):
        blockers.append("project.rated_load_kg_must_remain_zero")
    if not _exact_numeric_zero(project.get("rated_load_lb")):
        blockers.append("project.rated_load_lb_must_remain_zero")
    if shelf.get("selected_cassette_physical_qualification_complete") is not False:
        blockers.append(
            "shelf.selected_cassette_physical_qualification_complete_must_remain_false"
        )
    if orientation.get("software_envelope_proven") is not True:
        blockers.append(
            "shelf.cassette_saved_orientation_candidate."
            "software_envelope_proven_must_remain_true"
        )
    if orientation.get("physical_printability_qualified") is not False:
        blockers.append(
            "shelf.cassette_saved_orientation_candidate."
            "physical_printability_qualified_must_remain_false"
        )
    if d_frame.get("structural_capacity_credit_allowed") is not False:
        blockers.append(
            "d_frame.structural_capacity_credit_allowed_must_remain_false"
        )
    if material.get("printed_material") != "PETG only":
        blockers.append("material.printed_material_must_be_petg_only")
    if material.get("primary_part_material") != "PETG":
        blockers.append("material.primary_part_material_must_be_petg")
    if material.get("pla_allowed_in_primary_or_load_path_parts") is not False:
        blockers.append("material.pla_in_primary_or_load_path_must_remain_prohibited")
    for key in (
        "structural_credit_from_accessories_allowed",
        "printed_wall_anchors_allowed",
        "hollow_wall_anchors_allowed_in_primary_load_path",
    ):
        if material.get(key) is not False:
            blockers.append(f"material.{key}_must_remain_false")
    if printer.get("filament_product") != "PETG":
        blockers.append("printer.filament_product_must_be_petg")
    filament_preset = printer.get("filament_preset")
    if (
        not isinstance(filament_preset, str)
        or "PETG" not in filament_preset.upper()
        or "PLA" in filament_preset.upper()
    ):
        blockers.append("printer.filament_preset_must_be_petg")
    if (
        wall_attachment.get("continuous_blocking_or_verified_equivalent_required")
        is not True
    ):
        blockers.append(
            "wall_attachment.continuous_blocking_or_verified_equivalent_required"
        )
    if (
        wall_attachment.get("printed_fastener_or_anchor_substitution_allowed")
        is not False
    ):
        blockers.append(
            "wall_attachment.printed_fastener_or_anchor_substitution_must_remain_false"
        )
    if accessory.get("structural_or_shelf_load_credit") is not False:
        blockers.append(
            "accessory_system.structural_or_shelf_load_credit_must_remain_false"
        )
    if not _exact_numeric_zero(accessory.get("rated_load_kg")):
        blockers.append("accessory_system.rated_load_kg_must_remain_zero")
    if not _exact_numeric_zero(accessory.get("rated_load_lb")):
        blockers.append("accessory_system.rated_load_lb_must_remain_zero")
    if blockers:
        raise PlanningBlocked(blockers)


def validate_project_scope(cfg: dict[str, Any]) -> None:
    """Public fail-closed scope gate shared by planners and artifact builders."""

    _validate_project_scope(cfg)


def _cad_reference_volumes() -> _CadReferenceVolumes:
    """Return no live/v1 mass refs before new versioned manifests exist.

    The old qualification-v1 rail is geometrically incompatible with the final
    support stems, and the final negative-Z retained-module serialization also
    differs from v1.  Support, rail, and accessory values therefore remain
    blank until their exact final artifacts publish new manifests.  Variable-
    width registered cassette volume remains analytic below.
    """

    return _CadReferenceVolumes(
        clean_one_key_terminal_start_d_frame_mm3=None,
        clean_one_key_terminal_end_d_frame_mm3=None,
        smooth_interior_one_keeper_d_frame_mm3=None,
        bossed_interior_one_keeper_d_frame_mm3=None,
        smooth_penultimate_two_keeper_d_frame_mm3=None,
        bossed_penultimate_two_keeper_d_frame_mm3=None,
        retention_rail_mm3=None,
        retained_accessory_mm3=(
            ("blank", None),
            ("single_peg", None),
            ("three_cable_comb", None),
            ("coil_j_hook", None),
        ),
    )


def _selected_u_box_seed_volume_mm3(width_mm: float, cfg: dict[str, Any]) -> float:
    """Analytic pre-registration U-box volume used only as an intermediate."""

    shelf = cfg["shelf"]
    if shelf["selected_cassette_candidate"] != "front_first_open_back_u_box_3_web":
        raise ValueError("Mass model only covers the selected R8 front-first U-box")
    geometry = shelf["selected_cassette_geometry_mm"]
    length = _positive_config_float(width_mm, "cassette width")
    depth = _positive_config_float(shelf["depth_mm"], "shelf depth")
    height = _positive_config_float(shelf["cassette_total_height_mm"], "cassette height")
    top = _positive_config_float(geometry["top_skin"], "top skin")
    bottom = _positive_config_float(geometry["bottom_skin"], "bottom skin")
    front = _positive_config_float(geometry["visible_front_wall"], "front wall")
    end = _positive_config_float(geometry["full_depth_end_land"], "end land")
    web = _positive_config_float(geometry["internal_web"], "internal web")
    web_count = geometry["internal_web_count"]
    if isinstance(web_count, bool) or not isinstance(web_count, int) or web_count < 1:
        raise ValueError("internal_web_count must be a positive integer")
    if top + bottom >= height or front >= depth:
        raise ValueError("Selected U-box skins consume the cassette envelope")
    cross_run_solids = 2.0 * end + web_count * web
    if cross_run_solids >= length:
        raise ValueError("Selected U-box end lands and webs consume the cassette width")

    # The continuous top/bottom/front U shell repeats for the full length.
    # End lands and webs add only the still-open rear/vertical interior region.
    u_shell_area = depth * (top + bottom) + front * (height - top - bottom)
    rear_interior_area = (depth - front) * (height - top - bottom)
    return length * u_shell_area + cross_run_solids * rear_interior_area


def _boxes_have_positive_overlap(
    left: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    right: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> bool:
    return all(
        min(first[1], second[1]) - max(first[0], second[0]) > EPSILON
        for first, second in zip(left, right)
    )


def _registered_cassette_cutout_components_mm3(
    width_mm: float, cfg: dict[str, Any]
) -> tuple[float, float, float]:
    """Prove the three production cutouts disjoint and return exact volumes."""

    length = _positive_config_float(width_mm, "cassette width")
    shelf = cfg["shelf"]
    geometry = shelf["selected_cassette_geometry_mm"]
    depth = _positive_config_float(shelf["depth_mm"], "shelf depth")
    height = _positive_config_float(shelf["cassette_total_height_mm"], "height")
    bottom = _positive_config_float(geometry["bottom_skin"], "bottom skin")
    front = _positive_config_float(geometry["visible_front_wall"], "front wall")
    end_land = _positive_config_float(
        geometry["full_depth_end_land"], "full-depth end land"
    )
    remaining_bottom_skin = bottom - REGISTRATION_POCKET_DEPTH_MM
    if remaining_bottom_skin + EPSILON < FROZEN_REGISTRATION_REMAINING_BOTTOM_SKIN_MM:
        raise ValueError(
            "Registered cassette remaining bottom skin is below frozen 1 mm"
        )
    if front + EPSILON < KEEPER_SLOT_MATERIAL_Y_MM:
        raise ValueError("Keeper slot exceeds the cassette visible-front wall")
    if height + EPSILON < KEEPER_SLOT_Z_BOUNDS_MM[1]:
        raise ValueError("Keeper slot exceeds the cassette height")

    pocket_half_x = REGISTRATION_POCKET_X_MM / 2.0
    pocket_half_y = REGISTRATION_POCKET_Y_MM / 2.0
    required_end_land = REGISTRATION_POCKET_END_CENTER_OFFSET_MM + pocket_half_x
    if end_land + EPSILON < required_end_land:
        raise ValueError(
            "Registration pocket exceeds the selected full-depth end land"
        )
    pocket_y = (depth / 2.0 - pocket_half_y, depth / 2.0 + pocket_half_y)
    left_x = (
        REGISTRATION_POCKET_END_CENTER_OFFSET_MM - pocket_half_x,
        REGISTRATION_POCKET_END_CENTER_OFFSET_MM + pocket_half_x,
    )
    right_x = (
        length - REGISTRATION_POCKET_END_CENTER_OFFSET_MM - pocket_half_x,
        length - REGISTRATION_POCKET_END_CENTER_OFFSET_MM + pocket_half_x,
    )
    slot_center_x = length - KEEPER_SLOT_END_CENTER_OFFSET_MM
    slot_x = (
        slot_center_x - KEEPER_SLOT_X_MM / 2.0,
        slot_center_x + KEEPER_SLOT_X_MM / 2.0,
    )
    if (
        pocket_y[0] < -EPSILON
        or pocket_y[1] > depth + EPSILON
        or left_x[0] < -EPSILON
        or right_x[1] > length + EPSILON
        or slot_x[0] < -EPSILON
        or slot_x[1] > length + EPSILON
    ):
        raise ValueError("Registration or keeper cutout exceeds the cassette envelope")

    pocket_z = (0.0, REGISTRATION_POCKET_DEPTH_MM)
    pocket_boxes = (
        (left_x, pocket_y, pocket_z),
        (right_x, pocket_y, pocket_z),
    )
    slot_box = (
        slot_x,
        (0.0, KEEPER_SLOT_MATERIAL_Y_MM),
        KEEPER_SLOT_Z_BOUNDS_MM,
    )
    cutout_boxes = (*pocket_boxes, slot_box)
    if any(
        _boxes_have_positive_overlap(first, second)
        for index, first in enumerate(cutout_boxes)
        for second in cutout_boxes[index + 1 :]
    ):
        raise ValueError("Registered cassette cutout volumes overlap")

    pocket_volume = (
        REGISTRATION_POCKET_X_MM
        * REGISTRATION_POCKET_Y_MM
        * REGISTRATION_POCKET_DEPTH_MM
    )
    keeper_volume = (
        KEEPER_SLOT_X_MM
        * KEEPER_SLOT_MATERIAL_Y_MM
        * (KEEPER_SLOT_Z_BOUNDS_MM[1] - KEEPER_SLOT_Z_BOUNDS_MM[0])
    )
    total = REGISTRATION_POCKET_COUNT * pocket_volume + keeper_volume
    return pocket_volume, keeper_volume, total


def _selected_u_box_volume_mm3(width_mm: float, cfg: dict[str, Any]) -> float:
    """Exact registered production U-box volume, including all three cuts."""

    pre_registration = _selected_u_box_seed_volume_mm3(width_mm, cfg)
    _, _, cutout = _registered_cassette_cutout_components_mm3(width_mm, cfg)
    registered = pre_registration - cutout
    if registered <= 0.0:
        raise ValueError("Registration cutouts consume the selected U-box")
    return registered


def _derive_support_topology(
    runs: tuple[ProductionRunPlan, ProductionRunPlan], levels: int
) -> SupportTopologyProof:
    """Classify terminals, ordinary interiors, and two-keeper penultimates."""

    if type(levels) is not int or levels < 1:
        raise ValueError("selected_level_count must be a positive integer")
    terminal_starts = 0
    terminal_ends = 0
    smooth_interiors = 0
    bossed_interiors = 0
    smooth_penultimates = 0
    bossed_penultimates = 0
    penultimate_records: list[tuple[str, int, bool]] = []
    for run in runs:
        if run.layout.cassette_module_count < 2:
            raise PlanningBlocked(
                ("retention.single_module_run_requires_unauthored_terminal_keeper",)
            )
        eligible = set(run.accessory_eligible_support_indices)
        defaults = set(run.accessory_default_alternating_support_indices)
        if not defaults.issubset(eligible):
            raise AssertionError("Default rail supports exceed geometric eligibility")
        penultimate_index = run.layout.corbel_count - 2
        if penultimate_index not in eligible:
            raise AssertionError("Multi-module run has no eligible penultimate support")
        penultimate_is_bossed = penultimate_index in defaults
        penultimate_records.append(
            (run.run_id, penultimate_index, penultimate_is_bossed)
        )
        ordinary = eligible - {penultimate_index}
        terminal_starts += levels
        terminal_ends += levels
        bossed_interiors += len(ordinary & defaults) * levels
        smooth_interiors += len(ordinary - defaults) * levels
        if penultimate_is_bossed:
            bossed_penultimates += levels
        else:
            smooth_penultimates += levels

    terminals = terminal_starts + terminal_ends
    total = (
        terminals
        + smooth_interiors
        + bossed_interiors
        + smooth_penultimates
        + bossed_penultimates
    )
    expected_total = sum(run.layout.corbel_count for run in runs) * levels
    if total != expected_total:
        raise AssertionError("Serialized support families do not cover the topology")
    keepers = (
        smooth_interiors
        + bossed_interiors
        + 2 * (smooth_penultimates + bossed_penultimates)
    )
    return SupportTopologyProof(
        selected_level_count=levels,
        clean_one_key_terminal_start_count=terminal_starts,
        clean_one_key_terminal_end_count=terminal_ends,
        clean_one_key_terminal_count=terminals,
        smooth_interior_one_keeper_count=smooth_interiors,
        bossed_interior_one_keeper_count=bossed_interiors,
        smooth_penultimate_two_keeper_count=smooth_penultimates,
        bossed_penultimate_two_keeper_count=bossed_penultimates,
        total_support_count=total,
        total_integral_keeper_count=keepers,
        penultimate_station_by_run=tuple(penultimate_records),
    )


def _make_bom_and_budget(
    cfg: dict[str, Any],
    runs: tuple[ProductionRunPlan, ProductionRunPlan],
    *,
    density_g_cm3: float,
) -> tuple[
    tuple[BOMItem, ...],
    tuple[PlateRecipe, ...],
    SolidCadMassBudget,
    SupportTopologyProof,
]:
    levels = cfg["shelf"]["selected_level_count"]
    if type(levels) is not int or levels < 1:
        raise ValueError("selected_level_count must be a positive integer")
    screws_per_corbel = cfg["wall_attachment"][
        "minimum_metal_structural_screws_per_corbel"
    ]
    if type(screws_per_corbel) is not int or screws_per_corbel < 3:
        raise ValueError(
            "minimum_metal_structural_screws_per_corbel must be an integer >= 3"
        )

    support_topology = _derive_support_topology(runs, levels)
    total_corbels = support_topology.total_support_count
    geometrically_eligible_corbels = sum(
        len(run.accessory_eligible_support_indices) for run in runs
    ) * levels
    cassette_count = sum(run.layout.cassette_module_count for run in runs) * levels
    rail_count = sum(
        len(run.accessory_default_alternating_support_indices) for run in runs
    ) * levels
    if rail_count > geometrically_eligible_corbels:
        raise AssertionError("Default rails exceed geometrically eligible supports")
    bossed_supports = (
        support_topology.bossed_interior_one_keeper_count
        + support_topology.bossed_penultimate_two_keeper_count
    )
    if rail_count != bossed_supports:
        raise AssertionError("Every and only default rail support must carry bosses")
    if support_topology.total_integral_keeper_count != cassette_count:
        raise AssertionError("Every cassette must have exactly one integral keeper")
    sockets_per_rail = cfg["accessory_system"]["sockets_per_eligible_corbel"]
    if type(sockets_per_rail) is not int or sockets_per_rail < 1:
        raise ValueError(
            "sockets_per_eligible_corbel must be a positive integer"
        )
    blank_count = rail_count * sockets_per_rail
    screw_count = total_corbels * screws_per_corbel

    cad = _cad_reference_volumes()
    if (
        cad.retention_rail_mm3 is not None
        and not _finite_positive(cad.retention_rail_mm3)
    ):
        raise ValueError("Canonical retention-rail volume must be positive finite")
    if tuple(item[0] for item in cad.retained_accessory_mm3) != (
        FROZEN_ACCESSORY_VOLUME_KEYS
    ) or any(
        item[1] is not None and not _finite_positive(item[1])
        for item in cad.retained_accessory_mm3
    ):
        raise ValueError("Canonical accessory volume references are invalid")
    accessory_volumes = dict(cad.retained_accessory_mm3)
    blank_volume = accessory_volumes["blank"]
    rail_and_accessory_volumes_pending = bool(
        cad.retention_rail_mm3 is None
        or any(value is None for value in accessory_volumes.values())
    )
    maximum_kind: str | None = None
    maximum_accessory_volume: float | None = None
    if all(value is not None for value in accessory_volumes.values()):
        maximum_kind, maximum_accessory_volume = max(
            accessory_volumes.items(), key=lambda item: item[1]
        )
    cassette_widths_one_level = tuple(
        width
        for run in runs
        for width in run.layout.physical_module_widths_mm
    )
    cutout_components = tuple(
        _registered_cassette_cutout_components_mm3(width, cfg)
        for width in cassette_widths_one_level
    )
    if not cutout_components:
        raise AssertionError("A measured production plan has no cassettes")
    pocket_volume, keeper_volume, cutout_per_cassette = cutout_components[0]
    if any(
        not all(
            math.isclose(observed, expected, rel_tol=0.0, abs_tol=EPSILON)
            for observed, expected in zip(item, cutout_components[0])
        )
        for item in cutout_components[1:]
    ):
        raise AssertionError("Registration cutout volume changed with cassette width")
    cassette_volume_one_level = sum(
        _selected_u_box_volume_mm3(width, cfg)
        for width in cassette_widths_one_level
    )
    cassette_volume = cassette_volume_one_level * levels
    support_unit_volumes = (
        cad.clean_one_key_terminal_start_d_frame_mm3,
        cad.clean_one_key_terminal_end_d_frame_mm3,
        cad.smooth_interior_one_keeper_d_frame_mm3,
        cad.bossed_interior_one_keeper_d_frame_mm3,
        cad.smooth_penultimate_two_keeper_d_frame_mm3,
        cad.bossed_penultimate_two_keeper_d_frame_mm3,
    )
    if any(
        value is not None and not _finite_positive(value)
        for value in support_unit_volumes
    ):
        raise ValueError("Canonical support volume references must be positive finite")
    support_volumes_pending = any(value is None for value in support_unit_volumes)
    terminal_start_volume = (
        None
        if cad.clean_one_key_terminal_start_d_frame_mm3 is None
        else (
            support_topology.clean_one_key_terminal_start_count
            * cad.clean_one_key_terminal_start_d_frame_mm3
        )
    )
    terminal_end_volume = (
        None
        if cad.clean_one_key_terminal_end_d_frame_mm3 is None
        else (
            support_topology.clean_one_key_terminal_end_count
            * cad.clean_one_key_terminal_end_d_frame_mm3
        )
    )
    smooth_interior_volume = (
        None
        if cad.smooth_interior_one_keeper_d_frame_mm3 is None
        else (
            support_topology.smooth_interior_one_keeper_count
            * cad.smooth_interior_one_keeper_d_frame_mm3
        )
    )
    bossed_interior_volume = (
        None
        if cad.bossed_interior_one_keeper_d_frame_mm3 is None
        else (
            support_topology.bossed_interior_one_keeper_count
            * cad.bossed_interior_one_keeper_d_frame_mm3
        )
    )
    smooth_penultimate_volume = (
        None
        if cad.smooth_penultimate_two_keeper_d_frame_mm3 is None
        else (
            support_topology.smooth_penultimate_two_keeper_count
            * cad.smooth_penultimate_two_keeper_d_frame_mm3
        )
    )
    bossed_penultimate_volume = (
        None
        if cad.bossed_penultimate_two_keeper_d_frame_mm3 is None
        else (
            support_topology.bossed_penultimate_two_keeper_count
            * cad.bossed_penultimate_two_keeper_d_frame_mm3
        )
    )
    support_total_volume = None
    if not support_volumes_pending:
        support_total_volume = sum(
            value
            for value in (
                terminal_start_volume,
                terminal_end_volume,
                smooth_interior_volume,
                bossed_interior_volume,
                smooth_penultimate_volume,
                bossed_penultimate_volume,
            )
            if value is not None
        )
    rails_volume = (
        None
        if cad.retention_rail_mm3 is None
        else rail_count * cad.retention_rail_mm3
    )
    blanks_volume = (
        None if blank_volume is None else blank_count * blank_volume
    )
    known_blank_volume = (
        None
        if rails_volume is None or blanks_volume is None
        else cassette_volume + rails_volume + blanks_volume
    )
    known_maximum_volume = (
        None
        if rails_volume is None or maximum_accessory_volume is None
        else (
            cassette_volume
            + rails_volume
            + blank_count * maximum_accessory_volume
        )
    )
    base_volume = (
        None
        if support_total_volume is None or known_blank_volume is None
        else support_total_volume + known_blank_volume
    )
    maximum_volume = (
        None
        if support_total_volume is None or known_maximum_volume is None
        else support_total_volume + known_maximum_volume
    )
    mass_factor = density_g_cm3 / 1000.0
    cassette_volume_proof = RegisteredCassetteVolumeProof(
        registration_pocket_count_per_cassette=REGISTRATION_POCKET_COUNT,
        registration_pocket_volume_each_mm3=pocket_volume,
        keeper_slot_volume_each_mm3=keeper_volume,
        cutout_volume_per_cassette_mm3=cutout_per_cassette,
        production_cassette_count=cassette_count,
        total_cutout_volume_mm3=cutout_per_cassette * cassette_count,
        solid_petg_mass_delta_g=(
            cutout_per_cassette * cassette_count * mass_factor
        ),
        cutouts_pairwise_disjoint=True,
        cutout_volume_independent_of_cassette_width=True,
    )
    support_budget_included = base_volume is not None
    if support_budget_included:
        support_budget_note = (
            "Canonical local-SKU volume validated and included in the base budget."
        )
    elif support_volumes_pending:
        support_budget_note = (
            "Canonical local-SKU volume pending; excluded from the mass budget."
        )
    else:
        support_budget_note = (
            "Support volume validated but excluded until the complete rail/accessory "
            "blank-configuration manifest exists."
        )
    non_support_budget_included = known_blank_volume is not None
    rail_budget_note = (
        "Versioned manifest volume included in the non-support blank configuration."
        if non_support_budget_included
        else "Versioned v2 manifest volume pending; excluded from the mass budget."
    )

    bom = (
        BOMItem(
            "clean_one_key_terminal_start_d_frame_corbel",
            support_topology.clean_one_key_terminal_start_count,
            "PETG",
            cad.clean_one_key_terminal_start_d_frame_mm3,
            terminal_start_volume,
            support_budget_included,
            f"Handed clean run-start terminal; one key/no keeper. {support_budget_note}",
        ),
        BOMItem(
            "clean_one_key_terminal_end_d_frame_corbel",
            support_topology.clean_one_key_terminal_end_count,
            "PETG",
            cad.clean_one_key_terminal_end_d_frame_mm3,
            terminal_end_volume,
            support_budget_included,
            f"Handed clean run-end terminal; one key/no keeper. {support_budget_note}",
        ),
        BOMItem(
            "smooth_interior_one_keeper_d_frame_corbel",
            support_topology.smooth_interior_one_keeper_count,
            "PETG",
            cad.smooth_interior_one_keeper_d_frame_mm3,
            smooth_interior_volume,
            support_budget_included,
            f"Two keys, one keeper, no rail bosses. {support_budget_note}",
        ),
        BOMItem(
            "bossed_interior_one_keeper_d_frame_corbel",
            support_topology.bossed_interior_one_keeper_count,
            "PETG",
            cad.bossed_interior_one_keeper_d_frame_mm3,
            bossed_interior_volume,
            support_budget_included,
            f"Two keys, one keeper, rail bosses. {support_budget_note}",
        ),
        BOMItem(
            "smooth_penultimate_two_keeper_d_frame_corbel",
            support_topology.smooth_penultimate_two_keeper_count,
            "PETG",
            cad.smooth_penultimate_two_keeper_d_frame_mm3,
            smooth_penultimate_volume,
            support_budget_included,
            f"Two keys/two keepers; smooth penultimate. {support_budget_note}",
        ),
        BOMItem(
            "bossed_penultimate_two_keeper_d_frame_corbel",
            support_topology.bossed_penultimate_two_keeper_count,
            "PETG",
            cad.bossed_penultimate_two_keeper_d_frame_mm3,
            bossed_penultimate_volume,
            support_budget_included,
            f"Two keys/two keepers; bossed penultimate. {support_budget_note}",
        ),
        BOMItem(
            "selected_front_first_u_box_cassette",
            cassette_count,
            "PETG",
            None,
            cassette_volume,
            True,
            "Registered widths vary; pocket/keeper cutouts are included in volume.",
        ),
        BOMItem(
            "mounted_retention_rail",
            rail_count,
            "PETG",
            cad.retention_rail_mm3,
            rails_volume,
            non_support_budget_included,
            f"Clean default equips alternating interiors. {rail_budget_note}",
        ),
        BOMItem(
            "retained_socket_blank",
            blank_count,
            "PETG",
            blank_volume,
            blanks_volume,
            non_support_budget_included,
            f"Ships every default socket filled. {rail_budget_note}",
        ),
        BOMItem(
            "approved_metal_structural_screw",
            screw_count,
            "approved metal fastener",
            None,
            None,
            False,
            "Minimum count only; exact approved schedule governs installation.",
        ),
        BOMItem(
            "approved_metal_washer",
            screw_count,
            "approved metal washer",
            None,
            None,
            False,
            "One per structural screw unless the approved schedule says otherwise.",
        ),
    )
    if base_volume is not None:
        included_bom_volume = sum(
            item.nominal_total_solid_volume_mm3 or 0.0
            for item in bom
            if item.included_in_petg_mass_budget
        )
        if not math.isclose(
            included_bom_volume, base_volume, rel_tol=0.0, abs_tol=1.0e-5
        ):
            raise AssertionError("Included PETG BOM volume does not match base budget")
    rail_kit_geometry = derive_rail_kit_plate_geometry(cfg)
    rail_kit_plate_count = -(
        -rail_count // rail_kit_geometry.complete_kit_count
    )
    plates = (
        PlateRecipe(
            "one_d_frame_per_plate",
            total_corbels,
            "1 D-frame corbel",
            "Conservative saved broad-face orientation; no packing credit.",
        ),
        PlateRecipe(
            "one_cassette_per_plate",
            cassette_count,
            "1 measured U-box cassette",
            "Conservative 45-degree long-edge orientation; no packing credit.",
        ),
        PlateRecipe(
            "one_default_rail_kit_per_plate",
            rail_kit_plate_count,
            f"1 retention rail + {sockets_per_rail} retained blanks",
            "Coordinates prove brim containment/gaps; Studio exclusion review remains.",
            geometry_proof=rail_kit_geometry,
        ),
    )
    pending_groups: list[str] = []
    if support_volumes_pending:
        pending_groups.append("six canonical local support-SKU volumes")
    if rail_and_accessory_volumes_pending:
        pending_groups.append("versioned v2 rail/accessory manifest volumes")
    budget_caveat = (
        "Partial solid-CAD PETG proxy; pending " + " and ".join(pending_groups) + "."
        if pending_groups
        else "All versioned canonical solid-CAD part volumes are included."
    )
    budget_caveat += (
        " Live-mesh and protected qualification-v1 rail/accessory values are "
        "quarantined and not used. "
        "All values exclude wall loops, 25% infill, purge, brims, generated supports, "
        "and metal hardware."
    )
    budget = SolidCadMassBudget(
        assumed_petg_density_g_cm3=density_g_cm3,
        known_registered_cassette_volume_mm3=cassette_volume,
        known_registered_cassette_mass_g=cassette_volume * mass_factor,
        known_non_support_blank_configuration_volume_mm3=known_blank_volume,
        known_non_support_blank_configuration_mass_g=(
            None if known_blank_volume is None else known_blank_volume * mass_factor
        ),
        known_non_support_maximum_populated_volume_mm3=known_maximum_volume,
        known_non_support_maximum_populated_mass_g=(
            None
            if known_maximum_volume is None
            else known_maximum_volume * mass_factor
        ),
        base_blank_configuration_volume_mm3=base_volume,
        base_blank_configuration_mass_g=(
            None if base_volume is None else base_volume * mass_factor
        ),
        maximum_populated_configuration_volume_mm3=maximum_volume,
        maximum_populated_configuration_mass_g=(
            None if maximum_volume is None else maximum_volume * mass_factor
        ),
        maximum_volume_accessory_kind=maximum_kind,
        rail_and_accessory_reference_volume_basis=(
            "pending new versioned v2 manifests; protected qualification-v1 and "
            "unversioned live-mesh values are quarantined"
        ),
        rail_and_accessory_reference_volumes_pending=(
            rail_and_accessory_volumes_pending
        ),
        registered_cassette_volume_proof=cassette_volume_proof,
        support_reference_volumes_pending=support_volumes_pending,
        hardware_mass_included=False,
        slicer_filament_mass_required_for_purchasing=True,
        caveat=budget_caveat,
    )
    return bom, plates, budget, support_topology


def build_measurement_driven_plan(
    cfg: dict[str, Any],
    *,
    through_clear_length_mm: float | None,
    return_clear_length_mm: float | None,
    hardware: HardwareEnvelopeInput | None,
    framing_confirmed: bool,
    framing_confirmation_record: str | None,
    petg_density_g_cm3: float = DEFAULT_PETG_DENSITY_G_CM3,
) -> MeasurementDrivenPlan:
    """Build a nominal measured BOM after every field/hardware gate is closed.

    A successful return is still a qualification plan, never authorization to
    print production parts or install/load the shelf.
    """

    _validate_project_scope(cfg)
    seam, inset, cap = _frozen_layout_dimensions(cfg)
    through_length = _measurement(through_clear_length_mm, "through_clear_length_mm")
    return_length = _measurement(return_clear_length_mm, "return_clear_length_mm")
    density = _positive_config_float(petg_density_g_cm3, "PETG density")
    hardware_assessment = assess_hardware_envelope(
        hardware,
        framing_confirmed=framing_confirmed,
        framing_confirmation_record=framing_confirmation_record,
    )
    if hardware_assessment.blockers:
        raise PlanningBlocked(hardware_assessment.blockers)

    ceiling = derive_cassette_print_ceiling(cfg)
    through = derive_minimum_run_plan(
        "through",
        through_length,
        cassette_ceiling_mm=ceiling.maximum_physical_cassette_width_mm,
        seam_mm=seam,
        terminal_inset_mm=inset,
        cap_width_mm=cap,
    )
    return_run = derive_minimum_run_plan(
        "return",
        return_length,
        cassette_ceiling_mm=ceiling.maximum_physical_cassette_width_mm,
        seam_mm=seam,
        terminal_inset_mm=inset,
        cap_width_mm=cap,
    )
    bom, plates, budget, support_topology = _make_bom_and_budget(
        cfg, (through, return_run), density_g_cm3=density
    )
    levels = cfg["shelf"]["selected_level_count"]
    return MeasurementDrivenPlan(
        qualification_only=True,
        production_ready=False,
        installed_release_allowed=False,
        wall_bore_geometry_emitted=False,
        rated_load_kg=0.0,
        rated_load_lb=0.0,
        level_count=levels,
        print_ceiling=ceiling,
        through=through,
        return_run=return_run,
        hardware=hardware_assessment,
        support_topology=support_topology,
        bom=bom,
        plate_recipes=plates,
        nominal_plate_count=sum(recipe.plate_count for recipe in plates),
        mass_budget=budget,
        release_blockers=(
            "qualification-only planner; no installed release",
            "zero rated load until physical proof/creep testing passes",
            "measured cassette geometry must be regenerated and revalidated",
            "Bambu Studio slicing and plate placement remain manual verification gates",
            *hardware_assessment.geometry_feasibility_release_blockers,
            "wall-bore CAD is intentionally not emitted by this planner",
        ),
    )
