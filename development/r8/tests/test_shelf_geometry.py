#!/usr/bin/env python3
"""Topology, envelope, and qualification-scope tests for R8 shelf geometry."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np


R8 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R8))

from shelf_geometry import (  # noqa: E402
    CASSETTE_HEIGHT_MM,
    CASSETTE_MAX_CLEAR_SPAN_MM,
    CASSETTE_PERIMETER_MM,
    CASSETTE_RIB_MM,
    CASSETTE_SKIN_MM,
    CORBEL_INSTALLED_HEIGHT_MM,
    CORBEL_FRONT_NOSE_MM,
    CORBEL_MINIMUM_CURVED_WEB_MM,
    CORBEL_PROJECTION_MM,
    CORBEL_ROOT_RADIUS_MM,
    CORBEL_RUN_THICKNESS_MM,
    CORBEL_TOP_CHORD_MM,
    CORBEL_WALL_CHORD_MM,
    QUALIFICATION_ONLY,
    RATED_LOAD_KG,
    RATED_LOAD_LB,
    SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
    SHELF_DEPTH_MM,
    build_coffered_cassette_seed,
    build_front_first_u_box_cassette,
    build_matched_corbel_pair,
    cassette_seam_bearing_datums,
    corbel_layer_connectivity,
    orient_cassette_on_long_edge,
    print_envelope_with_margins,
    saved_layer_connectivity,
    minimum_curved_web_thickness_mm,
)


LONGEST_PHYSICAL_MODULE_MM = 201.134375


def assert_single_printable_body(test: unittest.TestCase, mesh) -> None:
    test.assertFalse(mesh.is_empty)
    test.assertTrue(mesh.is_watertight)
    test.assertTrue(mesh.is_winding_consistent)
    test.assertGreater(mesh.volume, 0.0)
    test.assertEqual(len(mesh.split(only_watertight=False)), 1)


class R8ShelfGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.curved, cls.straight = build_matched_corbel_pair()
        cls.cassette, cls.coffer = build_coffered_cassette_seed(
            LONGEST_PHYSICAL_MODULE_MM
        )
        cls.u_box, cls.u_box_metrics = build_front_first_u_box_cassette(
            LONGEST_PHYSICAL_MODULE_MM
        )

    def test_scope_is_qualification_only_and_unrated(self) -> None:
        self.assertTrue(QUALIFICATION_ONLY)
        self.assertEqual((RATED_LOAD_KG, RATED_LOAD_LB), (0.0, 0.0))

    def test_d_frame_and_control_are_single_watertight_bodies(self) -> None:
        expected = np.asarray(
            (CORBEL_PROJECTION_MM, CORBEL_INSTALLED_HEIGHT_MM, CORBEL_RUN_THICKNESS_MM)
        )
        for mesh in (self.curved, self.straight):
            assert_single_printable_body(self, mesh)
            np.testing.assert_allclose(mesh.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-6)
            np.testing.assert_allclose(mesh.extents, expected, atol=1.0e-6)

    def test_d_frame_has_frozen_chords_and_true_r10_root_study(self) -> None:
        self.assertEqual(CORBEL_WALL_CHORD_MM, 16.0)
        self.assertEqual(CORBEL_TOP_CHORD_MM, 16.0)
        self.assertEqual(CORBEL_ROOT_RADIUS_MM, 10.0)
        self.assertEqual(CORBEL_FRONT_NOSE_MM, 32.0)
        self.assertEqual(CORBEL_MINIMUM_CURVED_WEB_MM, 16.0)
        self.assertGreaterEqual(
            minimum_curved_web_thickness_mm(),
            CORBEL_MINIMUM_CURVED_WEB_MM,
        )

        # At q=8 mm the entire wall chord is uninterrupted: the resulting
        # section is one solid 160 x 32 rectangle, proving the qualification
        # mesh has no wall bores or accessory cuts in its structural spine.
        section = self.curved.section(
            plane_origin=(8.0, 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0)
        )
        self.assertIsNotNone(section)
        self.assertEqual(len(section.discrete), 1)
        points = np.asarray(section.discrete[0])
        self.assertAlmostEqual(float(np.ptp(points[:, 1])), CORBEL_INSTALLED_HEIGHT_MM, places=6)
        self.assertAlmostEqual(float(np.ptp(points[:, 2])), CORBEL_RUN_THICKNESS_MM, places=6)

    def test_curved_and_straight_controls_match_volume_within_one_percent(self) -> None:
        difference = abs(self.curved.volume - self.straight.volume)
        relative = difference / self.curved.volume
        self.assertLess(relative, 0.01)
        # The equal-area construction should be substantially tighter than the
        # study requirement; retaining this catches accidental profile drift.
        self.assertLess(relative, 1.0e-5)

    def test_saved_corbel_orientation_has_connected_material_at_every_layer(self) -> None:
        for mesh in (self.curved, self.straight):
            report = corbel_layer_connectivity(mesh, layer_height_mm=0.2)
            self.assertEqual(report.sampled_layer_count, 160)
            self.assertEqual(report.failed_layer_indices, ())
            self.assertTrue(report.all_layers_connected)

    def test_open_coffer_seed_dimensions_spans_volume_and_body(self) -> None:
        assert_single_printable_body(self, self.cassette)
        np.testing.assert_allclose(
            self.cassette.extents,
            (LONGEST_PHYSICAL_MODULE_MM, SHELF_DEPTH_MM, CASSETTE_HEIGHT_MM),
            atol=1.0e-6,
        )
        self.assertEqual(self.coffer.continuous_skin_mm, CASSETTE_SKIN_MM)
        self.assertEqual(self.coffer.perimeter_mm, CASSETTE_PERIMETER_MM)
        self.assertEqual(self.coffer.rib_mm, CASSETTE_RIB_MM)
        self.assertGreaterEqual(self.coffer.rib_mm, 3.2)
        self.assertLessEqual(self.coffer.rib_mm, 4.0)
        self.assertLessEqual(
            self.coffer.maximum_clear_span_mm,
            CASSETTE_MAX_CLEAR_SPAN_MM + 1.0e-7,
        )
        self.assertEqual(self.coffer.open_coffer_face, "underside")

        void_plan_area = (
            self.coffer.cells_along_run
            * self.coffer.cells_through_depth
            * self.coffer.clear_span_along_run_mm
            * self.coffer.clear_span_through_depth_mm
        )
        expected_volume = (
            LONGEST_PHYSICAL_MODULE_MM * SHELF_DEPTH_MM * CASSETTE_HEIGHT_MM
            - void_plan_area * (CASSETTE_HEIGHT_MM - CASSETTE_SKIN_MM)
        )
        # Manifold's float32 exchange introduces sub-cubic-millimetre noise
        # across the 108-cell boolean, while preserving the exact authored
        # dimensions and a relative volume error below 3e-7.
        self.assertAlmostEqual(self.cassette.volume, expected_volume, delta=0.5)

        # A section inside the top skin is an unbroken rectangle; the open
        # underside remains visually inspectable and avoids sealed cell shells.
        section = self.cassette.section(
            plane_origin=(0.0, 0.0, CASSETTE_HEIGHT_MM - CASSETTE_SKIN_MM / 2.0),
            plane_normal=(0.0, 0.0, 1.0),
        )
        self.assertIsNotNone(section)
        self.assertEqual(len(section.discrete), 1)

    def test_cassette_ends_publish_exact_full_depth_seam_bearing_datums(self) -> None:
        left, right = cassette_seam_bearing_datums(LONGEST_PHYSICAL_MODULE_MM)
        self.assertEqual(left.side, "left")
        self.assertEqual(right.side, "right")
        self.assertEqual(left.seam_plane_x_mm, 0.0)
        self.assertEqual(right.seam_plane_x_mm, LONGEST_PHYSICAL_MODULE_MM)
        self.assertEqual(
            left.land_x_bounds_mm,
            (0.0, SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM),
        )
        self.assertEqual(
            right.land_x_bounds_mm,
            (
                LONGEST_PHYSICAL_MODULE_MM
                - SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
                LONGEST_PHYSICAL_MODULE_MM,
            ),
        )
        for datum in (left, right):
            self.assertEqual(datum.depth_bounds_mm, (0.0, SHELF_DEPTH_MM))
            self.assertEqual(datum.underside_e_mm, 0.0)
            self.assertAlmostEqual(
                datum.land_x_bounds_mm[1] - datum.land_x_bounds_mm[0],
                SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
            )
        cfg = json.loads((R8 / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(
            cfg["shelf"]["selected_cassette_geometry_mm"][
                "full_depth_end_land"
            ],
            SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
        )

    def test_selected_u_box_is_smooth_lighter_open_rear_and_layer_connected(self) -> None:
        assert_single_printable_body(self, self.u_box)
        np.testing.assert_allclose(
            self.u_box.extents,
            (LONGEST_PHYSICAL_MODULE_MM, SHELF_DEPTH_MM, CASSETTE_HEIGHT_MM),
            atol=1.0e-6,
        )
        metrics = self.u_box_metrics
        self.assertEqual(
            (
                metrics.top_skin_mm,
                metrics.bottom_skin_mm,
                metrics.visible_front_wall_mm,
                metrics.full_depth_end_land_mm,
                metrics.internal_web_mm,
                metrics.internal_web_count,
            ),
            (3.2, 2.4, 4.0, 6.4, 2.4, 3),
        )
        self.assertAlmostEqual(
            metrics.clear_panel_span_along_run_mm,
            45.28359375,
            places=8,
        )
        self.assertEqual(metrics.hidden_open_face, "rear wall face")
        self.assertLess(self.u_box.volume, 0.60 * self.cassette.volume)

        # The top and underside are continuous sheets, the visible front is a
        # full rectangle, and the rear is intentionally only the connected
        # U-box section rather than another broad wall.
        for z in (1.2, CASSETTE_HEIGHT_MM - 1.6):
            section = self.u_box.section(
                plane_origin=(0.0, 0.0, z), plane_normal=(0.0, 0.0, 1.0)
            )
            self.assertIsNotNone(section)
            self.assertEqual(len(section.discrete), 1)
        front_section = self.u_box.section(
            plane_origin=(0.0, 2.0, 0.0), plane_normal=(0.0, 1.0, 0.0)
        )
        rear_section = self.u_box.section(
            plane_origin=(0.0, SHELF_DEPTH_MM - 0.1, 0.0),
            plane_normal=(0.0, 1.0, 0.0),
        )
        self.assertIsNotNone(front_section)
        self.assertIsNotNone(rear_section)
        self.assertEqual(len(front_section.discrete), 1)
        self.assertGreater(len(rear_section.discrete), 1)

        saved_mesh = orient_cassette_on_long_edge(self.u_box, yaw_degrees=45.0)
        report = saved_layer_connectivity(saved_mesh, layer_height_mm=0.2)
        self.assertEqual(report.sampled_layer_count, 762)
        self.assertEqual(report.failed_layer_indices, ())
        self.assertTrue(report.all_layers_connected)
        self.assertTrue(print_envelope_with_margins(saved_mesh).fits)

    def test_longest_module_fits_a1_mini_only_on_edge_with_45_degree_yaw(self) -> None:
        flat = print_envelope_with_margins(self.cassette)
        self.assertFalse(flat.fits)
        self.assertGreater(flat.required_build_volume_mm[0], 180.0)

        edge_zero = orient_cassette_on_long_edge(self.cassette, yaw_degrees=0.0)
        edge_zero_envelope = print_envelope_with_margins(edge_zero)
        self.assertFalse(edge_zero_envelope.fits)
        np.testing.assert_allclose(
            edge_zero_envelope.raw_part_mm,
            (LONGEST_PHYSICAL_MODULE_MM, CASSETTE_HEIGHT_MM, SHELF_DEPTH_MM),
            atol=1.0e-6,
        )

        edge_yaw = orient_cassette_on_long_edge(self.cassette, yaw_degrees=45.0)
        saved = print_envelope_with_margins(
            edge_yaw, brim_mm=5.0, reserve_per_bed_edge_mm=2.0
        )
        expected_bed_axis = (
            LONGEST_PHYSICAL_MODULE_MM + CASSETTE_HEIGHT_MM
        ) / math.sqrt(2.0)
        np.testing.assert_allclose(
            saved.raw_part_mm,
            (expected_bed_axis, expected_bed_axis, SHELF_DEPTH_MM),
            atol=1.0e-6,
        )
        np.testing.assert_allclose(
            saved.required_build_volume_mm,
            (expected_bed_axis + 14.0, expected_bed_axis + 14.0, SHELF_DEPTH_MM),
            atol=1.0e-6,
        )
        self.assertTrue(saved.fits)
        self.assertTrue(all(value <= 180.0 for value in saved.required_build_volume_mm))

    def test_saved_u_box_places_the_configured_visible_front_face_on_the_bed(self) -> None:
        cfg = json.loads((R8 / "config.json").read_text(encoding="utf-8"))
        description = cfg["shelf"]["cassette_saved_orientation_candidate"][
            "description"
        ]
        self.assertIn("visible front edge on plate", description)

        saved = orient_cassette_on_long_edge(self.u_box, yaw_degrees=45.0)
        triangles = np.asarray(saved.triangles, dtype=float)
        on_bed = np.all(np.isclose(triangles[:, :, 2], 0.0, atol=1.0e-7), axis=1)
        on_rear = np.all(
            np.isclose(triangles[:, :, 2], SHELF_DEPTH_MM, atol=1.0e-7),
            axis=1,
        )
        bed_contact_area = float(np.sum(saved.area_faces[on_bed]))
        rear_open_face_area = float(np.sum(saved.area_faces[on_rear]))

        # The authored visible-front wall is the complete length x height face.
        # After the +90-degree edge rotation it is the full build-plate contact;
        # the intentionally open rear has only the end/web section.
        self.assertAlmostEqual(
            bed_contact_area,
            LONGEST_PHYSICAL_MODULE_MM * CASSETTE_HEIGHT_MM,
            delta=0.001,
        )
        self.assertLess(rear_open_face_area, 0.30 * bed_contact_area)


if __name__ == "__main__":
    unittest.main(verbosity=2)
