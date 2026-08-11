#!/usr/bin/env python3
"""Exact topology, interface, envelope, and digest tests for R8 accessories."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


R8 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R8))

import accessory_geometry as cad  # noqa: E402


class R8AccessoryGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rail = cad.build_faceplate_rail()
        cls.modules = {
            kind: cad.build_accessory(kind)
            for kind in ("blank", "single_peg", "three_cable_comb", "coil_j_hook")
        }
        cls.ladder = cad.build_clearance_ladder()

    def assertOnePrintableBody(self, mesh) -> None:  # noqa: N802
        self.assertTrue(mesh.is_watertight)
        self.assertGreater(mesh.volume, 0.0)
        self.assertEqual(len(mesh.split(only_watertight=False)), 1)
        self.assertTrue(cad.mesh_is_one_body(mesh))

    def test_faceplate_is_exact_additive_envelope_and_one_body(self) -> None:
        self.assertOnePrintableBody(self.rail)
        np.testing.assert_allclose(self.rail.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-8)
        np.testing.assert_allclose(
            self.rail.bounds[1],
            (cad.FACEPLATE_WIDTH_MM, cad.FACEPLATE_THICKNESS_MM, cad.FACEPLATE_HEIGHT_MM),
            atol=1.0e-8,
        )
        np.testing.assert_allclose(self.rail.extents, (36.0, 8.8, 88.0), atol=1.0e-8)

    def test_three_keyed_gravity_sockets_preserve_the_full_back_web(self) -> None:
        self.assertEqual(cad.SOCKET_CENTER_Z_MM, (20.0, 46.0, 72.0))
        specs = [cad.socket_spec(center_z_mm=z) for z in cad.SOCKET_CENTER_Z_MM]
        self.assertTrue(all(spec.cavity_back_y_mm == 2.4 for spec in specs))
        self.assertTrue(all(spec.service_lift_mm == 8.0 for spec in specs))
        for spec in specs:
            self.assertGreater(spec.keyed_pocket_width_mm, spec.main_pocket_width_mm)
            self.assertGreater(spec.main_pocket_width_mm, spec.neck_width_mm)
            self.assertEqual(
                spec.front_y_mm - spec.undercut_front_y_mm,
                cad.FRONT_RETAINER_SKIN_MM,
            )
            cutters = cad.socket_cutters(center_z_mm=spec.center_z_mm)
            self.assertEqual(len(cutters), 4)
            self.assertTrue(
                all(cutter.bounds[0, 1] >= cad.UNINTERRUPTED_BACK_WEB_MM - 1.0e-9 for cutter in cutters)
            )
        # The mesh's complete rear plane remains present; every subtraction is
        # contained within this separate rail, never the structural D-frame.
        rear_vertices = self.rail.vertices[
            np.isclose(self.rail.vertices[:, 1], 0.0, atol=1.0e-9)
        ]
        self.assertGreaterEqual(len(rear_vertices), 4)
        self.assertEqual(float(rear_vertices[:, 1].min()), 0.0)
        self.assertEqual(float(rear_vertices[:, 1].max()), 0.0)

    def test_common_key_and_all_accessory_modules_are_one_body(self) -> None:
        for name, mesh in self.modules.items():
            with self.subTest(name=name):
                self.assertOnePrintableBody(mesh)
                # Every module retains the exact same keyed T-lug at the rear
                # of the common 16 mm pad.  Isolating the rearmost vertices
                # avoids confusing the wider external pad/comb for the key.
                self.assertAlmostEqual(mesh.bounds[0, 1], -6.0, places=6)
                rear = mesh.vertices[mesh.vertices[:, 1] < -5.9]
                self.assertGreater(len(rear), 0)
                self.assertAlmostEqual(float(rear[:, 0].min()), -7.0, places=6)
                self.assertAlmostEqual(float(rear[:, 0].max()), 5.5, places=6)
                self.assertLessEqual(mesh.bounds[0, 2], -8.0 + 1.0e-8)
                self.assertGreaterEqual(mesh.bounds[1, 2], 8.0 - 1.0e-8)
        self.assertEqual(tuple(self.modules), ("blank", "single_peg", "three_cable_comb", "coil_j_hook"))
        self.assertGreater(self.modules["single_peg"].bounds[1, 1], 20.0)
        self.assertGreater(self.modules["three_cable_comb"].extents[0], 25.0)
        self.assertGreater(self.modules["coil_j_hook"].bounds[1, 2], 10.0)

    def test_seating_and_insertion_transforms_require_exactly_8_mm_upward_service(self) -> None:
        module = self.modules["blank"]
        for index, center_z in enumerate(cad.SOCKET_CENTER_Z_MM):
            transforms = cad.seating_transforms(index)
            np.testing.assert_allclose(
                transforms.seated[:3, 3],
                (18.0, 8.8, center_z),
                atol=1.0e-12,
            )
            delta = transforms.insertion[:3, 3] - transforms.seated[:3, 3]
            np.testing.assert_allclose(delta, (0.0, 0.0, 8.0), atol=1.0e-12)
            self.assertEqual(transforms.service_lift_mm, 8.0)
            seated = cad.transformed_module(module, index, insertion=False)
            insertion = cad.transformed_module(module, index, insertion=True)
            np.testing.assert_allclose(
                insertion.bounds - seated.bounds,
                np.tile((0.0, 0.0, 8.0), (2, 1)),
                atol=1.0e-8,
            )
        with self.assertRaises(IndexError):
            cad.seating_transforms(3)

    def test_clearance_ladder_contains_all_four_exact_steps(self) -> None:
        self.assertEqual(self.ladder.clearances_mm, (0.2, 0.3, 0.4, 0.5))
        self.assertEqual(self.ladder.station_centers_x_mm, (18.0, 50.0, 82.0, 114.0))
        self.assertEqual(len(self.ladder.keys), 4)
        self.assertOnePrintableBody(self.ladder.receiver)
        np.testing.assert_allclose(self.ladder.receiver.extents, (132.0, 8.8, 32.0), atol=1.0e-8)
        for clearance, key in zip(self.ladder.clearances_mm, self.ladder.keys):
            self.assertOnePrintableBody(key)
            spec = cad.socket_spec(center_z_mm=12.0, clearance_mm=clearance)
            self.assertAlmostEqual(
                spec.main_pocket_width_mm - cad.LUG_HEAD_WIDTH_MM,
                2.0 * clearance,
                places=9,
            )
            self.assertAlmostEqual(
                spec.neck_width_mm - cad.LUG_STEM_WIDTH_MM,
                2.0 * clearance,
                places=9,
            )
            self.assertAlmostEqual(
                float(key.bounds[0, 1]),
                -6.4 + clearance,
                delta=1.0e-6,
            )

    def test_comparison_strain_proxy_is_exact_monotonic_and_zero_load_closed(self) -> None:
        zero = cad.rectangular_root_strain_proxy(
            force_n=0.0,
            projection_mm=22.0,
            root_width_mm=8.0,
            root_height_mm=8.0,
        )
        one = cad.rectangular_root_strain_proxy(
            force_n=1.0,
            projection_mm=22.0,
            root_width_mm=8.0,
            root_height_mm=8.0,
        )
        two = cad.rectangular_root_strain_proxy(
            force_n=2.0,
            projection_mm=22.0,
            root_width_mm=8.0,
            root_height_mm=8.0,
        )
        self.assertEqual(zero.surface_strain, 0.0)
        self.assertGreater(one.surface_strain, 0.0)
        self.assertAlmostEqual(two.surface_strain, 2.0 * one.surface_strain, places=15)
        self.assertAlmostEqual(one.second_moment_mm4, 341.3333333333333, places=10)
        self.assertTrue(cad.QUALIFICATION_ONLY)
        self.assertEqual((cad.RATED_LOAD_KG, cad.RATED_LOAD_LB), (0.0, 0.0))

    def test_all_parts_fit_a1_mini_in_declared_broad_face_orientation(self) -> None:
        named = {"rail": self.rail, **self.modules, "clearance_ladder": self.ladder.receiver}
        named.update({f"clearance_key_{clearance:.1f}": key for clearance, key in zip(self.ladder.clearances_mm, self.ladder.keys)})
        for name, mesh in named.items():
            with self.subTest(name=name):
                envelope = cad.saved_print_envelope(mesh, brim_mm=5.0)
                self.assertTrue(envelope.fits)
                self.assertTrue(all(value <= 180.0 + 1.0e-9 for value in envelope.with_brim_mm))
        rail_envelope = cad.saved_print_envelope(self.rail, brim_mm=5.0)
        np.testing.assert_allclose(rail_envelope.part_mm, (36.0, 88.0, 8.8), atol=1.0e-8)
        np.testing.assert_allclose(rail_envelope.with_brim_mm, (46.0, 98.0, 8.8), atol=1.0e-8)

    def test_geometry_digests_are_repeatable_and_frozen(self) -> None:
        first = {
            "rail": cad.mesh_geometry_digest(self.rail),
            **{name: cad.mesh_geometry_digest(mesh) for name, mesh in self.modules.items()},
            "clearance_ladder": cad.mesh_geometry_digest(self.ladder.receiver),
        }
        rebuilt = {
            "rail": cad.mesh_geometry_digest(cad.build_faceplate_rail()),
            **{
                name: cad.mesh_geometry_digest(cad.build_accessory(name))
                for name in self.modules
            },
            "clearance_ladder": cad.mesh_geometry_digest(cad.build_clearance_ladder().receiver),
        }
        self.assertEqual(first, rebuilt)
        self.assertEqual(
            first,
            {
                "rail": "aa3af9ca424c01e8785f301c416f5e675b68f915ad744c11ee152767f1527a76",
                "blank": "ec8445290d039f37bdd1f3af1b7a13dc7d5b41b1f04775f99d9eecf7c9168792",
                "single_peg": "7769ebbc1a82a32642e7c2fe241102c18e967d9e65ce7e53ace111d7113f3b89",
                "three_cable_comb": "2951e031a68ce40e058640e2ed5a2a41edbe399411f106e64cf95644a2928ac3",
                "coil_j_hook": "9ede71bfe2a752f574876461a32c411cbdf67a8cbe7d55b4006ebe426c3f13c8",
                "clearance_ladder": "e1883846308cd994bc73209495c31b5b20d7f9cc0c1913453a72366897f8c72c",
            },
        )


if __name__ == "__main__":
    unittest.main()
