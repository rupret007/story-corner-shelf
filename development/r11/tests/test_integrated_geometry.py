#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
import warnings

import numpy as np
from shapely.geometry import Polygon


R11_ROOT = Path(__file__).resolve().parents[1]
if str(R11_ROOT) not in sys.path:
    sys.path.insert(0, str(R11_ROOT))

import integrated_geometry as geometry  # noqa: E402


class R11IntegratedGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            cls.regular_saved = geometry.build_saved_regular_bay_parts()
            cls.terminal_saved = geometry.build_saved_terminal_bay_parts()
            cls.regular_evidence = geometry.build_regular_bay_evidence()
            cls.terminal_evidence = geometry.build_terminal_bay_evidence()
            cls.outer_evidence = geometry.build_outer_terminal_bay_evidence()

    def test_exact_regular_terminal_and_overlap_arithmetic(self) -> None:
        self.assertEqual(geometry.REGULAR_CLEAR_SPAN_MM, 253.65)
        self.assertEqual(geometry.REGULAR_CORE_LENGTH_MM, 126.65)
        self.assertEqual(geometry.REGULAR_MODULE_LENGTH_MM, 154.325)
        self.assertEqual(geometry.TERMINAL_CLEAR_SPAN_MM, 269.35)
        self.assertEqual(geometry.TERMINAL_CORE_LENGTH_MM, 134.5)
        self.assertEqual(geometry.TERMINAL_MODULE_LENGTH_MM, 162.175)
        self.assertEqual(geometry.TONGUE_PROJECTION_MM, 27.675)
        self.assertEqual(geometry.INCOMING_ENGAGEMENT_MM, 27.325)
        self.assertAlmostEqual(
            2.0 * geometry.REGULAR_MODULE_LENGTH_MM
            - geometry.REGULAR_CLEAR_SPAN_MM,
            55.0,
            places=9,
        )
        self.assertAlmostEqual(
            2.0 * geometry.TERMINAL_MODULE_LENGTH_MM
            - geometry.TERMINAL_CLEAR_SPAN_MM,
            55.0,
            places=9,
        )
        self.assertEqual(self.regular_evidence.physical_overlap_mm, 55.0)
        self.assertEqual(self.terminal_evidence.physical_overlap_mm, 55.0)

    def test_end_bays_use_four_terminal_halves_and_close(self) -> None:
        inventory = geometry.field_inventory_evidence()
        self.assertEqual(
            geometry.FIELD_BAY_KINDS,
            ("terminal", "regular", "regular", "regular", "regular", "terminal"),
        )
        self.assertEqual(inventory.terminal_half_decks, 4)
        self.assertEqual(inventory.regular_half_decks, 8)
        self.assertEqual(inventory.total_half_decks, 12)
        self.assertTrue(inventory.first_and_last_bays_use_two_terminal_halves_each)
        self.assertEqual(
            2.0 * geometry.TERMINAL_MODULE_LENGTH_MM
            - geometry.INTEGRATED_OVERLAP_MM,
            geometry.TERMINAL_CLEAR_SPAN_MM,
        )
        # The rejected one-terminal/one-regular combination is exactly one
        # 7.85 mm terminal extension short of the required end-bay span.
        mixed_span = (
            geometry.TERMINAL_MODULE_LENGTH_MM
            + geometry.REGULAR_MODULE_LENGTH_MM
            - geometry.INTEGRATED_OVERLAP_MM
        )
        self.assertEqual(mixed_span, 261.5)
        self.assertAlmostEqual(
            geometry.TERMINAL_CLEAR_SPAN_MM - mixed_span,
            geometry.TERMINAL_EXTENSION_MM,
            places=9,
        )

    def test_exact_28_article_kit_and_27_active_inventory(self) -> None:
        inventory = geometry.field_inventory_evidence()
        self.assertEqual(inventory.supports, 7)
        self.assertEqual(inventory.palatine_keystones, 6)
        self.assertEqual(inventory.cable_modules, 3)
        self.assertEqual(inventory.total_candidate_articles, 28)
        self.assertEqual(inventory.maximum_simultaneously_installed_articles, 27)
        self.assertEqual(inventory.interchangeable_cable_spare_articles, 1)
        self.assertEqual(inventory.safe_unbatched_print_starts, 28)
        self.assertEqual(inventory.target_batched_print_starts, 21)
        self.assertFalse(inventory.target_batched_plate_nesting_verified)
        self.assertIsNone(inventory.verified_production_print_starts)
        self.assertTrue(inventory.no_loose_logs)
        self.assertTrue(inventory.no_log_retainers)
        self.assertTrue(inventory.no_support_keys)
        self.assertFalse(hasattr(geometry, "build_splice_log"))
        self.assertFalse(hasattr(geometry, "build_log_retainer"))
        self.assertFalse(hasattr(geometry, "build_support_key"))

    def test_every_authored_article_is_one_watertight_positive_body(self) -> None:
        meshes = {
            **{f"regular_{key}": value for key, value in self.regular_saved.items()},
            **{f"terminal_{key}": value for key, value in self.terminal_saved.items()},
            "capture_lug": geometry.build_capture_lug_interface_fixture(
                center_x_mm=geometry.CAPTURE_LUG_CENTER_X_MM
            ),
        }
        for name, mesh in meshes.items():
            with self.subTest(name=name):
                self.assertEqual(len(mesh.split(only_watertight=False)), 1)
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_winding_consistent)
                self.assertGreater(float(mesh.volume), 0.0)
                self.assertTrue(np.isfinite(mesh.vertices).all())
                if name != "capture_lug":
                    np.testing.assert_allclose(
                        mesh.bounds[0], (0.0, 0.0, 0.0), atol=1e-5
                    )
                else:
                    self.assertAlmostEqual(float(mesh.bounds[0, 2]), 0.0, places=6)

    def test_actual_half_deck_envelopes_fit_one_per_a1_mini_plate(self) -> None:
        regular = geometry.print_envelope(
            self.regular_saved["r11_regular_bay_left_integrated_half_deck"]
        )
        terminal = geometry.print_envelope(
            self.terminal_saved["r11_terminal_bay_left_integrated_half_deck"]
        )
        self.assertEqual(geometry.XY_PROCESS_ALLOWANCE_MM, 14.2)
        self.assertEqual(regular.raw_part_mm, (154.325, 152.4, 32.0))
        self.assertEqual(regular.required_build_volume_mm, (168.525, 166.6, 32.0))
        self.assertEqual(terminal.raw_part_mm, (162.175, 152.4, 32.0))
        self.assertEqual(terminal.required_build_volume_mm, (176.375, 166.6, 32.0))
        self.assertEqual(terminal.minimum_xy_spare_mm, 3.625)
        self.assertTrue(regular.fits)
        self.assertTrue(terminal.fits)
        self.assertEqual(
            self.outer_evidence["parts"][
                "r11_bay0_left_terminal_integrated_half_deck"
            ]["saved_orientation"],
            "complete_top_datum_on_plate_one_half_deck_per_plate",
        )

    def test_three_full_height_reciprocal_lanes_exist_in_actual_mesh(self) -> None:
        mesh = geometry.build_regular_half_deck(hand="left")
        section = mesh.section(
            plane_origin=(geometry.REGULAR_MODULE_LENGTH_MM - 1.0, 0.0, 0.0),
            plane_normal=(1.0, 0.0, 0.0),
        )
        self.assertIsNotNone(section)
        areas = sorted(
            Polygon(np.asarray(loop)[:, 1:3]).area for loop in section.discrete
        )
        self.assertEqual(len(areas), 3)
        for area in areas:
            self.assertAlmostEqual(
                area,
                geometry.LAP_LANE_WIDTH_MM * geometry.SHELF_TOTAL_HEIGHT_MM,
                places=3,
            )
        self.assertEqual(geometry.RIB_STATIONS_Y_MM, (16.0, 76.2, 136.4))
        self.assertEqual(geometry.JOINT_CLEARANCE_PER_FACE_MM, 0.4)
        self.assertEqual(geometry.LAP_CENTER_GAP_MM, 0.8)

    def test_net_rib_section_exceeds_frozen_geometry_targets(self) -> None:
        section = geometry.rib_section_evidence()
        self.assertEqual(section.net_lane_width_mm, 9.6)
        self.assertEqual(section.height_mm, 32.0)
        self.assertAlmostEqual(section.net_second_moment_mm4, 26214.4, places=6)
        self.assertAlmostEqual(section.net_section_modulus_mm3, 1638.4, places=6)
        self.assertGreaterEqual(
            section.net_second_moment_mm4, geometry.NET_RIB_I_TARGET_MM4
        )
        self.assertGreaterEqual(
            section.net_section_modulus_mm3, geometry.NET_RIB_Z_TARGET_MM3
        )
        self.assertEqual(section.minimum_required_second_moment_mm4, 8263.957)
        self.assertEqual(section.minimum_required_section_modulus_mm3, 949.016)
        self.assertTrue(section.geometry_targets_pass)
        self.assertFalse(section.material_capacity_claimed)

    def test_two_uninterrupted_ribs_prove_exact_15p7_bearing_length(self) -> None:
        half = geometry.build_regular_half_deck(hand="left")
        expected_probe_volume = (
            geometry.SUPPORT_BEARING_LENGTH_MM * geometry.RIB_WIDTH_MM * 0.5
        )
        for station in (76.2, 136.4):
            with self.subTest(station=station):
                probe = geometry._box(
                    (geometry.SUPPORT_BEARING_LENGTH_MM, geometry.RIB_WIDTH_MM, 0.5),
                    (0.0, station - geometry.RIB_WIDTH_MM / 2.0, 0.0),
                )
                contact = geometry._intersection_volume(half, probe)
                self.assertAlmostEqual(contact, expected_probe_volume, places=3)
        self.assertEqual(
            self.regular_evidence.minimum_support_bearing_length_mm, 15.70
        )

    def test_target_join_wedge_drop_slide_settle_and_reverse_are_clear(self) -> None:
        for kind, evidence in (
            ("regular", self.regular_evidence.assembly),
            ("terminal", self.terminal_evidence.assembly),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(evidence.target_maximum_intersection_mm3, 0.0)
                self.assertEqual(evidence.midpoint_join_maximum_intersection_mm3, 0.0)
                self.assertEqual(evidence.keystone_insert_maximum_intersection_mm3, 0.0)
                self.assertEqual(evidence.capture_drop_maximum_intersection_mm3, 0.0)
                self.assertEqual(
                    evidence.capture_wallward_slide_maximum_intersection_mm3, 0.0
                )
                self.assertEqual(evidence.capture_settle_maximum_intersection_mm3, 0.0)
                self.assertEqual(evidence.exact_reverse_maximum_intersection_mm3, 0.0)
                self.assertTrue(evidence.all_authored_service_paths_collision_free)
                self.assertTrue(evidence.midpoint_join_precedes_capture)

    def test_gravity_settled_support_stop_is_positive_and_not_the_keystone(self) -> None:
        evidence = self.regular_evidence.assembly
        self.assertEqual(geometry.CAPTURE_WALLWARD_SLIDE_MM, 32.0)
        self.assertEqual(geometry.CAPTURE_SLIDE_ELEVATION_MM, 2.0)
        self.assertEqual(geometry.CAPTURE_REVERSE_SHOULDER_Z_MM, 8.4)
        self.assertGreater(evidence.blocked_reverse_slide_intersection_mm3, 90.0)
        self.assertTrue(evidence.positive_no_friction_reverse_stop)
        self.assertIn("half-to-half", evidence.keystone_role)
        self.assertIn("no gravity", evidence.keystone_role)
        self.assertIn("two remote bay-owned", evidence.support_capture_role)

        # Remove the keystone entirely and repeat the forbidden horizontal
        # reverse attempt.  The remote support shoulders still block it.
        parts = geometry.build_installed_regular_bay_parts()
        halves = (
            parts["r11_regular_bay_left_integrated_half_deck"],
            parts["r11_regular_bay_right_integrated_half_deck"],
        )
        lugs = geometry._installed_capture_lugs("regular")
        attempted = geometry._translated_group(halves, (0.0, 8.0, 0.0))
        self.assertGreater(
            geometry._moving_fixed_maximum(attempted, lugs),
            90.0,
        )

    def test_neighboring_bays_have_independent_lugs_and_no_shared_release(self) -> None:
        evidence = geometry.adjacent_capture_evidence()
        self.assertEqual(evidence.support_run_width_mm, 31.75)
        self.assertEqual(
            evidence.bay_owned_lug_centers_from_support_line_mm, (-7.85, 7.85)
        )
        self.assertEqual(evidence.lug_head_width_mm, 8.0)
        self.assertAlmostEqual(evidence.clear_gap_between_lug_heads_mm, 7.7, places=9)
        self.assertTrue(evidence.each_lug_inside_its_support_half_land)
        self.assertFalse(evidence.current_bay_service_motion_changes_x)
        self.assertEqual(evidence.shared_release_component_count, 0)
        self.assertTrue(evidence.adjacent_bay_release_independent)

    def test_all_saved_layers_are_anchored_and_support_off(self) -> None:
        meshes = {
            **self.regular_saved,
            **self.terminal_saved,
        }
        for name, mesh in meshes.items():
            with self.subTest(name=name):
                report = geometry.saved_layer_connectivity_report(mesh)
                self.assertEqual(report.island_layer_indices, ())
                self.assertFalse(report.support_required)
                self.assertGreater(report.first_layer_contact_area_mm2, 300.0)
        self.assertTrue(self.outer_evidence["all_saved_layer_islands_clear"])
        self.assertEqual(
            self.outer_evidence["support_required_by_part"],
            {name: False for name in geometry.OUTER_TERMINAL_BAY_PART_ORDER},
        )

    def test_outer_terminal_subset_contract_is_ordered_json_safe_and_fail_closed(self) -> None:
        parts = geometry.build_saved_outer_terminal_bay_parts()
        self.assertEqual(tuple(parts), geometry.OUTER_TERMINAL_BAY_PART_ORDER)
        self.assertEqual(
            tuple(parts),
            (
                "r11_bay0_left_terminal_integrated_half_deck",
                "r11_bay0_right_terminal_integrated_half_deck",
                "r11_bay0_positive_keystone",
            ),
        )
        evidence = self.outer_evidence
        self.assertTrue(evidence["geometry_subset_passed"])
        self.assertEqual(evidence["subset_analytic_blockers"], ())
        self.assertFalse(evidence["passed"])
        self.assertTrue(evidence["analytic_blockers"])
        self.assertTrue(evidence["physical_blockers"])
        self.assertIn("support", " ".join(evidence["analytic_blockers"]))
        self.assertIn("cable", " ".join(evidence["analytic_blockers"]))
        self.assertEqual(evidence["zero_rating"]["rated_load_kg"], 0.0)
        self.assertFalse(evidence["zero_rating"]["wall_installation_authorized"])
        json.dumps(evidence, sort_keys=True)

    def test_s0_fused_receiver_provenance_does_not_fabricate_missing_meshes(self) -> None:
        provenance = geometry.S0_CABLE_RECEIVER_PROVENANCE
        self.assertEqual(provenance["support_index"], 0)
        self.assertTrue(provenance["receiver_is_fused_into_support"])
        self.assertFalse(provenance["receiver_mesh_authored_in_this_module"])
        self.assertEqual(provenance["separate_cable_modules_required"], 3)
        self.assertEqual(
            provenance["separate_module_roles"],
            ("flush_blank_0", "flush_blank_1", "comb_hook"),
        )
        self.assertFalse(provenance["capacity_credit"])

    def test_geometry_is_deterministic_and_invalid_requests_fail_closed(self) -> None:
        first = geometry.build_terminal_half_deck(hand="left")
        second = geometry.build_terminal_half_deck(hand="left")
        np.testing.assert_array_equal(first.faces, second.faces)
        np.testing.assert_allclose(first.vertices, second.vertices, atol=0.0)
        with self.assertRaisesRegex(geometry.R11GeometryError, "hand"):
            geometry.build_regular_half_deck(hand="center")
        with self.assertRaisesRegex(geometry.R11GeometryError, "kind"):
            geometry.build_assembly_path_evidence("guessed")
        self.assertTrue(geometry.QUALIFICATION_ONLY)
        self.assertFalse(geometry.PRODUCTION_READY)
        self.assertFalse(geometry.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertFalse(geometry.WALL_INSTALLATION_AUTHORIZED)
        self.assertEqual((geometry.RATED_LOAD_KG, geometry.RATED_LOAD_LB), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
