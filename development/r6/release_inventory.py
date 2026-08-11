#!/usr/bin/env python3
"""Deterministic physical-object inventory for the Story Corner r6 release.

The inventory is deliberately separate from mesh generation.  Every
``ReleaseRecord`` is one independently printed object (``quantity == 1``),
assigned to exactly one independently supported shelf level. Cassette seams
and integral tenons/receivers are not physical objects and therefore are not
allowed to inflate the release total.

All parts remain provisional, experimental, and unrated.  The inventory does
not add a printed wall anchor, a production wall-fastener bore, a cross-level
tie, or numerical structural credit.
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal

from design_math import PlanGeometry, RunPlan, calculate_plan
from release_plan import (
    CassetteInstancePlan,
    enumerate_cassette_instances,
)


Classification = Literal["structural", "retention", "ornament", "test"]
PROVISIONAL_STATUS = "PROVISIONAL_EXPERIMENTAL_UNRATED"


@dataclass(frozen=True)
class LevelSpec:
    """One independent L-shaped shelf level in the selected installation."""

    level_id: str
    shelf_top_offset_above_outlet_in: float
    placement_status: str = "PROVISIONAL"


@dataclass(frozen=True)
class ReleaseRecord:
    """One, and only one, independently printed release object."""

    logical_id: str
    family: str
    variant: str
    level: str
    run: str
    quantity: int
    classification: Classification
    print_orientation_note: str
    zero_structural_credit: bool
    zero_credit_scope: str | None
    provisional_status: str
    position_local_mm: float | None
    interface_ref: str | None
    level_independent: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntegralFeatureRecord:
    """A modeled feature that remains fused to a parent printed object."""

    logical_id: str
    feature_family: str
    variant: str
    level: str
    run: str
    parent_object_id: str
    quantity: int
    printed_separately: bool
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# The 33-piece ornament contract is the approved r6 facade blueprint.  Its
# eight installed families are four handed/run carrier families, one pier
# overlay family, one ordinary end-cap family, and two independent corner
# families.  Connector coupons are test objects and are not installed parts.
# Ornament is isolated, removable, and receives zero structural credit.
ORNAMENT_BLUEPRINT_FAMILY_COUNTS: dict[str, int] = {
    "through_left_ornament_carrier": 6,
    "through_right_ornament_carrier": 6,
    "return_left_ornament_carrier": 3,
    "return_right_ornament_carrier": 3,
    "ornamental_pier_overlay": 11,
    "ordinary_outer_end_cap": 2,
    "corner_fixed_rosette": 1,
    "corner_floating_mate": 1,
}


FIXED_CROWN_SEAMS_PER_LEVEL = 9
SHARED_CROWN_RETENTION_PINS_PER_FIXED_CROWN = 2


EXPECTED_ONE_LEVEL_FAMILY_COUNTS: dict[str, int] = {
    "arcade_half": 18,
    "cassette_lock": 22,
    "cassette_top_retention_wedge": 36,
    "corner_fixed_rosette": 1,
    "corner_floating_mate": 1,
    "crown_bridge": FIXED_CROWN_SEAMS_PER_LEVEL,
    "crown_bridge_retention_pin": FIXED_CROWN_SEAMS_PER_LEVEL,
    "deck_cassette": 18,
    "diaphragm_bowtie_key": 48,
    "fixed_crown_diaphragm_keeper_strip": FIXED_CROWN_SEAMS_PER_LEVEL,
    "fixed_crown_entablature_tie_key": FIXED_CROWN_SEAMS_PER_LEVEL,
    "indexed_vertical_quarter_turn_pin": (
        FIXED_CROWN_SEAMS_PER_LEVEL
        * SHARED_CROWN_RETENTION_PINS_PER_FIXED_CROWN
    ),
    "ordinary_outer_end_cap": 2,
    "ornamental_pier_overlay": 11,
    "spring_retention_wedge": 18,
    "structural_pier_x_corbel": 11,
    "through_left_ornament_carrier": 6,
    "through_right_ornament_carrier": 6,
    "return_left_ornament_carrier": 3,
    "return_right_ornament_carrier": 3,
}


CONFIG_FAMILY_MAP: dict[str, str] = {
    "deck_cassette": "deck_cassettes",
    "arcade_half": "arcade_halves",
    "structural_pier_x_corbel": "structural_pier_x_corbels",
    "cassette_lock": "cassette_locks",
    "cassette_top_retention_wedge": "cassette_top_retention_wedges",
    "diaphragm_bowtie_key": "diaphragm_bowtie_keys",
    "fixed_crown_diaphragm_keeper_strip": "fixed_crown_diaphragm_keeper_strips",
    "fixed_crown_entablature_tie_key": "fixed_crown_entablature_tie_keys",
    "crown_bridge": "crown_bridges",
    "crown_bridge_retention_pin": "crown_bridge_retention_pins",
    "indexed_vertical_quarter_turn_pin": "indexed_vertical_quarter_turn_pins",
    "spring_retention_wedge": "spring_retention_wedges",
}


COUNTING_NOTES: tuple[str, ...] = (
    "The 16 cassette run seams per level are interfaces, not printed objects.",
    "The 36 cassette tenons and 18 spring tenons per level are integral to arcade halves; their receivers are integral to cassettes/corbels.",
    "The 33 removable ornament objects follow the approved facade blueprint and receive zero structural credit.",
    "Cassette locks, positive quarter-turn cross-keys (under historical wedge schema aliases), bridge pins, nine fixed-crown diaphragm keeper strips, and the eighteen shared-family keeper/front-tie quarter-turn pins are counted as separate printed retention objects.",
    "The full-width rectangular bearing cap and locator ridges are integral to each X-corbel; the rejected separate saddle and saddle pin are not installed objects.",
    "The geometry-current disconnected 41-segment/74-pin/4-tie stitch-rail study is excluded from the installed baseline; any future rail must prove benefit in a separately named rail-on/rail-off experiment.",
    "Two print-first ornament connector coupon meshes are test artifacts outside the installed 33-piece ornament count.",
    "Metal structural wall screws and compatible metal heads/washers are a nonprinted installation boundary and are not in this PETG-object inventory.",
)

# The approved blueprint resolves the earlier ornament-carrier grouping question;
# no remaining ambiguity changes the installed physical-object count.
PHYSICAL_COUNT_AMBIGUITIES: tuple[str, ...] = ()


ORIENTATIONS: dict[str, str] = {
    "cassette": (
        "continuous 3.2 mm top skin on the build plate; coffer lands upward; "
        "flip for installation"
    ),
    "arcade": "broad arcade elevation face on the build plate",
    "corbel": (
        "wall-contact face on the build plate; installed elevation and run lie "
        "in the bed plane; qualify the compact-clevis closure and every-layer "
        "connectivity before production"
    ),
    "pin": (
        "shaft axis parallel to the build plate; split plane perpendicular to "
        "the plate; round head and circular cross-section vertical/tangent to "
        "the plate; no support-free or production claim; qualify slicer mapping, "
        "brim, cooling, flexure, and actual-parent insertion/removal"
    ),
    "indexed_pin": (
        "shaft axis parallel to the build plate with the 8 mm handle edge and "
        "one T-tail edge on the plate; software-model mapping requires runtime "
        "actual-parent Boolean proof, while physical installation and production "
        "remain blocked pending coupons and the confirmed printer profile"
    ),
    "lock": "largest flat lock face on the build plate",
    "wedge": "locked crossbar and handle broad faces on the build plate; historical orientation key retained for schema compatibility",
    "bowtie": "largest bowtie plan face on the build plate",
    "keeper": (
        "broad keeper-strip face on the build plate; one rear-bayonet tongue "
        "upward; qualify the separate keeper-reach indexed quarter-turn pin "
        "with the exact actual-parent receiver orientation"
    ),
    "entablature_key": "largest key plan face on the build plate",
    "bridge": "broad crown-bridge ladder face on the build plate",
    "rail": "broad rail side face on the build plate",
    "tie": "largest run-end tie face on the build plate",
    "ornament": (
        "decorated d=0 face on the build plate with receiver housings upward; "
        "this is not a flat-back print and requires its actual-parent orientation coupon"
    ),
}


def selected_level_specs(cfg: dict[str, Any]) -> tuple[LevelSpec, ...]:
    """Return the two explicitly selected, still-provisional level placements."""

    vertical = cfg["closet"]["vertical_layout"]
    if int(vertical["selected_shelf_levels"]) != 2:
        raise ValueError("The r6 release inventory is frozen to exactly two levels")
    return (
        LevelSpec(
            "lower",
            float(vertical["reference_lower_shelf_top_above_outlet_top_in"]),
        ),
        LevelSpec(
            "upper",
            float(vertical["reference_upper_shelf_top_above_outlet_top_in"]),
        ),
    )


def _record(
    *,
    level: str,
    run: str,
    family: str,
    variant: str,
    suffix: str,
    classification: Classification,
    orientation: str,
    position: float | None = None,
    interface_ref: str | None = None,
    zero_credit: bool = False,
    zero_scope: str | None = None,
) -> ReleaseRecord:
    if classification not in {"structural", "retention", "ornament", "test"}:
        raise ValueError(f"Unsupported inventory classification {classification!r}")
    return ReleaseRecord(
        logical_id=f"{level}::{run}::{family}::{suffix}",
        family=family,
        variant=variant,
        level=level,
        run=run,
        quantity=1,
        classification=classification,
        print_orientation_note=orientation,
        zero_structural_credit=zero_credit,
        zero_credit_scope=zero_scope,
        provisional_status=PROVISIONAL_STATUS,
        position_local_mm=None if position is None else round(float(position), 6),
        interface_ref=interface_ref,
    )


def _runs(plan: PlanGeometry) -> tuple[RunPlan, RunPlan]:
    return (plan.through, plan.return_run)


def _support_variant(run: RunPlan, index: int) -> str:
    station_role = "start" if index == 0 else "end" if index + 1 == run.pier_count else "interior"
    return f"{run.role}_{station_role}"


def _seams(run: RunPlan) -> tuple[tuple[int, float, str], ...]:
    """Return one-based internal cassette seams and their movement classes."""

    return tuple(
        (
            boundary_index,
            float(station),
            "fixed_crown" if boundary_index % 2 else "floating_supported_pier",
        )
        for boundary_index, station in enumerate(
            run.cassette_boundary_stations_local_mm[1:-1], start=1
        )
    )


def _closest_support_index(run: RunPlan, cassette: CassetteInstancePlan) -> int:
    return min(
        range(run.pier_count),
        key=lambda index: abs(
            run.support_centers_local_mm[index] - cassette.support_center_local_mm
        ),
    )


def enumerate_level_inventory(
    cfg: dict[str, Any],
    level: str,
    plan: PlanGeometry | None = None,
) -> tuple[ReleaseRecord, ...]:
    """Enumerate the exact configured physical objects for one level."""

    plan = plan or calculate_plan(cfg)
    cassettes = enumerate_cassette_instances(cfg, plan)
    cassette_by_run = {
        run.run_id: tuple(item for item in cassettes if item.run_id == run.run_id)
        for run in _runs(plan)
    }
    records: list[ReleaseRecord] = []

    # Eighteen deck cassettes and their one-to-one handed arcade halves.
    for cassette in cassettes:
        cassette_ref = f"{level}::{cassette.run_id}::deck_cassette::{cassette.index + 1:02d}"
        records.append(
            _record(
                level=level,
                run=cassette.run_id,
                family="deck_cassette",
                variant=cassette.variant_id,
                suffix=f"{cassette.index + 1:02d}",
                classification="structural",
                orientation=ORIENTATIONS["cassette"],
                position=cassette.physical_start_local_mm,
            )
        )
        arcade_variant = f"{cassette.run_role}_{cassette.spring_side}_half"
        arcade_ref = f"{level}::{cassette.run_id}::arcade_half::{cassette.index + 1:02d}"
        records.append(
            _record(
                level=level,
                run=cassette.run_id,
                family="arcade_half",
                variant=arcade_variant,
                suffix=f"{cassette.index + 1:02d}",
                classification="structural",
                orientation=ORIENTATIONS["arcade"],
                position=cassette.support_center_local_mm,
                interface_ref=cassette_ref,
            )
        )
        top_wedges_per_half = int(cfg["tied_arcade"]["cassette_vertical_tenon_count_per_half"])
        for wedge_index in range(top_wedges_per_half):
            records.append(
                _record(
                    level=level,
                    run=cassette.run_id,
                    family="cassette_top_retention_wedge",
                    variant=arcade_variant,
                    suffix=f"half_{cassette.index + 1:02d}_wedge_{wedge_index + 1}",
                    classification="retention",
                    orientation=ORIENTATIONS["wedge"],
                    position=cassette.support_center_local_mm,
                    interface_ref=arcade_ref,
                    zero_credit=True,
                    zero_scope="withdrawal retention/preload only; zero vertical shelf-load credit",
                )
            )
        records.append(
            _record(
                level=level,
                run=cassette.run_id,
                family="spring_retention_wedge",
                variant=arcade_variant,
                suffix=f"half_{cassette.index + 1:02d}",
                classification="retention",
                orientation=ORIENTATIONS["wedge"],
                position=cassette.support_center_local_mm,
                interface_ref=arcade_ref,
                zero_credit=True,
                zero_scope="withdrawal retention/preload only; zero vertical shelf-load credit",
            )
        )
        records.append(
            _record(
                level=level,
                run=cassette.run_id,
                family=f"{cassette.run_role}_{cassette.spring_side}_ornament_carrier",
                variant=arcade_variant,
                suffix=f"half_{cassette.index + 1:02d}",
                classification="ornament",
                orientation=ORIENTATIONS["ornament"],
                position=cassette.nominal_start_local_mm,
                interface_ref=arcade_ref,
                zero_credit=True,
                zero_scope="isolated removable facade; zero structural credit",
            )
        )

    # Eleven independently wall-fastened X-corbels. Each owns an integral
    # full-width rectangular bearing cap and locator ridges; the rejected
    # separate saddle and pin are not installed objects. Production screw
    # bores remain absent.
    for run in _runs(plan):
        for support_index, station in enumerate(run.support_centers_local_mm):
            variant = _support_variant(run, support_index)
            support_ref = (
                f"{level}::{run.run_id}::structural_pier_x_corbel::{support_index + 1:02d}"
            )
            records.extend(
                (
                    _record(
                        level=level,
                        run=run.run_id,
                        family="structural_pier_x_corbel",
                        variant=variant,
                        suffix=f"{support_index + 1:02d}",
                        classification="structural",
                        orientation=ORIENTATIONS["corbel"],
                        position=station,
                    ),
                    _record(
                        level=level,
                        run=run.run_id,
                        family="ornamental_pier_overlay",
                        variant=variant,
                        suffix=f"{support_index + 1:02d}",
                        classification="ornament",
                        orientation=ORIENTATIONS["ornament"],
                        position=station,
                        interface_ref=support_ref,
                        zero_credit=True,
                        zero_scope="isolated removable facade; zero structural credit",
                    ),
                )
            )
            for lock_side in ("left_slot", "right_slot"):
                records.append(
                    _record(
                        level=level,
                        run=run.run_id,
                        family="cassette_lock",
                        variant=f"{variant}_{lock_side}",
                        suffix=f"support_{support_index + 1:02d}_{lock_side}",
                        classification="retention",
                        orientation=ORIENTATIONS["lock"],
                        position=station,
                        interface_ref=support_ref,
                        zero_credit=True,
                        zero_scope="cassette-to-integral-cap retention only; no independent load rating",
                    )
                )

    # Every internal cassette seam receives three diaphragm keys. Crown seams
    # additionally receive fixed front ties. The redundant seven supported-
    # pier front keys were deleted after their access mouths were proven to
    # collide with the final-X top receivers; the elongated diaphragm seats
    # already provide alignment without a fourth thermal constraint.
    diaphragm_positions = tuple(
        str(index + 1) for index, _ in enumerate(cfg["joinery"]["diaphragm_bowtie"]["centers_from_rear_mm"])
    )
    if len(diaphragm_positions) != 3:
        raise ValueError("Exactly three diaphragm keys are required at every run seam")
    for run in _runs(plan):
        for seam_index, station, seam_class in _seams(run):
            seam_ref = f"{run.run_id}_seam_{seam_index:02d}"
            for depth_index in diaphragm_positions:
                records.append(
                    _record(
                        level=level,
                        run=run.run_id,
                        family="diaphragm_bowtie_key",
                        variant=seam_class,
                        suffix=f"seam_{seam_index:02d}_depth_{depth_index}",
                        classification="structural",
                        orientation=ORIENTATIONS["bowtie"],
                        position=station,
                        interface_ref=seam_ref,
                        zero_scope=(
                            "zero longitudinal tension-splice credit at floating pier seam"
                            if seam_class == "floating_supported_pier"
                            else None
                        ),
                    )
                )
            if seam_class == "fixed_crown":
                keeper_ref = (
                    f"{level}::{run.run_id}::"
                    f"fixed_crown_diaphragm_keeper_strip::seam_{seam_index:02d}"
                )
                tie_ref = (
                    f"{level}::{run.run_id}::"
                    f"fixed_crown_entablature_tie_key::seam_{seam_index:02d}"
                )
                records.extend(
                    (
                        _record(
                            level=level,
                            run=run.run_id,
                            family="fixed_crown_diaphragm_keeper_strip",
                            variant=f"{run.role}_left_owner_opposite_crown_pin",
                            suffix=f"seam_{seam_index:02d}",
                            classification="retention",
                            orientation=ORIENTATIONS["keeper"],
                            position=station,
                            interface_ref=seam_ref,
                            zero_credit=True,
                            zero_scope=(
                                "positive anti-drop retention for three fixed-crown "
                                "diaphragm keys; zero shelf-load or splice credit"
                            ),
                        ),
                        _record(
                            level=level,
                            run=run.run_id,
                            family="fixed_crown_entablature_tie_key",
                            variant=run.role,
                            suffix=f"seam_{seam_index:02d}",
                            classification="structural",
                            orientation=ORIENTATIONS["entablature_key"],
                            position=station,
                            interface_ref=seam_ref,
                        ),
                        _record(
                            level=level,
                            run=run.run_id,
                            family="indexed_vertical_quarter_turn_pin",
                            variant="keeper_reach",
                            suffix=f"seam_{seam_index:02d}_keeper_reach",
                            classification="retention",
                            orientation=ORIENTATIONS["indexed_pin"],
                            position=station,
                            interface_ref=keeper_ref,
                            zero_credit=True,
                            zero_scope=(
                                "keeper reverse-slide/anti-drop retention only; "
                                "zero bearing, shear, splice, or shelf-load credit"
                            ),
                        ),
                        _record(
                            level=level,
                            run=run.run_id,
                            family="indexed_vertical_quarter_turn_pin",
                            variant="front_tie_reach",
                            suffix=f"seam_{seam_index:02d}_front_tie_reach",
                            classification="retention",
                            orientation=ORIENTATIONS["indexed_pin"],
                            position=station,
                            interface_ref=tie_ref,
                            zero_credit=True,
                            zero_scope=(
                                "front-tie withdrawal retention only; zero bearing, "
                                "shear, splice, or shelf-load credit"
                            ),
                        ),
                    )
                )

    # One rear bridge and one accessible anti-drop pin per visible bay crown.
    for run in _runs(plan):
        for bay_index, crown in enumerate(run.crown_seam_stations_local_mm):
            bridge_ref = f"{level}::{run.run_id}::crown_bridge::{bay_index + 1:02d}"
            records.extend(
                (
                    _record(
                        level=level,
                        run=run.run_id,
                        family="crown_bridge",
                        variant=run.role,
                        suffix=f"{bay_index + 1:02d}",
                        classification="structural",
                        orientation=ORIENTATIONS["bridge"],
                        position=crown,
                    ),
                    _record(
                        level=level,
                        run=run.run_id,
                        family="crown_bridge_retention_pin",
                        variant=f"{run.role}_fixed_right_half",
                        suffix=f"{bay_index + 1:02d}",
                        classification="retention",
                        orientation=ORIENTATIONS["pin"],
                        position=crown,
                        interface_ref=bridge_ref,
                        zero_credit=True,
                        zero_scope="anti-drop/reverse-slide retention only; zero shelf-load credit",
                    ),
                )
            )

    # Two ordinary free-end closures plus the independent two-piece corner
    # finish.  The floating return mate never becomes a structural L tie.
    for run in _runs(plan):
        records.append(
            _record(
                level=level,
                run=run.run_id,
                family="ordinary_outer_end_cap",
                variant=f"{run.role}_outer_end",
                suffix="outer_end",
                classification="ornament",
                orientation=ORIENTATIONS["ornament"],
                position=run.length_mm,
                zero_credit=True,
                zero_scope="removable end finish; zero structural credit",
            )
        )
    records.extend(
        (
            _record(
                level=level,
                run=plan.through.run_id,
                family="corner_fixed_rosette",
                variant="through_fixed_nine_petal_rosette",
                suffix="fixed_rosette",
                classification="ornament",
                orientation=ORIENTATIONS["ornament"],
                position=0.0,
                zero_credit=True,
                zero_scope="visual corner datum only; zero structural credit",
            ),
            _record(
                level=level,
                run=plan.return_run.run_id,
                family="corner_floating_mate",
                variant="return_floating_mate",
                suffix="floating_mate",
                classification="ornament",
                orientation=ORIENTATIONS["ornament"],
                position=0.0,
                zero_credit=True,
                zero_scope="floating visual mate; no mechanical L connection and zero structural credit",
            ),
        )
    )

    records.sort(key=lambda item: item.logical_id)
    _validate_level_inventory(cfg, records, level)
    return tuple(records)


def enumerate_selected_inventory(
    cfg: dict[str, Any], plan: PlanGeometry | None = None
) -> tuple[ReleaseRecord, ...]:
    """Enumerate both selected levels as distinct logical objects."""

    plan = plan or calculate_plan(cfg)
    records = tuple(
        record
        for level in selected_level_specs(cfg)
        for record in enumerate_level_inventory(cfg, level.level_id, plan)
    )
    expected = int(
        cfg["nominal_geometry_snapshot"]["baseline_complete_physical_object_counts"]
        ["complete_selected_two_levels"]
    )
    if len(records) != expected or len({item.logical_id for item in records}) != expected:
        raise AssertionError(
            f"The selected two-level release must contain {expected} unique objects"
        )
    return records


def enumerate_integral_features(
    cfg: dict[str, Any],
    level: str,
    plan: PlanGeometry | None = None,
) -> tuple[IntegralFeatureRecord, ...]:
    """Enumerate final-X tenons and matching receivers without counting parts."""

    plan = plan or calculate_plan(cfg)
    cassettes = enumerate_cassette_instances(cfg, plan)
    run_lookup = {run.run_id: run for run in _runs(plan)}
    features: list[IntegralFeatureRecord] = []
    for cassette in cassettes:
        run = run_lookup[cassette.run_id]
        cassette_ref = f"{level}::{cassette.run_id}::deck_cassette::{cassette.index + 1:02d}"
        arcade_ref = f"{level}::{cassette.run_id}::arcade_half::{cassette.index + 1:02d}"
        support_index = _closest_support_index(run, cassette)
        support_ref = (
            f"{level}::{run.run_id}::structural_pier_x_corbel::{support_index + 1:02d}"
        )
        variant = f"{cassette.run_role}_{cassette.spring_side}_half"
        top_tenons_per_half = int(cfg["tied_arcade"]["cassette_vertical_tenon_count_per_half"])
        for tenon_index in range(top_tenons_per_half):
            interface = f"half_{cassette.index + 1:02d}_top_{tenon_index + 1}"
            features.extend(
                (
                    IntegralFeatureRecord(
                        f"{level}::{cassette.run_id}::cassette_vertical_tenon::{interface}",
                        "cassette_vertical_tenon",
                        variant,
                        level,
                        cassette.run_id,
                        arcade_ref,
                        1,
                        False,
                        "integral final-X vertical tenon on arcade half",
                    ),
                    IntegralFeatureRecord(
                        f"{level}::{cassette.run_id}::cassette_open_bottom_receiver::{interface}",
                        "cassette_open_bottom_receiver",
                        cassette.variant_id,
                        level,
                        cassette.run_id,
                        cassette_ref,
                        1,
                        False,
                        "integral matching open-bottom receiver in deck cassette",
                    ),
                )
            )
        interface = f"half_{cassette.index + 1:02d}_spring"
        features.extend(
            (
                IntegralFeatureRecord(
                    f"{level}::{cassette.run_id}::spring_vertical_tenon::{interface}",
                    "spring_vertical_tenon",
                    variant,
                    level,
                    cassette.run_id,
                    arcade_ref,
                    1,
                    False,
                    "integral final-X spring tenon on arcade half",
                ),
                IntegralFeatureRecord(
                    f"{level}::{cassette.run_id}::spring_open_bottom_receiver::{interface}",
                    "spring_open_bottom_receiver",
                    _support_variant(run, support_index),
                    level,
                    cassette.run_id,
                    support_ref,
                    1,
                    False,
                    "integral matching spring receiver in X-corbel/pier",
                ),
            )
        )
    features.sort(key=lambda item: item.logical_id)
    expected = 2 * int(cfg["tied_arcade"]["cassette_vertical_tenon_count_per_half"]) * len(cassettes) + 2 * len(cassettes)
    if len(features) != expected or any(item.printed_separately for item in features):
        raise AssertionError("Integral feature inventory drift")
    return tuple(features)


def enumerate_selected_integral_features(
    cfg: dict[str, Any], plan: PlanGeometry | None = None
) -> tuple[IntegralFeatureRecord, ...]:
    plan = plan or calculate_plan(cfg)
    return tuple(
        feature
        for level in selected_level_specs(cfg)
        for feature in enumerate_integral_features(cfg, level.level_id, plan)
    )


def count_by(records: Iterable[ReleaseRecord], field: str) -> dict[str, int]:
    """Count quantity by a string ``ReleaseRecord`` field, sorted by key."""

    if field not in {"family", "variant", "level", "run", "classification"}:
        raise ValueError(f"Unsupported count field {field!r}")
    counts: Counter[str] = Counter()
    for record in records:
        value = getattr(record, field)
        if not isinstance(value, str) or record.quantity <= 0:
            raise ValueError("Inventory count inputs must be positive string-keyed records")
        counts[value] += record.quantity
    return dict(sorted(counts.items()))


def count_integral_features(
    features: Iterable[IntegralFeatureRecord],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for feature in features:
        if feature.quantity <= 0 or feature.printed_separately:
            raise ValueError("Integral feature records may not be separate physical objects")
        counts[feature.feature_family] += feature.quantity
    return dict(sorted(counts.items()))


def records_to_json(records: Iterable[ReleaseRecord]) -> str:
    """Serialize records deterministically without writing a file."""

    return json.dumps(
        [record.to_dict() for record in records],
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def records_to_csv(records: Iterable[ReleaseRecord]) -> str:
    """Serialize records deterministically as RFC-compatible CSV text."""

    fields = tuple(ReleaseRecord.__dataclass_fields__)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(record.to_dict())
    return stream.getvalue()


def integral_features_to_json(features: Iterable[IntegralFeatureRecord]) -> str:
    return json.dumps(
        [feature.to_dict() for feature in features],
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def inventory_reconciliation(
    cfg: dict[str, Any], records: Iterable[ReleaseRecord]
) -> dict[str, Any]:
    """Return count provenance and explicit contradictions, if any."""

    materialized = tuple(records)
    by_family = count_by(materialized, "family")
    config_counts = cfg["nominal_geometry_snapshot"]["nominal_part_topology"]
    contradictions: list[str] = []
    for family, config_key in CONFIG_FAMILY_MAP.items():
        actual = by_family.get(family, 0)
        expected = int(config_counts[config_key]) * len({item.level for item in materialized})
        if actual != expected:
            contradictions.append(
                f"{family}: enumerated {actual}, config contract requires {expected}"
            )
    level_count = len({item.level for item in materialized})
    if level_count == 2:
        selected_counts = cfg["nominal_geometry_snapshot"][
            "selected_two_level_part_topology"
        ]
        for family, config_key in CONFIG_FAMILY_MAP.items():
            actual = by_family.get(family, 0)
            selected_expected = int(selected_counts[config_key])
            if actual != selected_expected:
                contradictions.append(
                    f"{family}: enumerated {actual}, selected-two-level contract requires {selected_expected}"
                )
    ornament_expected = sum(ORNAMENT_BLUEPRINT_FAMILY_COUNTS.values()) * level_count
    ornament_actual = sum(
        item.quantity for item in materialized if item.classification == "ornament"
    )
    if ornament_actual != ornament_expected:
        contradictions.append(
            f"ornament: enumerated {ornament_actual}, blueprint requires {ornament_expected}"
        )
    return {
        "physical_object_count": sum(item.quantity for item in materialized),
        "level_count": level_count,
        "family_counts": by_family,
        "ornament_blueprint_family_counts_per_level": dict(
            sorted(ORNAMENT_BLUEPRINT_FAMILY_COUNTS.items())
        ),
        "counting_notes": list(COUNTING_NOTES),
        "physical_count_ambiguities": list(PHYSICAL_COUNT_AMBIGUITIES),
        "contradictions": contradictions,
        "provisional": True,
        "production_release_allowed": bool(cfg["project"]["production_release_allowed"]),
        "tested_load_rating_exists": bool(cfg["test_protocol"]["tested_load_rating_exists"]),
    }


def _validate_level_inventory(
    cfg: dict[str, Any], records: list[ReleaseRecord], level: str
) -> None:
    if any(item.level != level or item.quantity != 1 for item in records):
        raise AssertionError("Every one-level record must be one object on that level")
    expected = int(
        cfg["nominal_geometry_snapshot"]["baseline_complete_physical_object_counts"]
        ["complete_per_level"]
    )
    if len(records) != expected or len({item.logical_id for item in records}) != expected:
        raise AssertionError(
            f"One level must contain exactly {expected} unique physical objects"
        )
    actual = count_by(records, "family")
    if actual != EXPECTED_ONE_LEVEL_FAMILY_COUNTS:
        raise AssertionError(f"One-level physical taxonomy drift: {actual}")
    reconciliation = inventory_reconciliation(cfg, records)
    if reconciliation["contradictions"]:
        raise AssertionError("; ".join(reconciliation["contradictions"]))


__all__ = [
    "COUNTING_NOTES",
    "EXPECTED_ONE_LEVEL_FAMILY_COUNTS",
    "IntegralFeatureRecord",
    "LevelSpec",
    "ORNAMENT_BLUEPRINT_FAMILY_COUNTS",
    "PHYSICAL_COUNT_AMBIGUITIES",
    "PROVISIONAL_STATUS",
    "ReleaseRecord",
    "count_by",
    "count_integral_features",
    "enumerate_integral_features",
    "enumerate_level_inventory",
    "enumerate_selected_integral_features",
    "enumerate_selected_inventory",
    "integral_features_to_json",
    "inventory_reconciliation",
    "records_to_csv",
    "records_to_json",
    "selected_level_specs",
]
