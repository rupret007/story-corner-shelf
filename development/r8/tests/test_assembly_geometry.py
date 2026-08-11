#!/usr/bin/env python3
"""Exact qualification tests for the R8 one-bay assembly interface."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


R8 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R8))

import accessory_geometry as accessory  # noqa: E402
import assembly_geometry as assembly  # noqa: E402
import interface_geometry as interface  # noqa: E402
import shelf_geometry as shelf  # noqa: E402


class R8AssemblyGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seated = assembly.build_one_bay(keeper_state="seated")
        cls.released = assembly.build_one_bay(keeper_state="deflected")
        cls.tiled = assembly.build_tiled_through_run()
        cls.tiled_released = assembly.build_tiled_through_run(
            release_cassette_index=3
        )

    def assertOneBody(self, mesh) -> None:  # noqa: N802
        self.assertTrue(assembly.mesh_is_one_body(mesh))
        self.assertTrue(mesh.is_watertight)
        self.assertTrue(mesh.is_winding_consistent)
        self.assertGreater(mesh.volume, 0.0)
        self.assertEqual(len(mesh.split(only_watertight=False)), 1)

    def assertNoPositiveOverlap(self, first, second) -> None:  # noqa: N802
        self.assertLessEqual(
            assembly.positive_overlap_volume(first, second),
            assembly.COLLISION_TOLERANCE_MM3,
        )

    def test_release_material_and_load_gates_fail_closed(self) -> None:
        self.assertTrue(assembly.QUALIFICATION_ONLY)
        self.assertFalse(assembly.PRODUCTION_READY)
        self.assertFalse(assembly.PRINT_PROFILE_RELEASED)
        self.assertFalse(assembly.WALL_FASTENER_BORES_EMITTED)
        self.assertEqual(
            (assembly.RATED_LOAD_KG, assembly.RATED_LOAD_LB), (0.0, 0.0)
        )
        self.assertEqual(assembly.REQUIRED_PRINT_MATERIAL, "PETG")
        self.assertEqual(assembly.A1_MINI_BUILD_VOLUME_MM, (180.0, 180.0, 180.0))
        self.assertFalse(assembly.REGISTRATION_STRUCTURAL_CREDIT)
        self.assertFalse(assembly.KEEPER_STRUCTURAL_CREDIT)
        self.assertEqual(assembly.NOMINAL_PRINTED_PART_COUNT, 5)
        self.assertTrue(assembly.RAIL_SERVICE_REQUIRES_MODULE_REMOVAL)

    def test_depth_transform_puts_the_open_rear_at_the_wall(self) -> None:
        transform = assembly.cassette_source_to_installed_transform()
        source_front = np.asarray((20.0, 0.0, 10.0, 1.0))
        source_rear = np.asarray((20.0, shelf.SHELF_DEPTH_MM, 10.0, 1.0))
        np.testing.assert_allclose(
            transform @ source_front,
            (20.0, shelf.SHELF_DEPTH_MM, 170.0, 1.0),
            atol=1.0e-10,
        )
        np.testing.assert_allclose(
            transform @ source_rear,
            (20.0, 0.0, 170.0, 1.0),
            atol=1.0e-10,
        )
        np.testing.assert_allclose(
            self.seated.cassette.installed.bounds,
            (
                (0.0, 0.0, shelf.CORBEL_INSTALLED_HEIGHT_MM),
                (
                    assembly.NOMINAL_BAY_LENGTH_MM,
                    shelf.SHELF_DEPTH_MM,
                    shelf.CORBEL_INSTALLED_HEIGHT_MM + shelf.CASSETTE_HEIGHT_MM,
                ),
            ),
            atol=1.0e-5,
        )

        # A mid-height witness in the first clear U-box panel sees no broad
        # wall at installed y=0, but the same witness is solid at the front.
        wall_witness = assembly._box((19.0, 21.0), (0.1, 0.5), (169.0, 171.0))
        front_witness = assembly._box(
            (19.0, 21.0), (151.9, 152.3), (169.0, 171.0)
        )
        self.assertNoPositiveOverlap(
            self.seated.cassette.installed, wall_witness
        )
        self.assertAlmostEqual(
            assembly.positive_overlap_volume(
                self.seated.cassette.installed, front_witness
            ),
            front_witness.volume,
            delta=5.0e-5,
        )

    def test_registration_cuts_are_shallow_exact_and_leave_one_body(self) -> None:
        cassette = self.seated.cassette
        for mesh in (
            cassette.source_seed,
            cassette.source_registered,
            cassette.installed,
        ):
            self.assertOneBody(mesh)
        self.assertEqual(assembly.REGISTRATION_CLEARANCE_PER_FACE_MM, 0.4)
        self.assertAlmostEqual(
            assembly.REGISTRATION_POCKET_X_MM - assembly.REGISTRATION_KEY_X_MM,
            2.0 * assembly.REGISTRATION_CLEARANCE_PER_FACE_MM,
            places=12,
        )
        self.assertAlmostEqual(
            assembly.REGISTRATION_POCKET_Y_MM - assembly.REGISTRATION_KEY_Y_MM,
            2.0 * assembly.REGISTRATION_CLEARANCE_PER_FACE_MM,
            places=12,
        )
        self.assertEqual(
            cassette.metrics.bottom_skin_mm - assembly.REGISTRATION_POCKET_DEPTH_MM,
            assembly.REGISTRATION_REMAINING_BOTTOM_SKIN_MM,
        )
        self.assertEqual(assembly.REGISTRATION_REMAINING_BOTTOM_SKIN_MM, 1.0)
        self.assertAlmostEqual(
            cassette.source_seed.volume - cassette.source_registered.volume,
            154.88,
            delta=0.02,
        )

    def test_two_caps_publish_exact_seam_bearing_and_net_contact(self) -> None:
        left, right = self.seated.bearing_contacts
        self.assertEqual(assembly.SEAM_GAP_MM, 0.35)
        self.assertEqual(
            (assembly.LEFT_SUPPORT_CENTER_X_MM, assembly.RIGHT_SUPPORT_CENTER_X_MM),
            (-0.175, assembly.NOMINAL_BAY_LENGTH_MM + 0.175),
        )
        self.assertEqual(assembly.CAP_BEARING_WIDTH_MM, 15.825)
        self.assertEqual(left.cap_x_bounds_mm, (-16.175, 15.825))
        self.assertEqual(
            right.cap_x_bounds_mm,
            (
                assembly.NOMINAL_BAY_LENGTH_MM - 15.825,
                assembly.NOMINAL_BAY_LENGTH_MM + 16.175,
            ),
        )
        self.assertEqual(left.cassette_overlap_x_bounds_mm, (0.0, 15.825))
        self.assertEqual(
            right.cassette_overlap_x_bounds_mm,
            (
                assembly.NOMINAL_BAY_LENGTH_MM - 15.825,
                assembly.NOMINAL_BAY_LENGTH_MM,
            ),
        )
        for datum in (left, right):
            self.assertEqual(
                datum.selected_end_land_width_mm,
                shelf.SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
            )
            self.assertEqual(datum.pocket_plan_area_mm2, 51.2)
            self.assertEqual(datum.net_cap_contact_area_mm2, 2360.53)
            self.assertAlmostEqual(
                datum.net_selected_land_contact_area_mm2, 924.16, places=9
            )
            self.assertEqual(
                datum.contact_z_mm, shelf.CORBEL_INSTALLED_HEIGHT_MM
            )

    def test_structural_d_frame_cores_are_unchanged_and_additions_only(self) -> None:
        frozen_source_digest = accessory.mesh_geometry_digest(
            shelf.build_d_frame_corbel()
        )
        for support in (
            self.seated.left_support,
            self.seated.right_support,
            self.released.right_support,
        ):
            with self.subTest(side=support.side, state=support.keeper_state):
                self.assertOneBody(support.source_core)
                self.assertOneBody(support.installed_core)
                self.assertOneBody(support.body)
                self.assertEqual(
                    accessory.mesh_geometry_digest(support.source_core),
                    frozen_source_digest,
                )
                restored = assembly.transformed(
                    support.installed_core,
                    np.linalg.inv(support.source_to_installed),
                )
                self.assertEqual(
                    accessory.mesh_geometry_digest(restored),
                    frozen_source_digest,
                )
                retained = assembly.positive_overlap_volume(
                    support.installed_core, support.body
                )
                self.assertAlmostEqual(
                    retained, support.installed_core.volume, delta=0.05
                )
                self.assertGreater(support.body.volume, support.installed_core.volume)

    def test_left_uses_exact_eligible_through_boss_contract_and_right_is_smooth(self) -> None:
        left = self.seated.left_support
        eligibility = left.rail_eligibility
        self.assertIsNotNone(eligibility)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(
            (
                eligibility.run,
                eligibility.support_index,
                eligibility.support_count,
                eligibility.is_corner,
            ),
            ("through", 1, 9, False),
        )
        self.assertEqual(len(left.rail_mount_bosses), 4)
        self.assertEqual(len(left.registration_keys), 2)
        self.assertIsNotNone(left.keeper)

        exact = interface.build_eligible_d_frame_wrapper("through", 1, 9)
        placement = assembly.rail_local_to_assembly_transform()
        np.testing.assert_allclose(
            left.source_to_installed,
            placement @ exact.source_to_installed,
            atol=1.0e-12,
        )
        for actual, local in zip(left.rail_mount_bosses, exact.boss_parts):
            expected = assembly.transformed(local, placement)
            self.assertEqual(
                accessory.mesh_geometry_digest(actual),
                accessory.mesh_geometry_digest(expected),
            )

        right = self.seated.right_support
        self.assertIsNone(right.rail_eligibility)
        self.assertEqual(right.rail_mount_bosses, ())
        self.assertEqual(len(right.registration_keys), 2)
        self.assertIsNotNone(right.keeper)

    def test_ineligible_support_station_and_wrong_key_states_fail_closed(self) -> None:
        bad_supports = (
            {"support_index": 0},
            {"support_index": 8},
            {"support_count": 2},
            {"is_corner": True},
        )
        for kwargs in bad_supports:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    assembly.build_rail_ready_left_support(**kwargs)
        for invalid_support in (True, 1.0, "1"):
            with self.subTest(invalid_support=invalid_support):
                with self.assertRaises(ValueError):
                    assembly.build_rail_ready_left_support(
                        support_index=invalid_support
                    )
        with self.assertRaises(IndexError):
            assembly.blank_module_service_transforms(3)
        for invalid_station in (True, 1.0, "1"):
            with self.subTest(invalid_station=invalid_station):
                with self.assertRaises(TypeError):
                    assembly.blank_module_service_transforms(invalid_station)
        with self.assertRaises(ValueError):
            assembly.build_installed_retained_blank(latch_state="wrong")
        with self.assertRaises(ValueError):
            assembly.build_installed_support("left", keeper_state="wrong")
        with self.assertRaises(ValueError):
            assembly.build_support_variant(
                "terminal_start", 16.0, 0, keeper_state="deflected"
            )
        with self.assertRaises(ValueError):
            assembly.build_smooth_interior_support(
                support_index=2, next_keeper_state="seated"
            )
        with self.assertRaises(ValueError):
            assembly.build_rail_interior_support(
                assembly.THROUGH_RUN_LAYOUT.corbel_centers_mm[-2],
                support_index=assembly.RAIL_SUPPORT_COUNT - 2,
            )
        with self.assertRaises(IndexError):
            assembly.build_tiled_through_run(release_cassette_index=8)
        for invalid_release in (True, 1.0, "1"):
            with self.subTest(invalid_release=invalid_release):
                with self.assertRaises(TypeError):
                    assembly.build_tiled_through_run(
                        release_cassette_index=invalid_release
                    )
        with self.assertRaises(ValueError):
            interface.build_mounted_retention_rail(clearance_mm=0.5)

        for run, count in (("through", 3), ("through", 8), ("return", 4)):
            start = assembly.build_terminal_start_support(
                16.0, run=run, support_count=count
            )
            dynamic = assembly.build_rail_interior_support(
                support_index=1,
                run=run,
                support_count=count,
                next_keeper_state="seated" if count == 3 else None,
            )
            end = assembly.build_terminal_end_support(
                500.0, run=run, support_count=count
            )
            self.assertEqual(
                (start.support_index, dynamic.support_index, end.support_index),
                (0, 1, count - 1),
            )
            self.assertEqual(
                (start.side, dynamic.side, end.side),
                ("terminal_start", "interior", "terminal_end"),
            )
            self.assertTrue(dynamic.rail_eligibility.eligible)
            self.assertEqual(dynamic.support_count, count)
            self.assertEqual(len(dynamic.registration_keys), 2)
            self.assertEqual((start.keepers, end.keepers), ((), ()))

        wrong = interface.wrong_key_orientation(
            interface.build_retained_accessory(
                "blank", latch_state="deflected"
            )
        )
        at_entry = assembly.transformed(
            wrong, assembly.blank_module_service_transforms().insertion
        )
        self.assertGreater(
            assembly.positive_overlap_volume(
                self.seated.mounted_rail, at_entry
            ),
            10.0,
        )

    def test_nominal_final_is_contact_without_positive_collision(self) -> None:
        cassette = self.seated.cassette.installed
        left = self.seated.left_support.body
        right = self.seated.right_support.body
        self.assertNoPositiveOverlap(cassette, left)
        self.assertNoPositiveOverlap(cassette, right)
        self.assertNoPositiveOverlap(left, right)

        # Both support caps end at the cassette underside plane: this is the
        # intended zero-volume bearing contact, not a Boolean clearance gap.
        self.assertAlmostEqual(float(left.bounds[1, 2]), 163.4, places=4)
        self.assertAlmostEqual(float(right.bounds[1, 2]), 163.4, places=4)
        self.assertEqual(float(cassette.bounds[0, 2]), 160.0)
        for support in (
            self.seated.left_support,
            self.seated.right_support,
        ):
            self.assertEqual(float(support.installed_core.bounds[1, 2]), 160.0)

    def test_nominal_cable_system_is_explicit_one_body_and_collision_free(self) -> None:
        self.assertEqual(self.seated.rail_station_index, 1)
        np.testing.assert_allclose(
            self.seated.mounted_rail.bounds,
            ((-18.175, 17.0, 48.0), (17.825, 25.8, 136.0)),
            atol=1.0e-6,
        )
        parts = (
            ("cassette", self.seated.cassette.installed),
            ("left_support", self.seated.left_support.body),
            ("right_support", self.seated.right_support.body),
            ("rail", self.seated.mounted_rail),
            ("blank", self.seated.seated_retained_blank),
        )
        for _name, mesh in parts:
            self.assertOneBody(mesh)
        for index, (first_name, first) in enumerate(parts):
            for second_name, second in parts[index + 1 :]:
                with self.subTest(first=first_name, second=second_name):
                    self.assertNoPositiveOverlap(first, second)

    def test_registration_accepts_exact_clearance_then_fails_closed(self) -> None:
        cassette = self.seated.cassette.installed
        supports = (
            self.seated.left_support.body,
            self.seated.right_support.body,
        )
        for axis in ("x", "y"):
            at_clearance = assembly.transformed(
                cassette, assembly.translation(**{axis: 0.4})
            )
            blocked = assembly.transformed(
                cassette, assembly.translation(**{axis: 0.8})
            )
            for support in supports:
                self.assertNoPositiveOverlap(at_clearance, support)
            self.assertGreater(
                sum(
                    assembly.positive_overlap_volume(blocked, support)
                    for support in supports
                ),
                1.0,
            )

    def test_seated_keeper_blocks_lift_and_released_keeper_clears(self) -> None:
        self.assertEqual(self.released.left_support.keeper_state, "seated")
        self.assertEqual(self.released.right_support.keeper_state, "deflected")
        seated_cassette = self.seated.cassette.installed
        right = self.seated.right_support.body
        at_contact = assembly.transformed(
            seated_cassette,
            assembly.translation(z=assembly.KEEPER_CONTACT_LIFT_MM),
        )
        blocked = assembly.transformed(
            seated_cassette,
            assembly.translation(z=assembly.KEEPER_BLOCKING_LIFT_MM),
        )
        self.assertNoPositiveOverlap(at_contact, right)
        self.assertGreater(
            assembly.positive_overlap_volume(blocked, right), 1.0
        )

        released_right = self.released.right_support.body
        for offset in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0):
            lifted = assembly.transformed(
                self.released.cassette.installed,
                assembly.translation(z=offset),
            )
            self.assertNoPositiveOverlap(lifted, released_right)

        proxy = assembly.keeper_strain_proxy()
        self.assertEqual(proxy.tip_deflection_mm, 1.8)
        self.assertAlmostEqual(proxy.surface_strain, 0.027, places=12)
        self.assertTrue(proxy.below_three_percent)
        self.assertFalse(assembly.KEEPER_STRUCTURAL_CREDIT)

    def test_rail_install_drop_and_reverse_service_clear_the_full_bay(self) -> None:
        rail = interface.build_mounted_retention_rail()
        service = assembly.rail_mount_service_transforms()
        self.assertEqual(service.increment_mm, 0.4)
        self.assertEqual(len(service.approach), 7)
        self.assertEqual(len(service.drop), 11)
        np.testing.assert_allclose(service.approach[-1], service.insertion)
        np.testing.assert_allclose(service.drop[-1], service.seated)
        fixed = (
            self.seated.cassette.installed,
            self.seated.left_support.body,
            self.seated.right_support.body,
        )
        for phase, matrices in (
            ("approach", service.approach),
            ("drop", service.drop),
            ("reverse_lift", service.removal_lift),
            ("reverse_out", service.removal_outward),
        ):
            for index, matrix in enumerate(matrices):
                positioned = assembly.transformed(rail, matrix)
                for target_index, target in enumerate(fixed):
                    with self.subTest(
                        phase=phase,
                        index=index,
                        target=target_index,
                    ):
                        self.assertNoPositiveOverlap(positioned, target)

        # Removing a rail requires its modules to be removed first.  Without
        # the prescribed 4 mm lift, an outward pull remains boss-retained.
        unauthorized = assembly.transformed(
            rail, assembly.translation(y=0.8) @ service.seated
        )
        self.assertGreater(
            assembly.positive_overlap_volume(
                unauthorized, self.seated.left_support.body
            ),
            1.0,
        )

    def test_blank_module_service_clears_rail_supports_and_cassette(self) -> None:
        moving = interface.build_retained_accessory(
            "blank", latch_state="deflected"
        )
        service = assembly.blank_module_service_transforms()
        self.assertEqual(service.increment_mm, 0.4)
        self.assertEqual(len(service.approach), 17)
        self.assertEqual(len(service.drop), 21)
        fixed = (
            self.seated.mounted_rail,
            self.seated.left_support.body,
            self.seated.right_support.body,
            self.seated.cassette.installed,
        )
        for phase, matrices in (
            ("approach", service.approach),
            ("drop", service.drop),
            ("reverse_lift", service.removal_lift),
            ("reverse_out", service.removal_outward),
        ):
            for index, matrix in enumerate(matrices):
                positioned = assembly.transformed(moving, matrix)
                for target_index, target in enumerate(fixed):
                    with self.subTest(
                        phase=phase,
                        index=index,
                        target=target_index,
                    ):
                        self.assertNoPositiveOverlap(positioned, target)

    def test_released_install_and_reverse_removal_clear_every_point_two_mm(self) -> None:
        service = assembly.service_transforms()
        self.assertEqual(service.increment_mm, 0.2)
        self.assertEqual(service.lift_mm, 2.0)
        self.assertEqual(len(service.installation), 11)
        self.assertEqual(len(service.removal), 11)
        self.assertEqual(
            tuple(matrix[2, 3] for matrix in service.installation),
            tuple(2.0 - 0.2 * index for index in range(11)),
        )
        for phase, stations in (
            ("install", service.installation),
            ("remove", service.removal),
        ):
            for index, transform in enumerate(stations):
                with self.subTest(phase=phase, index=index):
                    cassette = assembly.transformed(
                        self.released.cassette.installed, transform
                    )
                    self.assertNoPositiveOverlap(
                        cassette, self.released.left_support.body
                    )
                    self.assertNoPositiveOverlap(
                        cassette, self.released.right_support.body
                    )
                    self.assertNoPositiveOverlap(
                        cassette, self.released.mounted_rail
                    )
                    self.assertNoPositiveOverlap(
                        cassette, self.released.seated_retained_blank
                    )

    def test_four_support_families_have_exact_keys_keepers_and_print_layers(self) -> None:
        start = assembly.build_terminal_start_support()
        end = assembly.build_terminal_end_support()
        smooth = assembly.build_smooth_interior_support()
        rail = assembly.build_rail_interior_support()
        penultimate = assembly.build_rail_interior_support(
            assembly.THROUGH_RUN_LAYOUT.corbel_centers_mm[-2],
            support_index=assembly.RAIL_SUPPORT_COUNT - 2,
            next_keeper_state="seated",
        )
        self.assertEqual(
            tuple(item.side for item in (start, end, smooth, rail)),
            ("terminal_start", "terminal_end", "interior", "interior"),
        )
        self.assertEqual(
            tuple(len(item.registration_keys) for item in (start, end, smooth, rail)),
            (1, 1, 2, 2),
        )
        self.assertAlmostEqual(
            float(np.mean(start.registration_keys[0].bounds[:, 0])), 3.2, places=6
        )
        self.assertAlmostEqual(
            float(np.mean(end.registration_keys[0].bounds[:, 0])),
            assembly.THROUGH_RUN_LAYOUT.length_mm - 3.2,
            places=6,
        )
        self.assertIsNone(start.keeper)
        self.assertIsNone(start.next_keeper)
        self.assertIsNone(end.keeper)
        self.assertIsNone(end.next_keeper)
        for terminal in (start, end):
            self.assertIsNone(terminal.rail_eligibility)
            self.assertEqual(terminal.rail_mount_bosses, ())
            self.assertLessEqual(
                float(terminal.body.bounds[1, 1]), shelf.SHELF_DEPTH_MM
            )
            self.assertAlmostEqual(float(terminal.body.bounds[1, 2]), 161.0)
            self.assertGreaterEqual(
                float(terminal.body.bounds[0, 0]),
                terminal.center_x_mm - 16.0 - 5.0e-5,
            )
            self.assertLessEqual(
                float(terminal.body.bounds[1, 0]),
                terminal.center_x_mm + 16.0 + 5.0e-5,
            )
        self.assertAlmostEqual(
            float(np.mean(smooth.keeper.bounds[:, 0])),
            smooth.center_x_mm - 8.175,
            delta=1.0e-5,
        )
        self.assertIsNone(smooth.rail_eligibility)
        self.assertTrue(rail.rail_eligibility.eligible)
        self.assertEqual(len(rail.rail_mount_bosses), 4)
        self.assertEqual(len(penultimate.keepers), 2)
        self.assertAlmostEqual(
            float(np.mean(penultimate.keeper.bounds[:, 0])),
            penultimate.center_x_mm - 8.175,
            delta=5.0e-5,
        )
        self.assertAlmostEqual(
            float(np.mean(penultimate.next_keeper.bounds[:, 0])),
            penultimate.center_x_mm + 8.175,
            delta=5.0e-5,
        )
        self.assertTrue(penultimate.rail_eligibility.eligible)

        for support in (start, end, smooth, rail, penultimate):
            self.assertOneBody(support.body)
            oriented = assembly.orient_installed_support_for_print(support.body)
            envelope = shelf.print_envelope_with_margins(
                oriented,
                brim_mm=5.0,
                brim_object_gap_mm=0.1,
                reserve_per_bed_edge_mm=2.0,
                available_build_volume_mm=assembly.A1_MINI_BUILD_VOLUME_MM,
            )
            self.assertTrue(envelope.fits)
            layers = interface.saved_oriented_layer_island_report(
                oriented, layer_height_mm=0.2
            )
            self.assertEqual(layers.sampled_layer_count, 160)
            self.assertEqual(layers.island_layer_indices, ())
            self.assertFalse(layers.support_required)

    def test_terminal_pockets_stay_inside_end_lands_and_publish_full_cap_contact(self) -> None:
        first = self.tiled.cassettes[0]
        last = self.tiled.cassettes[-1]
        first_pocket = first.registration_pockets_source[0]
        last_pocket = last.registration_pockets_source[1]
        self.assertGreaterEqual(float(first_pocket.bounds[0, 0]), 0.0)
        self.assertLessEqual(
            float(first_pocket.bounds[1, 0]),
            shelf.SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
        )
        last_length = last.metrics.module_length_mm
        self.assertGreaterEqual(
            float(last_pocket.bounds[0, 0]),
            last_length - shelf.SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
        )
        self.assertLessEqual(float(last_pocket.bounds[1, 0]), last_length)

        for side, contact in (
            ("left", self.tiled.bearing_contacts[0][0]),
            ("right", self.tiled.bearing_contacts[-1][1]),
        ):
            self.assertIsInstance(contact, assembly.TerminalBearingContact)
            self.assertEqual(contact.cap_overlap_width_mm, 32.0)
            self.assertEqual(
                contact.key_offset_from_support_center_mm,
                -12.8 if side == "left" else 12.8,
            )
            self.assertEqual(contact.selected_end_land_width_mm, 6.4)
            self.assertAlmostEqual(contact.net_cap_contact_area_mm2, 4825.6)
            self.assertAlmostEqual(
                contact.net_selected_land_contact_area_mm2, 924.16
            )

    def test_complete_through_run_consumes_design_math_topology_and_bom(self) -> None:
        tiled = self.tiled
        layout = assembly.THROUGH_RUN_LAYOUT
        self.assertEqual(len(tiled.cassettes), 8)
        self.assertEqual(len(tiled.supports), 9)
        np.testing.assert_allclose(
            tuple(cassette.installed.bounds[:, 0] for cassette in tiled.cassettes),
            layout.physical_module_bounds_mm,
            atol=1.0e-8,
        )
        np.testing.assert_allclose(
            tuple(item.metrics.module_length_mm for item in tiled.cassettes),
            (201.134375, *([184.959375] * 6), 201.134375),
            atol=1.0e-8,
        )
        np.testing.assert_allclose(
            tuple(item.center_x_mm for item in tiled.supports),
            layout.corbel_centers_mm,
            atol=1.0e-8,
        )
        self.assertEqual(layout.length_mm, 1514.475)
        self.assertEqual(
            tuple(item.side for item in tiled.supports),
            (
                "terminal_start",
                *(["interior"] * 7),
                "terminal_end",
            ),
        )
        self.assertEqual(
            tuple(len(item.registration_keys) for item in tiled.supports),
            (1, *([2] * 7), 1),
        )
        self.assertEqual(tiled.rail_support_indices, (1, 3, 5, 7))
        self.assertEqual(len(tiled.mounted_rails), 4)
        self.assertEqual(len(tiled.seated_retained_blanks), 12)
        self.assertEqual(tiled.rail_station_indices, (0, 1, 2) * 4)
        self.assertEqual(
            tuple(
                item.support_index
                for item in tiled.supports
                if item.rail_eligibility is not None
            ),
            (1, 3, 5, 7),
        )
        self.assertEqual(
            tuple(item.keeper_state for item in tiled.supports),
            (None, *(["seated"] * 7), None),
        )
        self.assertEqual(
            tuple(item.next_keeper_state for item in tiled.supports),
            (*([None] * 7), "seated", None),
        )
        self.assertEqual(
            tuple(item.keeper_side for item in tiled.cassettes),
            (*(["right"] * 7), "left"),
        )
        self.assertEqual(len(tiled.supports[7].keepers), 2)
        for terminal in (tiled.supports[0], tiled.supports[-1]):
            self.assertEqual(terminal.keepers, ())
            self.assertIsNone(terminal.rail_eligibility)
            self.assertLessEqual(
                float(terminal.body.bounds[1, 1]), shelf.SHELF_DEPTH_MM
            )
            self.assertAlmostEqual(float(terminal.body.bounds[1, 2]), 161.0)

    def test_tiled_run_contacts_registration_and_all_installed_parts_are_clear(self) -> None:
        tiled = self.tiled
        for index, cassette in enumerate(tiled.cassettes):
            self.assertNoPositiveOverlap(
                cassette.installed, tiled.supports[index].body
            )
            self.assertNoPositiveOverlap(
                cassette.installed, tiled.supports[index + 1].body
            )
            at_clearance = assembly.transformed(
                cassette.installed, assembly.translation(x=0.4)
            )
            blocked = assembly.transformed(
                cassette.installed, assembly.translation(x=0.8)
            )
            for support in tiled.supports[index : index + 2]:
                self.assertNoPositiveOverlap(at_clearance, support.body)
            self.assertGreater(
                sum(
                    assembly.positive_overlap_volume(blocked, support.body)
                    for support in tiled.supports[index : index + 2]
                ),
                9.0,
            )
            if index:
                prior = tiled.cassettes[index - 1]
                gap = float(
                    cassette.installed.bounds[0, 0]
                    - prior.installed.bounds[1, 0]
                )
                self.assertAlmostEqual(gap, 0.35, delta=1.0e-5)
                self.assertNoPositiveOverlap(cassette.installed, prior.installed)

        parts = (
            *(item.installed for item in tiled.cassettes),
            *(item.body for item in tiled.supports),
            *tiled.mounted_rails,
            *tiled.seated_retained_blanks,
        )
        for part in parts:
            self.assertOneBody(part)
        for index, first in enumerate(parts):
            for second in parts[index + 1 :]:
                self.assertNoPositiveOverlap(first, second)

    def test_tiled_service_deflects_only_target_keeper_and_preserves_safe_order(self) -> None:
        tiled = self.tiled_released
        self.assertEqual(
            tuple(item.keeper_state for item in tiled.supports),
            (
                None,
                "seated",
                "seated",
                "seated",
                "deflected",
                "seated",
                "seated",
                "seated",
                None,
            ),
        )
        self.assertEqual(
            tuple(item.next_keeper_state for item in tiled.supports),
            (*([None] * 7), "seated", None),
        )
        target = tiled.cassettes[3]
        fixed = (
            *(item.body for item in tiled.supports),
            *(item.installed for index, item in enumerate(tiled.cassettes) if index != 3),
            *tiled.mounted_rails,
            *tiled.seated_retained_blanks,
        )
        cassette_service = assembly.service_transforms()
        for matrices in (
            cassette_service.installation,
            cassette_service.removal,
        ):
            for matrix in matrices:
                moving = assembly.transformed(target.installed, matrix)
                for stationary in fixed:
                    self.assertNoPositiveOverlap(moving, stationary)

        self.assertTrue(assembly.RAIL_SERVICE_REQUIRES_MODULE_REMOVAL)
        rail_center = tiled.supports[1].center_x_mm
        local_rail = interface.build_mounted_retention_rail()
        rail_service = assembly.rail_mount_service_transforms(rail_center)
        rail_fixed = (
            *(item.body for item in tiled.supports),
            *(item.installed for item in tiled.cassettes),
            *tiled.mounted_rails[1:],
            *tiled.seated_retained_blanks[3:],
        )
        for matrices in (
            rail_service.approach,
            rail_service.drop,
            rail_service.removal_lift,
            rail_service.removal_outward,
        ):
            for matrix in matrices:
                moving = assembly.transformed(local_rail, matrix)
                for stationary in rail_fixed:
                    self.assertNoPositiveOverlap(moving, stationary)

        module = interface.build_retained_accessory(
            "blank", latch_state="deflected"
        )
        module_service = assembly.blank_module_service_transforms(
            1, support_center_x_mm=rail_center
        )
        module_fixed = (
            *tiled.mounted_rails,
            *(item.body for item in tiled.supports),
            *(item.installed for item in tiled.cassettes),
            tiled.seated_retained_blanks[0],
            *tiled.seated_retained_blanks[2:],
        )
        for matrices in (
            module_service.approach,
            module_service.drop,
            module_service.removal_lift,
            module_service.removal_outward,
        ):
            for matrix in matrices:
                moving = assembly.transformed(module, matrix)
                for stationary in module_fixed:
                    self.assertNoPositiveOverlap(moving, stationary)

    def test_every_cassette_release_maps_to_only_its_own_keeper(self) -> None:
        for target_index in range(len(self.tiled.cassettes)):
            with self.subTest(target_index=target_index):
                tiled = assembly.build_tiled_through_run(
                    release_cassette_index=target_index
                )
                primary_states = tuple(
                    item.keeper_state for item in tiled.supports
                )
                expected_primary = [None, *(["seated"] * 7), None]
                if target_index < len(tiled.cassettes) - 1:
                    expected_primary[target_index + 1] = "deflected"
                self.assertEqual(primary_states, tuple(expected_primary))

                expected_next = [None] * len(tiled.supports)
                expected_next[-2] = (
                    "deflected"
                    if target_index == len(tiled.cassettes) - 1
                    else "seated"
                )
                self.assertEqual(
                    tuple(item.next_keeper_state for item in tiled.supports),
                    tuple(expected_next),
                )

                target = tiled.cassettes[target_index]
                for transforms in (
                    assembly.service_transforms().installation,
                    assembly.service_transforms().removal,
                ):
                    for matrix in transforms:
                        moving = assembly.transformed(target.installed, matrix)
                        for support in tiled.supports:
                            self.assertNoPositiveOverlap(moving, support.body)

    def test_final_left_keeper_and_dual_rail_support_clear_all_service(self) -> None:
        released = assembly.build_tiled_through_run(release_cassette_index=7)
        penultimate = released.supports[7]
        terminal = released.supports[8]
        self.assertEqual(released.cassettes[7].keeper_side, "left")
        self.assertEqual(
            (penultimate.keeper_state, penultimate.next_keeper_state),
            ("seated", "deflected"),
        )
        self.assertEqual(terminal.keepers, ())
        self.assertIsNone(terminal.rail_eligibility)

        target = released.cassettes[7]
        fixed = (
            *(item.body for item in released.supports),
            *(item.installed for item in released.cassettes[:-1]),
            *released.mounted_rails,
            *released.seated_retained_blanks,
        )
        for transforms in (
            assembly.service_transforms().installation,
            assembly.service_transforms().removal,
        ):
            for matrix in transforms:
                moving = assembly.transformed(target.installed, matrix)
                for stationary in fixed:
                    self.assertNoPositiveOverlap(moving, stationary)

        blocked = assembly.transformed(
            self.tiled.cassettes[7].installed,
            assembly.translation(z=assembly.KEEPER_BLOCKING_LIFT_MM),
        )
        self.assertGreater(
            assembly.positive_overlap_volume(blocked, self.tiled.supports[7].body),
            1.0,
        )

        center = penultimate.center_x_mm
        local_rail = interface.build_mounted_retention_rail()
        rail_service = assembly.rail_mount_service_transforms(center)
        rail_fixed = (
            *(item.body for item in released.supports),
            *(item.installed for item in released.cassettes),
            *released.mounted_rails[:3],
            *released.seated_retained_blanks[:9],
        )
        for transforms in (
            rail_service.approach,
            rail_service.drop,
            rail_service.removal_lift,
            rail_service.removal_outward,
        ):
            for matrix in transforms:
                moving = assembly.transformed(local_rail, matrix)
                for stationary in rail_fixed:
                    self.assertNoPositiveOverlap(moving, stationary)

        for station_index in range(len(accessory.SOCKET_CENTER_Z_MM)):
            module = interface.build_retained_accessory(
                "blank", latch_state="deflected"
            )
            module_service = assembly.blank_module_service_transforms(
                station_index, support_center_x_mm=center
            )
            fixed_modules = (
                *released.mounted_rails,
                *(item.body for item in released.supports),
                *(item.installed for item in released.cassettes),
                *(
                    item
                    for index, item in enumerate(
                        released.seated_retained_blanks
                    )
                    if index != 9 + station_index
                ),
            )
            for transforms in (
                module_service.approach,
                module_service.drop,
                module_service.removal_lift,
                module_service.removal_outward,
            ):
                for matrix in transforms:
                    moving = assembly.transformed(module, matrix)
                    for stationary in fixed_modules:
                        self.assertNoPositiveOverlap(moving, stationary)

    def test_petg_parts_fit_a1_mini_and_have_no_saved_layer_islands(self) -> None:
        cassette = shelf.orient_cassette_on_long_edge(
            self.seated.cassette.source_registered, yaw_degrees=45.0
        )
        cassette_envelope = shelf.print_envelope_with_margins(
            cassette,
            brim_mm=5.0,
            brim_object_gap_mm=0.1,
            reserve_per_bed_edge_mm=2.0,
            available_build_volume_mm=assembly.A1_MINI_BUILD_VOLUME_MM,
        )
        self.assertTrue(cassette_envelope.fits)
        self.assertLessEqual(max(cassette_envelope.required_build_volume_mm), 180.0)
        cassette_layers = shelf.saved_layer_connectivity(
            cassette, layer_height_mm=0.2
        )
        self.assertEqual(cassette_layers.sampled_layer_count, 762)
        self.assertEqual(cassette_layers.failed_layer_indices, ())

        for cassette_variant in (
            self.tiled.cassettes[0],
            self.tiled.cassettes[1],
            self.tiled.cassettes[-1],
        ):
            oriented = shelf.orient_cassette_on_long_edge(
                cassette_variant.source_registered, yaw_degrees=45.0
            )
            envelope = shelf.print_envelope_with_margins(
                oriented,
                brim_mm=5.0,
                brim_object_gap_mm=0.1,
                reserve_per_bed_edge_mm=2.0,
                available_build_volume_mm=assembly.A1_MINI_BUILD_VOLUME_MM,
            )
            self.assertTrue(envelope.fits)
            layers = shelf.saved_layer_connectivity(
                oriented, layer_height_mm=0.2
            )
            self.assertEqual(layers.sampled_layer_count, 762)
            self.assertEqual(layers.failed_layer_indices, ())

        expected_required = (171.8, 177.6, 32.0)
        for support in (
            self.seated.left_support,
            self.seated.right_support,
        ):
            oriented = assembly.orient_installed_support_for_print(support.body)
            envelope = shelf.print_envelope_with_margins(
                oriented,
                brim_mm=5.0,
                brim_object_gap_mm=0.1,
                reserve_per_bed_edge_mm=2.0,
                available_build_volume_mm=assembly.A1_MINI_BUILD_VOLUME_MM,
            )
            self.assertTrue(envelope.fits)
            np.testing.assert_allclose(
                envelope.required_build_volume_mm,
                expected_required,
                atol=1.0e-5,
            )
            layers = interface.saved_oriented_layer_island_report(
                oriented, layer_height_mm=0.2
            )
            self.assertEqual(layers.sampled_layer_count, 160)
            self.assertEqual(layers.island_layer_indices, ())
            self.assertFalse(layers.support_required)

        rail_envelope = accessory.saved_print_envelope(
            self.seated.mounted_rail,
            brim_mm=5.0,
            brim_object_gap_mm=0.1,
            bed_axes=(0, 2),
        )
        self.assertTrue(rail_envelope.fits)
        oriented_blank = assembly.orient_one_bay_blank_for_print(
            self.seated.seated_retained_blank
        )
        blank_envelope = accessory.saved_print_envelope(
            oriented_blank,
            brim_mm=5.0,
            brim_object_gap_mm=0.1,
            bed_axes=(0, 1),
        )
        self.assertTrue(blank_envelope.fits)
        blank_layers = interface.saved_layer_island_report(
            self.seated.seated_retained_blank, layer_height_mm=0.2
        )
        self.assertEqual(blank_layers.sampled_layer_count, 137)
        self.assertEqual(blank_layers.island_layer_indices, ())
        self.assertFalse(blank_layers.support_required)
        self.assertEqual(blank_layers.support_classification, "support_free")
        self.assertGreaterEqual(
            blank_layers.first_layer_body_contact_area_mm2,
            interface.BLANK_MINIMUM_FIRST_LAYER_BODY_CONTACT_MM2,
        )
        self.assertEqual(
            interface.RETAINED_MODULE_SAVED_ORIENTATION,
            "local_xy_bed_local_negative_z_build",
        )
        with self.assertRaises(ValueError):
            assembly.orient_one_bay_blank_for_print(
                interface.build_retained_accessory("single_peg")
            )

    def test_rebuilds_are_deterministic(self) -> None:
        rebuilt = assembly.build_one_bay()
        first = self.seated
        pairs = (
            (first.cassette.source_registered, rebuilt.cassette.source_registered),
            (first.left_support.body, rebuilt.left_support.body),
            (first.right_support.body, rebuilt.right_support.body),
            (first.mounted_rail, rebuilt.mounted_rail),
            (first.seated_retained_blank, rebuilt.seated_retained_blank),
        )
        for original, repeated in pairs:
            self.assertEqual(
                accessory.mesh_geometry_digest(original),
                accessory.mesh_geometry_digest(repeated),
            )


if __name__ == "__main__":
    unittest.main()
