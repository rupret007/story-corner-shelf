#!/usr/bin/env python3
"""Executable geometry contract for the R10 printed Lincoln-log candidate."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


R10_ROOT = Path(__file__).resolve().parents[1]
R9_ROOT = R10_ROOT.parent / "r9"
for path in (R10_ROOT, R9_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import lincoln_geometry as geometry  # noqa: E402
import cable_geometry  # noqa: E402
import capacity_study  # noqa: E402


class R10LincolnGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = geometry.build_one_bay_evidence()
        cls.saved = geometry.build_saved_one_bay_parts()
        cls.terminals = geometry.build_saved_terminal_halves()

    def test_fail_closed_boundary_and_geometry_blockers_closed(self) -> None:
        self.assertTrue(geometry.QUALIFICATION_ONLY)
        self.assertFalse(geometry.PRODUCTION_READY)
        self.assertFalse(geometry.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertFalse(geometry.WALL_INSTALLATION_AUTHORIZED)
        self.assertEqual(geometry.RATED_LOAD_KG, 0.0)
        self.assertEqual(geometry.RATED_LOAD_LB, 0.0)
        self.assertIn("0 kg / 0 lb", self.evidence.no_load_boundary)
        self.assertIn("no wall installation", self.evidence.no_load_boundary)
        self.assertTrue(self.evidence.support_retainer_positive_capture_authored)
        self.assertTrue(self.evidence.support_retainer_service_path_collision_free)
        self.assertFalse(self.evidence.midpoint_notched_log_section_qualified)
        self.assertTrue(self.evidence.midpoint_net_section_geometry_authored)
        self.assertFalse(self.evidence.log_section.material_capacity_claimed)
        self.assertEqual(self.evidence.log_key_top_access_pockets_per_bay, 3)
        self.assertEqual(geometry.FIELD_LOG_KEY_TOP_ACCESS_POCKET_COUNT, 18)
        self.assertTrue(self.evidence.flush_log_key_access_closures_authored)
        self.assertEqual(self.evidence.release_blockers, ())

    def test_exact_field_context_and_physical_seam_math(self) -> None:
        self.assertEqual(self.evidence.field_support_count, 7)
        self.assertEqual(self.evidence.field_bay_count, 6)
        self.assertEqual(self.evidence.support_centers_mm, (0.0, 254.0))
        self.assertEqual(self.evidence.planning_bay_pitch_mm, 254.0)
        self.assertEqual(self.evidence.printed_regular_half_length_mm, 126.65)
        self.assertEqual(self.evidence.printed_terminal_half_length_mm, 142.35)
        self.assertEqual(self.evidence.printed_log_length_mm, 159.10)
        joinery = self.evidence.joinery
        self.assertEqual(joinery.midpoint_seam_mm, 0.35)
        self.assertEqual(joinery.support_line_seam_mm, 0.35)
        self.assertEqual(joinery.wall_endpoint_mm, 0.35)
        self.assertEqual(joinery.physical_bearing_contact_per_half_mm, 15.70)
        self.assertEqual(joinery.log_engagement_per_half_mm, 79.375)
        self.assertAlmostEqual(
            2.0 * joinery.log_engagement_per_half_mm + joinery.midpoint_seam_mm,
            self.evidence.printed_log_length_mm,
            places=9,
        )

    def test_geometry_matches_validated_canonical_config(self) -> None:
        config = capacity_study.load_config()
        capacity_study.validate_config(config)
        project = config["project"]
        field = config["field_reference"]
        arcade = config["printed_arcade"]
        log = arcade["splice_log"]
        log_key = arcade["transverse_lock_key"]
        support_key = arcade["support_capture_key"]
        cassette = arcade["cassette_half"]
        bores = arcade["wall_bore_candidate"]

        self.assertEqual(geometry.RATED_LOAD_KG, project["rated_load_kg"])
        self.assertEqual(geometry.RATED_LOAD_LB, project["rated_load_lb"])
        self.assertEqual(geometry.PRINTED_MATERIAL, arcade["printed_material"])
        self.assertEqual(geometry.FIELD_SUPPORT_COUNT, field["support_count"])
        self.assertEqual(geometry.FIELD_BAY_COUNT, field["bay_count"])
        self.assertEqual(geometry.SHELF_DEPTH_MM, field["shelf_depth_mm"])
        self.assertAlmostEqual(
            geometry.SUPPORT_PITCH_MM,
            (
                field["last_support_center_from_left_mm"]
                - field["first_support_center_from_left_mm"]
            )
            / field["bay_count"],
            places=9,
        )
        self.assertEqual(geometry.AESTHETIC_CONTRACT_ID, arcade["architecture_id"])
        self.assertEqual(geometry.SUPPORT_RUN_WIDTH_MM, arcade["support_run_width_mm"])
        self.assertEqual(geometry.SUPPORT_WALL_CHORD_MM, arcade["wall_chord_mm"])
        self.assertEqual(
            geometry.SUPPORT_TOTAL_DROP_MM,
            arcade["wall_strap_total_drop_from_shelf_underside_mm"],
        )
        self.assertEqual(geometry.SUPPORT_TOP_CHORD_MM, arcade["support_top_chord_mm"])
        self.assertEqual(
            geometry.SUPPORT_COMPRESSION_WEB_MM, arcade["compression_web_mm"]
        )
        self.assertEqual(geometry.SUPPORT_FRONT_NOSE_MM, arcade["front_nose_mm"])
        self.assertEqual(
            geometry.COMPACT_VISIBLE_DROP_MM,
            arcade["compact_visible_corbel_drop_mm"],
        )
        self.assertEqual(
            geometry.SHELF_TOTAL_HEIGHT_MM, arcade["shelf_total_thickness_mm"]
        )

        self.assertEqual(geometry.FIELD_BAY_COUNT * geometry.LOG_COUNT_PER_BAY, log["quantity"])
        self.assertEqual(geometry.LOG_COUNT_PER_BAY, log["per_bay"])
        self.assertEqual(geometry.LOG_LENGTH_MM, log["length_mm"])
        self.assertEqual(geometry.LOG_WIDTH_MM, log["width_in_shelf_depth_mm"])
        self.assertEqual(geometry.LOG_HEIGHT_MM, log["height_mm"])
        self.assertEqual(
            geometry.LOG_ENGAGEMENT_PER_HALF_MM,
            log["engagement_per_cassette_half_mm"],
        )
        self.assertEqual(
            geometry.JOINERY_CLEARANCE_PER_FACE_MM, log["clearance_per_face_mm"]
        )
        section = self.evidence.log_section
        proxy = log["midpoint_section_geometry_proxy"]
        for attribute, key in (
            ("gross_area_mm2", "gross_area_mm2"),
            ("gross_centroid_z_mm", "gross_centroid_z_mm"),
            ("gross_second_moment_about_y_mm4", "gross_second_moment_about_y_mm4"),
            ("gross_governing_section_modulus_mm3", "gross_governing_section_modulus_mm3"),
            ("net_area_mm2", "net_area_mm2"),
            ("net_centroid_z_mm", "net_centroid_z_mm"),
            ("net_second_moment_about_y_mm4", "net_second_moment_about_y_mm4"),
            ("net_governing_section_modulus_mm3", "net_governing_section_modulus_mm3"),
            ("net_to_gross_area_ratio", "net_to_gross_area_ratio"),
            ("net_to_gross_second_moment_ratio", "net_to_gross_second_moment_ratio"),
            ("net_to_gross_section_modulus_ratio", "net_to_gross_section_modulus_ratio"),
        ):
            self.assertAlmostEqual(getattr(section, attribute), proxy[key], places=6)
        self.assertIs(
            section.material_capacity_claimed, proxy["material_capacity_claimed"]
        )

        self.assertEqual(
            geometry.FIELD_BAY_COUNT * geometry.LOG_RETAINER_COUNT_PER_BAY,
            log_key["quantity"],
        )
        self.assertEqual(geometry.LOG_RETAINER_COUNT_PER_BAY, log_key["per_bay"])
        self.assertEqual(geometry.LOG_RETAINER_RUN_MM, log_key["width_along_run_mm"])
        self.assertEqual(
            geometry.LOG_RETAINER_STATION_MM,
            log_key["length_across_one_log_station_mm"],
        )
        self.assertEqual(geometry.LOG_RETAINER_HEIGHT_MM, log_key["height_mm"])
        self.assertIs(log_key["integrated_flush_access_cap"], True)
        self.assertEqual(geometry.LOG_RETAINER_CAP_RUN_MM, log_key["flush_cap_run_length_mm"])
        self.assertEqual(
            geometry.LOG_RETAINER_CAP_HEIGHT_MM,
            log_key["flush_cap_additional_height_mm"],
        )
        self.assertEqual(log_key["saved_print_envelope_mm"], [12.4, 28.0, 10.8])
        self.assertIs(log_key["loose_access_closure_present"], False)

        self.assertEqual(
            geometry.FULL_RUN_SUPPORT_RETAINER_COUNT, support_key["quantity"]
        )
        self.assertEqual(geometry.SUPPORT_RETAINERS_PER_BAY, support_key["per_bay"])
        self.assertEqual(geometry.SUPPORT_RETAINER_RUN_MM, support_key["width_along_run_mm"])
        self.assertEqual(
            geometry.SUPPORT_RETAINER_DEPTH_MM, support_key["shelf_depth_mm"]
        )
        self.assertEqual(geometry.SUPPORT_RETAINER_HEIGHT_MM, support_key["height_mm"])
        self.assertEqual(
            geometry.SUPPORT_RETAINER_SHAFT_RUN_MM,
            support_key["shaft_width_along_run_mm"],
        )
        self.assertEqual(
            geometry.SUPPORT_RETAINER_REAR_DOG_DEPTH_MM,
            support_key["rear_dog_depth_mm"],
        )
        self.assertEqual(
            geometry.SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM,
            support_key["front_handle_depth_mm"],
        )
        self.assertEqual(
            geometry.SUPPORT_RETAINER_BAYONET_SHIFT_MM,
            support_key["bayonet_shift_toward_bay_mm"],
        )
        self.assertEqual(
            geometry.SUPPORT_RETAINER_HAND_GRIP_PROTRUSION_MM,
            support_key["front_hand_grip_protrusion_mm"],
        )
        self.assertEqual(
            geometry.CAPTURE_LUG_RUN_MM,
            support_key["support_capture_lug_width_along_run_mm"],
        )
        self.assertIs(support_key["positive_no_friction_walkout_stop"], True)
        self.assertIs(support_key["retention_depends_on_friction_or_snap"], False)

        self.assertEqual(cassette["regular_quantity"], 10)
        self.assertEqual(cassette["terminal_quantity"], 2)
        self.assertEqual(
            geometry.PLANNING_REGULAR_HALF_LENGTH_MM,
            cassette["regular_nominal_length_mm"],
        )
        self.assertEqual(
            geometry.PLANNING_TERMINAL_HALF_LENGTH_MM,
            cassette["terminal_nominal_length_mm"],
        )
        self.assertEqual(
            geometry.PRINTED_REGULAR_HALF_LENGTH_MM,
            cassette["regular_printed_length_mm"],
        )
        self.assertEqual(
            geometry.PRINTED_TERMINAL_HALF_LENGTH_MM,
            cassette["terminal_printed_length_mm"],
        )
        self.assertEqual(
            geometry.MIDPOINT_SEAM_CLEARANCE_MM, cassette["midpoint_seam_gap_mm"]
        )
        self.assertEqual(
            geometry.SUPPORT_LINE_CLEARANCE_MM, cassette["support_line_seam_gap_mm"]
        )
        self.assertEqual(
            geometry.WALL_ENDPOINT_CLEARANCE_MM,
            cassette["endpoint_clearance_per_end_mm"],
        )
        self.assertEqual(geometry.SHELF_DEPTH_MM, cassette["depth_mm"])
        self.assertEqual(geometry.SHELF_TOTAL_HEIGHT_MM, cassette["total_height_mm"])
        self.assertEqual(geometry.TOP_SKIN_MM, cassette["top_skin_mm"])
        self.assertEqual(geometry.BOTTOM_SKIN_MM, cassette["bottom_skin_mm"])
        self.assertEqual(geometry.LOAD_WEB_MM, cassette["load_web_thickness_mm"])
        self.assertEqual(
            geometry.SUPPORT_HALF_LAND_NOMINAL_MM,
            cassette["support_half_land_nominal_mm"],
        )
        self.assertEqual(
            geometry.PHYSICAL_BEARING_CONTACT_PER_HALF_MM,
            cassette["minimum_cassette_bearing_contact_mm"],
        )

        self.assertEqual(geometry.WALL_BORE_COUNT, bores["count_per_support"])
        self.assertEqual(geometry.WALL_BORE_DIAMETER_MM, bores["diameter_mm"])
        self.assertEqual(
            geometry.WALL_BORE_DROPS_BELOW_UNDERSIDE_MM,
            tuple(bores["drops_below_shelf_underside_mm"]),
        )
        self.assertEqual(
            geometry.WASHER_BEARING_LAND_OUTER_DIAMETER_MM,
            bores["washer_bearing_land_outer_diameter_mm"],
        )

    def test_exact_32mm_channel_closes_at_point_four_per_face(self) -> None:
        joinery = self.evidence.joinery
        self.assertEqual(geometry.SHELF_TOTAL_HEIGHT_MM, 32.0)
        self.assertEqual(geometry.TOP_SKIN_MM, 4.0)
        self.assertEqual(geometry.BOTTOM_SKIN_MM, 3.2)
        self.assertEqual(geometry.LOG_HEIGHT_MM, 24.0)
        self.assertEqual(joinery.channel_clearance_per_face_mm, 0.4)
        self.assertEqual(joinery.channel_clear_height_mm, 24.8)
        self.assertEqual(joinery.cassette_internal_height_mm, 24.8)
        self.assertAlmostEqual(
            geometry.BOTTOM_SKIN_MM
            + joinery.channel_clear_height_mm
            + geometry.TOP_SKIN_MM,
            geometry.SHELF_TOTAL_HEIGHT_MM,
            places=9,
        )

    def test_inventory_uses_independent_bay_local_retainers(self) -> None:
        names = tuple(item.name for item in self.evidence.parts)
        self.assertEqual(self.evidence.one_bay_part_count, 12)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(sum(name.endswith("splice_log") for name in names), 3)
        self.assertEqual(sum(name.endswith("log_retainer") for name in names), 3)
        self.assertEqual(
            sum(name.endswith("support_retainer") for name in names), 2
        )
        self.assertEqual(self.evidence.joinery.independent_log_retainers_per_bay, 3)
        self.assertEqual(
            self.evidence.joinery.bay_local_support_retainers_per_bay, 2
        )
        self.assertEqual(geometry.FULL_RUN_SUPPORT_RETAINER_COUNT, 12)
        for item in self.evidence.parts:
            if item.name.endswith("retainer"):
                self.assertFalse(item.capacity_credit)

    def test_round_wall_bores_and_additive_ornament_preserve_run_width(self) -> None:
        cutters = geometry._wall_bore_cutters()
        self.assertEqual(len(cutters), 3)
        for cutter in cutters:
            np.testing.assert_allclose(cutter.extents, (21.05, 7.0, 7.0), atol=1e-6)
        ornament = geometry._palatine_additive_ornament()
        self.assertGreaterEqual(float(ornament.bounds[0, 2]), 0.0)
        self.assertLessEqual(
            float(ornament.bounds[1, 2]), geometry.SUPPORT_RUN_WIDTH_MM
        )
        support = geometry.build_support_candidate()
        np.testing.assert_allclose(
            support.extents,
            (152.4, 170.75, 31.75),
            atol=1e-5,
        )
        projecting = np.asarray(support.vertices)
        compact = projecting[
            (projecting[:, 0] > geometry.SUPPORT_WALL_CHORD_MM + 1.0e-6)
            & (projecting[:, 1] <= geometry.SUPPORT_TOTAL_DROP_MM + 1.0e-6)
        ]
        self.assertAlmostEqual(
            float(compact[:, 1].min()),
            geometry.SUPPORT_TOTAL_DROP_MM - geometry.COMPACT_VISIBLE_DROP_MM,
            places=5,
        )

    def test_all_round_bores_have_continuous_full_solid_washer_lands(self) -> None:
        lands = self.evidence.washer_lands
        self.assertEqual(len(lands), 3)
        self.assertEqual(
            tuple(item.bore_drop_below_shelf_underside_mm for item in lands),
            geometry.WALL_BORE_DROPS_BELOW_UNDERSIDE_MM,
        )
        for land in lands:
            with self.subTest(drop=land.bore_drop_below_shelf_underside_mm):
                self.assertEqual(land.bore_diameter_mm, 7.0)
                self.assertEqual(land.outer_diameter_mm, 27.025)
                self.assertEqual(land.radial_land_mm, 10.0125)
                self.assertEqual(land.surface_thickness_checked_mm, 1.0)
                self.assertGreater(land.minimum_run_edge_margin_mm, 0.0)
                self.assertGreater(land.minimum_vertical_edge_margin_mm, 0.0)
                self.assertTrue(land.continuous_single_body)
                self.assertTrue(land.full_solid)
                self.assertAlmostEqual(land.solid_volume_ratio, 1.0, places=6)
                self.assertAlmostEqual(
                    land.annulus_solid_volume_mm3,
                    land.annulus_probe_volume_mm3,
                    places=5,
                )

    def test_positive_axial_shoulders_and_exact_continuous_net_log_section(self) -> None:
        self.assertTrue(self.evidence.positive_log_body_shoulders_authored)
        self.assertEqual(geometry.LOG_REDUCED_NOSE_LENGTH_MM, 0.4)
        self.assertEqual(geometry.LOG_NOSE_AXIAL_CLEARANCE_MM, 0.4)
        main_shoulder_depth = (
            geometry.LOG_ENGAGEMENT_PER_HALF_MM
            - geometry.LOG_REDUCED_NOSE_LENGTH_MM
        )
        self.assertEqual(main_shoulder_depth, 78.975)
        log = geometry.build_splice_log()
        self.assertAlmostEqual(float(log.extents[0]), 159.10, places=4)
        # The retainer notch opens at the top instead of splitting the log into
        # two disconnected peak-moment strips.  Exact final-mesh properties
        # remain geometry proxies and do not create a PETG capacity claim.
        self.assertEqual(geometry.LOG_KEY_SLOT_BASE_MM, 17.2)
        self.assertAlmostEqual(
            geometry.LOG_KEY_SLOT_BASE_MM
            + geometry.LOG_RETAINER_HEIGHT_MM
            + 2.0 * geometry.JOINERY_CLEARANCE_PER_FACE_MM,
            geometry.LOG_HEIGHT_MM,
            places=9,
        )
        section = self.evidence.log_section
        self.assertAlmostEqual(section.gross_area_mm2, 464.0, places=5)
        self.assertAlmostEqual(section.gross_centroid_z_mm, 11.8635057471, places=5)
        self.assertAlmostEqual(
            section.gross_second_moment_about_y_mm4, 22428.688697318, places=4
        )
        self.assertAlmostEqual(
            section.gross_governing_section_modulus_mm3, 1848.036857267, places=4
        )
        self.assertAlmostEqual(section.net_area_mm2, 334.800014496, places=4)
        self.assertAlmostEqual(section.net_centroid_z_mm, 8.492075248, places=4)
        self.assertAlmostEqual(
            section.net_second_moment_about_y_mm4, 8263.957404514, places=3
        )
        self.assertAlmostEqual(
            section.net_governing_section_modulus_mm3, 949.015628344, places=3
        )
        self.assertAlmostEqual(section.net_to_gross_area_ratio, 0.7215517554, places=7)
        self.assertAlmostEqual(
            section.net_to_gross_second_moment_ratio, 0.3684547731, places=7
        )
        self.assertAlmostEqual(
            section.net_to_gross_section_modulus_ratio, 0.5135263534, places=7
        )
        self.assertFalse(section.material_capacity_claimed)

    def test_installed_pose_and_preassembly_slide_are_interference_free(self) -> None:
        self.assertTrue(self.evidence.target_pose_collision_free)
        self.assertLessEqual(self.evidence.target_pose_maximum_intersection_mm3, 1e-5)
        self.assertTrue(self.evidence.log_retainer_preassembly_path_authored)
        self.assertTrue(self.evidence.right_half_capture_path_collision_free)
        self.assertLessEqual(
            self.evidence.right_half_capture_path_maximum_intersection_mm3, 1e-5
        )
        self.assertTrue(self.evidence.support_retainer_positive_capture_authored)
        self.assertTrue(self.evidence.support_retainer_service_path_collision_free)
        self.assertLessEqual(
            self.evidence.support_retainer_service_path_maximum_intersection_mm3,
            1e-5,
        )
        self.assertGreater(
            self.evidence.support_retainer_walkout_stop_intersection_mm3,
            1.0,
        )
        self.assertEqual(
            self.evidence.support_retainer_hand_grip_protrusion_mm, 4.0
        )
        installed = geometry.build_installed_one_bay_parts()
        left = installed["r10_one_bay_left_cassette_half"]
        right = installed["r10_one_bay_right_cassette_half"]
        self.assertAlmostEqual(float(left.bounds[0, 0]), 0.175, places=5)
        self.assertAlmostEqual(float(left.bounds[1, 0]), 126.825, places=5)
        self.assertAlmostEqual(float(right.bounds[0, 0]), 127.175, places=5)
        self.assertAlmostEqual(float(right.bounds[1, 0]), 253.825, places=5)
        self.assertAlmostEqual(
            float(right.bounds[0, 0] - left.bounds[1, 0]), 0.35, places=5
        )
        log = installed["r10_one_bay_center_splice_log"]
        self.assertAlmostEqual(
            float(left.bounds[1, 0] - log.bounds[0, 0]), 79.375, places=4
        )
        self.assertAlmostEqual(
            float(log.bounds[1, 0] - right.bounds[0, 0]), 79.375, places=4
        )
        for station in ("rear", "center", "front"):
            key = installed[f"r10_one_bay_{station}_log_retainer"]
            top_vertices = np.asarray(key.vertices)[
                np.isclose(
                    np.asarray(key.vertices)[:, 2],
                    float(key.bounds[1, 2]),
                    atol=1.0e-6,
                )
            ]
            self.assertAlmostEqual(
                float(key.bounds[1, 2]),
                geometry.SUPPORT_TOTAL_DROP_MM + geometry.SHELF_TOTAL_HEIGHT_MM,
                places=5,
            )
            self.assertAlmostEqual(float(top_vertices[:, 0].min()), 120.6, places=5)
            self.assertAlmostEqual(float(top_vertices[:, 0].max()), 126.6, places=5)
            self.assertLessEqual(
                float(top_vertices[:, 0].max()), float(left.bounds[1, 0])
            )
            self.assertLess(float(top_vertices[:, 0].max()), float(right.bounds[0, 0]))
        left_support_key = installed["r10_one_bay_left_support_retainer"]
        right_support_key = installed["r10_one_bay_right_support_retainer"]
        self.assertAlmostEqual(
            float(left_support_key.bounds[0, 0]), 6.425, places=5
        )
        self.assertAlmostEqual(
            float(right_support_key.bounds[1, 0]), 247.575, places=5
        )
        self.assertAlmostEqual(float(left_support_key.bounds[1, 1]), 156.4, places=5)
        self.assertAlmostEqual(
            float(left_support_key.bounds[1, 1]) - geometry.SHELF_DEPTH_MM,
            4.0,
            places=5,
        )

    def test_every_saved_article_is_one_watertight_a1_mini_body(self) -> None:
        all_saved = {**self.saved, **self.terminals}
        self.assertEqual(len(self.saved), 12)
        self.assertEqual(len(self.terminals), 2)
        envelopes = geometry.print_envelopes()
        self.assertEqual(set(envelopes), set(all_saved))
        for name, mesh in all_saved.items():
            with self.subTest(name=name):
                self.assertEqual(len(mesh.split(only_watertight=False)), 1)
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_winding_consistent)
                self.assertGreater(float(mesh.volume), 0.0)
                np.testing.assert_allclose(mesh.bounds[0], (0.0, 0.0, 0.0), atol=1e-6)
                self.assertTrue(envelopes[name].fits)
        np.testing.assert_allclose(
            self.saved["r10_one_bay_left_cassette_half"].extents,
            (152.4, 32.0, 126.65),
            atol=1e-5,
        )
        np.testing.assert_allclose(
            self.terminals["r10_left_wall_terminal_cassette_half"].extents,
            (152.4, 32.0, 142.35),
            atol=1e-5,
        )
        np.testing.assert_allclose(
            self.saved["r10_one_bay_rear_splice_log"].extents,
            (159.10, 24.0, 20.0),
            atol=1e-5,
        )
        np.testing.assert_allclose(
            self.saved["r10_one_bay_rear_log_retainer"].extents,
            (12.4, 28.0, 10.8),
            atol=1e-5,
        )
        np.testing.assert_allclose(
            self.saved["r10_one_bay_left_support_retainer"].extents,
            (8.0, 136.0, 6.0),
            atol=1e-5,
        )

    def test_saved_orientations_have_no_sampled_layer_islands(self) -> None:
        # One representative of each unique authored topology is enough; the
        # named duplicates are exact copies in the other stations/hands.
        representatives = (
            self.saved["r10_one_bay_left_support"],
            self.saved["r10_one_bay_left_cassette_half"],
            self.saved["r10_one_bay_right_cassette_half"],
            self.terminals["r10_left_wall_terminal_cassette_half"],
            self.saved["r10_one_bay_rear_splice_log"],
            self.saved["r10_one_bay_rear_log_retainer"],
            self.saved["r10_one_bay_left_support_retainer"],
        )
        for mesh in representatives:
            report = cable_geometry.saved_layer_island_report(
                mesh, layer_height_mm=0.2
            )
            self.assertFalse(report.support_required)
            self.assertEqual(report.island_layer_indices, ())
            self.assertGreater(report.first_layer_contact_area_mm2, 40.0)
        self.assertTrue(all(not item.support_required for item in self.evidence.parts))

    def test_geometry_is_deterministic(self) -> None:
        first = geometry.build_saved_one_bay_parts()
        second = geometry.build_saved_one_bay_parts()
        for name in first:
            with self.subTest(name=name):
                np.testing.assert_array_equal(first[name].faces, second[name].faces)
                np.testing.assert_allclose(first[name].vertices, second[name].vertices, atol=0.0)


if __name__ == "__main__":
    unittest.main()
