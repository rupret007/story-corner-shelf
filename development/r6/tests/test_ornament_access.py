#!/usr/bin/env python3
"""Exact full-depth oculus and ornament-attachment service regressions."""

from __future__ import annotations

import copy
import json
import math
import sys
import unittest
import warnings
from pathlib import Path

import trimesh
from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.geometry import box as shapely_box
from shapely.ops import unary_union


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from ornament_access import (  # noqa: E402
    carrier_coordinate_contract,
    connector_housing_footprints,
    connector_internal_cutter_footprints,
    derived_carrier_receiver_centers,
    family_connector_to_oculus_clearances_mm,
    ornament_access_contract,
    swept_oculi_for_family,
)
from ornament_geometry import (  # noqa: E402
    _arch_opening_profile,
    _extrude,
    _gravity_aperture,
    build_ornament_families,
    compact_pier_gravity_keyhole_boss_mesh,
    gravity_keyhole_boss_mesh,
    noncapturing_loose_locator_post_mesh,
)


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    output: dict = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key {key!r}")
        output[key] = value
    return output


class R6OrnamentAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(
            (R6 / "config.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
        cls.contract = ornament_access_contract(cls.cfg)
        cls.families = build_ornament_families(cls.cfg)

    def test_exact_54_key_service_and_88_plus_11_attachment_topology(self) -> None:
        contract = self.contract
        self.assertEqual(
            (
                contract.top_cross_keys_per_level,
                contract.spring_cross_keys_per_level,
                contract.total_cross_keys_per_level,
            ),
            (36, 18, 54),
        )
        self.assertEqual(
            (
                contract.decorative_oculi_per_level,
                contract.unused_terminal_mirror_oculi_per_level,
            ),
            (58, 4),
        )
        self.assertEqual(
            (
                contract.standard_gravity_bosses_per_level,
                contract.compact_pier_gravity_bosses_per_level,
                contract.gravity_bosses_per_level,
                contract.loose_locators_per_level,
                contract.integral_attachment_features_per_level,
            ),
            (66, 22, 88, 11, 99),
        )
        self.assertAlmostEqual(
            contract.minimum_locked_handle_radial_clearance_mm, 3.6
        )
        self.assertTrue(contract.software_model_mapping_contract_required)
        self.assertFalse(contract.physical_installation_mapping_qualified)
        self.assertFalse(contract.production_release_eligible)

    def test_oculi_are_exact_swept_capsules_not_static_installed_circles(self) -> None:
        through = swept_oculi_for_family(self.cfg, "through_carrier_left")[0]
        pier = swept_oculi_for_family(self.cfg, "pier_overlay")[0]
        self.assertEqual(through.centerline_y_mm, (83.0, 89.0))
        for actual, expected in zip(
            through.centerline_x_mm, (69.8925, 71.0925)
        ):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(
            through.bounds_xy_mm, (56.6925, 69.8, 84.2925, 102.2)
        ):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(pier.centerline_y_mm, (51.0, 57.0))
        for actual, expected in zip(pier.centerline_x_mm, (2.2, 3.4)):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(
            pier.bounds_xy_mm, (-11.0, 37.8, 16.6, 70.2)
        ):
            self.assertAlmostEqual(actual, expected)

        # Every 0.4 mm drop state and both +/-0.6 mm run extremes carries the
        # complete radius-13.2 service disk, not merely its center point.
        for oculus in (through, pier):
            profile = oculus.profile()
            for run_offset in (-0.6, 0.6):
                for index in range(16):
                    drop = 0.4 * index
                    center_x = oculus.locked_center_x_mm + run_offset
                    center_y = oculus.locked_center_y_mm - drop
                    for angle_index in range(72):
                        angle = 2.0 * math.pi * angle_index / 72.0
                        probe = Point(
                            center_x + (oculus.radius_mm - 0.001) * math.cos(angle),
                            center_y + (oculus.radius_mm - 0.001) * math.sin(angle),
                        )
                        self.assertTrue(profile.covers(probe), oculus.access_id)

    def test_every_access_is_carved_through_all_d_0_to_10_2_solid(self) -> None:
        self.assertEqual(self.contract.depth_zone_mm, (0.0, 10.2))
        self.assertEqual(self.contract.minimum_depth_isolation_mm, 3.0)
        access_families = (
            "through_carrier_left",
            "through_carrier_right",
            "return_carrier_left",
            "return_carrier_right",
            "pier_overlay",
        )
        allowed = float(
            self.cfg["palatine"]["ornament_keyhole_contract"]
            ["strict_collision_gate"]["allowed_solid_overlap_mm3"]
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for family_id in access_families:
                mesh = self.families[family_id].mesh
                for oculus in swept_oculi_for_family(self.cfg, family_id):
                    # Stay 0.001 mm inside both authored depth faces so a
                    # coplanar triangle is never mistaken for opaque material.
                    cutter = _extrude(oculus.profile(), 0.001, 10.198)
                    overlap = trimesh.boolean.intersection(
                        [mesh, cutter], engine="manifold", check_volume=True
                    )
                    overlap_volume = 0.0 if overlap is None else abs(float(overlap.volume))
                    self.assertLessEqual(overlap_volume, allowed, oculus.access_id)

    def test_repacked_housings_preserve_clearance_and_actual_planar_necks(self) -> None:
        carrier_ids = (
            "through_carrier_left",
            "through_carrier_right",
            "return_carrier_left",
            "return_carrier_right",
        )
        for family_id in carrier_ids:
            clearances = family_connector_to_oculus_clearances_mm(
                self.cfg, family_id
            )
            self.assertGreaterEqual(min(clearances), 4.0 - 1.0e-7)

            coordinate = carrier_coordinate_contract(self.cfg, family_id)
            hand = coordinate.hand
            width = coordinate.physical_width_mm
            base = shapely_box(0.0, 0.0, width, 108.0).difference(
                _arch_opening_profile(
                    width,
                    2.0 * coordinate.nominal_half_span_mm,
                    92.0,
                    14.0,
                    nominal_x_offset_mm=coordinate.inset_each_nominal_end_mm,
                )
            )
            if hand == "left":
                base = affinity.scale(
                    base, xfact=-1.0, yfact=1.0, origin=(width / 2.0, 0.0)
                )
            section = unary_union(
                [base, *connector_housing_footprints(self.cfg, family_id)]
            ).difference(
                unary_union(
                    [
                        oculus.profile()
                        for oculus in swept_oculi_for_family(self.cfg, family_id)
                    ]
                )
            )
            eroded = section.buffer(-1.2, join_style=1)
            self.assertEqual(eroded.geom_type, "Polygon", family_id)
            self.assertFalse(eroded.is_empty, family_id)

            cutters = connector_internal_cutter_footprints(self.cfg, family_id)
            self.assertAlmostEqual(cutters[1].distance(cutters[2]), 2.4)

        pier_id = "pier_overlay"
        pier_clearances = family_connector_to_oculus_clearances_mm(
            self.cfg, pier_id
        )
        self.assertGreaterEqual(min(pier_clearances), 3.2 - 1.0e-7)
        pier_base = Polygon(
            [(0.0, 0.0), (34.4, 0.0), (31.2, 59.6), (3.2, 59.6)]
        )
        pier_section = unary_union(
            [pier_base, *connector_housing_footprints(self.cfg, pier_id)]
        ).difference(
            unary_union(
                [
                    oculus.profile()
                    for oculus in swept_oculi_for_family(self.cfg, pier_id)
                ]
            )
        )
        pier_eroded = pier_section.buffer(-1.6, join_style=1)
        self.assertEqual(pier_eroded.geom_type, "Polygon")
        self.assertFalse(pier_eroded.is_empty)
        pier_cutters = connector_internal_cutter_footprints(self.cfg, pier_id)
        self.assertAlmostEqual(pier_cutters[0].distance(pier_cutters[1]), 6.4)
        self.assertAlmostEqual(pier_cutters[0].distance(pier_cutters[2]), 3.4)
        self.assertAlmostEqual(pier_cutters[1].distance(pier_cutters[2]), 3.4)

    def test_receiver_apertures_are_exact_rectangular_head_plus_swept_neck_slots(self) -> None:
        standard_fixed = _gravity_aperture(
            0.0, 0.0, 12.0, 9.6, 7.2, 7.2, 6.0, 0.4
        )
        expected_standard_fixed = unary_union(
            [
                shapely_box(-6.4, -8.2, 6.4, 2.2),
                shapely_box(-4.0, -7.0, 4.0, 7.0),
            ]
        )
        self.assertLess(standard_fixed.symmetric_difference(expected_standard_fixed).area, 1.0e-9)

        standard_elongated = _gravity_aperture(
            0.0, 0.0, 12.0, 9.6, 7.2, 7.2, 6.0, 0.4, 1.2
        )
        expected_standard_elongated = unary_union(
            [
                shapely_box(-7.0, -8.2, 7.0, 2.2),
                shapely_box(-4.6, -7.0, 4.6, 7.0),
            ]
        )
        self.assertLess(
            standard_elongated.symmetric_difference(expected_standard_elongated).area,
            1.0e-9,
        )

        compact_elongated = _gravity_aperture(
            0.0, 0.0, 8.0, 7.2, 4.8, 4.8, 6.0, 0.4, 1.2
        )
        expected_compact_elongated = unary_union(
            [
                shapely_box(-5.0, -7.0, 5.0, 1.0),
                shapely_box(-3.4, -5.8, 3.4, 5.8),
            ]
        )
        self.assertLess(
            compact_elongated.symmetric_difference(expected_compact_elongated).area,
            1.0e-9,
        )

    @staticmethod
    def _solid_overlap_volume_mm3(
        removable: trimesh.Trimesh, parent_feature: trimesh.Trimesh
    ) -> float:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            overlap = trimesh.boolean.intersection(
                [removable, parent_feature],
                engine="manifold",
                check_volume=True,
            )
            return 0.0 if overlap is None else abs(float(overlap.volume))

    def test_actual_solids_clear_full_axial_insertion_gravity_drop_and_run_sweeps(self) -> None:
        keyholes = self.cfg["palatine"]["ornament_keyhole_contract"]
        mapping = keyholes["per_parent_boss_placement_map"]
        gate = keyholes["strict_collision_gate"]
        allowed = float(gate["allowed_solid_overlap_mm3"])
        axial_step = float(gate["axial_insertion_sweep_step_mm"])
        axial_total = float(gate["axial_insertion_sweep_total_mm"])
        drop_step = float(gate["gravity_sweep_step_mm"])
        drop_total = float(gate["gravity_sweep_total_mm"])
        run_extremes = tuple(float(value) for value in gate["elongated_receiver_extremes_mm"])
        self.assertEqual((axial_step, axial_total, drop_step, drop_total), (0.4, 4.4, 0.4, 6.0))

        for family_id, record in mapping.items():
            removable = self.families[family_id].mesh
            centers = record["carrier_local_receiver_centers_x_y_mm"]
            connector_types = record["attachment_feature_types"]
            for connector_index, (center, connector_type) in enumerate(
                zip(centers, connector_types), start=1
            ):
                center_x, center_y = (float(value) for value in center)
                if connector_type == "noncapturing_loose_locator":
                    run_offsets = (0.0,)
                    axial_total_for_feature = 2.4
                    boss_factory = lambda x, y: noncapturing_loose_locator_post_mesh(
                        self.cfg, x, y
                    )
                else:
                    run_offsets = (*run_extremes, 0.0) if connector_index in (1, 2) else (0.0,)
                    axial_total_for_feature = axial_total
                    if connector_type == "gravity_keyhole":
                        boss_factory = gravity_keyhole_boss_mesh
                    elif connector_type == "compact_gravity_keyhole":
                        boss_factory = lambda x, y: compact_pier_gravity_keyhole_boss_mesh(
                            self.cfg, x, y
                        )
                    else:
                        self.fail(f"{family_id}: unknown connector {connector_type!r}")

                entry_y = center_y - drop_total / 2.0
                axial_states = int(round(axial_total_for_feature / axial_step))
                for run_offset in run_offsets:
                    for axial_index in range(axial_states + 1):
                        depth_offset = axial_total_for_feature - axial_step * axial_index
                        parent_feature = boss_factory(center_x + run_offset, entry_y)
                        parent_feature.apply_translation((0.0, 0.0, depth_offset))
                        overlap = self._solid_overlap_volume_mm3(
                            removable, parent_feature
                        )
                        self.assertLessEqual(
                            overlap,
                            allowed,
                            f"{family_id} connector {connector_index} axial "
                            f"d={depth_offset:.1f} x={run_offset:+.1f}",
                        )

                    drop_states = int(round(drop_total / drop_step))
                    for drop_index in range(drop_states + 1):
                        parent_feature = boss_factory(
                            center_x + run_offset,
                            entry_y + drop_step * drop_index,
                        )
                        overlap = self._solid_overlap_volume_mm3(
                            removable, parent_feature
                        )
                        self.assertLessEqual(
                            overlap,
                            allowed,
                            f"{family_id} connector {connector_index} drop "
                            f"y={drop_step * drop_index:.1f} x={run_offset:+.1f}",
                        )

    def test_parent_maps_coupons_and_saved_orientations_remain_fail_closed(self) -> None:
        keyholes = self.cfg["palatine"]["ornament_keyhole_contract"]
        mapping = keyholes["per_parent_boss_placement_map"]
        pier = mapping["pier_overlay"]
        self.assertEqual(
            pier["attachment_feature_types"],
            [
                "compact_gravity_keyhole",
                "compact_gravity_keyhole",
                "noncapturing_loose_locator",
            ],
        )
        self.assertEqual(
            pier["locked_boss_centers_parent_local_run_e_mm"],
            [[-8.4, 12.4], [8.4, 12.4]],
        )
        self.assertEqual(
            pier["locked_locator_center_parent_local_run_e_mm"], [0.0, 29.8]
        )
        for family_id in (
            "through_carrier_left",
            "through_carrier_right",
            "return_carrier_left",
            "return_carrier_right",
        ):
            self.assertEqual(
                mapping[family_id]["carrier_local_receiver_centers_x_y_mm"],
                [
                    list(center)
                    for center in derived_carrier_receiver_centers(
                        self.cfg, family_id
                    )
                ],
            )
        for family_id, record in mapping.items():
            self.assertIn("orientation", record["actual_parent_coupon"], family_id)
            self.assertTrue(record["parent_saved_orientation"], family_id)
        access = keyholes["cross_key_oculus_access_contract"]
        self.assertIn("actual-parent", access["actual_parent_coupon_gate"])
        self.assertTrue(access["software_model_mapping_contract_required"])
        self.assertFalse(access["physical_installation_mapping_qualified"])
        self.assertFalse(access["production_release_eligible"])
        self.assertTrue(keyholes["software_model_mapping_contract_required"])
        self.assertFalse(keyholes["physical_installation_mapping_qualified"])
        self.assertFalse(keyholes["production_release_eligible"])

    def test_contract_fails_closed_on_static_shallow_close_or_self_release(self) -> None:
        static = copy.deepcopy(self.cfg)
        static["palatine"]["ornament_keyhole_contract"][
            "cross_key_oculus_access_contract"
        ]["run_sweep_extremes_mm"] = [0.0, 0.0]
        with self.assertRaises(ValueError):
            ornament_access_contract(static)

        shallow = copy.deepcopy(self.cfg)
        shallow["palatine"]["ornament_keyhole_contract"][
            "cross_key_oculus_access_contract"
        ]["cutter_depth_zone_mm"] = [0.0, 3.2]
        with self.assertRaises(ValueError):
            ornament_access_contract(shallow)

        close = copy.deepcopy(self.cfg)
        close["palatine"]["ornament_keyhole_contract"][
            "per_parent_boss_placement_map"
        ]["pier_overlay"]["carrier_local_receiver_centers_x_y_mm"][2][1] = 30.0
        with self.assertRaises(ValueError):
            ornament_access_contract(close)

        self_release = copy.deepcopy(self.cfg)
        self_release["palatine"]["ornament_keyhole_contract"][
            "cross_key_oculus_access_contract"
        ]["production_release_eligible"] = True
        with self.assertRaises(ValueError):
            ornament_access_contract(self_release)


if __name__ == "__main__":
    unittest.main(verbosity=2)
