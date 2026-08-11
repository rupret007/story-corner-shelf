#!/usr/bin/env python3
"""Determinism, bijection, and fail-closed tests for the R8 bundle generator."""

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

from generate_qualification import (  # noqa: E402
    CLEARANCE_V2_PART_IDS,
    PACKAGE_ID,
    PACKAGE_FILENAME,
    RUNTIME_REQUIREMENTS,
    SOURCE_PATHS,
    _validate_frozen_scope,
    build,
)
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


class R8QualificationGeneratorTests(unittest.TestCase):
    def test_generate_twice_is_byte_exact_and_touches_no_frozen_or_default_tree(self) -> None:
        protected = (DEVELOPMENT / "r6", DEVELOPMENT / "r7", R8 / "generated")
        before = {path: _tree_digest(path) for path in protected}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first"
            second = root / "second"
            first_manifest = build(first)
            second_manifest = build(second)

            self.assertEqual(first_manifest, second_manifest)
            self.assertEqual(first_manifest["qualification_object_count"], 15)
            self.assertEqual(first_manifest["package_id"], PACKAGE_ID)
            self.assertEqual(first_manifest["artifact_count_excluding_manifest"], 33)
            self.assertTrue(first_manifest["qualification_only"])
            self.assertTrue(first_manifest["unsliced"])
            self.assertFalse(first_manifest["generated_gcode_present"])
            self.assertFalse(first_manifest["embedded_print_profile_present"])
            self.assertTrue(
                first_manifest["manual_support_and_brim_review_required"]
            )
            self.assertFalse(first_manifest["physical_qualification_complete"])
            self.assertFalse(first_manifest["installed_release_allowed"])
            self.assertFalse(first_manifest["production_ready"])
            self.assertFalse(first_manifest["load_rating_allowed"])
            self.assertEqual(
                (first_manifest["rated_load_kg"], first_manifest["rated_load_lb"]),
                (0.0, 0.0),
            )
            self.assertEqual(first_manifest["scale_percent"], 100.0)
            self.assertEqual(first_manifest["material"], "PETG only")
            self.assertTrue(first_manifest["unresolved_blockers"])

            first_files = _files(first)
            second_files = _files(second)
            self.assertEqual(first_files, second_files)
            self.assertEqual(len(first_files), 34)
            self.assertEqual(
                set(first_files), set(first_manifest["exact_file_allowlist"])
            )
            self.assertEqual(set(path.name for path in root.iterdir()), {"first", "second"})

            hashed = first_manifest["hashed_artifacts_excluding_manifest"]
            self.assertEqual(len(hashed), 33)
            self.assertEqual(
                [record["path"] for record in hashed],
                sorted(set(first_files) - {"manifest.json"}),
            )
            for record in hashed:
                payload = first_files[record["path"]]
                self.assertEqual(record["bytes"], len(payload))
                self.assertEqual(record["sha256"], model_io.sha256_bytes(payload))

            validation = json.loads(first_files["validation.json"])
            self.assertTrue(validation["validation_passed"])
            self.assertTrue(
                validation["serialized_stl_individual_3mf_combined_bijection"]
            )
            self.assertTrue(
                validation["all_serialized_parts_watertight_one_body_positive"]
            )
            self.assertTrue(validation["all_candidate_orientations_fit_a1_mini"])
            self.assertFalse(validation["combined_catalog_is_single_a1_mini_plate"])
            self.assertFalse(validation["embedded_print_profile_present"])
            self.assertTrue(validation["manual_support_and_brim_review_required"])
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
            self.assertEqual(len(validation["parts"]), 15)

            part_by_id = {record["mesh_id"]: record for record in validation["parts"]}
            self.assertEqual(len(part_by_id), 15)
            self.assertIn("r8_selected_front_first_u_box_cassette", part_by_id)
            self.assertIn("r8_matched_heavy_coffer_control", part_by_id)
            self.assertIn("r8_retained_shortened_coil_j_hook", part_by_id)
            self.assertIn("r8_clearance_ladder_receiver", part_by_id)
            for clearance in ("0p2", "0p3", "0p4", "0p5"):
                self.assertIn(f"r8_clearance_key_{clearance}", part_by_id)

            for mesh_id in (
                "r8_selected_front_first_u_box_cassette",
                "r8_matched_heavy_coffer_control",
            ):
                self.assertEqual(
                    part_by_id[mesh_id]["print_orientation"],
                    "visible front long edge down with frozen 45 degree bed yaw",
                )

            for mesh_id, record in part_by_id.items():
                with self.subTest(mesh_id=mesh_id):
                    digests = record["serialized_geometry_digests"]
                    self.assertEqual(
                        set(digests),
                        {"source_float32", "stl", "individual_3mf", "combined_3mf"},
                    )
                    self.assertEqual(len(set(digests.values())), 1)
                    self.assertEqual(len(next(iter(digests.values()))), 64)
                    evidence = record["serialized_geometry_evidence"]
                    self.assertTrue(evidence["closed_one_body_positive"])
                    self.assertTrue(evidence["watertight"])
                    self.assertTrue(evidence["winding_consistent"])
                    self.assertTrue(evidence["positive_volume"])
                    self.assertEqual(evidence["body_count"], 1)
                    self.assertEqual(evidence["zero_area_triangle_count"], 0)
                    self.assertTrue(record["a1_mini_candidate_envelope"]["fits"])
                    self.assertEqual(record["scale_percent"], 100.0)
                    self.assertTrue(
                        all(record["individual_3mf_neutral_checks"].values())
                    )

            for mesh_id in (
                "r8_curved_eligible_d_frame_mount",
                "r8_smooth_curved_core",
                "r8_equal_volume_straight_control",
            ):
                envelope = part_by_id[mesh_id]["a1_mini_candidate_envelope"]
                self.assertEqual(envelope["additional_edge_reserve_each_side_mm"], 2.0)
                for observed, expected in zip(
                    envelope["required_with_brim_and_reserved_edges_mm"][:2],
                    (166.6, 174.2),
                ):
                    self.assertAlmostEqual(observed, expected, places=4)

            cassette = validation["geometry_context"]["cassette"]
            self.assertEqual(cassette["selected_candidate"], "front_first_open_back_u_box_3_web")
            self.assertEqual(cassette["selected_physical_length_mm"], 201.134375)
            self.assertLess(cassette["selected_to_control_volume_ratio"], 0.60)
            settings = validation["petg_a1_mini_candidate_settings"]
            self.assertEqual(settings["scale_percent"], 100.0)
            self.assertEqual(settings["material"], "PETG only")
            self.assertEqual(settings["printer"], "Bambu Lab A1 mini")
            self.assertEqual(settings["layer_height_mm"], 0.2)
            self.assertEqual(settings["wall_loops"], 6)
            self.assertEqual(settings["top_shell_layers"], 5)
            self.assertEqual(settings["bottom_shell_layers"], 3)
            self.assertEqual(settings["infill_percent"], 25)
            self.assertEqual(settings["filament_asin"], "B0D1KC72YP")
            self.assertIn("amazon.com/dp/B0D1KC72YP", settings["filament_product_url"])
            self.assertIn("4 kg bundle", settings["filament_selected_variant"])
            self.assertEqual(settings["drying_temperature_range_c"], [50.0, 50.0])
            self.assertEqual(settings["drying_duration_range_h"], [6.0, 8.0])
            self.assertTrue(settings["drying_record_required"])
            clearance_contract = validation["clearance_v2_geometry_contract"]
            self.assertEqual(
                tuple(clearance_contract["mesh_ids_in_order"]),
                CLEARANCE_V2_PART_IDS,
            )
            self.assertEqual(
                len(clearance_contract["canonical_float32_triangle_digests"]),
                5,
            )
            self.assertTrue(
                validation["artifact_config_identity"]["exact_match"]
            )
            runtime = validation["runtime_provenance"]
            self.assertTrue(runtime["requirements_exactly_matched"])
            self.assertEqual(
                [(item["distribution"], item["observed_version"]) for item in runtime["distributions"]],
                list(RUNTIME_REQUIREMENTS),
            )
            self.assertEqual(runtime, first_manifest["runtime_provenance"])
            self.assertEqual(
                validation["support_required_part_ids"],
                [
                    "r8_retained_single_peg",
                    "r8_retained_three_cable_comb",
                    "r8_retained_shortened_coil_j_hook",
                ],
            )
            self.assertTrue(validation["saved_orientation_support_contracts_passed"])
            blank_support = part_by_id["r8_retained_blank"][
                "saved_layer_support_evidence"
            ]
            self.assertFalse(blank_support["support_required"])
            self.assertGreaterEqual(
                blank_support["first_layer_body_contact_area_mm2"], 64.0
            )
            layout = validation["accessory_rail_layout"]
            self.assertEqual(
                layout["geometrically_eligible_corbel_indices"],
                {"through": [1, 2, 3, 4, 5, 6, 7], "return": [1, 2, 3]},
            )
            self.assertEqual(layout["geometrically_eligible_rails_per_level"], 10)
            self.assertEqual(layout["geometrically_eligible_sockets_per_level"], 30)
            self.assertEqual(
                layout["clean_default_equipped_corbel_indices"],
                {"through": [1, 3, 5, 7], "return": [1, 3]},
            )
            self.assertEqual(layout["clean_default_rails_per_level"], 6)
            self.assertEqual(layout["clean_default_sockets_per_level"], 18)
            self.assertEqual(layout["clean_default_rails_selected_two_levels"], 12)
            self.assertEqual(layout["clean_default_sockets_selected_two_levels"], 36)

            readme = first_files["README.md"].decode("utf-8")
            for phrase in (
                "unsliced, zero-rated qualification set",
                "100% scale",
                "combined 3MF is an all-parts catalog",
                "do **not** select a printer, filament, or process",
                "Never reuse a PLA preset",
                "0.20mm Strength @BBL A1M",
                "Support rules are part-specific",
                "Outer brim only",
                "loosest to tightest",
                "authored interface is 0.4 mm",
                "visible front long edge on",
                "177.6367 x 177.6367 mm",
                "B0D1KC72YP",
                "50 C / 50 C",
                "never auto-scale",
                "6 rails / 18 sockets per level",
                "Do not install or load these parts yet",
            ):
                self.assertIn(phrase, readme)

        after = {path: _tree_digest(path) for path in protected}
        self.assertEqual(before, after)

    def test_every_3mf_is_strict_neutral_and_every_stl_reloads_as_one_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "bundle"
            manifest = build(output)
            three_mf_paths = sorted(output.rglob("*.3mf"))
            stl_paths = sorted(output.rglob("*.stl"))
            self.assertEqual(len(three_mf_paths), 16)
            self.assertEqual(len(stl_paths), 15)

            combined = output / "model_only_3mf" / PACKAGE_FILENAME
            for path in three_mf_paths:
                with self.subTest(path=path.name):
                    inspection = model_io.inspect_model_only_3mf(path)
                    self.assertTrue(inspection.passed)
                    with zipfile.ZipFile(path) as archive:
                        self.assertEqual(
                            tuple(archive.namelist()), model_io.MODEL_ONLY_ENTRY_ORDER
                        )
                        self.assertIsNone(archive.testzip())
                        for info in archive.infolist():
                            self.assertEqual(
                                info.date_time, model_io.CANONICAL_ZIP_TIMESTAMP
                            )
                            self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
                    if path == combined:
                        self.assertEqual(len(inspection.objects), 15)
                    else:
                        self.assertEqual(len(inspection.objects), 1)
                        self.assertEqual(
                            set(inspection.translations_mm.values()), {(0.0, 0.0, 0.0)}
                        )

            expected_digests = manifest["geometry_digests_by_mesh_id"]
            for path in stl_paths:
                with self.subTest(path=path.name):
                    mesh = model_io.read_binary_stl(path)
                    evidence = model_io.serialized_mesh_evidence(mesh)
                    self.assertTrue(evidence["closed_one_body_positive"])
                    self.assertEqual(
                        evidence["canonical_float32_triangle_digest"],
                        expected_digests[path.stem],
                    )

    def test_source_sha_bundle_is_complete_and_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "bundle"
            manifest = build(output)
            source = manifest["source_sha_bundle"]
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
            self.assertEqual(source["bundle_sha256"], model_io.sha256_bytes(payload))

    def test_generator_refuses_every_existing_destination_without_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, create in (
                ("directory", lambda path: path.mkdir()),
                ("file", lambda path: path.write_text("owner data", encoding="utf-8")),
            ):
                destination = root / name
                create(destination)
                with self.subTest(kind=name):
                    with self.assertRaises(FileExistsError):
                        build(destination)
                if destination.is_file():
                    self.assertEqual(destination.read_text(encoding="utf-8"), "owner data")
            self.assertEqual(
                sorted(path.name for path in root.iterdir()), ["directory", "file"]
            )

        for index, protected in enumerate(
            (DEVELOPMENT / "r6", DEVELOPMENT / "r7", R8 / "generated" / "qualification_v1")
        ):
            destination = protected / f".forbidden-r8-v2-{os.getpid()}-{index}"
            self.assertFalse(os.path.lexists(destination))
            with self.assertRaises(PermissionError):
                build(destination)
            self.assertFalse(os.path.lexists(destination))

    def test_petg_anchor_and_zero_rating_scope_mutations_fail_closed(self) -> None:
        config = json.loads((R8 / "config.json").read_text(encoding="utf-8"))
        mutations = (
            (("material", "primary_part_material"), "PLA"),
            (("material", "pla_allowed_in_primary_or_load_path_parts"), True),
            (("material", "printed_wall_anchors_allowed"), True),
            (("printer", "filament_product"), "PLA"),
            (("printer", "filament_preset"), "Generic PLA @BBL A1M"),
            (("printer", "model"), "X1 Carbon"),
            (("shelf", "selected_level_count"), 3),
            (("d_frame", "wall_chord_mm"), 20.0),
            (("accessory_system", "sockets_per_eligible_corbel"), 2),
            (("project", "rated_load_kg"), False),
            (("accessory_system", "structural_or_shelf_load_credit"), True),
        )
        for path, value in mutations:
            candidate = json.loads(json.dumps(config))
            candidate[path[0]][path[1]] = value
            with self.subTest(path=".".join(path), value=value):
                with self.assertRaises(ValueError):
                    _validate_frozen_scope(candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
