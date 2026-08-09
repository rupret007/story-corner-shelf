#!/usr/bin/env python3
"""Mesh-level regressions for the frozen r6 arch/corbel interface datums."""

from __future__ import annotations

import copy
import json
import sys
import unittest
import warnings
from pathlib import Path

import numpy as np
import trimesh


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

import generate_all_petg_r6 as generator  # noqa: E402
from design_math import calculate_plan, x_corbel_geometry  # noqa: E402


def probe_volume(mesh: trimesh.Trimesh, center: tuple[float, float, float]) -> float:
    probe = trimesh.creation.box(extents=[0.6, 0.6, 0.6])
    probe.apply_translation(center)
    result = trimesh.boolean.intersection([mesh, probe], engine="manifold")
    if result is None or len(result.faces) < 4 or not result.is_watertight:
        return 0.0
    return abs(float(result.volume))


def transformed_mesh(mesh: trimesh.Trimesh, matrix: list[list[float]]) -> trimesh.Trimesh:
    installed = mesh.copy()
    installed.apply_transform(np.asarray(matrix, dtype=float))
    return installed


def solid_overlap_volume(
    left: trimesh.Trimesh, right: trimesh.Trimesh
) -> tuple[float, list[list[float]] | None]:
    """Return real positive Boolean overlap, never a centroid/AABB proxy."""

    if not np.all(
        np.asarray(left.bounds[1], dtype=float)
        > np.asarray(right.bounds[0], dtype=float) + 1.0e-9
    ) or not np.all(
        np.asarray(right.bounds[1], dtype=float)
        > np.asarray(left.bounds[0], dtype=float) + 1.0e-9
    ):
        return 0.0, None
    # Exact bearing/contact planes can make manifold return a zero-thickness
    # shell.  Trimesh warns while asking that shell for a center of mass; it is
    # not positive solid overlap and is rejected by the extent gate below.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        overlap = trimesh.boolean.intersection(
            [left, right], engine="manifold", check_volume=True
        )
        if overlap is None or len(overlap.faces) < 4 or not overlap.is_watertight:
            return 0.0, None
        if np.any(np.asarray(overlap.extents, dtype=float) <= 1.0e-8):
            return 0.0, None
        volume = abs(float(overlap.volume))
        return volume, np.round(overlap.bounds, 6).tolist()


class R6GeneratorInterfaceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads((R6 / "config.json").read_text(encoding="utf-8"))
        cls.plan = calculate_plan(cls.cfg)
        cls.arches = generator.final_x_arch_family(
            cls.cfg, cls.plan, selected_levels=2
        )
        cls.corbels = generator.final_x_corbel_family(
            cls.cfg,
            x_corbel_geometry(cls.cfg),
            plan=cls.plan,
            selected_levels=2,
        )
        cls.cassettes, _cassette_report = generator.cassette_chassis_family(
            cls.cfg, plan=cls.plan
        )
        cls.cassette_lock = generator.final_x_cassette_lock(cls.cfg)
        cls.crown_bridge, cls.crown_pin = generator.crown_bridge_and_pin(cls.cfg)
        cls.ornaments, cls.ornament_report = generator.removable_ornament_parts(
            cls.cfg, selected_levels=2
        )

    def corbel_placements_by_station(self) -> dict[tuple[str, float], tuple[object, dict]]:
        placements: dict[tuple[str, float], tuple[object, dict]] = {}
        for part in self.corbels:
            for placement in part.design_metrics["authoritative_instance_placements"]:
                key = (
                    str(placement["run_id"]),
                    round(float(placement["support_station_local_s_mm"]), 7),
                )
                self.assertNotIn(key, placements)
                placements[key] = (part, placement)
        self.assertEqual(len(placements), 11)
        return placements

    def test_all_99_zero_credit_ornament_parent_bosses_are_embodied_and_conflicts_fail_closed(self) -> None:
        expected_overlap = float(
            self.cfg["ornament_isolation"][
                "minimum_boss_neck_parent_union_volume_mm3"
            ]
        )
        arch_bosses = sum(
            int(part.design_metrics["quantity_per_level"])
            * int(part.design_metrics["integral_ornament_boss_count"])
            for part in self.arches
        )
        corbel_bosses = sum(
            int(part.design_metrics["quantity_per_level"])
            * int(part.design_metrics["integral_ornament_boss_count"])
            for part in self.corbels
        )
        cassette_bosses = sum(
            int(part.design_metrics["integral_ornament_boss_count"])
            for part in self.cassettes
        )
        self.assertEqual((arch_bosses, corbel_bosses, cassette_bosses), (54, 33, 12))
        self.assertEqual(arch_bosses + corbel_bosses + cassette_bosses, 99)

        for part in self.arches:
            self.assertEqual(part.design_metrics["saved_build_face"], "structural rear source z=18 broad face")
            parent_depth = float(
                self.cfg["palatine"]["ornament_keyhole_contract"]
                ["coordinate_contract"]["structural_parent_source_z_envelope_mm"]
                [1]
            )
            boss_front_depth = float(
                self.cfg["palatine"]["ornament_keyhole_contract"]
                ["boss_head_depth_zone_mm"][0]
            )
            parent_front_d = float(
                self.cfg["palatine"]["ornament_keyhole_contract"]
                ["coordinate_contract"]["structural_parent_front_global_d_mm"]
            )
            self.assertAlmostEqual(
                part.mesh.extents[2],
                parent_depth + parent_front_d - boss_front_depth,
                delta=1.0e-4,
            )
        compact_overlap = float(
            self.cfg["ornament_isolation"][
                "minimum_compact_pier_boss_neck_parent_union_volume_mm3"
            ]
        )
        for part in self.corbels:
            self.assertAlmostEqual(
                part.mesh.extents[2],
                float(
                    self.cfg["corbel"]["print_connectivity_contract"]
                    ["maximum_build_height_mm"]
                ),
                delta=1.0e-4,
            )
            feature_types = part.design_metrics[
                "integral_ornament_attachment_feature_types"
            ]
            volumes = part.design_metrics[
                "integral_ornament_boss_parent_union_volumes_mm3"
            ]
            self.assertEqual(
                feature_types,
                [
                    "compact_gravity_keyhole",
                    "compact_gravity_keyhole",
                    "noncapturing_loose_locator",
                ],
            )
            for feature_type, volume in zip(feature_types, volumes):
                expected = (
                    compact_overlap
                    if feature_type == "compact_gravity_keyhole"
                    else expected_overlap
                )
                self.assertAlmostEqual(volume, expected, delta=0.001)
        decorated = [
            part
            for part in self.cassettes
            if part.design_metrics["integral_ornament_boss_count"]
        ]
        self.assertEqual(len(decorated), 4)
        for part in decorated:
            record = part.design_metrics["integral_ornament_backing_panel"]
            for volume in record["boss_parent_union_volumes_mm3"]:
                self.assertAlmostEqual(volume, expected_overlap, delta=0.001)
            self.assertFalse(
                record[
                    "positive_cross_key_parent_feature_overlap_requires_aperture"
                ]
            )

        # The final pair of pier oculi resolves the former spring-key access
        # conflict without silently subtracting any structural parent boss.
        conflicting_piers = sum(
            int(part.design_metrics["quantity_per_level"])
            for part in self.corbels
            if part.design_metrics[
                "ornament_to_cross_key_parent_feature_overlap_requires_aperture"
            ]
        )
        self.assertEqual(conflicting_piers, 0)
        self.assertTrue(self.ornament_report["structural_parent_bosses_generated"])
        self.assertTrue(self.ornament_report["structural_parent_boss_maps_complete"])
        self.assertEqual(
            self.ornament_report["structural_parent_boss_count_per_level"], 99
        )
        floating_map = self.cfg["palatine"]["ornament_keyhole_contract"][
            "per_parent_boss_placement_map"
        ]["corner_floating_return"]
        floating_parent = next(
            part
            for part in self.cassettes
            if part.design_metrics.get("ornament_parent_family_id")
            == "corner_floating_return"
        ).design_metrics["integral_ornament_backing_panel"]
        self.assertAlmostEqual(
            floating_parent["locked_piece_origin_run_s_mm"],
            float(floating_map["locked_piece_origin_run_s_mm"]),
            places=7,
        )
        self.assertTrue(
            np.allclose(
                floating_parent["panel_run_global_s_envelope_mm"],
                floating_map["parent_panel_run_envelope_mm"],
                atol=1.0e-7,
                rtol=0.0,
            )
        )
        self.assertTrue(
            np.allclose(
                floating_parent["boss_centers_run_s_e_mm"],
                floating_map["locked_boss_centers_run_s_e_mm"],
                atol=1.0e-7,
                rtol=0.0,
            )
        )
        self.assertFalse(self.ornament_report["software_model_mapping_complete"])
        self.assertFalse(
            self.ornament_report["physical_installation_mapping_qualified"]
        )
        self.assertFalse(self.ornament_report["production_release_eligible"])

    def test_all_33_ornaments_pass_actual_parent_and_connector_service_sweeps(self) -> None:
        report = generator.validate_ornament_actual_parent_sweeps(
            self.cfg,
            ornaments=self.ornaments,
            arches=self.arches,
            corbels=self.corbels,
            cassettes=self.cassettes,
        )
        self.assertEqual(report["installed_ornament_instance_count_per_level"], 33)
        self.assertEqual(report["actual_parent_boolean_pair_count"], 33 * (12 + 16))
        self.assertEqual(report["local_connector_sweep_boolean_pair_count"], 928)
        self.assertEqual(report["maximum_actual_parent_overlap_volume_mm3"], 0.0)
        self.assertEqual(report["maximum_local_connector_overlap_volume_mm3"], 0.0)
        self.assertLessEqual(
            report["maximum_full_depth_oculus_residual_solid_volume_mm3"],
            float(
                self.cfg["palatine"]["ornament_keyhole_contract"]
                ["strict_collision_gate"]["allowed_solid_overlap_mm3"]
            ),
        )
        self.assertEqual(report["repeated_full_depth_oculus_count_per_level"], 58)
        self.assertEqual(report["unique_full_depth_oculus_void_count"], 10)
        self.assertEqual(
            report["unique_source_connector_type_counts"],
            {
                "gravity_keyhole": 21,
                "compact_gravity_keyhole": 2,
                "noncapturing_loose_locator": 1,
            },
        )
        self.assertTrue(report["software_model_package_eligible"])
        self.assertFalse(report["physical_installation_qualified"])
        self.assertFalse(report["production_release_eligible"])
        self.assertTrue(report["actual_parent_orientation_coupon_mappings_complete"])
        self.assertFalse(
            report["actual_parent_orientation_coupons_physically_passed"]
        )

    def test_corner_facades_clear_both_arms_and_full_service_paths(self) -> None:
        report = generator.validate_inside_corner_ornament_cross_arm_clearance(
            self.cfg,
            plan=self.plan,
            ornaments=self.ornaments,
            arches=self.arches,
            corbels=self.corbels,
            cassettes=self.cassettes,
        )
        self.assertEqual(report["final_cross_arm_boolean_pair_count"], 9)
        self.assertGreater(report["service_sweep_boolean_pair_count"], 0)
        self.assertEqual(report["maximum_final_cross_arm_overlap_volume_mm3"], 0.0)
        self.assertEqual(report["maximum_service_sweep_overlap_volume_mm3"], 0.0)
        self.assertTrue(
            report[
                "return_cosmetic_overhang_removed_before_through_rosette_service"
            ]
        )
        self.assertTrue(report["software_model_package_eligible"])
        self.assertFalse(report["physical_installation_qualified"])
        self.assertFalse(report["production_release_eligible"])

    def test_physical_crown_faces_and_all_36_top_centers_are_exact(self) -> None:
        self.assertEqual(len(self.arches), 4)
        placement_count = 0
        top_center_count = 0
        for part in self.arches:
            metrics = part.design_metrics
            self.assertTrue(part.mesh.is_watertight, part.name)
            self.assertTrue(part.mesh.is_volume, part.name)
            self.assertLessEqual(max(part.mesh.extents), 180.0)
            self.assertTrue(
                metrics["radial_band_parent_watertight_one_body_before_union"]
            )
            self.assertLessEqual(
                metrics["radial_band_duplicate_cleanup_area_delta_mm2"], 1.0e-8
            )
            self.assertAlmostEqual(
                metrics["physical_half_span_to_crown_face_mm"],
                metrics["half_span_mm"] - 0.175,
                places=7,
            )
            placements = metrics["authoritative_instance_placements"]
            placement_count += len(placements)
            for placement in placements:
                top_center_count += len(placement["top_receiver_center_errors_mm"])
                self.assertTrue(
                    all(
                        error < 1.0e-7
                        for error in placement["top_receiver_center_errors_mm"]
                    )
                )
                self.assertLess(placement["spring_center_error_mm"], 1.0e-7)
        self.assertEqual(placement_count, 18)
        self.assertEqual(top_center_count, 36)

    def test_structural_cross_key_service_access_has_no_hidden_default(self) -> None:
        expected = float(
            self.cfg["tied_arcade"]["retention_wedge"]
            ["exact_service_kinematics"]
            ["minimum_external_straight_service_access_mm"]
        )
        self.assertEqual(
            generator.structural_cross_key_service_access_mm(self.cfg), expected
        )
        peer_paths = (
            (
                "tied_arcade",
                "spring_final_x_vertical_joint",
                "minimum_straight_service_access_mm",
            ),
            (
                "tied_arcade",
                "rear_crown_bridge",
                "minimum_straight_service_access_mm",
            ),
            (
                "closet",
                "vertical_layout",
                "minimum_straight_wedge_and_pin_service_access_mm",
            ),
        )
        for path in peer_paths:
            mutated = copy.deepcopy(self.cfg)
            target = mutated
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = expected + 1.0
            with self.assertRaises(ValueError, msg=".".join(path)):
                generator.structural_cross_key_service_access_mm(mutated)

        missing = copy.deepcopy(self.cfg)
        del missing["tied_arcade"]["retention_wedge"][
            "exact_service_kinematics"
        ]["minimum_external_straight_service_access_mm"]
        with self.assertRaises(KeyError):
            generator.structural_cross_key_service_access_mm(missing)

    def test_crown_keyways_and_double_shear_parent_ears_are_real_meshes(self) -> None:
        bridge = self.crown_bridge
        pin = self.crown_pin
        self.assertTrue(bridge.mesh.is_watertight)
        self.assertTrue(pin.mesh.is_watertight)
        self.assertEqual((bridge.mesh.body_count, pin.mesh.body_count), (1, 1))
        self.assertTrue(
            np.allclose(bridge.mesh.extents, [72.0, 48.0, 11.2], atol=1.0e-5)
        )
        self.assertTrue(
            np.allclose(pin.mesh.extents, [21.2, 8.0, 8.0], atol=1.0e-5)
        )
        self.assertEqual(
            bridge.design_metrics[
                "source_keyway_center_inward_from_physical_crown_face_mm"
            ],
            27.825,
        )
        self.assertEqual(
            bridge.design_metrics["installed_keyway_center_from_nominal_seam_mm"],
            28.0,
        )

        right_arches = [
            part for part in self.arches if part.design_metrics["handedness"] == "right"
        ]
        left_arches = [
            part for part in self.arches if part.design_metrics["handedness"] == "left"
        ]
        self.assertEqual((len(left_arches), len(right_arches)), (2, 2))
        for part in left_arches + right_arches:
            metrics = part.design_metrics
            self.assertTrue(
                all(
                    value > 0.0
                    for value in metrics[
                        "crown_bridge_keyway_parent_intersection_volumes_mm3"
                    ]
                )
            )
            self.assertGreater(
                metrics["crown_bridge_keyway_hard_stop_roof_probe_volume_mm3"],
                0.0,
            )
            self.assertEqual(
                metrics[
                    "crown_bridge_keyway_source_center_inward_from_physical_face_mm"
                ],
                27.825,
            )
        self.assertTrue(
            all(part.design_metrics["fixed_crown_front_pin_ear_generated"] for part in right_arches)
        )
        self.assertTrue(
            all(not part.design_metrics["fixed_crown_front_pin_ear_generated"] for part in left_arches)
        )

        rear_ear_cassettes = [
            part
            for part in self.cassettes
            if part.design_metrics["fixed_crown_rear_pin_ear_generated"]
        ]
        self.assertEqual(len(rear_ear_cassettes), 9)
        for part in rear_ear_cassettes:
            record = part.design_metrics["fixed_crown_rear_pin_ear"]
            self.assertEqual(record["q_envelope_mm"], [122.8, 127.6])
            self.assertEqual(record["parent_spine_q_envelope_mm"], [124.4, 127.6])
            self.assertEqual(record["parent_spine_e_envelope_mm"], [138.0, 141.2])
            self.assertEqual(record["transition_angle_deg"], 45.0)
            self.assertGreater(record["parent_spine_occupied_volume_mm3"], 0.0)
            self.assertGreater(record["ear_parent_union_volume_mm3"], 0.0)
            self.assertGreater(
                record["retention_pin_hole_parent_intersection_volume_mm3"], 0.0
            )

        pin_installed = transformed_mesh(
            pin.mesh, pin.design_metrics["installed_from_saved_matrix_row_major"]
        )
        self.assertTrue(
            np.allclose(
                pin_installed.bounds,
                [[5.7, 124.3, 120.8], [13.7, 132.3, 142.0]],
                atol=2.0e-5,
            )
        )
        self.assertEqual(pin.design_metrics["split_slot_width_u_mm"], 1.2)
        self.assertEqual(pin.design_metrics["expanded_barb_outer_radius_mm"], 3.3)
        self.assertEqual(pin.design_metrics["parent_bore_diameter_mm"], 5.4)
        self.assertEqual(pin.design_metrics["radial_capture_each_side_mm"], 0.6)

    def test_all_nine_crown_bridges_clear_full_upward_lift_and_pin_is_void_mated(self) -> None:
        arch_by_key: dict[tuple[str, int, str], tuple[object, dict]] = {}
        for arch in self.arches:
            run_id = str(arch.design_metrics["run_id"])
            handedness = str(arch.design_metrics["handedness"])
            for placement in arch.design_metrics["authoritative_instance_placements"]:
                arch_by_key[(run_id, int(placement["bay_index_1_based"]), handedness)] = (
                    arch,
                    placement,
                )
        cassette_by_key = {
            (
                str(part.design_metrics["run_id"]),
                int(part.design_metrics["position_index_1_based"]),
            ): part
            for part in self.cassettes
        }
        deltas = np.linspace(-48.0, 0.0, 121)
        checked_lift_pairs = 0
        checked_pins = 0
        for placement in self.crown_bridge.design_metrics[
            "authoritative_instance_placements"
        ]:
            run_id = str(placement["run_id"])
            bay_index = int(placement["bay_index_1_based"])
            installed_bridge = transformed_mesh(
                self.crown_bridge.mesh,
                placement["bridge_saved_to_run_matrix_row_major"],
            )
            installed_pin = transformed_mesh(
                self.crown_pin.mesh,
                placement["pin_saved_to_run_matrix_row_major"],
            )
            stationary: list[tuple[trimesh.Trimesh, str]] = []
            for handedness in ("left", "right"):
                arch, arch_placement = arch_by_key[(run_id, bay_index, handedness)]
                installed_arch = transformed_mesh(
                    arch.mesh, arch_placement["arch_saved_to_run_matrix_row_major"]
                )
                cassette = cassette_by_key[
                    (run_id, int(arch_placement["cassette_index_1_based"]))
                ]
                installed_cassette = transformed_mesh(
                    cassette.mesh,
                    cassette.design_metrics["saved_print_transform"][
                        "saved_to_run_matrix_row_major"
                    ],
                )
                stationary.extend(
                    [
                        (installed_arch, f"{handedness} arch"),
                        (installed_cassette, f"{handedness} cassette"),
                    ]
                )
                for mate, label in (
                    (installed_arch, f"{handedness} arch"),
                    (installed_cassette, f"{handedness} cassette"),
                ):
                    volume, bounds = solid_overlap_volume(installed_pin, mate)
                    self.assertLessEqual(
                        volume,
                        1.0e-5,
                        f"{run_id} crown pin overlaps {label} by {volume:.6f} at {bounds}",
                    )
            volume, bounds = solid_overlap_volume(installed_pin, installed_bridge)
            self.assertLessEqual(
                volume,
                1.0e-5,
                f"{run_id} crown pin overlaps bridge by {volume:.6f} at {bounds}",
            )
            checked_pins += 1
            for delta_e in deltas:
                moving_bridge = installed_bridge.copy()
                moving_bridge.apply_translation([0.0, 0.0, float(delta_e)])
                for mate, label in stationary:
                    volume, bounds = solid_overlap_volume(moving_bridge, mate)
                    self.assertLessEqual(
                        volume,
                        1.0e-5,
                        f"{run_id} bay {bay_index} crown bridge delta {delta_e:.1f} "
                        f"overlaps {label} by {volume:.6f} at {bounds}",
                    )
                    checked_lift_pairs += 1
        self.assertEqual(checked_pins, 9)
        self.assertEqual(checked_lift_pairs, 9 * len(deltas) * 4)

    def test_all_nine_crown_pins_pass_compressed_insert_and_reverse_sweeps(self) -> None:
        report = generator.validate_crown_pin_parent_sweeps(
            self.cfg,
            arches=self.arches,
            cassettes=self.cassettes,
            crown_bridge=self.crown_bridge,
            crown_pin=self.crown_pin,
        )
        self.assertEqual(report["crown_interface_count"], 9)
        self.assertEqual(report["insertion_translation_station_count"], 49)
        self.assertEqual(
            report["compressed_insert_and_reverse_parent_boolean_pair_count"],
            9 * 49 * 3,
        )
        self.assertEqual(report["expanded_final_parent_boolean_pair_count"], 27)
        self.assertEqual(report["release_window_parent_boolean_pair_count"], 27)
        self.assertEqual(report["maximum_positive_parent_overlap_volume_mm3"], 0.0)
        self.assertEqual(report["compressed_proxy_maximum_outer_radius_mm"], 2.5)
        self.assertAlmostEqual(
            report["barb_to_rear_ear_axial_approach_mm"], 0.8, places=7
        )
        self.assertAlmostEqual(
            report["barb_radial_capture_each_side_mm"], 0.6, places=7
        )
        self.assertTrue(report["inverse_removal_uses_exact_reversed_states"])
        self.assertFalse(report["physical_flex_cycle_and_tool_reach_qualified"])
        self.assertIn("perpendicular to the plate", self.crown_pin.saved_orientation)
        self.assertEqual(
            self.crown_pin.design_metrics["saved_split_plane"],
            "saved x-z; perpendicular to build plate",
        )
        self.assertFalse(
            self.crown_pin.design_metrics["support_free_claim_allowed"]
        )
        self.assertFalse(
            self.crown_pin.design_metrics["production_orientation_allowed"]
        )
        self.assertTrue(
            self.crown_pin.design_metrics[
                "actual_parent_orientation_coupon_required"
            ]
        )

        rear_ear_cassettes = [
            part
            for part in self.cassettes
            if part.design_metrics["fixed_crown_rear_pin_ear_generated"]
        ]
        self.assertEqual(len(rear_ear_cassettes), 9)
        for part in rear_ear_cassettes:
            rear_ear_q_min = float(
                part.design_metrics["fixed_crown_rear_pin_ear"]["q_envelope_mm"][0]
            )
            expected_saved_plane = (
                float(part.design_metrics["depth_mm"])
                + float(part.design_metrics["ornament_visible_front_extension_mm"])
                - rear_ear_q_min
            )
            self.assertGreater(
                part.design_metrics[
                    "fixed_crown_rear_ear_q_min_plane_snapped_vertex_count"
                ],
                0,
            )
            self.assertAlmostEqual(
                part.design_metrics[
                    "fixed_crown_rear_ear_saved_q_min_plane_after_snap_mm"
                ],
                expected_saved_plane,
                places=7,
            )

    def test_arch_mortises_are_real_voids_cut_before_saved_normalization(self) -> None:
        for part in self.arches:
            metrics = part.design_metrics
            saved_y_min = float(metrics["saved_y_min_installed_mm"])
            for record in metrics["integral_top_tenons"]:
                center = (
                    float(record["local_x_from_spring_mm"]),
                    149.0 - saved_y_min,
                    9.0,
                )
                self.assertLess(probe_volume(part.mesh, center), 1.0e-8, part.name)
            spring_center = float(
                metrics["spring_tenon_center_from_support_crownward_mm"]
            )
            self.assertLess(
                probe_volume(part.mesh, (spring_center, 57.0 - saved_y_min, 9.0)),
                1.0e-8,
                part.name,
            )
            self.assertGreaterEqual(
                metrics["installed_coordinate_wedge_mortise_removed_volume_mm3"] + 1.0e-3,
                metrics[
                    "installed_coordinate_wedge_mortise_minimum_expected_volume_mm3"
                ],
            )

    def test_spring_receiver_q_and_all_18_arch_socket_centers_match(self) -> None:
        arch_centers: list[tuple[float, float, float]] = []
        for part in self.arches:
            metrics = part.design_metrics
            saved_y_min = float(metrics["saved_y_min_installed_mm"])
            x = float(metrics["spring_tenon_center_from_support_crownward_mm"])
            for placement in metrics["authoritative_instance_placements"]:
                matrix = np.asarray(
                    placement["arch_saved_to_run_matrix_row_major"], dtype=float
                )
                center = matrix @ np.asarray(
                    [x, 57.0 - saved_y_min, 9.0, 1.0], dtype=float
                )
                arch_centers.append(tuple(np.round(center[:3], 7)))

        socket_centers: list[tuple[float, float, float]] = []
        for part in self.corbels:
            metrics = part.design_metrics
            self.assertTrue(part.mesh.is_watertight, part.name)
            self.assertTrue(part.mesh.is_volume, part.name)
            self.assertEqual(
                metrics["spring_receiver_wall_projection_interval_mm"],
                [145.35, 154.15],
            )
            self.assertEqual(
                metrics["spring_receiver_housing_wall_projection_interval_mm"],
                [140.75, 158.75],
            )
            for placement in metrics["authoritative_instance_placements"]:
                matrix = np.asarray(
                    placement["saved_to_run_matrix_row_major"], dtype=float
                )
                for socket in metrics["spring_receivers"]:
                    source_s_min = float(
                        metrics["source_run_envelope_from_support_mm"][0]
                    )
                    center_saved = np.asarray(
                        [
                            57.0 - float(metrics["saved_source_e_min_mm"]),
                            float(socket["center_across_run_from_support_mm"])
                            - source_s_min,
                            149.75,
                            1.0,
                        ],
                        dtype=float,
                    )
                    center = matrix @ center_saved
                    socket_centers.append(tuple(np.round(center[:3], 7)))
                    self.assertLess(
                        probe_volume(
                            part.mesh,
                            tuple(float(value) for value in center_saved[:3]),
                        ),
                        1.0e-8,
                        part.name,
                    )
        self.assertEqual(len(arch_centers), 18)
        self.assertEqual(len(socket_centers), 18)
        self.assertEqual(sorted(arch_centers), sorted(socket_centers))

    def test_authoritative_arch_and_corbel_solids_have_no_final_overlap(self) -> None:
        """Real final-position arch/corbel solids must complement."""

        corbels = self.corbel_placements_by_station()
        checked_arches = 0
        for arch in self.arches:
            run_id = str(arch.design_metrics["run_id"])
            for placement in arch.design_metrics["authoritative_instance_placements"]:
                key = (
                    run_id,
                    round(float(placement["spring_station_local_s_mm"]), 7),
                )
                corbel, corbel_placement = corbels[key]
                installed_arch = transformed_mesh(
                    arch.mesh,
                    placement["arch_saved_to_run_matrix_row_major"],
                )
                installed_corbel = transformed_mesh(
                    corbel.mesh,
                    corbel_placement["saved_to_run_matrix_row_major"],
                )
                volume, bounds = solid_overlap_volume(installed_arch, installed_corbel)
                self.assertLessEqual(
                    volume,
                    1.0e-5,
                    f"{run_id} arch/corbel solid overlap {volume:.6f} mm^3 at {bounds}",
                )
                checked_arches += 1

        self.assertEqual(checked_arches, 18)

    def test_authoritative_cassette_and_corbel_solids_have_no_final_overlap(self) -> None:
        """Real final-position cassette/corbel solids must complement."""

        corbels = self.corbel_placements_by_station()
        checked_cassettes = 0
        for cassette in self.cassettes:
            metrics = cassette.design_metrics
            support = metrics["support_station"]
            key = (
                str(metrics["run_id"]),
                round(float(support["support_center_local_to_run_mm"]), 7),
            )
            corbel, corbel_placement = corbels[key]
            installed_cassette = transformed_mesh(
                cassette.mesh,
                metrics["saved_print_transform"]["saved_to_run_matrix_row_major"],
            )
            installed_corbel = transformed_mesh(
                corbel.mesh,
                corbel_placement["saved_to_run_matrix_row_major"],
            )
            volume, bounds = solid_overlap_volume(installed_cassette, installed_corbel)
            self.assertLessEqual(
                volume,
                1.0e-5,
                f"{metrics['logical_instance_id']} cassette/corbel solid overlap "
                f"{volume:.6f} mm^3 at {bounds}",
            )
            checked_cassettes += 1
        self.assertEqual(checked_cassettes, 18)

    def test_repacked_inside_corner_l_has_real_final_and_seating_clearance(self) -> None:
        report = generator.validate_inside_corner_l_assembly_clearance(
            self.cfg,
            plan=self.plan,
            cassettes=self.cassettes,
            corbels=self.corbels,
        )
        self.assertEqual(report["final_cross_pair_count"], 4)
        self.assertEqual(report["seating_sweep_boolean_pair_count"], 14)
        self.assertEqual(report["maximum_final_positive_overlap_volume_mm3"], 0.0)
        self.assertEqual(
            report["maximum_seating_sweep_positive_overlap_volume_mm3"], 0.0
        )
        self.assertAlmostEqual(
            report["visible_front_projection_beyond_cassette_mm"],
            float(
                self.cfg["nominal_geometry_snapshot"][
                    "corner_full_removable_facade_projection_beyond_cassette_mm"
                ]
            ),
            places=7,
        )
        snapshot = self.cfg["nominal_geometry_snapshot"]
        self.assertAlmostEqual(
            report["structural_arm_clearance_mm"],
            float(snapshot["corner_structural_arm_clearance_mm"]),
            places=7,
        )
        self.assertAlmostEqual(
            report["exact_corbel_to_corbel_plan_gap_mm"],
            float(snapshot["minimum_nominal_perpendicular_corbel_clearance_mm"]),
            places=7,
        )
        self.assertAlmostEqual(
            report[
                "exact_actual_visible_front_to_perpendicular_cap_plan_reserve_mm"
            ],
            float(
                snapshot[
                    "minimum_nominal_visible_front_to_perpendicular_corbel_plan_reserve_mm"
                ]
            ),
            places=7,
        )
        self.assertEqual(
            report["run_start_terminal_handing"],
            {
                "through_socket_offset_from_support_mm": 14.4,
                "return_socket_offset_from_support_mm": 14.4,
            },
        )

    def test_full_width_cap_and_outboard_lock_axes_are_embodied(self) -> None:
        for corbel in self.corbels:
            metrics = corbel.design_metrics
            cap = metrics["integrated_bearing_cap"]
            self.assertEqual(cap["base_run_envelope_at_e_128_mm"], [-24.0, 24.0])
            self.assertEqual(cap["top_run_envelope_at_e_138_mm"], [-24.0, 24.0])
            self.assertEqual(cap["side_flare_angle_deg"], 0.0)
            self.assertEqual(
                metrics[
                    "integrated_cap_lock_centers_s_q_from_support_and_rear_mm"
                ],
                [[-18.9, 57.55], [18.9, 95.45]],
            )
            self.assertGreaterEqual(
                float(cap["base_run_envelope_at_e_128_mm"][1])
                - 18.9
                - 1.9,
                3.2,
            )

    def test_all_22_installed_split_tail_locks_clear_real_cassettes_and_caps(self) -> None:
        """Every exact lock position is a void mate, not metadata-only geometry."""

        lock_cfg = self.cfg["corbel"]["integrated_cap_cassette_lock"]
        head_run, head_q = (
            float(value) for value in lock_cfg["pull_head_run_q_mm"]
        )
        head_e = tuple(float(value) for value in lock_cfg["pull_head_y_envelope_mm"])
        overall_height = (
            float(lock_cfg["tail_capture_shoulder_y_envelope_mm"][1])
            + float(self.cfg["joinery"]["minimum_wall_mm"])
            - head_e[0]
        )
        self.assertTrue(self.cassette_lock.mesh.is_watertight)
        self.assertTrue(self.cassette_lock.mesh.is_volume)
        self.assertEqual(len(self.cassette_lock.mesh.split()), 1)
        self.assertTrue(
            np.allclose(self.cassette_lock.mesh.bounds[0], [0.0, 0.0, 0.0])
        )
        self.assertTrue(
            np.allclose(
                self.cassette_lock.mesh.bounds[1],
                [head_run, head_q, overall_height],
                atol=1.0e-6,
            )
        )

        corbels = self.corbel_placements_by_station()
        checked_locks = 0
        for cassette in self.cassettes:
            metrics = cassette.design_metrics
            support = metrics["support_station"]
            key = (
                str(metrics["run_id"]),
                round(float(support["support_center_local_to_run_mm"]), 7),
            )
            corbel, corbel_placement = corbels[key]
            installed_cassette = transformed_mesh(
                cassette.mesh,
                metrics["saved_print_transform"]["saved_to_run_matrix_row_major"],
            )
            installed_corbel = transformed_mesh(
                corbel.mesh,
                corbel_placement["saved_to_run_matrix_row_major"],
            )
            physical_start = float(metrics["physical_interval_local_mm"][0])
            for receiver in metrics["integrated_cap_cassette_lock_receivers"]:
                installed_lock = self.cassette_lock.mesh.copy()
                # Saved lock x/y are normalized around the configured pull
                # head; saved z=0 is the authoritative installed head datum.
                installed_lock.apply_translation(
                    [
                        physical_start
                        + float(receiver["center_x_relative_to_physical_part_mm"])
                        - head_run / 2.0,
                        float(receiver["center_q_from_rear_mm"]) - head_q / 2.0,
                        head_e[0],
                    ]
                )
                for mate, label in (
                    (installed_cassette, "cassette"),
                    (installed_corbel, "integral corbel cap"),
                ):
                    volume, bounds = solid_overlap_volume(installed_lock, mate)
                    self.assertLessEqual(
                        volume,
                        1.0e-5,
                        f"{metrics['logical_instance_id']} "
                        f"{receiver['ownership']} lock overlaps {label} by "
                        f"{volume:.6f} mm^3 at {bounds}",
                    )
                checked_locks += 1
        self.assertEqual(checked_locks, 22)

    def test_all_22_compressed_locks_clear_full_75mm_service_sweep(self) -> None:
        """Sample the exact declared straight service stroke every 0.4 mm."""

        lock_cfg = self.cfg["corbel"]["integrated_cap_cassette_lock"]
        head_run, head_q = (
            float(value) for value in lock_cfg["pull_head_run_q_mm"]
        )
        head_e = tuple(float(value) for value in lock_cfg["pull_head_y_envelope_mm"])
        overall_height = (
            float(lock_cfg["tail_capture_shoulder_y_envelope_mm"][1])
            + float(self.cfg["joinery"]["minimum_wall_mm"])
            - head_e[0]
        )
        proxy = generator.final_x_cassette_lock_compressed_insertion_proxy(
            self.cfg
        )
        self.assertTrue(proxy.is_watertight)
        self.assertTrue(proxy.is_volume)
        self.assertTrue(np.allclose(proxy.bounds[0], [0.0, 0.0, 0.0]))
        self.assertTrue(
            np.allclose(
                proxy.extents,
                [head_run, head_q, overall_height],
                atol=1.0e-6,
            )
        )
        service_stroke_mm = 75.0
        deltas = np.linspace(
            -service_stroke_mm,
            0.0,
            int(round(service_stroke_mm / 0.4)) + 1,
        )
        corbels = self.corbel_placements_by_station()
        checked_positions = 0
        checked_locks = 0
        for cassette in self.cassettes:
            metrics = cassette.design_metrics
            support = metrics["support_station"]
            key = (
                str(metrics["run_id"]),
                round(float(support["support_center_local_to_run_mm"]), 7),
            )
            corbel, corbel_placement = corbels[key]
            installed_cassette = transformed_mesh(
                cassette.mesh,
                metrics["saved_print_transform"]["saved_to_run_matrix_row_major"],
            )
            installed_corbel = transformed_mesh(
                corbel.mesh,
                corbel_placement["saved_to_run_matrix_row_major"],
            )
            physical_start = float(metrics["physical_interval_local_mm"][0])
            for receiver in metrics["integrated_cap_cassette_lock_receivers"]:
                self.assertIn(
                    float(receiver["center_s_from_support_mm"]),
                    (-18.9, 18.9),
                )
                seated_proxy = proxy.copy()
                seated_proxy.apply_translation(
                    [
                        physical_start
                        + float(receiver["center_x_relative_to_physical_part_mm"])
                        - head_run / 2.0,
                        float(receiver["center_q_from_rear_mm"]) - head_q / 2.0,
                        head_e[0],
                    ]
                )
                for delta_e in deltas:
                    moving = seated_proxy.copy()
                    moving.apply_translation([0.0, 0.0, float(delta_e)])
                    for mate, label in (
                        (installed_cassette, "cassette"),
                        (installed_corbel, "integral corbel cap/X"),
                    ):
                        volume, bounds = solid_overlap_volume(moving, mate)
                        self.assertLessEqual(
                            volume,
                            1.0e-5,
                            f"{metrics['logical_instance_id']} "
                            f"{receiver['ownership']} compressed lock at "
                            f"delta {delta_e:.3f} overlaps {label} by "
                            f"{volume:.6f} mm^3 at {bounds}",
                        )
                        checked_positions += 1
                checked_locks += 1
        self.assertEqual(checked_locks, 22)
        self.assertEqual(checked_positions, 22 * len(deltas) * 2)

    def test_cassette_lock_head_requires_and_embodies_its_active_config_datum(self) -> None:
        missing = copy.deepcopy(self.cfg)
        del missing["corbel"]["integrated_cap_cassette_lock"][
            "pull_head_run_q_mm"
        ]
        with self.assertRaises(KeyError):
            generator.final_x_cassette_lock(missing)
        with self.assertRaises(KeyError):
            generator.final_x_cassette_lock_compressed_insertion_proxy(missing)

        mutated = copy.deepcopy(self.cfg)
        mutated_head = [8.4, 7.6]
        mutated["corbel"]["integrated_cap_cassette_lock"][
            "pull_head_run_q_mm"
        ] = mutated_head
        with self.assertRaises(ValueError):
            generator.final_x_cassette_lock(mutated)
        with self.assertRaises(ValueError):
            generator.final_x_cassette_lock_compressed_insertion_proxy(mutated)
        self.assertEqual(
            self.cassette_lock.design_metrics["pull_head_run_q_e_mm"][:2],
            self.cfg["corbel"]["integrated_cap_cassette_lock"][
                "pull_head_run_q_mm"
            ],
        )

    def test_full_straight_vertical_arch_lift_is_collision_free(self) -> None:
        """Sample every 0.4 mm through the complete 22 mm receiver lift."""

        corbels = self.corbel_placements_by_station()
        top_joint = self.cfg["tied_arcade"][
            "cassette_final_x_vertical_tenon_joint"
        ]
        spring_joint = self.cfg["tied_arcade"]["spring_final_x_vertical_joint"]
        lift_mm = max(
            float(top_joint["tenon_engagement_height_mm"]),
            float(spring_joint["tenon_engagement_height_mm"]),
        )
        step_mm = 0.4
        deltas = np.linspace(
            -lift_mm,
            0.0,
            int(round(lift_mm / step_mm)) + 1,
        )
        checked_positions = 0
        for arch in self.arches:
            run_id = str(arch.design_metrics["run_id"])
            for placement in arch.design_metrics["authoritative_instance_placements"]:
                key = (
                    run_id,
                    round(float(placement["spring_station_local_s_mm"]), 7),
                )
                corbel, corbel_placement = corbels[key]
                installed_arch = transformed_mesh(
                    arch.mesh,
                    placement["arch_saved_to_run_matrix_row_major"],
                )
                installed_corbel = transformed_mesh(
                    corbel.mesh,
                    corbel_placement["saved_to_run_matrix_row_major"],
                )
                for delta_e in deltas:
                    lifted = installed_arch.copy()
                    lifted.apply_translation([0.0, 0.0, float(delta_e)])
                    volume, bounds = solid_overlap_volume(lifted, installed_corbel)
                    self.assertLessEqual(
                        volume,
                        1.0e-5,
                        f"{run_id} vertical lift delta {delta_e:.3f} mm overlaps "
                        f"corbel by {volume:.6f} mm^3 at {bounds}",
                    )
                    checked_positions += 1
        self.assertEqual(checked_positions, 18 * len(deltas))

    def test_arch_to_cassette_full_vertical_lift_is_collision_free(self) -> None:
        """Each moving half clears its actual mating cassette for the full lift."""

        cassettes = {
            (
                str(part.design_metrics["run_id"]),
                int(part.design_metrics["position_index_1_based"]),
            ): part
            for part in self.cassettes
        }
        self.assertEqual(len(cassettes), 18)
        top_joint = self.cfg["tied_arcade"][
            "cassette_final_x_vertical_tenon_joint"
        ]
        spring_joint = self.cfg["tied_arcade"]["spring_final_x_vertical_joint"]
        lift_mm = max(
            float(top_joint["tenon_engagement_height_mm"]),
            float(spring_joint["tenon_engagement_height_mm"]),
        )
        step_mm = 0.4
        deltas = np.linspace(
            -lift_mm,
            0.0,
            int(round(lift_mm / step_mm)) + 1,
        )
        checked_positions = 0
        for arch in self.arches:
            run_id = str(arch.design_metrics["run_id"])
            for placement in arch.design_metrics["authoritative_instance_placements"]:
                cassette = cassettes[
                    (run_id, int(placement["cassette_index_1_based"]))
                ]
                installed_arch = transformed_mesh(
                    arch.mesh,
                    placement["arch_saved_to_run_matrix_row_major"],
                )
                installed_cassette = transformed_mesh(
                    cassette.mesh,
                    cassette.design_metrics["saved_print_transform"][
                        "saved_to_run_matrix_row_major"
                    ],
                )
                for delta_e in deltas:
                    lifted = installed_arch.copy()
                    lifted.apply_translation([0.0, 0.0, float(delta_e)])
                    volume, bounds = solid_overlap_volume(
                        lifted, installed_cassette
                    )
                    self.assertLessEqual(
                        volume,
                        1.0e-5,
                        f"{run_id} cassette {placement['cassette_index_1_based']} "
                        f"vertical lift delta {delta_e:.3f} mm overlaps by "
                        f"{volume:.6f} mm^3 at {bounds}",
                    )
                    checked_positions += 1
        self.assertEqual(checked_positions, 18 * len(deltas))


if __name__ == "__main__":
    unittest.main(verbosity=2)
