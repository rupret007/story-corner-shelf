#!/usr/bin/env python3
"""Publication contracts for the R9 qualification-only bundle."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile
import unittest


R9 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R9))

import generate_qualification as generator  # noqa: E402
import model_io  # noqa: E402


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class R9QualificationGeneratorTests(unittest.TestCase):
    def test_inventory_is_exact_and_every_saved_part_is_a1_safe(self) -> None:
        parts = generator._qualification_parts()
        self.assertEqual(
            tuple(part.mesh_id for part in parts),
            (
                "r9_shortened_outer_bookend_support",
                "r9_compact_support",
                "r9_concealed_corner_half_control",
                "r9_through_hidden_corner_half",
                "r9_return_hidden_corner_half",
                "r9_under_shelf_shear_key_coupon",
                "r9_cosmetic_corner_cover_coupon",
                "r9_90_degree_tabletop_angle_fixture",
                "r9_rear_ledger_male_coupon",
                "r9_rear_ledger_female_coupon",
                "r9_front_beam_lower_lap_coupon",
                "r9_front_beam_upper_lap_coupon",
                "r9_two_socket_outer_bookend_rail_fit_coupon",
                "r9_flush_blank_cable_module",
                "r9_multi_cable_comb_hook_module",
                "r9_through_outer_bookend_additive_two_socket_candidate",
                "r9_return_outer_bookend_additive_two_socket_candidate",
            ),
        )
        self.assertEqual(len({part.mesh_id for part in parts}), 17)
        for part in parts:
            with self.subTest(part=part.mesh_id):
                self.assertFalse(part.support_required)
                self.assertTrue(part.support_evidence)
                self.assertTrue(part.envelope["fits"])
                self.assertLessEqual(
                    max(part.envelope["required_build_volume_mm"]), 180.0
                )

    def test_config_source_runtime_and_r8_dependencies_are_bound(self) -> None:
        cfg = generator._load_frozen_config()
        self.assertEqual(
            generator._canonical_json_sha256(cfg),
            generator.EXPECTED_CONFIG_CANONICAL_SHA256,
        )
        source = generator._source_bundle()
        source_paths = {record["path"] for record in source["records"]}
        self.assertIn("requirements.txt", source_paths)
        self.assertIn("development/r8/model_io.py", source_paths)
        self.assertIn("development/r9/bookend_attachment.py", source_paths)
        self.assertIn("development/r9/fixture_assembly.py", source_paths)
        self.assertIn("development/r9/gate0_geometry.py", source_paths)
        self.assertIn("development/r9/docs/PRINTER_KICKOFF.md", source_paths)
        runtime = generator.runtime_provenance()
        self.assertTrue(runtime["requirements_exactly_matched"])
        self.assertEqual(
            runtime["frozen_r8_model_writer_sha256"],
            model_io.EXPECTED_R8_MODEL_IO_SHA256,
        )
        dependency = generator._r8_dependency()
        self.assertEqual(
            dependency["gate0_print_order_mesh_ids"],
            list(generator.R8_GATE0_IDS),
        )
        self.assertEqual(
            [record["mesh_id"] for record in dependency["records"]],
            [*generator.R8_GATE0_IDS, generator.R8_CONTROL_ID],
        )

    def test_fixture_evidence_is_honest_and_one_bay_stays_blocked(self) -> None:
        evidence = generator._fixture_evidence()
        self.assertTrue(
            evidence["rear_ledger_joint"]["service_path"][
                "sampled_path_collision_free"
            ]
        )
        self.assertTrue(
            evidence["front_beam_joint"]["service_path"][
                "sampled_path_collision_free"
            ]
        )
        self.assertTrue(evidence["nominal_90_degree_corner"]["target_pose_collision_free"])
        self.assertFalse(evidence["nominal_90_degree_corner"]["field_angle_verified"])
        self.assertTrue(evidence["compact_one_bay"]["blocked"])
        self.assertFalse(evidence["compact_one_bay"]["emitted_meshes"])
        self.assertEqual(evidence["compact_one_bay"]["placed_parts"], ())

    def test_two_fresh_builds_are_byte_identical_and_strictly_valid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r9-qualification-test-") as temp:
            root = Path(temp)
            first = generator.build_bundle(root / "first")
            second = generator.build_bundle(root / "second")
            self.assertEqual(tree_bytes(first), tree_bytes(second))
            first_manifest = generator.validate_bundle(first)
            second_manifest = generator.validate_bundle(second)
            self.assertEqual(first_manifest, second_manifest)
            self.assertEqual(first_manifest["package_id"], generator.PACKAGE_ID)
            self.assertEqual(len(first_manifest["object_names_in_order"]), 17)
            self.assertEqual(
                tuple(first_manifest["stage0_geometry_digests_by_mesh_id"]),
                (generator.STAGE0_RECEIVER_ID, generator.STAGE0_KEY_ID),
            )
            routing = first_manifest["effective_gate0_print_routing"]
            self.assertFalse(routing["legacy_r8_identity_pose_keys_printable"])
            self.assertEqual(routing["required_fit_clearance_per_face_mm"], 0.4)
            self.assertTrue(first_manifest["qualification_only"])
            self.assertTrue(first_manifest["unsliced"])
            for flag in (
                "generated_gcode_present",
                "embedded_print_profile_present",
                "full_shelf_set_present",
                "wall_bores_present",
                "physical_qualification_complete",
                "production_ready",
                "installed_release_allowed",
                "load_rating_allowed",
            ):
                self.assertIs(first_manifest[flag], False)
            self.assertEqual(first_manifest["rated_load_kg"], 0.0)
            self.assertEqual(first_manifest["rated_load_lb"], 0.0)
            self.assertAlmostEqual(
                first_manifest["field_measurements"]["through"][
                    "clear_length_lower_mm"
                ],
                1555.75,
            )
            self.assertAlmostEqual(
                first_manifest["field_measurements"]["return"][
                    "clear_length_lower_mm"
                ],
                933.45,
            )
            self.assertFalse(
                first_manifest["field_measurements"][
                    "measurements_authorize_installed_cad"
                ]
            )

    def test_all_formats_share_exact_geometry_and_neutral_3mf_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r9-format-test-") as temp:
            bundle = generator.build_bundle(Path(temp) / "bundle")
            manifest = generator.validate_bundle(bundle)
            catalog = model_io.inspect_model_only_3mf(
                bundle / manifest["combined_catalog_path"]
            )
            self.assertEqual(
                tuple(catalog.objects), tuple(manifest["object_names_in_order"])
            )
            for mesh_id, digest in manifest["geometry_digests_by_mesh_id"].items():
                stl = model_io.read_binary_stl(bundle / "stl" / f"{mesh_id}.stl")
                individual = model_io.inspect_model_only_3mf(
                    bundle
                    / "individual_model_only_3mf"
                    / f"MODEL_ONLY_{mesh_id}.3mf"
                )
                self.assertEqual(model_io.canonical_triangle_digest(stl), digest)
                self.assertEqual(
                    model_io.canonical_triangle_digest(individual.objects[mesh_id]),
                    digest,
                )
                self.assertEqual(
                    individual.translations_mm, {mesh_id: (0.0, 0.0, 0.0)}
                )
                self.assertTrue(all(individual.checks.values()))
            prior = json.loads(
                (R9 / "generated" / "qualification_v3" / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                manifest["geometry_digests_by_mesh_id"],
                prior["geometry_digests_by_mesh_id"],
            )
            for mesh_id, digest in manifest[
                "stage0_geometry_digests_by_mesh_id"
            ].items():
                stage0 = model_io.inspect_model_only_3mf(
                    bundle
                    / "stage0_individual_model_only_3mf"
                    / f"MODEL_ONLY_{mesh_id}.3mf"
                )
                self.assertEqual(tuple(stage0.objects), (mesh_id,))
                self.assertEqual(stage0.translations_mm, {mesh_id: (0.0, 0.0, 0.0)})
                self.assertEqual(
                    model_io.canonical_triangle_digest(stage0.objects[mesh_id]),
                    digest,
                )

    def test_existing_and_protected_destinations_fail_without_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r9-refusal-test-") as temp:
            existing = Path(temp) / "existing"
            existing.mkdir()
            marker = existing / "marker.txt"
            marker.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                generator.build_bundle(existing)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        with self.assertRaises(ValueError):
            generator.build_bundle(R9)
        protected_candidates = (
            R9.parent / "r6" / "new_bundle_must_not_exist",
            R9.parent / "r7" / "new_bundle_must_not_exist",
            R9.parent / "r8" / "new_bundle_must_not_exist",
            R9 / "tests" / "new_bundle_must_not_exist",
            R9 / "generated" / "nested" / "new_bundle_must_not_exist",
        )
        sentinels = {
            path: model_io.sha256_file(path)
            for path in (
                R9 / "config.json",
                R9.parent / "r6" / "config.json",
                R9.parent / "r7" / "config.json",
                R9.parent / "r8" / "config.json",
            )
        }
        for candidate in protected_candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                generator.build_bundle(candidate)
            self.assertFalse(candidate.exists())
        self.assertEqual(
            {path: model_io.sha256_file(path) for path in sentinels}, sentinels
        )

    def test_manifest_allowlist_has_no_cache_toolpath_or_hidden_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r9-allowlist-test-") as temp:
            bundle = generator.build_bundle(Path(temp) / "bundle")
            manifest = json.loads((bundle / "manifest.json").read_text())
            paths = manifest["exact_file_allowlist"]
            self.assertEqual(paths, sorted(paths))
            self.assertEqual(len(paths), len(set(paths)))
            for relative in paths:
                lowered = relative.lower()
                self.assertNotIn("__pycache__", lowered)
                self.assertNotIn(".pyc", lowered)
                self.assertNotIn("gcode", lowered)
                self.assertNotIn("toolpath", lowered)
                self.assertFalse(Path(relative).name.startswith("."))
            self.assertFalse(any(path.is_symlink() for path in bundle.rglob("*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
