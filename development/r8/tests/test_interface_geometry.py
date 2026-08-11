#!/usr/bin/env python3
"""Exact integration tests for the additive R8 rail mount and PETG latch."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
import json

import numpy as np


R8 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R8))

import accessory_geometry as accessory  # noqa: E402
import interface_geometry as interface  # noqa: E402
import shelf_geometry as shelf  # noqa: E402


class R8InterfaceGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = interface.build_eligible_d_frame_wrapper(
            "through", 4, 9
        )
        cls.mirrored_wrapper = interface.build_eligible_d_frame_wrapper(
            "through", 4, 9, mirrored=True
        )
        cls.rail = interface.build_mounted_retention_rail()
        cls.retained = {
            kind: interface.build_retained_accessory(kind)
            for kind in ("blank", "single_peg", "three_cable_comb", "coil_j_hook")
        }
        cls.deflected = {
            kind: interface.build_retained_accessory(
                kind, latch_state="deflected"
            )
            for kind in cls.retained
        }
        cls.deflected_blank = cls.deflected["blank"]

    def assertOneBody(self, mesh) -> None:  # noqa: N802
        self.assertTrue(interface.mesh_is_one_body(mesh))
        self.assertTrue(mesh.is_watertight)
        self.assertTrue(mesh.is_winding_consistent)
        self.assertGreater(mesh.volume, 0.0)
        self.assertEqual(len(mesh.split(only_watertight=False)), 1)

    def assertNoPositiveOverlap(self, first, second) -> None:  # noqa: N802
        overlap = interface.positive_overlap_volume(first, second)
        self.assertLessEqual(overlap, interface.COLLISION_TOLERANCE_MM3)

    def test_scope_is_zero_rated_qualification_only(self) -> None:
        self.assertTrue(interface.QUALIFICATION_ONLY)
        self.assertFalse(interface.PRODUCTION_READY)
        self.assertEqual(
            (interface.RATED_LOAD_KG, interface.RATED_LOAD_LB), (0.0, 0.0)
        )
        self.assertEqual(interface.MOUNT_CLEARANCE_MM, 0.4)
        self.assertEqual(interface.SERVICE_INCREMENT_MM, 0.4)

    def test_config_matches_the_authored_rail_and_latch_contract(self) -> None:
        cfg = json.loads((R8 / "config.json").read_text(encoding="utf-8"))
        contract = cfg["accessory_system"]
        self.assertEqual(contract["rail_envelope_mm"], [36.0, 88.0, 8.8])
        self.assertEqual(
            contract["socket_centers_from_rail_bottom_mm"],
            list(accessory.SOCKET_CENTER_Z_MM),
        )
        self.assertEqual(
            contract["rail_installed_lower_edge_mm_above_corbel_bottom"],
            interface.RAIL_SEATED_Z_MM,
        )
        self.assertEqual(
            shelf.CORBEL_INSTALLED_HEIGHT_MM - interface.RAIL_SEATED_Z_MM,
            112.0,
        )
        self.assertEqual(contract["module_service_lift_mm"], 8.0)
        self.assertEqual(contract["rail_service_lift_mm"], 4.0)
        self.assertEqual(contract["nominal_clearance_per_face_mm"], 0.4)
        self.assertEqual(
            contract["clearance_ladder_per_face_mm"],
            list(accessory.CLEARANCE_LADDER_MM),
        )
        self.assertTrue(contract["positive_release_latch_authored"])
        self.assertAlmostEqual(
            contract["latch_comparison_strain_proxy"],
            interface.latch_strain_proxy().surface_strain,
            places=12,
        )

    def test_support_selection_fails_closed_at_every_endpoint_and_corner(self) -> None:
        expected_eligible = {
            "through": (1, 2, 3, 4, 5, 6, 7),
            "return": (1, 2, 3),
        }
        for run, count in interface.NOMINAL_SUPPORT_COUNTS.items():
            observed = tuple(
                index
                for index in range(count)
                if interface.support_eligibility(run, index, count).eligible
            )
            self.assertEqual(observed, expected_eligible[run])
            for index in (0, count - 1):
                with self.assertRaises(interface.IneligibleSupportError):
                    interface.build_eligible_d_frame_wrapper(run, index, count)
            with self.assertRaises(interface.IneligibleSupportError):
                interface.build_eligible_d_frame_wrapper(
                    run, count // 2, count, is_corner=True
                )
        for run, count in (("through", 3), ("through", 8), ("return", 4), ("return", 11)):
            observed = tuple(
                index
                for index in range(count)
                if interface.support_eligibility(run, index, count).eligible
            )
            self.assertEqual(observed, tuple(range(1, count - 1)))
            wrapper = interface.build_eligible_d_frame_wrapper(run, 1, count)
            self.assertTrue(wrapper.eligibility.eligible)
            self.assertEqual(wrapper.eligibility.support_count, count)

        for args in (("unknown", 1, 9), ("through", 1, 2), ("return", 5, 5)):
            self.assertFalse(interface.support_eligibility(*args).eligible)
            with self.assertRaises(interface.IneligibleSupportError):
                interface.build_eligible_d_frame_wrapper(*args)
        for invalid_index in (True, 1.0, "1"):
            with self.subTest(invalid_index=invalid_index):
                self.assertFalse(
                    interface.support_eligibility("through", invalid_index, 9).eligible
                )
                with self.assertRaises(interface.IneligibleSupportError):
                    interface.build_eligible_d_frame_wrapper(
                        "through", invalid_index, 9
                    )

    def test_d_frame_core_is_byte_volume_and_digest_identical_before_boss_union(self) -> None:
        for wrapper in (self.wrapper, self.mirrored_wrapper):
            with self.subTest(mirrored=wrapper.mirrored):
                self.assertOneBody(wrapper.source_core)
                self.assertOneBody(wrapper.installed_core)
                self.assertOneBody(wrapper.body)
                self.assertEqual(len(wrapper.boss_parts), 4)
                report = interface.core_preservation_report(wrapper)
                self.assertTrue(report.vertex_face_bytes_identical)
                self.assertEqual(report.source_digest, report.restored_digest)
                self.assertAlmostEqual(report.volume_delta_mm3, 0.0, places=8)
                self.assertGreater(
                    report.wrapper_volume_mm3, report.installed_volume_mm3
                )
                self.assertTrue(report.additive_only)

                # Actual Boolean containment: the complete original core is
                # still present inside the final additive wrapper.
                retained_core_volume = interface.positive_overlap_volume(
                    wrapper.installed_core, wrapper.body
                )
                self.assertAlmostEqual(
                    retained_core_volume,
                    report.installed_volume_mm3,
                    delta=0.05,
                )
                self.assertEqual(
                    wrapper.source_core.volume, shelf.build_d_frame_corbel().volume
                )

    def test_complete_bossed_wrapper_is_broad_face_support_free(self) -> None:
        self.assertEqual(interface.MOUNT_BOSS_CENTER_X_MM, (4.0, 32.0))
        self.assertEqual(interface.MOUNT_STEM_CENTER_X_MM, (5.0, 31.0))
        for wrapper in (self.wrapper, self.mirrored_wrapper):
            broad_face = np.asarray(
                (
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (-1.0 if wrapper.mirrored else 1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                ),
                dtype=float,
            )
            core_x = tuple(float(value) for value in wrapper.installed_core.bounds[:, 0])
            for boss in wrapper.boss_parts:
                self.assertGreaterEqual(
                    float(boss.bounds[0, 0]), core_x[0] - 1.0e-7
                )
                self.assertLessEqual(
                    float(boss.bounds[1, 0]), core_x[1] + 1.0e-7
                )
            oriented = interface.transformed(wrapper.body, broad_face)
            oriented.apply_translation(-oriented.bounds[0])
            report = interface.saved_oriented_layer_island_report(
                oriented, layer_height_mm=0.2
            )
            self.assertEqual(report.sampled_layer_count, 160)
            self.assertEqual(report.island_layer_indices, ())
            self.assertTrue(report.all_layers_supported)
            self.assertFalse(report.support_required)
            self.assertEqual(report.support_classification, "support_free")

            prior = interface._section_material_region(
                oriented, (139.0 + 0.5) * 0.2
            )
            far_head_start = interface._section_material_region(
                oriented, (140.0 + 0.5) * 0.2
            )
            components = interface._filled_components(far_head_start)
            self.assertEqual(len(components), 1)
            self.assertTrue(
                all(
                    component.intersection(prior).area > 1.0e-8
                    for component in components
                )
            )
            envelope = accessory.saved_print_envelope(
                wrapper.body, brim_mm=5.0, bed_axes=(1, 2)
            )
            self.assertTrue(envelope.fits)
            np.testing.assert_allclose(
                envelope.with_brim_mm, (162.4, 170.0, 32.0), atol=1.0e-5
            )

    def test_final_rail_preserves_socket_back_web_zone_and_front_skin(self) -> None:
        self.assertOneBody(self.rail)
        np.testing.assert_allclose(
            self.rail.bounds,
            ((0.0, 0.0, 0.0), (36.0, 8.8, 88.0)),
            atol=1.0e-8,
        )
        original = accessory.build_faceplate_rail()
        self.assertLess(self.rail.volume, original.volume)

        # An actual solid witness through the entire keyed-socket x band and
        # 2.4 mm rear web is still wholly present after mount/latch cutting.
        socket_x_min = (
            accessory.SOCKET_CENTER_X_MM
            - accessory.LUG_HEAD_WIDTH_MM / 2.0
            - accessory.LUG_KEY_EXTENSION_MM
            - accessory.NOMINAL_CLEARANCE_MM
        )
        socket_x_max = (
            accessory.SOCKET_CENTER_X_MM
            + accessory.LUG_HEAD_WIDTH_MM / 2.0
            + accessory.NOMINAL_CLEARANCE_MM
        )
        witness = interface._box(
            (socket_x_min + 0.05, socket_x_max - 0.05),
            (0.05, accessory.UNINTERRUPTED_BACK_WEB_MM - 0.05),
            (0.05, accessory.FACEPLATE_HEIGHT_MM - 0.05),
        )
        witness_overlap = interface.positive_overlap_volume(self.rail, witness)
        self.assertAlmostEqual(witness_overlap, witness.volume, delta=0.02)

        for cutter in interface._mount_cavity_cutters():
            x0, x1 = cutter.bounds[:, 0]
            self.assertTrue(x1 < socket_x_min or x0 > socket_x_max)
            self.assertLessEqual(
                cutter.bounds[1, 1],
                accessory.UNINTERRUPTED_BACK_WEB_MM + 1.0e-9,
            )
        for cutter in interface._latch_recess_cutters():
            self.assertGreater(cutter.bounds[0, 0], socket_x_max)
            self.assertGreaterEqual(
                cutter.bounds[0, 1], interface.LATCH_RECESS_BACK_Y_MM
            )

    def test_mount_install_drop_reverse_and_mirror_clear_at_every_point_four_mm(self) -> None:
        sequence = interface.rail_mount_service_transforms()
        self.assertEqual(sequence.increment_mm, 0.4)
        self.assertEqual(len(sequence.approach), 7)   # 2.4 / 0.4 + endpoints
        self.assertEqual(len(sequence.drop), 11)      # 4.0 / 0.4 + endpoints
        self.assertEqual(len(sequence.removal_lift), len(sequence.drop))
        self.assertEqual(len(sequence.removal_outward), len(sequence.approach))
        np.testing.assert_allclose(sequence.approach[-1], sequence.insertion)
        np.testing.assert_allclose(sequence.drop[-1], sequence.seated)
        for mirrored, wrapper in (
            (False, self.wrapper),
            (True, self.mirrored_wrapper),
        ):
            local_rail = (
                interface.mirror_for_opposite_run(self.rail)
                if mirrored
                else self.rail
            )
            for phase, matrices in (
                ("approach", sequence.approach),
                ("drop", sequence.drop),
                ("reverse_lift", sequence.removal_lift),
                ("reverse_out", sequence.removal_outward),
            ):
                for step, matrix in enumerate(matrices):
                    with self.subTest(mirrored=mirrored, phase=phase, step=step):
                        positioned = interface.transformed(local_rail, matrix)
                        self.assertNoPositiveOverlap(positioned, wrapper.body)

            seated = interface.transformed(local_rail, sequence.seated)
            self.assertNoPositiveOverlap(seated, wrapper.body)
            # Without the prescribed lift, an outward pull makes each wide
            # boss head contact the 0.8 mm rear lip: geometry is retained.
            unauthorized_pull = interface.transformed(
                local_rail,
                interface._translation(y=0.8) @ sequence.seated,
            )
            self.assertGreater(
                interface.positive_overlap_volume(
                    unauthorized_pull, wrapper.body
                ),
                1.0,
            )

    def test_final_modules_latch_and_all_one_body(self) -> None:
        for name, mesh in self.retained.items():
            with self.subTest(name=name):
                self.assertOneBody(mesh)
                seed_volume = accessory.build_accessory(name).volume
                if name == "coil_j_hook":
                    self.assertNotAlmostEqual(mesh.volume, seed_volume, places=6)
                else:
                    self.assertGreater(mesh.volume, seed_volume)
        self.assertOneBody(self.deflected_blank)
        self.assertAlmostEqual(
            self.retained["coil_j_hook"].bounds[1, 2],
            interface.FINAL_COIL_TIP_MAX_Z_MM,
            places=8,
        )
        proxy = interface.latch_strain_proxy()
        self.assertAlmostEqual(proxy.surface_strain, 0.024, places=12)
        self.assertLess(proxy.surface_strain, 0.03)
        self.assertTrue(proxy.below_three_percent)

    def test_flipped_retained_modules_publish_exact_support_classification(self) -> None:
        self.assertEqual(
            interface.RETAINED_MODULE_SAVED_ORIENTATION,
            "local_xy_bed_local_negative_z_build",
        )
        self.assertEqual(interface.RETAINED_MODULE_PRINT_ROTATION_X_DEG, 180.0)
        expected_layers = {
            "blank": 137,
            "single_peg": 137,
            "three_cable_comb": 137,
            "coil_j_hook": 162,
        }
        expected_islands = {
            "blank": (),
            "single_peg": (5,),
            "three_cable_comb": (10,),
            "coil_j_hook": (25,),
        }
        for name, retained in self.retained.items():
            oriented = interface.orient_retained_module_for_print(retained)
            report = interface.saved_layer_island_report(
                retained, layer_height_mm=0.2
            )
            with self.subTest(name=name):
                self.assertEqual(
                    report.sampled_layer_count, expected_layers[name]
                )
                self.assertEqual(
                    report.island_layer_indices, expected_islands[name]
                )
                self.assertEqual(report.support_required, name != "blank")
                self.assertEqual(
                    report.support_classification,
                    "support_free" if name == "blank" else "support_required",
                )
                self.assertEqual(
                    report.all_layers_supported, name == "blank"
                )
                if name == "blank":
                    self.assertGreaterEqual(
                        report.first_layer_body_contact_area_mm2,
                        interface.BLANK_MINIMUM_FIRST_LAYER_BODY_CONTACT_MM2,
                    )
                    self.assertAlmostEqual(
                        report.first_layer_body_contact_area_mm2, 64.0, places=5
                    )
                    self.assertIn("every saved-layer", report.support_evidence)
                else:
                    self.assertIn(
                        str(expected_islands[name][0]), report.support_evidence
                    )
                envelope = accessory.saved_print_envelope(
                    oriented, brim_mm=5.0, bed_axes=(0, 1)
                )
                self.assertTrue(envelope.fits)
        blank = self.retained["blank"]
        oriented_blank = interface.orient_retained_module_for_print(blank)
        source_top = np.isclose(blank.vertices[:, 2], blank.bounds[1, 2])
        source_bottom = np.isclose(blank.vertices[:, 2], blank.bounds[0, 2])
        np.testing.assert_allclose(oriented_blank.vertices[source_top, 2], 0.0)
        np.testing.assert_allclose(
            oriented_blank.vertices[source_bottom, 2],
            oriented_blank.extents[2],
            atol=1.0e-6,
        )
        np.testing.assert_allclose(
            oriented_blank.extents,
            (22.4, 11.7, 27.4),
            atol=1.0e-6,
        )

    def test_actual_module_install_drop_reverse_and_mirror_clear_every_point_four_mm(self) -> None:
        rail_mount = interface.rail_mount_service_transforms().seated
        for station in range(len(accessory.SOCKET_CENTER_Z_MM)):
            sequence = interface.module_service_transforms(station)
            self.assertEqual(len(sequence.approach), 17)  # 6.4 / 0.4 + endpoints
            self.assertEqual(len(sequence.drop), 21)      # 8.0 / 0.4 + endpoints
            for mirrored in (False, True):
                rail = (
                    interface.mirror_for_opposite_run(self.rail)
                    if mirrored
                    else self.rail
                )
                # Mirroring a local module about the rail centre requires the
                # placement transform first, then whole-assembly reflection.
                for module_name, moving in self.deflected.items():
                    for phase, matrices in (
                        ("approach", sequence.approach),
                        ("drop", sequence.drop),
                        ("reverse_lift", sequence.removal_lift),
                        ("reverse_out", sequence.removal_outward),
                    ):
                        for step, matrix in enumerate(matrices):
                            placed = interface.transformed(moving, matrix)
                            if mirrored:
                                placed = interface.mirror_for_opposite_run(placed)
                            with self.subTest(
                                station=station,
                                mirrored=mirrored,
                                module=module_name,
                                phase=phase,
                                step=step,
                            ):
                                self.assertNoPositiveOverlap(rail, placed)

                                # Also test the actual installed D-frame.  The
                                # 1 mm standoff clears the lower R10 root, and
                                # the lowered rail keeps the tallest J-hook
                                # below the top chord during service.
                                installed = interface.transformed(
                                    moving, rail_mount @ matrix
                                )
                                if mirrored:
                                    installed = interface.mirror_for_opposite_run(
                                        installed
                                    )
                                wrapper = (
                                    self.mirrored_wrapper
                                    if mirrored
                                    else self.wrapper
                                )
                                self.assertNoPositiveOverlap(
                                    wrapper.body, installed
                                )

                for name, free_module in self.retained.items():
                    placed = interface.transformed(free_module, sequence.seated)
                    if mirrored:
                        placed = interface.mirror_for_opposite_run(placed)
                    with self.subTest(
                        station=station, mirrored=mirrored, seated=name
                    ):
                        self.assertNoPositiveOverlap(rail, placed)

    def test_latch_blocks_uncommanded_lift_but_is_clear_of_gravity_path(self) -> None:
        for station in range(len(accessory.SOCKET_CENTER_Z_MM)):
            sequence = interface.module_service_transforms(station)
            free = interface.transformed(self.retained["blank"], sequence.seated)
            self.assertNoPositiveOverlap(self.rail, free)

            # The recess gives the hook 0.4 mm clearance above and below, so
            # the latch carries no seated gravity reaction.
            free_lift_at_clearance = interface.transformed(
                self.retained["blank"],
                interface._translation(z=interface.LATCH_CLEARANCE_MM)
                @ sequence.seated,
            )
            self.assertNoPositiveOverlap(self.rail, free_lift_at_clearance)
            blocked_lift = interface.transformed(
                self.retained["blank"],
                interface._translation(z=0.8) @ sequence.seated,
            )
            self.assertGreater(
                interface.positive_overlap_volume(self.rail, blocked_lift),
                0.1,
            )

            # Pulling the front tab deflects the hook fully outside y=8.8;
            # the prescribed reverse lift is then collision-free (tested
            # point-by-point above).
            deflected = interface.transformed(
                self.deflected_blank, sequence.seated
            )
            self.assertNoPositiveOverlap(self.rail, deflected)

    def test_adjacent_coil_hooks_clear_every_service_step(self) -> None:
        stationary = self.retained["coil_j_hook"]
        moving = self.deflected["coil_j_hook"]
        for station in range(len(accessory.SOCKET_CENTER_Z_MM)):
            sequence = interface.module_service_transforms(station)
            neighbors = tuple(
                candidate
                for candidate in (station - 1, station + 1)
                if candidate in range(len(accessory.SOCKET_CENTER_Z_MM))
            )
            for neighbor in neighbors:
                neighbor_transform = interface.module_service_transforms(
                    neighbor
                ).seated
                fixed = interface.transformed(stationary, neighbor_transform)
                for mirrored in (False, True):
                    fixed_side = (
                        interface.mirror_for_opposite_run(fixed)
                        if mirrored
                        else fixed
                    )
                    for phase, matrices in (
                        ("approach", sequence.approach),
                        ("drop", sequence.drop),
                        ("reverse_lift", sequence.removal_lift),
                        ("reverse_out", sequence.removal_outward),
                    ):
                        for step, matrix in enumerate(matrices):
                            placed = interface.transformed(moving, matrix)
                            if mirrored:
                                placed = interface.mirror_for_opposite_run(placed)
                            with self.subTest(
                                station=station,
                                neighbor=neighbor,
                                mirrored=mirrored,
                                phase=phase,
                                step=step,
                            ):
                                self.assertNoPositiveOverlap(fixed_side, placed)

    def test_full_adjacent_module_matrix_encodes_comb_service_order(self) -> None:
        """Only a comb below an occupied neighbor needs ordered service."""

        for moving_kind, moving in self.deflected.items():
            for fixed_kind, fixed_source in self.retained.items():
                for station in range(len(accessory.SOCKET_CENTER_Z_MM)):
                    sequence = interface.module_service_transforms(station)
                    for neighbor in (station - 1, station + 1):
                        if neighbor not in range(len(accessory.SOCKET_CENTER_Z_MM)):
                            continue
                        fixed = interface.transformed(
                            fixed_source,
                            interface.module_service_transforms(neighbor).seated,
                        )
                        maximum = 0.0
                        for matrices in (
                            sequence.approach,
                            sequence.drop,
                            sequence.removal_lift,
                            sequence.removal_outward,
                        ):
                            maximum = max(
                                maximum,
                                *(
                                    interface.positive_overlap_volume(
                                        fixed,
                                        interface.transformed(moving, matrix),
                                    )
                                    for matrix in matrices
                                ),
                            )
                        ordered_comb_case = (
                            moving_kind == "three_cable_comb"
                            and neighbor == station + 1
                        )
                        with self.subTest(
                            moving=moving_kind,
                            fixed=fixed_kind,
                            station=station,
                            neighbor=neighbor,
                        ):
                            if ordered_comb_case:
                                self.assertGreater(maximum, 1.0)
                            else:
                                self.assertLessEqual(
                                    maximum,
                                    interface.COLLISION_TOLERANCE_MM3,
                                )

    def test_asymmetric_key_rejects_wrong_orientation(self) -> None:
        for station in range(len(accessory.SOCKET_CENTER_Z_MM)):
            sequence = interface.module_service_transforms(station)
            wrong = interface.wrong_key_orientation(self.deflected_blank)
            wrong_at_entry = interface.transformed(wrong, sequence.insertion)
            overlap = interface.positive_overlap_volume(self.rail, wrong_at_entry)
            self.assertGreater(overlap, 10.0)
            mirrored_overlap = interface.positive_overlap_volume(
                interface.mirror_for_opposite_run(self.rail),
                interface.mirror_for_opposite_run(wrong_at_entry),
            )
            self.assertAlmostEqual(mirrored_overlap, overlap, delta=1.0e-4)

    def test_every_final_mesh_fits_a1_mini(self) -> None:
        named = {
            "d_frame_mount": self.wrapper.body,
            "mirrored_d_frame_mount": self.mirrored_wrapper.body,
            "retention_rail": self.rail,
            **{f"retained_{name}": mesh for name, mesh in self.retained.items()},
            **{f"deflected_{name}": mesh for name, mesh in self.deflected.items()},
        }
        for name, mesh in named.items():
            if "d_frame" in name:
                bed_axes = (1, 2)
            elif "retained" in name or "deflected" in name:
                bed_axes = (0, 1)
            else:
                bed_axes = (0, 2)
            envelope = accessory.saved_print_envelope(
                mesh, brim_mm=5.0, bed_axes=bed_axes
            )
            with self.subTest(name=name):
                self.assertTrue(envelope.fits)
                self.assertTrue(
                    all(value <= 180.0 + 1.0e-8 for value in envelope.with_brim_mm)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
