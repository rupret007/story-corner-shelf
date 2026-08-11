#!/usr/bin/env python3
"""Executable contract for the additive R10 S0 cable bookend."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest
import warnings

import numpy as np


R10_ROOT = Path(__file__).resolve().parents[1]
R9_ROOT = R10_ROOT.parent / "r9"
for path in (R10_ROOT, R9_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cable_bookend as bookend  # noqa: E402
import cable_geometry as r9_cable  # noqa: E402
import lincoln_geometry as geometry  # noqa: E402


class R10CableBookendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = bookend.build_first_wall_left_cable_bookend()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            cls.evidence = bookend.build_cable_bookend_evidence()
        cls.saved = bookend.build_saved_cable_bookend_parts()

    def test_fail_closed_boundary_and_first_wall_scope(self) -> None:
        self.assertTrue(bookend.QUALIFICATION_ONLY)
        self.assertFalse(bookend.PRODUCTION_READY)
        self.assertFalse(bookend.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertFalse(bookend.WALL_INSTALLATION_AUTHORIZED)
        self.assertFalse(bookend.FIELD_CLEARANCE_QUALIFIED)
        self.assertFalse(
            bookend.DOOR_TRIM_OUTLET_AND_CABLE_LOOP_CLEARANCE_QUALIFIED
        )
        self.assertFalse(bookend.STRUCTURAL_OR_SHELF_LOAD_CREDIT)
        self.assertFalse(bookend.SUPPORT_CORE_SUBTRACTION_ALLOWED)
        self.assertEqual((bookend.RATED_LOAD_KG, bookend.RATED_LOAD_LB), (0.0, 0.0))
        self.assertEqual(bookend.FIRST_WALL_ACTIVE_SUPPORT_INDICES, (0,))
        self.assertTrue(bookend.receiver_allowed_on_first_wall_support(0))
        for support_index in range(1, 7):
            self.assertFalse(
                bookend.receiver_allowed_on_first_wall_support(support_index)
            )
        self.assertFalse(bookend.INTERMEDIATE_SUPPORT_CABLE_HARDWARE_ALLOWED)
        self.assertFalse(bookend.CORNER_CABLE_HARDWARE_ALLOWED)
        self.assertEqual(self.candidate.support_index, 0)
        self.assertEqual(self.candidate.inward_axis, "+support_run")

    def test_exact_r10_datums_and_inward_receiver_mapping(self) -> None:
        self.assertEqual(bookend.SUPPORT_RUN_WIDTH_MM, 31.75)
        self.assertEqual(bookend.SUPPORT_WALL_CHORD_MM, 19.05)
        self.assertEqual(bookend.SUPPORT_TOTAL_DROP_MM, 158.75)
        self.assertEqual(bookend.SOCKETS_PER_BOOKEND, 2)
        self.assertEqual(bookend.SOCKET_CLEARANCE_PER_FACE_MM, 0.4)
        self.assertEqual(bookend.SOCKET_SERVICE_LIFT_MM, 8.0)
        self.assertTrue(bookend.INWARD_FACING)
        np.testing.assert_allclose(
            self.candidate.source_support.extents,
            (152.4, 170.75, 31.75),
            atol=1.0e-5,
        )
        np.testing.assert_allclose(
            self.candidate.mapped_receiver.bounds,
            ((32.0, 90.0, 31.35), (68.0, 152.0, 40.15)),
            atol=1.0e-5,
        )
        self.assertGreater(
            bookend.SOCKET_CAVITY_NEAREST_CORE_RUN_MM,
            bookend.SUPPORT_RUN_WIDTH_MM,
        )
        transform = self.candidate.receiver_to_support
        np.testing.assert_allclose(
            transform[:3, 1],
            (0.0, 0.0, 1.0),
            atol=1.0e-12,
        )

    def test_fusion_preserves_every_source_core_voxel_additively(self) -> None:
        evidence = self.evidence.core
        self.assertEqual(evidence.source_digest_before, evidence.source_digest_after)
        self.assertEqual(evidence.containment_numerical_tolerance_mm3, 1.0e-5)
        self.assertEqual(evidence.missing_source_core_volume_mm3, 0.0)
        self.assertTrue(evidence.source_core_preserved)
        self.assertTrue(evidence.additive_only)
        self.assertGreater(evidence.outer_emphasis_source_overlap_mm3, 0.0)
        self.assertGreater(evidence.receiver_source_overlap_mm3, 0.0)
        self.assertGreater(evidence.ramp_source_overlap_mm3, 0.0)
        self.assertGreater(evidence.receiver_ramp_overlap_mm3, 0.0)
        body = self.candidate.fused_body
        self.assertEqual(len(body.split(only_watertight=False)), 1)
        self.assertTrue(body.is_volume)
        self.assertTrue(body.is_watertight)
        self.assertTrue(body.is_winding_consistent)
        self.assertGreater(float(body.volume), evidence.source_volume_mm3)

    def test_s0_additive_emphasis_reaches_exact_outer_bookend_drop(self) -> None:
        emphasis = self.candidate.additive_outer_emphasis
        projecting = np.asarray(emphasis.vertices)[
            emphasis.vertices[:, 0] > bookend.SUPPORT_WALL_CHORD_MM
        ]
        self.assertGreater(len(projecting), 0)
        visible_drop = bookend.SUPPORT_TOTAL_DROP_MM - float(projecting[:, 1].min())
        self.assertAlmostEqual(visible_drop, 120.65, places=6)
        self.assertEqual(bookend.OUTER_BOOKEND_VISIBLE_CORBEL_DROP_MM, 120.65)
        self.assertFalse(bookend.OUTER_EMPHASIS_STRUCTURAL_CREDIT)
        self.assertGreaterEqual(float(emphasis.bounds[0, 2]), 0.4)
        self.assertLessEqual(float(emphasis.bounds[1, 2]), 31.35)

    def test_additions_clear_all_bores_and_both_retainer_service_lanes(self) -> None:
        evidence = self.evidence.clearance
        self.assertEqual(len(evidence.bore_addition_intersection_mm3), 3)
        self.assertEqual(evidence.bore_addition_intersection_mm3, (0.0, 0.0, 0.0))
        self.assertEqual(len(evidence.retainer_service_intersection_mm3), 2)
        self.assertEqual(evidence.retainer_service_intersection_mm3, (0.0, 0.0))
        self.assertAlmostEqual(evidence.minimum_bore_q_gap_mm, 3.55, places=5)
        self.assertAlmostEqual(evidence.minimum_retainer_e_gap_mm, 10.75, places=5)
        self.assertTrue(evidence.wall_bores_clear)
        self.assertTrue(evidence.both_support_retainer_service_lanes_clear)
        self.assertGreater(
            bookend.PRINT_RAMP_Q_START_MM,
            max(cutter.bounds[1, 0] for cutter in geometry._wall_bore_cutters()),
        )

    def test_blank_and_comb_are_exact_r9_interface_geometry(self) -> None:
        pairs = (
            (
                bookend.build_flush_blank_module(),
                r9_cable.build_flush_blank_module(),
            ),
            (
                bookend.build_multi_cable_comb_hook_module(),
                r9_cable.build_multi_cable_organizer_hook_module(),
            ),
        )
        for ported, frozen in pairs:
            np.testing.assert_array_equal(ported.faces, frozen.faces)
            np.testing.assert_allclose(ported.vertices, frozen.vertices, atol=0.0)
            self.assertEqual(len(ported.split(only_watertight=False)), 1)
            self.assertTrue(ported.is_watertight)
            self.assertTrue(ported.is_winding_consistent)

    def test_both_modules_service_both_sockets_at_one_mm_without_collision(self) -> None:
        service = self.evidence.module_service
        self.assertEqual(len(service), 4)
        self.assertEqual(
            {(item.module_name, item.station_index) for item in service},
            {
                ("flush_blank", 0),
                ("flush_blank", 1),
                ("multi_cable_comb_hook", 0),
                ("multi_cable_comb_hook", 1),
            },
        )
        for item in service:
            with self.subTest(module=item.module_name, station=item.station_index):
                self.assertEqual(item.increment_mm, 1.0)
                self.assertEqual(item.insertion_sample_count, 7)
                self.assertEqual(item.drop_sample_count, 9)
                self.assertEqual(item.lift_sample_count, 9)
                self.assertEqual(item.outward_sample_count, 7)
                self.assertEqual(item.insertion_maximum_intersection_mm3, 0.0)
                self.assertEqual(item.drop_maximum_intersection_mm3, 0.0)
                self.assertEqual(item.lift_maximum_intersection_mm3, 0.0)
                self.assertEqual(item.outward_maximum_intersection_mm3, 0.0)
                self.assertTrue(item.removal_is_exact_reverse)
                self.assertTrue(item.collision_free)

    def test_saved_inventory_is_exact_support_free_and_a1_safe(self) -> None:
        self.assertEqual(
            tuple(self.saved),
            (
                bookend.FIRST_WALL_BOOKEND_PART_NAME,
                bookend.FIRST_WALL_BLANK_0_PART_NAME,
                bookend.FIRST_WALL_BLANK_1_PART_NAME,
                bookend.FIRST_WALL_COMB_PART_NAME,
            ),
        )
        print_evidence = self.evidence.saved_print
        self.assertEqual(
            print_evidence.orientation_id,
            "wall_face_down_45deg_with_additive_inward_reveal_ramp",
        )
        self.assertFalse(print_evidence.support_required)
        self.assertEqual(print_evidence.sampled_layer_height_mm, 0.2)
        self.assertEqual(print_evidence.disconnected_layer_indices, ())
        self.assertEqual(print_evidence.body_count, 1)
        self.assertTrue(print_evidence.watertight)
        self.assertTrue(print_evidence.winding_consistent)
        self.assertTrue(print_evidence.envelope.fits)
        self.assertGreater(print_evidence.first_layer_contact_area_mm2, 4000.0)
        self.assertLessEqual(
            print_evidence.maximum_new_reveal_per_02_layer_mm,
            0.2,
        )
        for name, mesh in self.saved.items():
            with self.subTest(part=name):
                np.testing.assert_allclose(mesh.bounds[0], (0.0, 0.0, 0.0), atol=1e-6)
                self.assertEqual(len(mesh.split(only_watertight=False)), 1)
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_winding_consistent)
                self.assertTrue(geometry.print_envelope(mesh).fits)
        np.testing.assert_allclose(
            self.saved[bookend.FIRST_WALL_BOOKEND_PART_NAME].extents,
            (141.88097563, 141.88097538, 152.3999939),
            atol=1.0e-5,
        )

    def test_evidence_stays_unreleased_even_when_geometry_checks_pass(self) -> None:
        evidence = self.evidence
        self.assertEqual(evidence.active_first_wall_support_indices, (0,))
        self.assertEqual(evidence.sockets_per_bookend, 2)
        self.assertTrue(evidence.inward_facing)
        self.assertFalse(evidence.intermediate_support_hardware_allowed)
        self.assertFalse(evidence.corner_hardware_allowed)
        self.assertFalse(evidence.field_clearance_qualified)
        self.assertEqual(evidence.outer_visible_corbel_emphasis_mm, 120.65)
        self.assertFalse(evidence.outer_emphasis_structural_credit)
        self.assertEqual((evidence.rated_load_kg, evidence.rated_load_lb), (0.0, 0.0))
        self.assertFalse(evidence.wall_installation_authorized)
        self.assertGreaterEqual(len(evidence.release_blockers), 4)
        self.assertTrue(any("unmeasured" in item for item in evidence.release_blockers))

    def test_invalid_scope_and_service_inputs_fail_closed(self) -> None:
        for value in (-1, 7):
            with self.subTest(support_index=value):
                with self.assertRaises(IndexError):
                    bookend.receiver_allowed_on_first_wall_support(value)
        for value in (True, 1.5, "0"):
            with self.subTest(support_index=value):
                with self.assertRaises(ValueError):
                    bookend.receiver_allowed_on_first_wall_support(value)  # type: ignore[arg-type]
        with self.assertRaises(IndexError):
            bookend.mapped_module_service_path(
                bookend.build_flush_blank_module(),
                module_name="flush_blank",
                station_index=2,
            )
        with self.assertRaises(ValueError):
            bookend.mapped_module_service_path(
                bookend.build_flush_blank_module(),
                module_name="peg",
                station_index=0,
            )
        with self.assertRaises(ValueError):
            bookend.mapped_module_service_path(
                bookend.build_flush_blank_module(),
                module_name="flush_blank",
                station_index=0,
                increment_mm=0.3,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
