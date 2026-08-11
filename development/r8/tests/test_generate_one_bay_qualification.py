#!/usr/bin/env python3
"""Determinism, scene-evidence, and isolation tests for the one-bay bundle."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


R8 = Path(__file__).resolve().parents[1]
DEVELOPMENT = R8.parent
REPOSITORY = DEVELOPMENT.parent
sys.path.insert(0, str(R8))

from generate_one_bay_qualification import (  # noqa: E402
    EXPECTED_PART_IDS,
    PACKAGE_ID,
    PACKAGE_FILENAME,
    SOURCE_PATHS,
    _validate_frozen_scope,
    build,
)
import generate_qualification as general_qualification  # noqa: E402
import model_io  # noqa: E402


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _tree_digest(root: Path) -> tuple[tuple[str, int, str], ...] | None:
    if not os.path.lexists(root):
        return None
    return tuple(
        (
            path.relative_to(root).as_posix(),
            path.stat().st_size,
            model_io.sha256_file(path),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


class R8OneBayQualificationGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protected = (
            DEVELOPMENT / "r6",
            DEVELOPMENT / "r7",
            R8 / "generated" / "qualification_v1",
        )
        cls.protected_before = {
            path: _tree_digest(path) for path in cls.protected
        }
        cls.temp_context = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp_context.cleanup)
        cls.temp_root = Path(cls.temp_context.name)
        cls.first = cls.temp_root / "first"
        cls.second = cls.temp_root / "second"
        cls.first_manifest = build(cls.first)
        cls.second_manifest = build(cls.second)
        cls.first_files = _files(cls.first)
        cls.second_files = _files(cls.second)

    def test_two_builds_are_byte_exact_and_protected_trees_are_untouched(self) -> None:
        self.assertEqual(self.first_manifest, self.second_manifest)
        self.assertEqual(self.first_files, self.second_files)
        manifest = self.first_manifest
        self.assertEqual(manifest["package_id"], PACKAGE_ID)
        self.assertEqual(PACKAGE_ID, "r8_16b_petg_one_bay_qualification_v2")
        self.assertEqual(manifest["qualification_object_count"], 5)
        self.assertEqual(manifest["artifact_count_excluding_manifest"], 13)
        self.assertEqual(len(self.first_files), 14)
        self.assertEqual(
            set(self.first_files), set(manifest["exact_file_allowlist"])
        )
        self.assertEqual(
            set(path.name for path in self.temp_root.iterdir()),
            {"first", "second"},
        )
        for key, expected in (
            ("qualification_only", True),
            ("unsliced", True),
            ("generated_gcode_present", False),
            ("embedded_print_profile_present", False),
            ("combined_catalog_is_single_a1_mini_plate", False),
            ("physical_qualification_complete", False),
            ("installed_release_allowed", False),
            ("production_ready", False),
            ("load_rating_allowed", False),
        ):
            self.assertEqual(manifest[key], expected, key)
        self.assertEqual(
            (manifest["rated_load_kg"], manifest["rated_load_lb"]),
            (0.0, 0.0),
        )
        self.assertEqual(manifest["scale_percent"], 100.0)
        self.assertEqual(manifest["material"], "PETG only")

        hashed = manifest["hashed_artifacts_excluding_manifest"]
        self.assertEqual(len(hashed), 13)
        self.assertEqual(
            [record["path"] for record in hashed],
            sorted(set(self.first_files) - {"manifest.json"}),
        )
        for record in hashed:
            payload = self.first_files[record["path"]]
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(record["sha256"], model_io.sha256_bytes(payload))

        protected_after = {
            path: _tree_digest(path) for path in self.protected
        }
        self.assertEqual(self.protected_before, protected_after)

    def test_exact_five_parts_orientations_envelopes_and_geometry_bijection(self) -> None:
        validation = json.loads(self.first_files["validation.json"])
        self.assertTrue(validation["validation_passed"])
        self.assertEqual(validation["qualification_object_count"], 5)
        self.assertEqual(validation["individual_stl_count"], 5)
        self.assertEqual(validation["individual_neutral_3mf_count"], 5)
        self.assertEqual(validation["combined_neutral_3mf_count"], 1)
        self.assertTrue(
            validation["serialized_stl_individual_3mf_combined_bijection"]
        )
        self.assertTrue(
            validation["all_serialized_parts_watertight_one_body_positive"]
        )
        self.assertTrue(validation["all_candidate_orientations_fit_a1_mini"])
        self.assertFalse(validation["combined_catalog_is_single_a1_mini_plate"])
        self.assertFalse(validation["combined_package"]["single_plate_claim"])
        self.assertTrue(
            validation["combined_package"]["object_order_readback_exact"]
        )
        self.assertTrue(
            validation["combined_package"]["translations_readback_exact"]
        )
        self.assertEqual(
            validation["combined_package"]["object_names_in_order"],
            validation["combined_package"]["readback_object_names_in_order"],
        )
        self.assertEqual(
            validation["combined_package"]["translations_mm"],
            validation["combined_package"]["readback_translations_mm"],
        )
        self.assertGreater(
            max(validation["combined_package"]["catalog_extent_mm"]), 180.0
        )

        parts = validation["parts"]
        self.assertEqual(tuple(record["mesh_id"] for record in parts), EXPECTED_PART_IDS)
        expected_orientation_fragments = {
            EXPECTED_PART_IDS[0]: "visible front face down",
            EXPECTED_PART_IDS[1]: "broad run-side face down",
            EXPECTED_PART_IDS[2]: "broad run-side face down",
            EXPECTED_PART_IDS[3]: "broad rear face down",
            EXPECTED_PART_IDS[4]: "local XY on bed",
        }
        for record in parts:
            mesh_id = record["mesh_id"]
            with self.subTest(mesh_id=mesh_id):
                self.assertIn(
                    expected_orientation_fragments[mesh_id],
                    record["print_orientation"],
                )
                self.assertEqual(record["scale_percent"], 100.0)
                self.assertTrue(record["a1_mini_candidate_envelope"]["fits"])
                self.assertTrue(
                    record["serialized_geometry_evidence"][
                        "closed_one_body_positive"
                    ]
                )
                digests = record["serialized_geometry_digests"]
                self.assertEqual(
                    set(digests),
                    {"source_float32", "stl", "individual_3mf", "combined_3mf"},
                )
                self.assertEqual(len(set(digests.values())), 1)
                self.assertEqual(len(next(iter(digests.values()))), 64)
                self.assertTrue(
                    all(record["individual_3mf_neutral_checks"].values())
                )
                support = record["saved_layer_support_evidence"]
                self.assertIsNotNone(support)
                self.assertFalse(support["support_required"])

        part_by_id = {record["mesh_id"]: record for record in parts}
        for mesh_id in EXPECTED_PART_IDS[:3]:
            self.assertEqual(
                part_by_id[mesh_id]["a1_mini_candidate_envelope"][
                    "additional_edge_reserve_each_side_mm"
                ],
                2.0,
            )
        for mesh_id in EXPECTED_PART_IDS[3:]:
            self.assertEqual(
                part_by_id[mesh_id]["a1_mini_candidate_envelope"][
                    "additional_edge_reserve_each_side_mm"
                ],
                0.0,
            )
        blank = part_by_id[EXPECTED_PART_IDS[4]]["saved_layer_support_evidence"]
        self.assertGreaterEqual(blank["first_layer_body_contact_area_mm2"], 64.0)
        self.assertEqual(validation["support_required_part_ids"], [])
        self.assertTrue(validation["saved_orientation_support_contracts_passed"])

    def test_cross_bundle_blank_and_v2_clearance_contracts_are_exact(self) -> None:
        validation = json.loads(self.first_files["validation.json"])
        blank = validation["retained_blank_cross_bundle_contract"]
        expected_blank = general_qualification.retained_blank_v2_geometry_digest()
        self.assertTrue(blank["exact_match"])
        self.assertEqual(
            blank["general_v2_canonical_float32_triangle_digest"],
            expected_blank,
        )
        self.assertEqual(
            blank["one_bay_printable_canonical_float32_triangle_digest"],
            expected_blank,
        )
        self.assertTrue(
            blank["installed_scene_copy_used_only_for_scene_evidence"]
        )
        self.assertNotEqual(
            blank["installed_scene_copy_canonical_float32_triangle_digest"],
            expected_blank,
        )

        prior = validation["prior_clearance_qualification"]
        self.assertEqual(prior["source_package_id"], general_qualification.PACKAGE_ID)
        self.assertTrue(prior["source_contract_without_checked_output_dependency"])
        self.assertEqual(
            prior["clearance_v2_geometry_contract"],
            general_qualification.clearance_v2_geometry_contract(),
        )
        self.assertEqual(
            len(
                prior["clearance_v2_geometry_contract"][
                    "canonical_float32_triangle_digests"
                ]
            ),
            5,
        )

    def test_every_3mf_is_strict_neutral_and_every_stl_is_one_body(self) -> None:
        three_mf_paths = sorted(self.first.rglob("*.3mf"))
        stl_paths = sorted(self.first.rglob("*.stl"))
        self.assertEqual(len(three_mf_paths), 6)
        self.assertEqual(len(stl_paths), 5)
        combined = self.first / "model_only_3mf" / PACKAGE_FILENAME
        for path in three_mf_paths:
            with self.subTest(path=path.name):
                inspection = model_io.inspect_model_only_3mf(path)
                self.assertTrue(inspection.passed)
                with zipfile.ZipFile(path) as archive:
                    self.assertEqual(
                        tuple(archive.namelist()), model_io.MODEL_ONLY_ENTRY_ORDER
                    )
                    self.assertIsNone(archive.testzip())
                    self.assertFalse(
                        any(
                            token in name.lower()
                            for name in archive.namelist()
                            for token in (
                                "gcode",
                                "toolpath",
                                "slice_info",
                                "print_profile",
                            )
                        )
                    )
                if path == combined:
                    self.assertEqual(tuple(inspection.objects), EXPECTED_PART_IDS)
                else:
                    self.assertEqual(len(inspection.objects), 1)
                    self.assertEqual(
                        set(inspection.translations_mm.values()),
                        {(0.0, 0.0, 0.0)},
                    )

        expected_digests = self.first_manifest["geometry_digests_by_mesh_id"]
        for path in stl_paths:
            with self.subTest(path=path.name):
                serialized = model_io.read_binary_stl(path)
                evidence = model_io.serialized_mesh_evidence(serialized)
                self.assertTrue(evidence["closed_one_body_positive"])
                self.assertEqual(
                    evidence["canonical_float32_triangle_digest"],
                    expected_digests[path.stem],
                )

    def test_validation_contains_boolean_contact_and_service_evidence(self) -> None:
        validation = json.loads(self.first_files["validation.json"])
        evidence = validation["installed_scene_evidence"]
        self.assertTrue(evidence["all_installed_scene_evidence_passed"])
        nominal = evidence["nominal_five_part_pairwise_boolean"]
        self.assertEqual(nominal["pair_count"], 10)
        self.assertEqual(len(nominal["records"]), 10)
        self.assertTrue(nominal["all_pairs_clear_within_numeric_tolerance"])
        self.assertTrue(
            all(record["clear_within_numeric_tolerance"] for record in nominal["records"])
        )

        contacts = evidence["bearing_contact_datums"]
        self.assertEqual(len(contacts), 2)
        for contact in contacts:
            self.assertEqual(contact["cap_overlap_width_mm"], 15.825)
            self.assertGreater(contact["net_cap_contact_area_mm2"], 0.0)
            self.assertGreater(contact["net_selected_land_contact_area_mm2"], 0.0)
        preservation = evidence["structural_core_preservation"]
        self.assertTrue(preservation["all_cores_preserved_additions_only"])
        self.assertEqual(
            [record["rail_mount_boss_count"] for record in preservation["records"]],
            [4, 0],
        )
        self.assertFalse(preservation["registration_structural_credit"])
        self.assertFalse(preservation["keeper_structural_credit"])

        registration = evidence["registration_clearance_fail_closed"]
        self.assertEqual(registration["clearance_per_face_mm"], 0.4)
        self.assertEqual(registration["remaining_bottom_skin_mm"], 1.0)
        self.assertTrue(registration["passed"])
        for axis in registration["axes"]:
            self.assertTrue(axis["fail_closed"])
            self.assertLessEqual(
                axis["accepted_positive_overlap_mm3"],
                evidence["collision_numeric_tolerance_mm3"],
            )
            self.assertGreater(axis["rejected_positive_overlap_mm3"], 1.0)

        keeper = evidence["keeper_retention"]
        self.assertTrue(keeper["seated_blocks_and_deflected_service_clears"])
        self.assertGreater(keeper["blocking_positive_overlap_mm3"], 1.0)
        self.assertAlmostEqual(keeper["strain_proxy"]["surface_strain"], 0.027)
        self.assertTrue(keeper["strain_proxy"]["below_three_percent"])

        service = evidence["service_evidence"]
        self.assertTrue(service["cassette"]["all_phases_clear"])
        self.assertEqual(service["cassette"]["increment_mm"], 0.2)
        self.assertEqual(service["cassette"]["lift_mm"], 2.0)
        self.assertTrue(service["rail"]["all_phases_clear"])
        self.assertTrue(service["rail"]["module_removal_required_first"])
        self.assertTrue(service["rail"]["unauthorized_pull_fail_closed"])
        self.assertGreater(
            service["rail"]["unauthorized_pull_without_lift_overlap_mm3"],
            1.0,
        )
        self.assertTrue(service["retained_blank"]["all_phases_clear"])
        self.assertEqual(
            service["safe_order"]["removal"][0],
            "release and remove retained blank",
        )

    def test_readme_contains_process_service_and_physical_test_gates(self) -> None:
        readme = self.first_files["README.md"].decode("utf-8")
        for phrase in (
            "unsliced, zero-rated, five-part fit qualification",
            "0.4 mm per face",
            "never scale these parts",
            "100% scale",
            "not one build plate",
            "Never use a PLA preset",
            "All five exact saved meshes pass the deposited-layer support gate",
            "5.0 mm outer brim",
            "B0D1KC72YP",
            "50 C / 50 C",
            "release/lift/remove the blank first",
            "Required one-bay physical tests",
            "cannot establish an installed shelf load rating",
        ):
            self.assertIn(phrase, readme)
        validation = json.loads(self.first_files["validation.json"])
        prior = validation["prior_clearance_qualification"]
        self.assertTrue(prior["required"])
        self.assertEqual(prior["required_clearance_per_face_mm"], 0.4)
        self.assertFalse(prior["coupon_included_in_this_bundle"])
        self.assertEqual(prior["source_package_id"], general_qualification.PACKAGE_ID)
        self.assertTrue(validation["manual_support_and_brim_review_required"])
        self.assertGreaterEqual(len(validation["physical_test_requirements"]), 8)
        settings = validation["petg_a1_mini_candidate_settings"]
        self.assertEqual(settings["drying_temperature_range_c"], [50.0, 50.0])
        self.assertEqual(settings["drying_duration_range_h"], [6.0, 8.0])
        self.assertIn("4 kg bundle", settings["filament_selected_variant"])
        self.assertTrue(validation["artifact_config_identity"]["exact_match"])
        self.assertEqual(
            validation["runtime_provenance"],
            self.first_manifest["runtime_provenance"],
        )

    def test_source_sha_bundle_is_complete_and_current(self) -> None:
        source = self.first_manifest["source_sha_bundle"]
        records = source["records"]
        self.assertEqual([record["path"] for record in records], list(SOURCE_PATHS))
        for record in records:
            path = REPOSITORY / record["path"]
            self.assertEqual(record["bytes"], path.stat().st_size)
            self.assertEqual(record["sha256"], model_io.sha256_file(path))
        payload = b"".join(
            f"{record['path']}\0{record['bytes']}\0{record['sha256']}\n".encode(
                "utf-8"
            )
            for record in records
        )
        self.assertEqual(
            source["bundle_sha256"], model_io.sha256_bytes(payload)
        )

    def test_existing_and_protected_destinations_are_refused_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            refusal_root = Path(temp)
            for name, create in (
                ("existing-directory", lambda path: path.mkdir()),
                (
                    "existing-file",
                    lambda path: path.write_text("owner data", encoding="utf-8"),
                ),
            ):
                destination = refusal_root / name
                create(destination)
                with self.subTest(kind=name):
                    with self.assertRaises(FileExistsError):
                        build(destination)
                if destination.is_file():
                    self.assertEqual(
                        destination.read_text(encoding="utf-8"), "owner data"
                    )

        for index, protected in enumerate(self.protected):
            destination = protected / f".forbidden-one-bay-test-{os.getpid()}-{index}"
            self.assertFalse(os.path.lexists(destination))
            with self.subTest(protected=protected):
                with self.assertRaises(PermissionError):
                    build(destination)
            self.assertFalse(os.path.lexists(destination))
        self.assertEqual(
            self.protected_before,
            {path: _tree_digest(path) for path in self.protected},
        )

    def test_petg_anchor_and_zero_rating_scope_mutations_fail_closed(self) -> None:
        config = json.loads((R8 / "config.json").read_text(encoding="utf-8"))
        mutations = (
            (("material", "primary_part_material"), "PLA"),
            (("material", "hollow_wall_anchors_allowed_in_primary_load_path"), True),
            (("printer", "filament_product"), "PLA"),
            (("printer", "filament_preset"), "Generic PLA @BBL A1M"),
            (("printer", "model"), "X1 Carbon"),
            (("shelf", "selected_level_count"), 3),
            (("d_frame", "wall_chord_mm"), 20.0),
            (("accessory_system", "sockets_per_eligible_corbel"), 2),
            (("project", "rated_load_lb"), "0"),
            (("accessory_system", "rated_load_kg"), False),
        )
        for path, value in mutations:
            candidate = json.loads(json.dumps(config))
            candidate[path[0]][path[1]] = value
            with self.subTest(path=".".join(path), value=value):
                with self.assertRaises(ValueError):
                    _validate_frozen_scope(candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
