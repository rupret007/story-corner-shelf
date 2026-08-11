#!/usr/bin/env python3
"""Exact removable-ornament access geometry for the r6 cross-keys.

The oculi are service openings, not painted or recessed circles.  Their planar
profile is the Minkowski sum of the complete ornament motion rectangle and a
13.2 mm disk.  The corresponding cutter crosses the entire removable-solid
depth, ``d = 0 .. 10.2 mm``.  Keeping this contract in a pure module lets the
ornament meshes, the structural-parent generator, and focused release checks
consume one source of truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from shapely.geometry import box as shapely_box


EPSILON = 1.0e-7


@dataclass(frozen=True)
class SweptOculus:
    """One decorative service opening in removable-ornament coordinates."""

    family_id: str
    access_id: str
    locked_center_x_mm: float
    locked_center_y_mm: float
    radius_mm: float
    run_extremes_mm: tuple[float, float]
    removal_drop_mm: float
    depth_zone_mm: tuple[float, float]
    service_role: str

    @property
    def centerline_x_mm(self) -> tuple[float, float]:
        return (
            self.locked_center_x_mm + self.run_extremes_mm[0],
            self.locked_center_x_mm + self.run_extremes_mm[1],
        )

    @property
    def centerline_y_mm(self) -> tuple[float, float]:
        return (
            self.locked_center_y_mm - self.removal_drop_mm,
            self.locked_center_y_mm,
        )

    @property
    def bounds_xy_mm(self) -> tuple[float, float, float, float]:
        x0, x1 = self.centerline_x_mm
        y0, y1 = self.centerline_y_mm
        return (
            x0 - self.radius_mm,
            y0 - self.radius_mm,
            x1 + self.radius_mm,
            y1 + self.radius_mm,
        )

    def profile(self) -> Any:
        """Return the exact rounded-rectangle (swept-capsule) cutter profile."""

        x0, x1 = self.centerline_x_mm
        y0, y1 = self.centerline_y_mm
        return shapely_box(x0, y0, x1, y1).buffer(
            self.radius_mm,
            quad_segs=128,
            cap_style=1,
            join_style=1,
        )

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["centerline_x_mm"] = list(self.centerline_x_mm)
        record["centerline_y_mm"] = list(self.centerline_y_mm)
        record["bounds_xy_mm"] = list(self.bounds_xy_mm)
        return record


@dataclass(frozen=True)
class OrnamentAccessContract:
    radius_mm: float
    depth_zone_mm: tuple[float, float]
    run_extremes_mm: tuple[float, float]
    removal_drop_mm: float
    sweep_step_mm: float
    top_cross_keys_per_level: int
    spring_cross_keys_per_level: int
    total_cross_keys_per_level: int
    decorative_oculi_per_level: int
    unused_terminal_mirror_oculi_per_level: int
    standard_gravity_bosses_per_level: int
    compact_pier_gravity_bosses_per_level: int
    gravity_bosses_per_level: int
    loose_locators_per_level: int
    integral_attachment_features_per_level: int
    minimum_depth_isolation_mm: float
    minimum_connector_to_oculus_clearance_mm: float
    minimum_remaining_planar_web_mm: float
    minimum_pier_connector_to_oculus_clearance_mm: float
    minimum_pier_remaining_planar_web_mm: float
    minimum_locked_handle_radial_clearance_mm: float
    software_model_mapping_contract_required: bool
    physical_installation_mapping_qualified: bool
    production_release_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CarrierCoordinateContract:
    """Exact centered physical-carrier coordinates inside one nominal half bay."""

    family_id: str
    run_role: str
    hand: str
    nominal_half_span_mm: float
    physical_width_mm: float
    inset_each_nominal_end_mm: float

    def nominal_x_from_local(self, local_x_mm: float) -> float:
        return float(local_x_mm) + self.inset_each_nominal_end_mm

    def installed_origin_s_mm(self, spring_s_mm: float) -> float:
        if self.hand == "left":
            return float(spring_s_mm) + self.inset_each_nominal_end_mm
        return (
            float(spring_s_mm)
            - self.nominal_half_span_mm
            + self.inset_each_nominal_end_mm
        )

    def installed_s_bounds_mm(self, spring_s_mm: float) -> tuple[float, float]:
        start = self.installed_origin_s_mm(spring_s_mm)
        return (start, start + self.physical_width_mm)


_CARRIER_IDENTITIES = {
    "through_carrier_left": ("through", "left"),
    "through_carrier_right": ("through", "right"),
    "return_carrier_left": ("return", "left"),
    "return_carrier_right": ("return", "right"),
}


def carrier_coordinate_contract(
    cfg: dict[str, Any], family_id: str
) -> CarrierCoordinateContract:
    """Return the physical-local to nominal-half placement transform."""

    if family_id not in _CARRIER_IDENTITIES:
        raise ValueError(f"{family_id}: not a handed half-bay carrier")
    run_role, hand = _CARRIER_IDENTITIES[family_id]
    visual = cfg["palatine"]["visual_carrier_contract"]
    nominal = float(visual[f"{run_role}_nominal_half_span_mm"])
    physical = float(visual[f"{run_role}_physical_carrier_width_mm"])
    inset = float(visual["inset_each_nominal_end_mm"])
    seam = float(visual["visual_seam_mm"])
    if (
        abs(seam - 2.0 * inset) > EPSILON
        or abs(physical - (nominal - 2.0 * inset)) > EPSILON
        or abs(float(visual["carrier_local_to_nominal_x_offset_mm"]) - inset)
        > EPSILON
    ):
        raise ValueError("Physical carrier is not a centered 0.3 mm inset at both ends")
    return CarrierCoordinateContract(
        family_id,
        run_role,
        hand,
        nominal,
        physical,
        inset,
    )


def derived_carrier_receiver_centers(
    cfg: dict[str, Any], family_id: str
) -> tuple[tuple[float, float], ...]:
    """Derive female local centers from unchanged structural-parent boss datums."""

    coordinate = carrier_coordinate_contract(cfg, family_id)
    record = _raw_maps(cfg)[family_id]
    parent_centers = record["locked_boss_centers_parent_local_u_e_mm"]
    spring_e = float(
        cfg["palatine"]["visual_carrier_contract"]["visual_spring_extrados_y_mm"]
    )
    locked_drop = float(
        cfg["palatine"]["ornament_keyhole_contract"]["gravity_drop_mm"]
    ) / 2.0
    output: list[tuple[float, float]] = []
    for parent_u, parent_e in parent_centers:
        parent_u = float(parent_u)
        if coordinate.hand == "left":
            local_x = parent_u - coordinate.inset_each_nominal_end_mm
        else:
            local_x = (
                coordinate.nominal_half_span_mm
                - coordinate.inset_each_nominal_end_mm
                - parent_u
            )
        local_y = float(parent_e) - spring_e - locked_drop
        output.append((round(local_x, 6), round(local_y, 6)))
    return tuple(output)


def _raw_access(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg["palatine"]["ornament_keyhole_contract"][
        "cross_key_oculus_access_contract"
    ]


def _raw_maps(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg["palatine"]["ornament_keyhole_contract"][
        "per_parent_boss_placement_map"
    ]


def swept_oculi_for_family(
    cfg: dict[str, Any], family_id: str
) -> tuple[SweptOculus, ...]:
    """Build every frozen oculus for one installed ornament family."""

    raw = _raw_access(cfg)
    family_maps = raw["per_ornament_family_access_map"]
    if family_id not in family_maps:
        return ()
    radius = float(raw["oculus_radius_mm"])
    run_extremes = tuple(float(value) for value in raw["run_sweep_extremes_mm"])
    depth_zone = tuple(float(value) for value in raw["cutter_depth_zone_mm"])
    drop = float(raw["removal_drop_mm"])
    family = family_maps[family_id]
    service_role = str(family["service_role"])
    axes = family["locked_cross_key_axes_local_x_y_mm"]
    return tuple(
        SweptOculus(
            family_id=family_id,
            access_id=f"{family_id}_oculus_{index}",
            locked_center_x_mm=float(center[0]),
            locked_center_y_mm=float(center[1]),
            radius_mm=radius,
            run_extremes_mm=run_extremes,
            removal_drop_mm=drop,
            depth_zone_mm=depth_zone,
            service_role=service_role,
        )
        for index, center in enumerate(axes, start=1)
    )


def connector_types_for_family(
    cfg: dict[str, Any], family_id: str
) -> tuple[str, ...]:
    record = _raw_maps(cfg)[family_id]
    types = tuple(str(value) for value in record["attachment_feature_types"])
    if len(types) != 3:
        raise ValueError(f"{family_id}: exactly three attachment feature types are required")
    return types


def _connector_footprint(
    cfg: dict[str, Any],
    family_id: str,
    connector_index: int,
) -> Any:
    keyholes = cfg["palatine"]["ornament_keyhole_contract"]
    center = _raw_maps(cfg)[family_id]["carrier_local_receiver_centers_x_y_mm"][
        connector_index - 1
    ]
    center_x, center_y = (float(value) for value in center)
    connector_type = connector_types_for_family(cfg, family_id)[connector_index - 1]
    if connector_type == "gravity_keyhole":
        outer_run, outer_y = (
            float(value)
            for value in keyholes["gravity_receiver_housing_outer_run_y_mm"]
        )
    elif connector_type == "compact_gravity_keyhole":
        compact = keyholes["compact_pier_gravity_keyhole_contract"]
        outer_run, outer_y = (
            float(value) for value in compact["receiver_housing_outer_run_y_mm"]
        )
    elif connector_type == "noncapturing_loose_locator":
        locator = keyholes["noncapturing_loose_locator_contract"]
        outer_run, outer_y = (
            float(value) for value in locator["receiver_housing_outer_run_y_mm"]
        )
    else:
        raise ValueError(f"{family_id}: unsupported attachment type {connector_type!r}")
    return shapely_box(
        center_x - outer_run / 2.0,
        center_y - outer_y / 2.0,
        center_x + outer_run / 2.0,
        center_y + outer_y / 2.0,
    )


def family_connector_to_oculus_clearances_mm(
    cfg: dict[str, Any], family_id: str
) -> tuple[float, ...]:
    """Return exact planar housing-to-service-cutter clearances."""

    oculi = swept_oculi_for_family(cfg, family_id)
    if not oculi:
        return ()
    profiles = tuple(oculus.profile() for oculus in oculi)
    return tuple(
        min(float(footprint.distance(profile)) for profile in profiles)
        for footprint in (
            _connector_footprint(cfg, family_id, index) for index in range(1, 4)
        )
    )


def connector_housing_footprints(
    cfg: dict[str, Any], family_id: str
) -> tuple[Any, ...]:
    """Return the three exact planar housing envelopes for ligament audits."""

    return tuple(
        _connector_footprint(cfg, family_id, index) for index in range(1, 4)
    )


def connector_internal_cutter_footprints(
    cfg: dict[str, Any], family_id: str
) -> tuple[Any, ...]:
    """Return conservative planar envelopes for all three internal cutters."""

    keyholes = cfg["palatine"]["ornament_keyhole_contract"]
    centers = _raw_maps(cfg)[family_id]["carrier_local_receiver_centers_x_y_mm"]
    footprints: list[Any] = []
    for center, connector_type in zip(
        centers, connector_types_for_family(cfg, family_id)
    ):
        center_x, center_y = (float(value) for value in center)
        if connector_type == "gravity_keyhole":
            run, height = (
                float(value)
                for value in keyholes["gravity_receiver_internal_chase_run_y_mm"]
            )
        elif connector_type == "compact_gravity_keyhole":
            run, height = (
                float(value)
                for value in keyholes["compact_pier_gravity_keyhole_contract"]
                ["internal_chase_run_y_mm"]
            )
        elif connector_type == "noncapturing_loose_locator":
            run, height = (
                float(value)
                for value in keyholes["noncapturing_loose_locator_contract"]
                ["receiver_slot_run_y_mm"]
            )
        else:
            raise ValueError(f"{family_id}: unsupported internal cutter type")
        footprints.append(
            shapely_box(
                center_x - run / 2.0,
                center_y - height / 2.0,
                center_x + run / 2.0,
                center_y + height / 2.0,
            )
        )
    return tuple(footprints)


def ornament_access_contract(cfg: dict[str, Any]) -> OrnamentAccessContract:
    """Validate and summarize the full oculus/attachment access contract."""

    raw = _raw_access(cfg)
    keyholes = cfg["palatine"]["ornament_keyhole_contract"]
    isolation = cfg["ornament_isolation"]
    retention = cfg["tied_arcade"]["retention_wedge"]
    radius = float(raw["oculus_radius_mm"])
    depth_zone = tuple(float(value) for value in raw["cutter_depth_zone_mm"])
    run_extremes = tuple(float(value) for value in raw["run_sweep_extremes_mm"])
    drop = float(raw["removal_drop_mm"])
    step = float(raw["sweep_step_mm"])
    collision_gate = keyholes["strict_collision_gate"]
    axial_step = float(collision_gate["axial_insertion_sweep_step_mm"])
    axial_total = float(collision_gate["axial_insertion_sweep_total_mm"])
    if abs(radius - 13.2) > EPSILON:
        raise ValueError("The r6 decorative service oculus radius must remain 13.2 mm")
    handle_span = float(
        retention["visible_handle_and_positive_index"]["handle_long_span_mm"]
    )
    handle_radial_clearance = radius - handle_span / 2.0
    if handle_radial_clearance + EPSILON < 3.2:
        raise ValueError("Oculus does not clear the complete locked cross-key handle")
    if depth_zone != (0.0, 10.2):
        raise ValueError("Every oculus must cut all removable solid from d=0 through 10.2 mm")
    carrier_zone = tuple(float(value) for value in isolation["carrier_depth_zone_mm"])
    chase_zone = tuple(float(value) for value in isolation["connector_chase_depth_zone_mm"])
    no_go = tuple(float(value) for value in isolation["unloaded_no_go_gap_depth_zone_mm"])
    if carrier_zone != (0.0, 3.2) or chase_zone != (3.2, 10.2):
        raise ValueError("Oculus cutter no longer spans the complete carrier and chase depth")
    if depth_zone != (carrier_zone[0], chase_zone[1]) or no_go != (10.2, 13.2):
        raise ValueError("Oculus depth or unloaded ornament/structure gap drift")
    minimum_depth_isolation = no_go[1] - no_go[0]
    if minimum_depth_isolation + EPSILON < float(
        isolation["minimum_unloaded_clearance_from_structure_mm"]
    ):
        raise ValueError("Removable ornament does not preserve the required 3 mm isolation")
    if run_extremes != (-0.6, 0.6) or abs(drop - 6.0) > EPSILON or abs(step - 0.4) > EPSILON:
        raise ValueError("Oculus does not cover both run extremes and every 0.4 mm of the 6 mm drop")
    if abs(drop / step - round(drop / step)) > EPSILON:
        raise ValueError("Oculus sweep step does not divide the full removal travel")
    if (
        abs(axial_step - 0.4) > EPSILON
        or abs(axial_total - 4.4) > EPSILON
        or abs(axial_total / axial_step - round(axial_total / axial_step)) > EPSILON
    ):
        raise ValueError("Gravity connectors need the exact 4.4 mm axial insertion sweep every 0.4 mm")
    required_states = collision_gate["required_states"]
    expected_states = [
        "axial_entry_clear",
        "every_0.4_mm_axial_insertion_step",
        "gravity_entry",
        "every_0.4_mm_drop_step",
        "locked",
        "both_run_travel_extremes",
    ]
    if required_states != expected_states:
        raise ValueError("Ornament collision gate omits an exact insertion/drop/run state")

    standard_head = tuple(float(value) for value in keyholes["boss_head_depth_zone_mm"])
    standard_full_head = tuple(
        float(value) for value in keyholes["boss_full_head_block_depth_zone_mm"]
    )
    standard_transition = tuple(
        float(value)
        for value in keyholes["boss_head_to_neck_transition_depth_zone_mm"]
    )
    standard_neck = tuple(float(value) for value in keyholes["boss_neck_depth_zone_mm"])
    standard_chase_z = tuple(
        float(value)
        for value in keyholes["gravity_receiver_internal_chase_depth_zone_mm"]
    )
    standard_lip_z = tuple(
        float(value)
        for value in keyholes["gravity_receiver_lip_aperture_depth_zone_mm"]
    )
    if (
        standard_head != (6.0, 8.0)
        or standard_full_head != (6.0, 6.42)
        or standard_transition != (6.4, 8.0)
        or standard_neck != (8.0, 13.22)
        or standard_chase_z != (4.8, 8.6)
        or standard_lip_z != (8.4, 10.4)
    ):
        raise ValueError("Standard mushroom/chase/lip depth topology drift")
    if (
        abs(standard_full_head[0] - standard_chase_z[0] - 1.2) > EPSILON
        or abs(standard_chase_z[1] - standard_transition[1] - 0.6) > EPSILON
        or abs(standard_lip_z[0] - standard_transition[1] - 0.4) > EPSILON
    ):
        raise ValueError("Standard gravity boss loses a conservative depth reserve")

    compact = keyholes["compact_pier_gravity_keyhole_contract"]
    compact_head = tuple(float(value) for value in compact["boss_head_run_y_mm"])
    compact_neck = tuple(float(value) for value in compact["boss_neck_run_y_mm"])
    compact_receiver = tuple(
        float(value) for value in compact["receiver_head_run_y_mm"]
    )
    compact_chase = tuple(
        float(value) for value in compact["internal_chase_run_y_mm"]
    )
    compact_housing = tuple(
        float(value) for value in compact["receiver_housing_outer_run_y_mm"]
    )
    compact_clearance = float(compact["clearance_per_face_mm"])
    compact_wall = float(compact["minimum_receiver_wall_mm"])
    compact_head_z = tuple(float(value) for value in compact["boss_head_depth_zone_mm"])
    compact_full_head_z = tuple(
        float(value) for value in compact["boss_full_head_block_depth_zone_mm"]
    )
    compact_transition_z = tuple(
        float(value)
        for value in compact["boss_head_to_neck_transition_depth_zone_mm"]
    )
    compact_neck_z = tuple(float(value) for value in compact["boss_neck_depth_zone_mm"])
    compact_chase_z = tuple(
        float(value) for value in compact["internal_chase_depth_zone_mm"]
    )
    compact_lip_z = tuple(
        float(value) for value in compact["lip_aperture_depth_zone_mm"]
    )
    if (
        compact_head != (8.0, 7.2)
        or compact_neck != (4.8, 4.8)
        or compact_receiver != (8.8, 8.0)
        or compact_chase != (10.4, 14.0)
        or compact_housing != (15.2, 18.8)
        or compact_head_z != standard_head
        or compact_full_head_z != standard_full_head
        or compact_transition_z != standard_transition
        or compact_neck_z != standard_neck
        or compact_chase_z != standard_chase_z
        or compact_lip_z != standard_lip_z
    ):
        raise ValueError("Pier compact gravity-keyhole family envelope drift")
    if any(
        abs(receiver - head - 2.0 * compact_clearance) > EPSILON
        for receiver, head in zip(compact_receiver, compact_head)
    ):
        raise ValueError("Pier compact gravity-keyhole fit clearance drift")
    if any(
        abs(outer - chase - 2.0 * compact_wall) > EPSILON
        for outer, chase in zip(compact_housing, compact_chase)
    ):
        raise ValueError("Pier compact gravity-keyhole housing wall drift")
    compact_union_volume = compact_neck[0] * compact_neck[1] * 0.02
    if abs(
        compact_union_volume
        - float(isolation["minimum_compact_pier_boss_neck_parent_union_volume_mm3"])
    ) > EPSILON:
        raise ValueError("Pier compact boss parent-union volume drift")

    family_maps = raw["per_ornament_family_access_map"]
    expected_access_families = {
        "through_carrier_left",
        "through_carrier_right",
        "return_carrier_left",
        "return_carrier_right",
        "pier_overlay",
    }
    if set(family_maps) != expected_access_families:
        raise ValueError("Oculus access map must cover four carriers and the pier overlay")
    attachment_maps = keyholes["per_parent_boss_placement_map"]
    expected_axes = {
        family_id: [
            [float(center[0]), 89.0]
            for center in attachment_maps[family_id][
                "carrier_local_receiver_centers_x_y_mm"
            ][:2]
        ]
        for family_id in _CARRIER_IDENTITIES
    }
    expected_axes["pier_overlay"] = [[2.8, 57.0], [31.6, 57.0]]
    for family_id, axes in expected_axes.items():
        if family_maps[family_id]["locked_cross_key_axes_local_x_y_mm"] != axes:
            raise ValueError(f"{family_id}: oculus axis map drift")
        if len(swept_oculi_for_family(cfg, family_id)) != 2:
            raise ValueError(f"{family_id}: exactly two decorative access oculi are required")

    for family_id in _CARRIER_IDENTITIES:
        actual_centers = tuple(
            tuple(float(value) for value in center)
            for center in _raw_maps(cfg)[family_id][
                "carrier_local_receiver_centers_x_y_mm"
            ]
        )
        derived_centers = derived_carrier_receiver_centers(cfg, family_id)
        if len(actual_centers) != len(derived_centers) or any(
            abs(actual - expected) > EPSILON
            for actual_center, expected_center in zip(
                actual_centers, derived_centers
            )
            for actual, expected in zip(actual_center, expected_center)
        ):
            raise ValueError(
                f"{family_id}: physical-local receivers no longer map to the unchanged parent bosses"
            )

    counts = raw["count_contract"]
    top = int(counts["top_cross_keys_per_level"])
    spring = int(counts["spring_cross_keys_per_level"])
    total = int(counts["total_cross_keys_per_level"])
    decorative = int(counts["decorative_oculi_per_level"])
    unused_terminal = int(counts["unused_terminal_mirror_oculi_per_level"])
    retention_counts = retention["object_count_contract"]
    if (top, spring, total) != (36, 18, 54) or top + spring != total:
        raise ValueError("Oculus count contract must service exactly 36 top plus 18 spring keys")
    if (
        top != int(retention_counts["cassette_top_keys_per_level"])
        or spring != int(retention_counts["spring_keys_per_level"])
        or total != int(retention_counts["total_keys_per_level"])
    ):
        raise ValueError("Oculus access count disagrees with the structural cross-key inventory")
    map_counts = {
        family: int(_raw_maps(cfg)[family]["installed_count_per_level"])
        for family in expected_access_families
    }
    computed_decorative = sum(
        map_counts[family] * len(swept_oculi_for_family(cfg, family))
        for family in expected_access_families
    )
    if computed_decorative != decorative or decorative - spring - top != unused_terminal:
        raise ValueError("Decorative oculus repeats do not equal the 54 used plus four terminal mirrors")

    standard_gravity_bosses = 0
    compact_gravity_bosses = 0
    loose_locators = 0
    for family_id, record in _raw_maps(cfg).items():
        repeats = int(record["installed_count_per_level"])
        for connector_type in connector_types_for_family(cfg, family_id):
            if connector_type == "gravity_keyhole":
                standard_gravity_bosses += repeats
            elif connector_type == "compact_gravity_keyhole":
                compact_gravity_bosses += repeats
            elif connector_type == "noncapturing_loose_locator":
                loose_locators += repeats
            else:
                raise ValueError(f"{family_id}: unknown attachment feature type")
    gravity_bosses = standard_gravity_bosses + compact_gravity_bosses
    integral = gravity_bosses + loose_locators
    feature_counts = raw["integral_attachment_feature_count_contract"]
    if (
        standard_gravity_bosses,
        compact_gravity_bosses,
        gravity_bosses,
        loose_locators,
        integral,
    ) != (66, 22, 88, 11, 99):
        raise ValueError(
            "Attachment topology must remain 66 standard plus 22 compact gravity bosses and 11 loose locators"
        )
    if (
        standard_gravity_bosses != int(feature_counts["standard_gravity_bosses_per_level"])
        or compact_gravity_bosses != int(feature_counts["compact_pier_gravity_bosses_per_level"])
        or gravity_bosses != int(feature_counts["gravity_bosses_per_level"])
        or loose_locators != int(feature_counts["loose_locators_per_level"])
        or integral != int(feature_counts["total_integral_features_per_level"])
        or integral != int(keyholes["boss_count_per_level"])
        or integral != int(isolation["parent_boss_feature_count_per_level"])
    ):
        raise ValueError("Integral ornament attachment feature counts disagree")

    minimum_clearance = float(raw["minimum_connector_housing_to_oculus_clearance_mm"])
    minimum_planar_web = float(raw["minimum_remaining_planar_web_mm"])
    minimum_pier_clearance = float(
        raw["minimum_pier_connector_housing_to_oculus_clearance_mm"]
    )
    minimum_pier_web = float(raw["minimum_pier_remaining_planar_web_mm"])
    if minimum_clearance + EPSILON < 2.4 or minimum_planar_web + EPSILON < 2.4:
        raise ValueError("Oculus repack may not reduce the 2.4 mm housing/web threshold")
    if minimum_pier_clearance + EPSILON < 3.2 or minimum_pier_web + EPSILON < 3.2:
        raise ValueError("Pier oculus repack may not reduce the 3.2 mm housing/web threshold")
    for family_id in expected_access_families:
        clearances = family_connector_to_oculus_clearances_mm(cfg, family_id)
        family_minimum = (
            minimum_pier_clearance if family_id == "pier_overlay" else minimum_clearance
        )
        if not clearances or min(clearances) + EPSILON < family_minimum:
            raise ValueError(
                f"{family_id}: connector housing enters the swept oculus keepout"
            )

    carrier_ids = expected_access_families - {"pier_overlay"}
    for family_id in carrier_ids:
        housings = connector_housing_footprints(cfg, family_id)
        cutters = connector_internal_cutter_footprints(cfg, family_id)
        # The vertically stacked B/C housings deliberately overlap to remain
        # one printable housing, while the internal chases retain a real wall.
        housing_overlap = float(housings[1].intersection(housings[2]).area)
        expected_overlap = 21.6 * 2.4
        if abs(housing_overlap - expected_overlap) > EPSILON:
            raise ValueError(f"{family_id}: two-storey outer housing overlap drift")
        if abs(float(cutters[1].distance(cutters[2])) - 2.4) > EPSILON:
            raise ValueError(f"{family_id}: two-storey chase separator is not 2.4 mm")

    pier_cutters = connector_internal_cutter_footprints(cfg, "pier_overlay")
    compact = keyholes["compact_pier_gravity_keyhole_contract"]
    compact_gap = float(pier_cutters[0].distance(pier_cutters[1]))
    if abs(compact_gap - float(compact["minimum_independent_chase_gap_mm"])) > EPSILON:
        raise ValueError("Pier compact keyhole chases are not independently separated")
    for compact_cutter in pier_cutters[:2]:
        gap = float(compact_cutter.distance(pier_cutters[2]))
        if gap + EPSILON < float(compact["minimum_chase_to_locator_slot_vertical_gap_mm"]):
            raise ValueError("Pier locator slot merges with a compact gravity chase")
    for record, label in (
        (keyholes, "ornament keyhole"),
        (raw, "ornament oculus"),
    ):
        if not bool(record["software_model_mapping_contract_required"]):
            raise ValueError(f"{label} source omits the software mapping contract")
        if bool(record["physical_installation_mapping_qualified"]):
            raise ValueError(f"{label} source claims unperformed physical qualification")
        if bool(record["production_release_eligible"]):
            raise ValueError(f"{label} source claims unearned production eligibility")

    return OrnamentAccessContract(
        radius_mm=radius,
        depth_zone_mm=depth_zone,
        run_extremes_mm=run_extremes,
        removal_drop_mm=drop,
        sweep_step_mm=step,
        top_cross_keys_per_level=top,
        spring_cross_keys_per_level=spring,
        total_cross_keys_per_level=total,
        decorative_oculi_per_level=decorative,
        unused_terminal_mirror_oculi_per_level=unused_terminal,
        standard_gravity_bosses_per_level=standard_gravity_bosses,
        compact_pier_gravity_bosses_per_level=compact_gravity_bosses,
        gravity_bosses_per_level=gravity_bosses,
        loose_locators_per_level=loose_locators,
        integral_attachment_features_per_level=integral,
        minimum_depth_isolation_mm=minimum_depth_isolation,
        minimum_connector_to_oculus_clearance_mm=minimum_clearance,
        minimum_remaining_planar_web_mm=minimum_planar_web,
        minimum_pier_connector_to_oculus_clearance_mm=minimum_pier_clearance,
        minimum_pier_remaining_planar_web_mm=minimum_pier_web,
        minimum_locked_handle_radial_clearance_mm=handle_radial_clearance,
        software_model_mapping_contract_required=True,
        physical_installation_mapping_qualified=False,
        production_release_eligible=False,
    )
