#!/usr/bin/env python3
"""Contracts for the separate R9 qualification-fixture evidence layer."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np


R9 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R9))

import fixture_assembly as fixtures  # noqa: E402
import support_geometry as geometry  # noqa: E402


class R9FixtureAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = fixtures.build_rear_ledger_insertion_removal_evidence()
        cls.beam = fixtures.build_front_beam_insertion_removal_evidence()
        cls.corner = fixtures.build_nominal_corner_tabletop_dry_fit_evidence()
        cls.blocker = fixtures.build_compact_one_bay_tabletop_evidence()

    def test_scope_material_field_and_capacity_state_fail_closed(self) -> None:
        self.assertTrue(fixtures.QUALIFICATION_ONLY)
        self.assertFalse(fixtures.PRODUCTION_READY)
        self.assertFalse(fixtures.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertFalse(fixtures.FIELD_ANGLE_VERIFIED)
        self.assertFalse(fixtures.WALL_BORES_EMITTED)
        self.assertEqual(fixtures.PRINTED_MATERIAL, "PETG")
        self.assertEqual((fixtures.RATED_LOAD_KG, fixtures.RATED_LOAD_LB), (0.0, 0.0))
        for evidence in (self.ledger, self.beam, self.corner):
            self.assertTrue(evidence.qualification_only)
            self.assertFalse(evidence.physical_qualification_complete)
            self.assertEqual(evidence.printed_material, "PETG")
            self.assertEqual((evidence.rated_load_kg, evidence.rated_load_lb), (0.0, 0.0))

    def test_coupon_paths_use_the_existing_exact_assembly_transforms(self) -> None:
        ledger_pair = geometry.build_modular_rear_ledger_joint_coupon()
        beam_pair = geometry.build_staggered_front_beam_splice_coupon()
        self.assertEqual(
            self.ledger.service_path.target_transform.translation_mm,
            ledger_pair.part_b_assembly_translation_mm,
        )
        self.assertEqual(
            self.beam.service_path.target_transform.translation_mm,
            beam_pair.part_b_assembly_translation_mm,
        )
        self.assertEqual(
            self.ledger.service_path.service_travel_mm,
            geometry.REAR_LEDGER_TONGUE_LENGTH_MM + ledger_pair.clearance_per_face_mm,
        )
        self.assertEqual(
            self.beam.service_path.service_travel_mm,
            geometry.FRONT_BEAM_SPLICE_LENGTH_MM,
        )

    def test_joint_clearances_are_exact_and_not_overstated_as_contact(self) -> None:
        ledger = {
            item.name: item.value_mm
            for item in self.ledger.service_path.target_clearances
        }
        self.assertEqual(
            ledger,
            {
                "socket_y_clearance_each_face": 0.4,
                "socket_z_clearance_each_face": 0.4,
                "tongue_tip_clearance": 0.4,
                "body_shoulder_contact": 0.0,
            },
        )
        self.assertEqual(len(self.ledger.service_path.intended_target_contacts), 1)

        beam = {
            item.name: item.value_mm for item in self.beam.service_path.target_clearances
        }
        self.assertEqual(
            beam,
            {
                "left_axial_shoulder_gap": 0.4,
                "right_axial_shoulder_gap": 0.4,
                "opposed_lap_face_gap": 0.8,
            },
        )
        self.assertEqual(self.beam.service_path.intended_target_contacts, ())

    def test_joint_insertion_and_reverse_removal_are_sampled_collision_free(self) -> None:
        for fixture in (self.ledger, self.beam):
            path = fixture.service_path
            with self.subTest(path=path.name):
                self.assertEqual(len(path.insertion_samples), 9)
                self.assertEqual(path.removal_samples, tuple(reversed(path.insertion_samples)))
                self.assertEqual(path.insertion_samples[0].seated_fraction, 0.0)
                self.assertEqual(path.insertion_samples[-1].seated_fraction, 1.0)
                self.assertEqual(
                    path.insertion_samples[0].service_offset_mm,
                    path.service_travel_mm,
                )
                self.assertEqual(path.insertion_samples[-1].service_offset_mm, 0.0)
                self.assertTrue(path.sampled_path_collision_free)
                self.assertLessEqual(
                    path.maximum_intersection_volume_mm3,
                    fixtures.COLLISION_VOLUME_TOLERANCE_MM3,
                )
                self.assertTrue(
                    all(
                        sample.total_intersection_volume_mm3
                        <= fixtures.COLLISION_VOLUME_TOLERANCE_MM3
                        for sample in path.insertion_samples
                    )
                )

    def test_every_joint_part_is_one_body_watertight_and_a1_mini_safe(self) -> None:
        for fixture in (self.ledger, self.beam):
            for part in fixture.parts:
                with self.subTest(part=part.part_name):
                    self.assertEqual(part.body_count, 1)
                    self.assertTrue(part.watertight)
                    self.assertTrue(part.winding_consistent)
                    self.assertTrue(part.positive_volume)
                    self.assertTrue(part.a1_mini_fits)
                    self.assertTrue(
                        all(
                            needed <= available + geometry.GEOMETRY_EPSILON
                            for needed, available in zip(
                                part.required_build_volume_mm,
                                geometry.A1_MINI_BUILD_VOLUME_MM,
                            )
                        )
                    )

    def test_corner_uses_exact_right_handed_nominal_square_transforms(self) -> None:
        placed = {item.part.part_name: item for item in self.corner.placed_parts}
        corner_set = geometry.build_hidden_corner_dry_fit_set()
        self.assertEqual(self.corner.nominal_fixture_angle_deg, 90.0)
        self.assertFalse(self.corner.field_angle_verified)
        self.assertFalse(self.corner.corner_load_path_authored)

        np.testing.assert_allclose(
            placed[corner_set.through_half_name].target_transform.as_array(),
            np.eye(4),
            atol=0.0,
        )
        np.testing.assert_allclose(
            placed[corner_set.return_half_name].target_transform.as_array(),
            (
                (0.0, 0.0, -1.0, 16.0),
                (0.0, 1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            atol=0.0,
        )
        for item in placed.values():
            rotation = item.target_transform.as_array()[:3, :3]
            self.assertAlmostEqual(float(np.linalg.det(rotation)), 1.0, places=12)

    def test_corner_target_bounds_prove_the_tabletop_stack_datums(self) -> None:
        meshes = fixtures.build_nominal_corner_target_meshes()
        corner_set = geometry.build_hidden_corner_dry_fit_set()
        expected = {
            corner_set.tabletop_fixture_name: ((0.0, -4.0, 0.0), (160.0, 0.0, 160.0)),
            corner_set.through_half_name: ((0.0, 0.0, 0.0), (152.4, 160.0, 16.0)),
            corner_set.return_half_name: ((0.0, 0.0, 0.0), (16.0, 160.0, 152.4)),
            corner_set.shear_key_name: ((0.0, 160.0, 0.0), (48.0, 164.0, 48.0)),
            corner_set.cosmetic_cover_name: ((0.0, 164.0, 0.0), (64.0, 165.6, 64.0)),
        }
        self.assertEqual(tuple(meshes), tuple(expected))
        for name, bounds in expected.items():
            with self.subTest(part=name):
                np.testing.assert_allclose(meshes[name].bounds, bounds, atol=1.0e-5)
                self.assertEqual(len(meshes[name].split(only_watertight=False)), 1)

    def test_corner_target_and_all_service_paths_have_no_unintended_penetration(self) -> None:
        self.assertEqual(len(self.corner.placed_parts), 5)
        self.assertEqual(len(self.corner.target_pair_intersections), 10)
        self.assertTrue(self.corner.target_pose_collision_free)
        self.assertLessEqual(
            self.corner.maximum_target_intersection_volume_mm3,
            fixtures.COLLISION_VOLUME_TOLERANCE_MM3,
        )
        for path in self.corner.service_paths:
            with self.subTest(path=path.name):
                self.assertEqual(path.removal_samples, tuple(reversed(path.insertion_samples)))
                self.assertTrue(path.sampled_path_collision_free)
                self.assertTrue(path.intended_target_contacts)
                self.assertLessEqual(
                    path.maximum_intersection_volume_mm3,
                    fixtures.COLLISION_VOLUME_TOLERANCE_MM3,
                )

    def test_every_corner_part_is_one_body_and_fits_the_a1_mini(self) -> None:
        for placed in self.corner.placed_parts:
            part = placed.part
            with self.subTest(part=part.part_name):
                self.assertEqual(part.body_count, 1)
                self.assertTrue(part.watertight)
                self.assertTrue(part.winding_consistent)
                self.assertTrue(part.positive_volume)
                self.assertTrue(part.a1_mini_fits)

    def test_one_bay_layout_is_explicitly_blocked_instead_of_invented(self) -> None:
        blocker = self.blocker
        self.assertTrue(blocker.blocked)
        self.assertFalse(blocker.emitted_meshes)
        self.assertEqual(blocker.placed_parts, ())
        self.assertTrue(blocker.qualification_only)
        self.assertFalse(blocker.production_ready)
        self.assertEqual(blocker.printed_material, "PETG")
        self.assertEqual((blocker.rated_load_kg, blocker.rated_load_lb), (0.0, 0.0))
        self.assertGreaterEqual(len(blocker.missing_authored_interfaces), 5)
        joined = " ".join(blocker.missing_authored_interfaces).lower()
        for term in ("ledger", "front-beam", "cassette", "bay", "wall fastener"):
            self.assertIn(term, joined)

    def test_builders_are_deterministic_and_invalid_sample_counts_fail_closed(self) -> None:
        first = fixtures.build_nominal_corner_tabletop_dry_fit_evidence(sample_count=3)
        second = fixtures.build_nominal_corner_tabletop_dry_fit_evidence(sample_count=3)
        self.assertEqual(first, second)
        for invalid in (0, 1, -1, True):
            with self.subTest(sample_count=invalid):
                with self.assertRaises(ValueError):
                    fixtures.build_rear_ledger_insertion_removal_evidence(
                        sample_count=invalid
                    )
                with self.assertRaises(ValueError):
                    fixtures.build_nominal_corner_tabletop_dry_fit_evidence(
                        sample_count=invalid
                    )

    def test_rigid_transform_rejects_reflections_and_non_unit_service_axes(self) -> None:
        reflected = (
            (-1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
        with self.assertRaises(ValueError):
            fixtures.RigidTransform(reflected)
        with self.assertRaises(ValueError):
            fixtures._unit_vector((2.0, 0.0, 0.0))
        self.assertTrue(math.isclose(np.linalg.det(fixtures.identity_transform().as_array()[:3, :3]), 1.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
