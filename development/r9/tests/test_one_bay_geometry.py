#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np


R9_ROOT = Path(__file__).resolve().parents[1]
if str(R9_ROOT) not in sys.path:
    sys.path.insert(0, str(R9_ROOT))

import one_bay_geometry as one_bay  # noqa: E402
import cable_geometry  # noqa: E402


class R9OneBayGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = one_bay.build_one_bay_evidence()
        cls.saved = one_bay.build_saved_one_bay_parts()

    def test_exact_five_part_inventory_and_no_load_boundary(self) -> None:
        self.assertEqual(
            tuple(item.name for item in self.evidence.parts),
            (
                "r9_one_bay_left_compact_support",
                "r9_one_bay_right_compact_support",
                "r9_one_bay_rear_ledger",
                "r9_one_bay_front_beam",
                "r9_one_bay_shelf_cassette",
            ),
        )
        self.assertTrue(one_bay.QUALIFICATION_ONLY)
        self.assertFalse(one_bay.PRODUCTION_READY)
        self.assertFalse(one_bay.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertEqual(one_bay.RATED_LOAD_KG, 0.0)
        self.assertEqual(one_bay.RATED_LOAD_LB, 0.0)
        self.assertTrue(one_bay.WALL_BORES_EMITTED)
        self.assertIn("candidate printed wall bores", self.evidence.no_load_boundary)
        self.assertIn("no wall-install authorization", self.evidence.no_load_boundary)

    def test_exact_full_depth_a1_mini_bay_dimensions(self) -> None:
        self.assertEqual(self.evidence.bay_width_mm, 160.0)
        self.assertEqual(self.evidence.shelf_depth_mm, 152.4)
        self.assertEqual(self.evidence.shelf_height_mm, 30.0)
        cassette = self.saved["r9_one_bay_shelf_cassette"]
        np.testing.assert_allclose(cassette.extents, (160.0, 152.4, 30.0), atol=1e-5)
        envelopes = one_bay.print_envelopes()
        self.assertTrue(all(item.fits for item in envelopes.values()))
        np.testing.assert_allclose(
            envelopes["r9_one_bay_shelf_cassette"].required_build_volume_mm,
            (174.2, 166.6, 30.0),
            atol=1e-5,
        )

    def test_every_saved_part_is_one_watertight_positive_body(self) -> None:
        for name, mesh in self.saved.items():
            with self.subTest(name=name):
                self.assertEqual(len(mesh.split(only_watertight=False)), 1)
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_winding_consistent)
                self.assertGreater(mesh.volume, 0.0)
                np.testing.assert_allclose(mesh.bounds[0], (0.0, 0.0, 0.0), atol=1e-6)

    def test_member_and_deck_interfaces_have_exact_clearance(self) -> None:
        self.assertEqual(self.evidence.member_socket_clearance_per_face_mm, 0.4)
        self.assertEqual(self.evidence.deck_locator_clearance_per_face_mm, 0.4)
        self.assertEqual(one_bay.MEMBER_TONGUE_LENGTH_MM, 8.0)
        self.assertEqual(one_bay.MEMBER_TONGUE_HEIGHT_MM, 30.0)
        self.assertEqual(one_bay.LOCATOR_BOSS_PROTRUSION_MM, 1.4)
        self.assertEqual(one_bay.LOCATOR_POCKET_DEPTH_MM, 2.0)

    def test_three_support_free_mounting_bores_clear_the_member_sockets(self) -> None:
        self.assertEqual(self.evidence.mounting_bores_per_support, 3)
        self.assertEqual(self.evidence.mounting_bore_diameter_mm, 7.0)
        self.assertEqual(
            self.evidence.mounting_bore_drops_below_underside_mm,
            (16.0, 80.0, 144.0),
        )
        self.assertEqual(self.evidence.mounting_bore_center_spacing_mm, 64.0)
        self.assertAlmostEqual(
            self.evidence.fastener_candidate_minimum_spacing_mm,
            59.944,
            places=3,
        )
        self.assertTrue(self.evidence.fastener_candidate_geometry_spacing_passes)
        self.assertIn("GRK RSS", self.evidence.fastener_candidate_product)
        self.assertEqual(self.evidence.maximum_flat_washer_outer_diameter_mm, 20.0)
        self.assertTrue(self.evidence.mounting_bores_clear_member_sockets)
        radius = one_bay.MOUNTING_BORE_DIAMETER_MM / 2.0
        self.assertGreaterEqual(
            one_bay.MOUNTING_BORE_DIAMOND_HALF_DIAGONAL_MM,
            radius * np.sqrt(2.0),
        )

    def test_fully_assembled_target_pose_has_no_positive_overlap(self) -> None:
        self.assertEqual(len(self.evidence.pair_intersections), 10)
        self.assertTrue(self.evidence.target_pose_collision_free)
        self.assertLessEqual(
            self.evidence.maximum_intersection_volume_mm3,
            one_bay.COLLISION_TOLERANCE_MM3,
        )
        for item in self.evidence.pair_intersections:
            with self.subTest(pair=(item.first_name, item.second_name)):
                self.assertLessEqual(item.volume_mm3, one_bay.COLLISION_TOLERANCE_MM3)
        self.assertTrue(self.evidence.service_paths_collision_free)
        self.assertLessEqual(
            self.evidence.service_path_maximum_intersection_volume_mm3,
            one_bay.COLLISION_TOLERANCE_MM3,
        )

    def test_palatine_moderne_details_are_additive_and_print_connected(self) -> None:
        self.assertEqual(
            self.evidence.aesthetic_contract_id,
            "r9_palatine_moderne_v1",
        )
        keystone = one_bay._support_keystone_insert()
        self.assertTrue(keystone.is_watertight)
        np.testing.assert_allclose(keystone.extents[2], 32.0, atol=1e-6)
        rear = one_bay.build_rear_ledger()
        front = one_bay.build_front_beam()
        self.assertGreater(front.volume, rear.volume)
        self.assertEqual(front.extents[1], 18.0)

    def test_support_hands_are_distinct_and_source_dimensions_are_preserved(self) -> None:
        left = one_bay.build_left_compact_support()
        right = one_bay.build_right_compact_support()
        self.assertFalse(
            np.array_equal(left.faces, right.faces)
            and np.array_equal(left.vertices, right.vertices)
        )
        np.testing.assert_allclose(left.extents, right.extents, atol=1e-6)
        np.testing.assert_allclose(
            left.extents,
            (152.4, 161.4, 32.0),
            atol=1e-5,
        )

    def test_print_routing_is_support_off_and_deterministic(self) -> None:
        first = one_bay.build_saved_one_bay_parts()
        second = one_bay.build_saved_one_bay_parts()
        for item in self.evidence.parts:
            with self.subTest(name=item.name):
                self.assertFalse(item.support_required)
                np.testing.assert_array_equal(first[item.name].faces, second[item.name].faces)
                np.testing.assert_allclose(
                    first[item.name].vertices,
                    second[item.name].vertices,
                    atol=0.0,
                )

    def test_every_saved_layer_overlaps_deposited_material_below(self) -> None:
        for name, mesh in self.saved.items():
            with self.subTest(name=name):
                report = cable_geometry.saved_layer_island_report(mesh)
                self.assertFalse(report.support_required)
                self.assertEqual(report.island_layer_indices, ())
                self.assertGreater(report.first_layer_contact_area_mm2, 100.0)

    def test_tabletop_assembly_order_is_complete_and_reversible(self) -> None:
        self.assertEqual(len(self.evidence.tabletop_assembly_order), 5)
        joined = " ".join(self.evidence.tabletop_assembly_order)
        for term in (
            "rear ledger",
            "front beam",
            "handed compact supports",
            "cassette",
            "reverse",
        ):
            self.assertIn(term, joined)


if __name__ == "__main__":
    unittest.main()
