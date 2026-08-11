from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np


R7_ROOT = Path(__file__).resolve().parents[1]
R6_ROOT = R7_ROOT.parent / "r6"
for candidate in (R7_ROOT, R6_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cable_peg_geometry import (  # noqa: E402
    cable_bundle_envelope_mesh,
    cable_hook_mesh,
    clearance_ladder_mesh,
    compressed_approach_components,
    load_config,
    overlay_edges_mm,
    qualification_meshes,
    reference_pier_overlay_mesh,
    saved_hook_mesh,
    validate_geometry,
)
from generate_cable_peg_qualification import build  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R7CablePegGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = load_config()

    def test_frozen_collar_and_corner_exclusion_contract(self) -> None:
        hook = self.cfg["cable_hook"]
        clearance = self.cfg["clearance_contract"]
        self.assertEqual(hook["collar_band_elevation_mm"], [22.0, 30.0])
        self.assertEqual(hook["nominal_clearance_per_face_mm"], 0.4)
        self.assertEqual(hook["rear_lip_depth_zone_mm"], [3.6, 6.0])
        self.assertEqual(hook["rear_lip_inward_undercut_mm"], 1.2)
        self.assertEqual(hook["compressed_proxy_jaw_spread_each_side_mm"], 1.6)
        self.assertEqual(hook["hook_usable_projection_from_overlay_face_mm"], 18.0)
        self.assertEqual(hook["vertical_stop_foot_bottom_elevation_mm"], 19.0)
        self.assertEqual(hook["jaw_root_fillet_mm"], 2.0)
        self.assertEqual(hook["front_bridge_crossbar_height_mm"], 2.4)
        self.assertEqual(hook["maximum_qualified_cable_bundle_diameter_mm"], 5.0)
        self.assertTrue(hook["manual_jaw_pre_spread_required"])
        self.assertFalse(hook["automatic_insertion_cam_claimed"])
        self.assertEqual(hook["normal_hook_locations_per_level"], 9)
        self.assertEqual(hook["excluded_run_start_corner_locations_per_level"], 2)
        self.assertAlmostEqual(clearance["inside_corner_static_plan_reserve_mm"], 8.6325)
        self.assertAlmostEqual(
            clearance["inside_corner_service_swept_plan_reserve_mm"], 4.2325
        )
        self.assertLess(
            clearance["inside_corner_service_swept_plan_reserve_mm"],
            hook["hook_usable_projection_from_overlay_face_mm"],
        )

    def test_exact_tapered_overlay_edges_and_nominal_cavity(self) -> None:
        left22, right22 = overlay_edges_mm(22.0, self.cfg)
        left30, right30 = overlay_edges_mm(30.0, self.cfg)
        self.assertAlmostEqual(left22, 1.1812080536912752)
        self.assertAlmostEqual(right22, 33.21879194630872)
        self.assertAlmostEqual(left30, 1.610738255033557)
        self.assertAlmostEqual(right30, 32.78926174496644)
        clearance = self.cfg["cable_hook"]["nominal_clearance_per_face_mm"]
        self.assertAlmostEqual((right22 - left22) + 2 * clearance, 32.83758389261745)
        self.assertAlmostEqual((right30 - left30) + 2 * clearance, 31.978523489932884)

    def test_hook_overlay_and_ladder_are_closed_single_bodies(self) -> None:
        meshes = qualification_meshes(self.cfg)
        self.assertEqual(len(meshes), 3)
        for name, mesh in meshes.items():
            with self.subTest(name=name):
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_volume)
                self.assertEqual(mesh.body_count, 1)
                self.assertGreater(mesh.volume, 0.0)
                self.assertTrue(np.isfinite(mesh.vertices).all())
                self.assertTrue((mesh.area_faces > 1.0e-12).all())

    def test_exact_r6_overlay_is_used_as_the_parent_coupon(self) -> None:
        overlay = reference_pier_overlay_mesh()
        np.testing.assert_allclose(overlay.extents, [34.4, 59.6, 10.2], atol=1.0e-5)
        self.assertAlmostEqual(float(overlay.volume), 7719.856080728481, places=5)

    def test_seated_and_compressed_approach_sweeps_are_collision_free(self) -> None:
        metrics = validate_geometry(self.cfg)
        self.assertLessEqual(metrics.maximum_seated_overlay_overlap_mm3, 1.0e-5)
        self.assertLessEqual(metrics.maximum_compressed_approach_overlap_mm3, 1.0e-5)
        self.assertEqual(len(compressed_approach_components(self.cfg)), 3)
        self.assertAlmostEqual(metrics.maximum_free_downward_travel_mm, 0.2)
        self.assertGreater(metrics.downward_stop_overlap_at_gate_mm3, 1.0e-5)
        self.assertAlmostEqual(
            metrics.flex_strain_proxy,
            self.cfg["cable_hook"]["conservative_flex_strain_proxy"],
        )
        self.assertLess(
            metrics.flex_strain_proxy,
            self.cfg["cable_hook"]["maximum_flex_strain_proxy"],
        )
        self.assertAlmostEqual(metrics.installed_bounds_mm[1][2], 6.0, places=5)
        self.assertGreaterEqual(13.2 - metrics.installed_bounds_mm[1][2], 7.2 - 1.0e-5)
        self.assertLessEqual(
            metrics.maximum_cable_bundle_to_bridge_overlap_mm3, 1.0e-5
        )
        self.assertLessEqual(
            metrics.maximum_cable_bundle_to_collar_overlap_mm3, 1.0e-5
        )
        self.assertGreaterEqual(
            metrics.cable_bundle_to_tip_clearance_mm,
            self.cfg["cable_hook"]["minimum_cable_to_tip_clearance_mm"],
        )
        cable = cable_bundle_envelope_mesh(self.cfg)
        self.assertAlmostEqual(float(cable.extents[0]), 6.0, places=5)
        self.assertAlmostEqual(float(cable.extents[1]), 5.0, places=5)
        self.assertAlmostEqual(float(cable.extents[2]), 5.0, places=5)

    def test_saved_orientation_and_a1_mini_envelope(self) -> None:
        saved = saved_hook_mesh(cable_hook_mesh(self.cfg), self.cfg)
        np.testing.assert_allclose(saved.bounds[0], [0.0, 0.0, 0.0], atol=1.0e-6)
        on_plate = np.all(
            np.isclose(saved.triangles[:, :, 2], 0.0, atol=1.0e-6), axis=1
        )
        contact_area = float(np.sum(saved.area_faces[on_plate]))
        self.assertAlmostEqual(
            contact_area,
            validate_geometry(self.cfg).saved_plate_contact_area_mm2,
            places=5,
        )
        self.assertGreaterEqual(
            contact_area,
            self.cfg["printing"]["minimum_plate_contact_area_mm2"],
        )
        self.assertLessEqual(float(saved.extents.max()), 180.0)
        brim = float(self.cfg["printing"]["brim_mm"])
        self.assertLessEqual(float(saved.extents[0]) + 2.0 * brim, 180.0)
        self.assertLessEqual(float(saved.extents[1]) + 2.0 * brim, 180.0)
        self.assertFalse(self.cfg["printing"]["support_free"])

    def test_load_state_is_fail_closed(self) -> None:
        project = self.cfg["project"]
        load = self.cfg["load_qualification"]
        self.assertFalse(project["installed_release_allowed"])
        self.assertFalse(project["physical_qualification_complete"])
        self.assertFalse(project["production_ready"])
        self.assertFalse(project["load_rating_allowed"])
        self.assertEqual(load["rated_load_before_physical_qualification_kg"], 0.0)
        self.assertEqual(load["provisional_working_load_after_all_gates_kg"], 0.25)
        self.assertEqual(load["proof_load_kg"], 1.0)
        self.assertEqual(load["proof_duration_h"], 1.0)
        self.assertEqual(load["creep_load_kg"], 0.5)
        self.assertEqual(load["creep_duration_days"], 90)

    def test_live_flex_stop_bridge_and_orientation_datums_fail_closed(self) -> None:
        mutations = (
            ("flex", lambda cfg: cfg["cable_hook"].__setitem__(
                "flex_arm_effective_length_mm", 18.0
            )),
            ("stop", lambda cfg: cfg["cable_hook"].__setitem__(
                "vertical_stop_foot_bottom_elevation_mm", 19.2
            )),
            ("bridge", lambda cfg: cfg["cable_hook"].__setitem__(
                "front_bridge_crossbar_height_mm", 3.0
            )),
            ("orientation", lambda cfg: cfg["printing"].__setitem__(
                "saved_left_run_side_rotation_deg", 0.0
            )),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                changed = copy.deepcopy(self.cfg)
                mutate(changed)
                with self.assertRaises(ValueError):
                    validate_geometry(changed)

    def test_clearance_ladder_has_four_frozen_slots(self) -> None:
        ladder = clearance_ladder_mesh(self.cfg)
        np.testing.assert_allclose(ladder.extents, [48.0, 16.0, 8.0], atol=1.0e-5)
        self.assertEqual(
            self.cfg["cable_hook"]["fit_ladder_clearances_per_face_mm"],
            [0.2, 0.3, 0.4, 0.5],
        )

    def test_fresh_generator_is_deterministic_and_model_only(self) -> None:
        r6_manifest = R6_ROOT / "generated" / "manifest.json"
        before_r6 = sha256(r6_manifest) if r6_manifest.exists() else None
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first"
            second = Path(temp) / "second"
            first_manifest = build(first)
            second_manifest = build(second)
            self.assertEqual(first_manifest["artifact_count_excluding_manifest"], 7)
            self.assertEqual(first_manifest["qualification_object_count"], 3)
            self.assertTrue(first_manifest["qualification_only"])
            self.assertTrue(first_manifest["unsliced"])
            self.assertFalse(first_manifest["generated_gcode_present"])
            self.assertFalse(first_manifest["installed_release_allowed"])
            self.assertEqual(first_manifest["promoted_counts_if_all_physical_gates_pass"], {
                "one_level": 267,
                "two_levels": 534,
            })
            translations = next(
                record["translations_mm"]
                for record in first_manifest["artifacts"]
                if record["kind"] == "qualification_model_only_3mf"
            )
            self.assertEqual(
                translations["R7_DEV_CABLE_PEG_EXACT_R6_PIER_OVERLAY_COUPON"],
                [5.2, 5.2, 0.0],
            )
            individual_digests = {
                record["mesh_name"]: record["canonical_triangle_digest_0p001mm"]
                for record in first_manifest["artifacts"]
                if record["kind"] == "individual_model_only_3mf"
            }
            package_digests = next(
                record["canonical_source_triangle_digests_0p001mm"]
                for record in first_manifest["artifacts"]
                if record["kind"] == "qualification_model_only_3mf"
            )
            self.assertEqual(len(individual_digests), 3)
            self.assertEqual(individual_digests, package_digests)
            self.assertTrue(all(len(value) == 64 for value in package_digests.values()))
            first_files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
            second_files = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
            self.assertEqual(first_files, second_files)
            for relative in first_files:
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())
            for three_mf in first.rglob("*.3mf"):
                with zipfile.ZipFile(three_mf) as archive:
                    names = archive.namelist()
                    self.assertEqual(len(names), len(set(names)))
                    self.assertFalse(any(name.lower().endswith((".gcode", ".gco", ".bgcode")) for name in names))
                    self.assertIn("3D/3dmodel.model", names)
        after_r6 = sha256(r6_manifest) if r6_manifest.exists() else None
        self.assertEqual(before_r6, after_r6)

    def test_generator_refuses_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "existing"
            destination.mkdir()
            with self.assertRaises(FileExistsError):
                build(destination)

    def test_geometry_current_rendering_and_prompt_are_present(self) -> None:
        asset = R7_ROOT / "assets" / "artist_rendering_all_petg_two_level_cable_pegs_concept_v2.png"
        prompt = R7_ROOT / "assets" / "artist_rendering_all_petg_two_level_cable_pegs_concept_v2.prompt.md"
        self.assertTrue(asset.is_file())
        self.assertTrue(prompt.is_file())
        self.assertEqual(
            sha256(asset),
            "2ef8c1e3a72be730a0583b27b52adf0952ef2b0f3ac80e44bc198c905b2b14cb",
        )
        text = prompt.read_text()
        self.assertIn("nine normal-facing", text)
        self.assertIn("4.2325 mm", text)


if __name__ == "__main__":
    unittest.main()
