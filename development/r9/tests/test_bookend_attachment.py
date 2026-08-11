#!/usr/bin/env python3
"""Contracts for the additive R9 outer-bookend rail attachment candidate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


R9 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R9))

import bookend_attachment as attachment  # noqa: E402
import cable_geometry as cable  # noqa: E402
import support_geometry as support  # noqa: E402


def assert_one_body(test: unittest.TestCase, mesh) -> None:
    test.assertFalse(mesh.is_empty)
    test.assertTrue(mesh.is_watertight)
    test.assertTrue(mesh.is_winding_consistent)
    test.assertTrue(mesh.is_volume)
    test.assertGreater(float(mesh.volume), 0.0)
    test.assertEqual(len(mesh.split(only_watertight=False)), 1)


class R9BookendAttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.through = attachment.build_outer_bookend_attachment("through_outer")
        cls.return_candidate = attachment.build_outer_bookend_attachment(
            "return_outer"
        )

    def test_scope_is_petg_only_zero_rated_and_installed_clearance_unqualified(self) -> None:
        self.assertTrue(attachment.QUALIFICATION_ONLY)
        self.assertFalse(attachment.PRODUCTION_READY)
        self.assertFalse(attachment.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertEqual(attachment.PRINTED_MATERIAL, "PETG")
        self.assertEqual(
            (attachment.RATED_LOAD_KG, attachment.RATED_LOAD_LB), (0.0, 0.0)
        )
        self.assertFalse(attachment.STRUCTURAL_OR_SHELF_LOAD_CREDIT)
        self.assertFalse(attachment.SUPPORT_CORE_SUBTRACTION_ALLOWED)
        self.assertFalse(attachment.WALL_BORES_EMITTED)
        self.assertFalse(attachment.ENDPOINT_INSTALLED_CLEARANCE_QUALIFIED)
        self.assertFalse(attachment.DOOR_AND_CABLE_LOOP_CLEARANCE_QUALIFIED)

    def test_rail_mapping_is_centered_and_uses_exact_middle_band_and_overlap(self) -> None:
        self.assertEqual(attachment.RAIL_TO_STRAP_OVERLAP_MM, 0.4)
        self.assertEqual(attachment.RAIL_ACROSS_RUN_REVEAL_EACH_SIDE_MM, 2.0)
        self.assertEqual(attachment.RAIL_VERTICAL_BOTTOM_MM, 64.0)
        self.assertEqual(attachment.RAIL_VERTICAL_TOP_MM, 126.0)
        self.assertEqual(attachment.RAIL_BACK_Q_MM, 15.6)
        self.assertEqual(attachment.RAIL_FRONT_Q_MM, 24.4)
        self.assertEqual(attachment.SOCKET_CAVITY_NEAREST_CORE_Q_MM, 18.0)
        self.assertEqual(attachment.SOURCE_CORE_OUTER_Q_MM, 16.0)
        np.testing.assert_allclose(
            self.through.mapped_rail.bounds,
            ((15.6, 64.0, -2.0), (24.4, 126.0, 34.0)),
            atol=1.0e-6,
        )
        np.testing.assert_allclose(
            self.through.body.bounds,
            ((0.0, 0.0, -2.0), (152.4, 160.0, 34.0)),
            atol=1.0e-6,
        )

    def test_union_is_one_body_and_source_core_is_exactly_contained(self) -> None:
        for endpoint, candidate in (
            ("through_outer", self.through),
            ("return_outer", self.return_candidate),
        ):
            with self.subTest(endpoint=endpoint):
                assert_one_body(self, candidate.body)
                evidence = attachment.core_containment_evidence(endpoint)
                self.assertEqual(
                    evidence.source_core_digest_before,
                    evidence.source_core_digest_after,
                )
                self.assertAlmostEqual(
                    evidence.expected_overlap_volume_mm3, 793.6, places=7
                )
                self.assertGreater(evidence.additive_print_foot_volume_mm3, 0.0)
                self.assertAlmostEqual(
                    evidence.positive_overlap_volume_mm3,
                    evidence.expected_overlap_volume_mm3,
                    delta=0.01,
                )
                self.assertLessEqual(evidence.volume_balance_error_mm3, 0.01)
                self.assertEqual(evidence.missing_source_core_volume_mm3, 0.0)
                self.assertTrue(evidence.source_core_preserved)
                self.assertTrue(evidence.additive_only)

    def test_socket_cavities_remain_outside_the_untouched_support_core(self) -> None:
        self.assertGreater(
            attachment.SOCKET_CAVITY_NEAREST_CORE_Q_MM,
            attachment.SOURCE_CORE_OUTER_Q_MM,
        )
        # The original strap section remains an exact 160 x 32 rectangle well
        # behind the additive rail overlap.  The wrapper is 34 mm at this
        # plane only because the authored 2 mm print foot extends one side.
        for candidate in (self.through, self.return_candidate):
            source_section = candidate.source_core.section(
                plane_origin=(8.0, 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0)
            )
            self.assertIsNotNone(source_section)
            self.assertEqual(len(source_section.discrete), 1)
            source_points = np.vstack(source_section.discrete)
            np.testing.assert_allclose(
                np.ptp(source_points, axis=0), (0.0, 160.0, 32.0), atol=1.0e-6
            )
            wrapper_section = candidate.body.section(
                plane_origin=(8.0, 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0)
            )
            self.assertIsNotNone(wrapper_section)
            self.assertEqual(len(wrapper_section.discrete), 1)
            wrapper_points = np.vstack(wrapper_section.discrete)
            np.testing.assert_allclose(
                np.ptp(wrapper_points, axis=0), (0.0, 160.0, 34.0), atol=1.0e-6
            )

    def test_both_endpoint_candidates_preserve_two_socket_service_for_both_modules(self) -> None:
        modules = (
            cable.build_flush_blank_module(),
            cable.build_multi_cable_organizer_hook_module(),
        )
        for endpoint, candidate in (
            ("through_outer", self.through),
            ("return_outer", self.return_candidate),
        ):
            for module in modules:
                for station in range(2):
                    path = attachment.mapped_module_service_path(
                        module, endpoint=endpoint, station_index=station
                    )
                    self.assertEqual(path.increment_mm, 1.0)
                    self.assertEqual(len(path.insertion_approach), 7)
                    self.assertEqual(len(path.gravity_drop), 9)
                    for pose in (*path.insertion_approach, *path.gravity_drop):
                        self.assertAlmostEqual(
                            attachment.attachment_collision_volume(
                                candidate.body, pose
                            ),
                            0.0,
                            places=7,
                        )
                    self.assertEqual(
                        [support.mesh_fingerprint(mesh) for mesh in path.gravity_drop],
                        [
                            support.mesh_fingerprint(mesh)
                            for mesh in reversed(path.removal_lift)
                        ],
                    )

    def test_saved_wall_face_orientation_is_layer_connected_support_free_and_a1_safe(self) -> None:
        saved = attachment.build_saved_attachment_candidates()
        evidence = attachment.saved_attachment_print_evidence()
        self.assertEqual(tuple(saved), tuple(item.part_name for item in evidence))
        for item in evidence:
            with self.subTest(endpoint=item.endpoint):
                self.assertEqual(
                    item.orientation_id,
                    "broad_run_side_additive_print_foot_on_plate",
                )
                self.assertFalse(item.support_required)
                self.assertEqual(item.support_classification, "support_free")
                self.assertTrue(item.layer_connected)
                self.assertEqual(item.disconnected_layer_indices, ())
                self.assertEqual(item.sampled_layer_count, 180)
                self.assertGreater(item.first_layer_contact_area_mm2, 8000.0)
                self.assertEqual(item.maximum_new_side_reveal_mm, 2.0)
                self.assertEqual(item.body_count, 1)
                self.assertTrue(item.watertight)
                self.assertTrue(item.winding_consistent)
                self.assertTrue(item.envelope.fits)
                np.testing.assert_allclose(
                    item.envelope.raw_part_mm,
                    (152.4, 160.0, 36.0),
                    atol=1.0e-6,
                )
                np.testing.assert_allclose(
                    item.envelope.required_build_volume_mm,
                    (166.6, 174.2, 36.0),
                    atol=1.0e-6,
                )

    def test_keyed_interface_requires_deterministic_handed_endpoint_candidates(self) -> None:
        semantics = attachment.endpoint_semantics_evidence()
        self.assertFalse(attachment.SAME_CANDIDATE_SKU_BOTH_ENDPOINTS)
        self.assertFalse(semantics.same_candidate_sku_both_endpoints)
        self.assertFalse(semantics.through_is_self_mirror_symmetric)
        self.assertTrue(semantics.mirrored_through_matches_return)
        self.assertTrue(semantics.return_mirrored_back_matches_through)
        self.assertIn("keyed socket extension is asymmetric", semantics.reason)
        self.assertNotEqual(semantics.through_part_name, semantics.return_part_name)

    def test_builders_and_double_mirror_are_deterministic(self) -> None:
        first = attachment.build_all_attachment_candidates()
        second = attachment.build_all_attachment_candidates()
        self.assertEqual(
            tuple(first),
            (attachment.THROUGH_PART_NAME, attachment.RETURN_PART_NAME),
        )
        self.assertEqual(
            {name: support.mesh_fingerprint(mesh) for name, mesh in first.items()},
            {name: support.mesh_fingerprint(mesh) for name, mesh in second.items()},
        )
        through = first[attachment.THROUGH_PART_NAME]
        double = attachment.mirror_across_support_run_center(
            attachment.mirror_across_support_run_center(through)
        )
        self.assertEqual(
            support.mesh_fingerprint(through), support.mesh_fingerprint(double)
        )
        saved = attachment.build_saved_attachment_candidates()
        self.assertNotEqual(
            support.mesh_fingerprint(saved[attachment.THROUGH_PART_NAME]),
            support.mesh_fingerprint(saved[attachment.RETURN_PART_NAME]),
        )

    def test_invalid_endpoint_and_service_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            attachment.build_outer_bookend_attachment("left")
        with self.assertRaises(ValueError):
            attachment.mapped_module_service_path(
                cable.build_flush_blank_module(),
                endpoint="left",
                station_index=0,
            )
        with self.assertRaises(IndexError):
            attachment.mapped_module_service_path(
                cable.build_flush_blank_module(),
                endpoint="through_outer",
                station_index=2,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
