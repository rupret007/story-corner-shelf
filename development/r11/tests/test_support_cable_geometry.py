#!/usr/bin/env python3
"""Executable R11 support/cable qualification-geometry contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
import warnings

import numpy as np


R11_ROOT = Path(__file__).resolve().parents[1]
if str(R11_ROOT) not in sys.path:
    sys.path.insert(0, str(R11_ROOT))

import support_cable_geometry as geometry  # noqa: E402


class R11SupportCableGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            cls.parts = geometry.build_saved_outer_bay_support_cable_parts()
            cls.evidence = geometry.build_outer_bay_support_cable_evidence()

    def test_exact_ordered_provider_identity(self) -> None:
        self.assertEqual(
            geometry.OUTER_BAY_SUPPORT_CABLE_PART_ORDER,
            (
                "r11_first_wall_s0_fused_two_socket_support",
                "r11_first_wall_s1_ordinary_support",
                "r11_first_wall_socket_0_flush_blank",
                "r11_first_wall_socket_1_flush_blank",
                "r11_first_wall_multi_cable_comb_hook",
            ),
        )
        self.assertEqual(tuple(self.parts), geometry.OUTER_BAY_SUPPORT_CABLE_PART_ORDER)
        self.assertEqual(len(self.parts), 5)

    def test_support_straddles_station_and_exact_datums_are_distinguished(self) -> None:
        support = geometry.build_ordinary_support()
        np.testing.assert_allclose(
            support.bounds[:, 0], (-15.875, 15.875), atol=1e-5
        )
        np.testing.assert_allclose(
            support.extents, (31.75, 152.4, 168.75), atol=1e-5
        )
        self.assertEqual(geometry.STRUCTURAL_STRAP_HEIGHT_MM, 158.75)
        self.assertEqual(geometry.CAPTURE_LUG_CENTERS_X_MM, (-7.85, 7.85))
        wall = self.evidence["wall_connection_geometry"]
        self.assertEqual(wall["structural_strap_height_mm"], 158.75)
        self.assertEqual(wall["capture_lug_height_above_bearing_mm"], 10.0)
        self.assertEqual(wall["complete_installed_z_envelope_mm"], 168.75)

    def test_supports_are_new_r11_one_body_geometry_with_additive_ornament(self) -> None:
        structural = self.evidence["structural_contract"]
        self.assertEqual(structural["run_width_mm"], 31.75)
        self.assertEqual(structural["projection_mm"], 152.4)
        self.assertEqual(structural["central_diagonal_web_x_bounds_mm"], (-10.0, 10.0))
        self.assertEqual(structural["palatine_side_moulding_count"], 2)
        self.assertTrue(structural["palatine_mouldings_are_additive"])
        self.assertFalse(structural["palatine_mouldings_structural_credit"])
        for name in (geometry.S0_SUPPORT_PART, geometry.S1_SUPPORT_PART):
            with self.subTest(name=name):
                mesh = self.parts[name]
                self.assertEqual(len(mesh.split(only_watertight=False)), 1)
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_winding_consistent)
                self.assertGreater(float(mesh.volume), 0.0)
                self.assertTrue(np.isfinite(mesh.vertices).all())

    def test_three_actual_bores_and_full_solid_washer_lands(self) -> None:
        wall = self.evidence["wall_connection_geometry"]
        self.assertEqual(wall["wall_bore_count"], 3)
        self.assertEqual(wall["wall_bore_diameter_mm"], 7.0)
        self.assertEqual(
            wall["wall_bore_centers_installed_xz_mm"],
            ((0.0, -19.05), (0.0, -79.375), (0.0, -139.7)),
        )
        self.assertEqual(wall["washer_land_outer_diameter_mm"], 27.025)
        self.assertEqual(wall["washer_land_missing_material_mm3"], (0.0, 0.0, 0.0))
        self.assertFalse(wall["drilling_coordinates_released"])

    def test_s0_receiver_is_additive_only_and_clears_bores_and_lugs(self) -> None:
        core = geometry.build_ordinary_support()
        fused = geometry.build_s0_fused_two_socket_support()
        self.assertGreater(float(fused.volume), float(core.volume))
        preservation = self.evidence["core_preservation"]
        self.assertFalse(
            preservation["support_core_subtraction_for_cable_allowed"]
        )
        self.assertEqual(preservation["missing_structural_core_volume_mm3"], 0.0)
        self.assertTrue(preservation["preserved"])
        self.assertEqual(
            self.evidence["wall_connection_geometry"][
                "receiver_bore_intersection_mm3"
            ],
            (0.0, 0.0, 0.0),
        )
        self.assertEqual(geometry.RECEIVER_TO_LUG_SERVICE_GAP_MM, 8.0)

    def test_full_support_capture_lower_slide_settle_reverse_contract(self) -> None:
        capture = self.evidence["independent_capture_contract"]
        self.assertEqual(capture["lug_centers_x_mm"], (-7.85, 7.85))
        self.assertEqual(capture["lower_to_service_elevation_mm"], 2.0)
        self.assertEqual(capture["wallward_slide_mm"], 32.0)
        self.assertEqual(capture["gravity_settle_mm"], 2.0)
        self.assertEqual(capture["shared_release_component_count"], 0)
        self.assertTrue(capture["adjacent_bay_release_independent"])
        self.assertFalse(capture["keystone_receives_capture_credit"])
        path = capture["full_support_service_path"]
        for key in (
            "target_maximum_intersection_mm3",
            "lower_maximum_intersection_mm3",
            "wallward_slide_maximum_intersection_mm3",
            "gravity_settle_maximum_intersection_mm3",
            "exact_reverse_maximum_intersection_mm3",
        ):
            self.assertEqual(path[key], 0.0, key)
        self.assertGreater(path["forbidden_horizontal_reverse_intersection_mm3"], 90.0)
        self.assertTrue(path["all_service_samples_collision_free"])
        self.assertTrue(path["positive_reverse_stop"])
        self.assertTrue(path["full_s0_and_s1_support_meshes_exercised"])

    def test_exact_two_socket_point_four_clearance_and_eight_mm_service(self) -> None:
        cable = self.evidence["cable_contract"]
        self.assertEqual(cable["support_index"], 0)
        self.assertTrue(cable["receiver_fused_additive_only"])
        self.assertEqual(cable["socket_count"], 2)
        self.assertEqual(cable["socket_clearance_per_face_mm"], 0.4)
        self.assertEqual(cable["service_lift_drop_mm"], 8.0)
        self.assertEqual(cable["flush_blank_quantity"], 2)
        self.assertEqual(cable["comb_hook_quantity"], 1)
        self.assertEqual(cable["installed_socket_capacity"], 2)
        self.assertEqual(cable["interchangeable_spare_articles"], 1)
        self.assertEqual(len(cable["service_samples"]), 4)
        for sample in cable["service_samples"]:
            with self.subTest(
                module=sample["module"], station=sample["station_index"]
            ):
                self.assertEqual(sample["maximum_intersection_mm3"], 0.0)
                self.assertTrue(sample["collision_free"])
                self.assertTrue(sample["removal_is_exact_reverse"])

    def test_saved_orientation_is_support_off_and_a1_mini_safe(self) -> None:
        self.assertEqual(
            self.evidence["support_required_by_part"],
            {
                name: False
                for name in geometry.OUTER_BAY_SUPPORT_CABLE_PART_ORDER
            },
        )
        self.assertTrue(self.evidence["all_saved_layer_islands_clear"])
        for name, item in self.evidence["parts"].items():
            with self.subTest(name=name):
                self.assertFalse(item["support_required"])
                self.assertEqual(item["layer_connectivity"]["island_layer_indices"], ())
                self.assertGreater(
                    item["layer_connectivity"]["first_layer_contact_area_mm2"],
                    40.0,
                )
                self.assertTrue(item["print_envelope"]["fits"])
                required = item["print_envelope"]["required_build_volume_mm"]
                self.assertTrue(all(value <= 180.0 for value in required))

    def test_two_blank_ids_may_share_geometry_but_comb_is_distinct(self) -> None:
        first = self.parts[geometry.BLANK_0_PART]
        second = self.parts[geometry.BLANK_1_PART]
        np.testing.assert_allclose(first.vertices, second.vertices, atol=0.0)
        np.testing.assert_array_equal(first.faces, second.faces)
        comb = self.parts[geometry.COMB_PART]
        self.assertGreater(float(comb.volume), float(first.volume))
        self.assertGreater(float(comb.extents[2]), float(first.extents[2]))

    def test_geometry_subset_passes_but_every_external_gate_stays_closed(self) -> None:
        self.assertTrue(self.evidence["geometry_subset_passed"])
        self.assertEqual(self.evidence["subset_analytic_blockers"], ())
        self.assertTrue(self.evidence["subset_physical_and_field_blockers"])
        self.assertFalse(self.evidence["passed"])
        boundary = self.evidence["zero_rating_and_authorization"]
        self.assertEqual((boundary["rated_load_kg"], boundary["rated_load_lb"]), (0.0, 0.0))
        for key in (
            "print_authorized",
            "wall_installation_authorized",
            "drilling_coordinates_released",
            "test_load_authorized",
            "production_ready",
        ):
            self.assertFalse(boundary[key], key)
        self.assertFalse(self.evidence["cable_contract"]["structural_credit"])
        json.dumps(self.evidence, allow_nan=False, sort_keys=True)

    def test_invalid_service_station_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            geometry.R11SupportCableGeometryError, "station must be 0 or 1"
        ):
            geometry._installed_module(
                comb_hook=False, station_index=2
            )


if __name__ == "__main__":
    unittest.main()
