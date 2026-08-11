#!/usr/bin/env python3
"""Regression tests for the R9-owned corrected Gate-0 key pose."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

import numpy as np


R9 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R9))

import gate0_geometry as gate0  # noqa: E402
import model_io  # noqa: E402


class Gate0GeometryTests(unittest.TestCase):
    def test_frozen_sources_are_exact_and_are_not_modified(self) -> None:
        self.assertEqual(
            hashlib.sha256(gate0.RECEIVER_SOURCE.read_bytes()).hexdigest(),
            gate0.EXPECTED_RECEIVER_STL_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(gate0.KEY_SOURCE.read_bytes()).hexdigest(),
            gate0.EXPECTED_KEY_STL_SHA256,
        )

    def test_handle_down_is_a_proper_rigid_pose_of_the_exact_key(self) -> None:
        source = gate0.build_frozen_saved_key_control()
        corrected = gate0.build_handle_down_key_control()
        self.assertTrue(corrected.is_watertight)
        self.assertTrue(corrected.is_winding_consistent)
        self.assertEqual(len(corrected.split(only_watertight=False)), 1)
        np.testing.assert_allclose(corrected.bounds[0], (0.0, 0.0, 0.0))
        np.testing.assert_allclose(corrected.extents, (20.0, 16.0, 9.2), atol=1e-5)
        self.assertAlmostEqual(float(corrected.volume), float(source.volume), places=5)
        source_digest = model_io.canonical_triangle_digest(
            model_io.canonicalize_mesh(source)
        )
        corrected_digest = model_io.canonical_triangle_digest(
            model_io.canonicalize_mesh(corrected)
        )
        self.assertNotEqual(source_digest, corrected_digest)
        # Undo the proper rotation and compare the canonical physical geometry.
        restored = corrected.copy()
        transform = np.eye(4, dtype=float)
        transform[1, 1] = -1.0
        transform[2, 2] = -1.0
        restored.apply_transform(transform)
        restored.apply_translation(-np.asarray(restored.bounds[0], dtype=float))
        restored_digest = model_io.canonical_triangle_digest(
            model_io.canonicalize_mesh(restored)
        )
        self.assertEqual(restored_digest, source_digest)

    def test_layer_regression_detects_old_cantilever_and_quantifies_fix(self) -> None:
        old = gate0.layer_overhang_report(gate0.build_frozen_saved_key_control())
        corrected = gate0.layer_overhang_report(gate0.build_handle_down_key_control())
        self.assertEqual(old.sampled_layer_count, 46)
        self.assertEqual(corrected.sampled_layer_count, 46)
        self.assertEqual(old.island_layer_indices, ())
        self.assertEqual(corrected.island_layer_indices, ())
        self.assertAlmostEqual(old.first_layer_contact_area_mm2, 100.0, places=5)
        self.assertAlmostEqual(
            corrected.first_layer_contact_area_mm2, 320.0, places=5
        )
        self.assertAlmostEqual(
            old.largest_new_unsupported_area_mm2, 272.0, places=4
        )
        self.assertEqual(old.largest_new_unsupported_layer_index, 30)
        self.assertAlmostEqual(
            corrected.largest_new_unsupported_area_mm2, 52.0, places=4
        )
        self.assertEqual(corrected.largest_new_unsupported_layer_index, 28)
        self.assertLess(
            corrected.largest_new_unsupported_area_mm2,
            0.2 * old.largest_new_unsupported_area_mm2,
        )

    def test_saved_evidence_is_fail_closed_about_empirical_overhang(self) -> None:
        evidence = {
            item.part_name: item for item in gate0.saved_gate0_print_evidence()
        }
        self.assertEqual(
            tuple(evidence),
            (
                "r8_clearance_ladder_receiver",
                "r9_gate0_clearance_key_0p4_handle_down",
            ),
        )
        key = evidence["r9_gate0_clearance_key_0p4_handle_down"]
        self.assertFalse(key.support_required)
        self.assertTrue(key.slicer_preview_required)
        self.assertTrue(key.physical_overhang_screen_required)
        self.assertIn("52 mm2", key.support_evidence)
        self.assertTrue(key.envelope.fits)


if __name__ == "__main__":
    unittest.main()
