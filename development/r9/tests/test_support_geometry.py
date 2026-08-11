#!/usr/bin/env python3
"""Geometry contracts for the minimized R9 qualification studies."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np


R9 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R9))

import support_geometry as geometry  # noqa: E402


def assert_one_watertight_body(test: unittest.TestCase, mesh) -> None:
    test.assertFalse(mesh.is_empty)
    test.assertTrue(mesh.is_watertight)
    test.assertTrue(mesh.is_winding_consistent)
    test.assertTrue(mesh.is_volume)
    test.assertGreater(float(mesh.volume), 0.0)
    test.assertEqual(len(mesh.split(only_watertight=False)), 1)


def section_spans(mesh, axis: int, coordinate: float) -> tuple[int, np.ndarray]:
    origin = np.zeros(3, dtype=float)
    normal = np.zeros(3, dtype=float)
    origin[axis] = coordinate
    normal[axis] = 1.0
    section = mesh.section(plane_origin=origin, plane_normal=normal)
    if section is None:
        raise AssertionError("Expected a nonempty mesh section")
    points = np.vstack([np.asarray(loop, dtype=float) for loop in section.discrete])
    return len(section.discrete), np.ptp(points, axis=0)


class R9SupportGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outer = geometry.build_outer_feature_support_candidate()
        cls.compact = geometry.build_compact_support_candidate()
        cls.corner = geometry.build_concealed_corner_half_candidate()
        cls.corner_set = geometry.build_hidden_corner_dry_fit_set()
        cls.ledger = geometry.build_modular_rear_ledger_joint_coupon()
        cls.beam = geometry.build_staggered_front_beam_splice_coupon()

    def test_scope_material_and_capacity_state_fail_closed(self) -> None:
        self.assertTrue(geometry.QUALIFICATION_ONLY)
        self.assertFalse(geometry.PRODUCTION_READY)
        self.assertFalse(geometry.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertEqual(geometry.PRINTED_MATERIAL, "PETG")
        self.assertEqual((geometry.RATED_LOAD_KG, geometry.RATED_LOAD_LB), (0.0, 0.0))
        self.assertFalse(geometry.WALL_BORES_EMITTED)

    def test_r9_dimensions_retain_only_the_r8_envelope_datums_needed(self) -> None:
        self.assertEqual(geometry.SHELF_PROJECTION_MM, 152.4)
        self.assertEqual(geometry.SUPPORT_RUN_THICKNESS_MM, 32.0)
        self.assertEqual(geometry.WALL_STRAP_TOTAL_DROP_MM, 160.0)
        self.assertEqual(geometry.WALL_STRAP_PROJECTION_MM, 16.0)
        self.assertEqual(geometry.OUTER_FEATURE_VISIBLE_DROP_MM, 120.65)
        self.assertEqual(geometry.COMPACT_VISIBLE_DROP_MM, 76.2)
        self.assertEqual(geometry.CONCEALED_CORNER_VISIBLE_DROP_MM, 50.8)
        self.assertEqual(geometry.CONCEALED_CORNER_HALF_THICKNESS_MM, 16.0)

    def test_supports_have_exact_bounds_and_shortened_projecting_bodies(self) -> None:
        cases = (
            (
                self.outer,
                geometry.OUTER_FEATURE_VISIBLE_DROP_MM,
                geometry.SUPPORT_RUN_THICKNESS_MM,
            ),
            (
                self.compact,
                geometry.COMPACT_VISIBLE_DROP_MM,
                geometry.SUPPORT_RUN_THICKNESS_MM,
            ),
            (
                self.corner,
                geometry.CONCEALED_CORNER_VISIBLE_DROP_MM,
                geometry.CONCEALED_CORNER_HALF_THICKNESS_MM,
            ),
        )
        for mesh, visible_drop, thickness in cases:
            with self.subTest(visible_drop=visible_drop, thickness=thickness):
                np.testing.assert_allclose(mesh.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
                np.testing.assert_allclose(
                    mesh.extents,
                    (
                        geometry.SHELF_PROJECTION_MM,
                        geometry.WALL_STRAP_TOTAL_DROP_MM,
                        thickness,
                    ),
                    atol=1.0e-7,
                )
                expected_bottom = geometry.WALL_STRAP_TOTAL_DROP_MM - visible_drop
                self.assertAlmostEqual(
                    geometry.projecting_body_bottom_mm(mesh), expected_bottom, places=7
                )

    def test_support_topology_is_one_body_with_only_the_deliberate_d_window(self) -> None:
        for mesh in (self.outer, self.compact, self.corner):
            assert_one_watertight_body(self, mesh)
            # One through-window in one closed orientable body has Euler zero.
            # Any extra tunnel would change this contract.
            self.assertEqual(mesh.euler_number, 0)

    def test_wall_straps_are_solid_full_drop_rectangles_with_no_bores(self) -> None:
        for mesh, thickness in (
            (self.outer, 32.0),
            (self.compact, 32.0),
            (self.corner, 16.0),
        ):
            self.assertTrue(geometry.wall_strap_is_uninterrupted(mesh))
            loops, spans = section_spans(
                mesh, axis=0, coordinate=geometry.WALL_STRAP_PROJECTION_MM / 2.0
            )
            self.assertEqual(loops, 1)
            np.testing.assert_allclose(spans, (0.0, 160.0, thickness), atol=1.0e-6)

    def test_explicit_corner_halves_have_complementary_handed_miters(self) -> None:
        corner = self.corner_set
        self.assertFalse(corner.field_angle_verified)
        self.assertFalse(corner.corner_load_path_authored)
        self.assertEqual(corner.nominal_fixture_angle_deg, 90.0)
        for half in (corner.through_half, corner.return_half):
            assert_one_watertight_body(self, half)
            self.assertEqual(half.euler_number, 0)
            np.testing.assert_allclose(half.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
            np.testing.assert_allclose(half.extents, (152.4, 160.0, 16.0), atol=1.0e-7)

        # At q=8 mm, through owns z=0..8 and return owns z=8..16.  These
        # complementary sections meet on the authored 45-degree plane without
        # overlapping the original 16 x 16 mm corner prism.
        sections = []
        for half in (corner.through_half, corner.return_half):
            section = half.section(
                plane_origin=(8.0, 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0)
            )
            self.assertIsNotNone(section)
            self.assertEqual(len(section.discrete), 1)
            sections.append(np.vstack(section.discrete))
        through_z = (float(np.min(sections[0][:, 2])), float(np.max(sections[0][:, 2])))
        return_z = (float(np.min(sections[1][:, 2])), float(np.max(sections[1][:, 2])))
        np.testing.assert_allclose(through_z, (0.0, 8.0), atol=1.0e-6)
        np.testing.assert_allclose(return_z, (8.0, 16.0), atol=1.0e-6)

    def test_corner_key_cover_and_tabletop_fixture_are_exact_nonrated_coupons(self) -> None:
        corner = self.corner_set
        cases = (
            (corner.shear_key, (48.0, 48.0, 4.0)),
            (corner.cosmetic_cover, (64.0, 64.0, 1.6)),
            (corner.tabletop_fixture, (160.0, 160.0, 4.0)),
        )
        for mesh, extents in cases:
            assert_one_watertight_body(self, mesh)
            self.assertEqual(mesh.euler_number, 2)
            np.testing.assert_allclose(mesh.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
            np.testing.assert_allclose(mesh.extents, extents, atol=1.0e-7)
            self.assertTrue(geometry.print_envelope_with_margins(mesh).fits)

        fixture = corner.tabletop_fixture
        # Points in both 20 mm arms are material; the open upper-right field
        # distinguishes an L-square from a filled plate.
        horizontal = fixture.section(
            plane_origin=(80.0, 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0)
        )
        vertical = fixture.section(
            plane_origin=(0.0, 80.0, 0.0), plane_normal=(0.0, 1.0, 0.0)
        )
        self.assertIsNotNone(horizontal)
        self.assertIsNotNone(vertical)
        self.assertEqual(len(horizontal.discrete), 1)
        self.assertEqual(len(vertical.discrete), 1)

    def test_saved_support_orientation_is_connected_at_representative_layers(self) -> None:
        for mesh in (self.outer, self.compact, self.corner):
            for build_z in (0.1, float(mesh.extents[2]) / 2.0, float(mesh.extents[2]) - 0.1):
                section = mesh.section(
                    plane_origin=(0.0, 0.0, build_z),
                    plane_normal=(0.0, 0.0, 1.0),
                )
                self.assertIsNotNone(section)
                # Outer shell plus one hole: two loops, one connected material body.
                self.assertEqual(len(section.discrete), 2)
            self.assertEqual(len(mesh.split(only_watertight=False)), 1)

    def test_rear_ledger_coupon_bounds_topology_and_exact_socket_clearance(self) -> None:
        pair = self.ledger
        self.assertEqual(pair.clearance_per_face_mm, 0.4)
        self.assertEqual(pair.part_b_assembly_translation_mm, (60.0, 0.0, 0.0))
        np.testing.assert_allclose(pair.part_a.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
        np.testing.assert_allclose(pair.part_a.extents, (72.0, 16.0, 30.0), atol=1.0e-7)
        np.testing.assert_allclose(pair.part_b.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
        np.testing.assert_allclose(pair.part_b.extents, (60.0, 16.0, 30.0), atol=1.0e-7)
        for part in (pair.part_a, pair.part_b):
            assert_one_watertight_body(self, part)
            self.assertEqual(part.euler_number, 2)

        # The male tongue is exactly 8 x 18 mm.  The female end socket adds
        # 0.4 mm on every depth/height face and 0.4 mm beyond the tongue tip.
        male_loops, male_spans = section_spans(pair.part_a, axis=0, coordinate=66.0)
        self.assertEqual(male_loops, 1)
        np.testing.assert_allclose(male_spans, (0.0, 8.0, 18.0), atol=1.0e-6)
        female_section = pair.part_b.section(
            plane_origin=(6.0, 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0)
        )
        self.assertIsNotNone(female_section)
        self.assertEqual(len(female_section.discrete), 2)
        loop_spans = sorted(
            (
                tuple(np.ptp(np.asarray(loop, dtype=float), axis=0)[1:])
                for loop in female_section.discrete
            ),
            key=lambda span: span[0] * span[1],
        )
        np.testing.assert_allclose(loop_spans[0], (8.8, 18.8), atol=1.0e-6)
        np.testing.assert_allclose(loop_spans[1], (16.0, 30.0), atol=1.0e-6)
        assembled_a, assembled_b = pair.assembled_parts()
        np.testing.assert_allclose(assembled_a.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
        np.testing.assert_allclose(assembled_b.bounds[0], (60.0, 0.0, 0.0), atol=1.0e-7)
        self.assertAlmostEqual(float(assembled_b.bounds[1, 0]), 120.0, places=7)

    def test_front_beam_coupon_is_an_exact_staggered_noncolliding_pair(self) -> None:
        pair = self.beam
        self.assertEqual(pair.clearance_per_face_mm, 0.4)
        self.assertEqual(pair.part_b_assembly_translation_mm, (60.4, 0.0, 0.0))
        for part in (pair.part_a, pair.part_b):
            assert_one_watertight_body(self, part)
            self.assertEqual(part.euler_number, 2)
            np.testing.assert_allclose(part.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
            np.testing.assert_allclose(part.extents, (76.0, 16.0, 30.0), atol=1.0e-7)

        lower_loops, lower_spans = section_spans(pair.part_a, axis=0, coordinate=68.0)
        upper_loops, upper_spans = section_spans(pair.part_b, axis=0, coordinate=8.0)
        self.assertEqual((lower_loops, upper_loops), (1, 1))
        np.testing.assert_allclose(lower_spans, (0.0, 16.0, 14.6), atol=1.0e-6)
        np.testing.assert_allclose(upper_spans, (0.0, 16.0, 14.6), atol=1.0e-6)

        assembled_a, assembled_b = pair.assembled_parts()
        self.assertAlmostEqual(float(assembled_b.bounds[0, 0]), 60.4, places=7)
        self.assertAlmostEqual(float(assembled_b.bounds[1, 0]), 136.4, places=7)
        # In the 15.6 mm lap region, A ends at z=14.6 and B begins at z=15.4.
        # The resulting 0.8 mm total gap is 0.4 mm per opposing face.
        self.assertAlmostEqual(15.4 - 14.6, 0.8, places=7)
        self.assertEqual(len(assembled_a.split(only_watertight=False)), 1)
        self.assertEqual(len(assembled_b.split(only_watertight=False)), 1)

    def test_every_individual_part_fits_the_a1_mini_with_r8_process_margins(self) -> None:
        all_parts = (
            self.outer,
            self.compact,
            self.corner,
            self.ledger.part_a,
            self.ledger.part_b,
            self.beam.part_a,
            self.beam.part_b,
            self.corner_set.through_half,
            self.corner_set.return_half,
            self.corner_set.shear_key,
            self.corner_set.cosmetic_cover,
            self.corner_set.tabletop_fixture,
        )
        for mesh in all_parts:
            envelope = geometry.print_envelope_with_margins(mesh)
            self.assertTrue(envelope.fits)
            self.assertEqual(envelope.available_build_volume_mm, (180.0, 180.0, 180.0))
            self.assertTrue(
                all(
                    required <= available + geometry.GEOMETRY_EPSILON
                    for required, available in zip(
                        envelope.required_build_volume_mm,
                        envelope.available_build_volume_mm,
                    )
                )
            )
        outer_envelope = geometry.print_envelope_with_margins(self.outer)
        np.testing.assert_allclose(
            outer_envelope.required_build_volume_mm,
            (166.6, 174.2, 32.0),
            atol=1.0e-7,
        )

    def test_builders_are_deterministic_and_do_not_mutate_coupon_sources(self) -> None:
        first = geometry.build_all_qualification_parts()
        second = geometry.build_all_qualification_parts()
        self.assertEqual(tuple(first), tuple(second))
        self.assertEqual(len(first), 12)
        self.assertEqual(
            {name: geometry.mesh_fingerprint(mesh) for name, mesh in first.items()},
            {name: geometry.mesh_fingerprint(mesh) for name, mesh in second.items()},
        )

        original = geometry.mesh_fingerprint(self.ledger.part_b)
        assembled = self.ledger.assembled_parts()
        self.assertEqual(original, geometry.mesh_fingerprint(self.ledger.part_b))
        self.assertFalse(
            math.isclose(
                float(assembled[1].bounds[0, 0]),
                float(self.ledger.part_b.bounds[0, 0]),
                abs_tol=1.0e-9,
            )
        )

    def test_saved_orientations_are_complete_connected_and_a1_mini_safe(self) -> None:
        installed = geometry.build_all_qualification_parts()
        saved = geometry.build_saved_qualification_parts()
        evidence = geometry.saved_print_orientation_evidence()
        self.assertEqual(tuple(saved), tuple(installed))
        self.assertEqual(tuple(item.part_name for item in evidence), tuple(saved))
        self.assertEqual(len(evidence), 12)
        for item in evidence:
            with self.subTest(part=item.part_name):
                self.assertFalse(item.support_required)
                self.assertTrue(item.analytic_layer_rule)
                self.assertEqual(item.body_count, 1)
                self.assertTrue(item.watertight)
                self.assertTrue(item.winding_consistent)
                self.assertTrue(item.envelope.fits)
                self.assertEqual(
                    geometry.mesh_fingerprint(saved[item.part_name]),
                    geometry.mesh_fingerprint(
                        geometry.build_saved_qualification_parts()[item.part_name]
                    ),
                )

    def test_invalid_joint_clearances_fail_closed(self) -> None:
        for value in (0.0, -0.1, 1.1, float("nan"), True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    geometry.build_modular_rear_ledger_joint_coupon(
                        clearance_per_face_mm=value
                    )
                with self.assertRaises(ValueError):
                    geometry.build_staggered_front_beam_splice_coupon(
                        clearance_per_face_mm=value
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
