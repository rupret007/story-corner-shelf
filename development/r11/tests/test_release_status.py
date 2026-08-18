from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


R11_ROOT = Path(__file__).resolve().parents[1]
if str(R11_ROOT) not in sys.path:
    sys.path.insert(0, str(R11_ROOT))

import release_status  # noqa: E402


class R11ReleaseStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pending = release_status.build_release_status()

    def test_every_external_transition_is_hard_false_and_zero_rated(self) -> None:
        for key in (
            "full_wall_set_complete",
            "all_physical_gates_complete",
            "production_ready",
            "wall_installation_authorized",
            "drilling_coordinates_released",
            "drilling_schedule_released",
            "print_authorized",
            "test_load_authorized",
        ):
            self.assertFalse(self.pending[key], key)
        self.assertTrue(
            self.pending["fresh_human_permission_required_before_every_print"]
        )
        self.assertEqual(
            (self.pending["rated_load_kg"], self.pending["rated_load_lb"]),
            (0.0, 0.0),
        )

    def test_complete_artifact_gate_cannot_override_hard_safety_boundary(self) -> None:
        artifact = release_status.complete_artifact_gate(
            individual_mesh_count=8,
            catalog_object_count=8,
            neutral_3mf_audit_passed=True,
            stl_geometry_matches_3mf=True,
            source_snapshot_matches_live_tree=True,
            runtime_provenance_present=True,
        )
        self.assertTrue(artifact["passed"])
        status = release_status.build_release_status(artifact_gate=artifact)
        self.assertFalse(status["print_authorized"])
        self.assertFalse(status["wall_installation_authorized"])
        self.assertFalse(status["drilling_schedule_released"])
        self.assertFalse(status["drilling_coordinates_released"])
        self.assertFalse(status["test_load_authorized"])
        self.assertFalse(status["production_ready"])
        self.assertFalse(status["full_wall_set_complete"])
        self.assertEqual((status["rated_load_kg"], status["rated_load_lb"]), (0.0, 0.0))

    def test_config_gate_closes_wall_and_requires_two_terminal_bay0_halves(self) -> None:
        gate = self.pending["config_gate"]
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["frozen_r10_tree"]["path"], "development/r10")
        self.assertTrue(
            gate["checks"]["exact_outer_terminal_and_interior_regular_identity"]
        )
        report = gate["layout_report"]
        self.assertEqual(report["layout"]["bay_count"], 6)
        self.assertEqual(report["layout"]["support_count"], 7)
        self.assertEqual(
            report["joinery_candidate"]["terminal_half_deck_length_mm"],
            162.175,
        )
        bay0 = report["layout"]["bay_stations"][0]
        self.assertEqual(
            (bay0["left_half_kind"], bay0["right_half_kind"]),
            ("terminal", "terminal"),
        )
        bay5 = report["layout"]["bay_stations"][5]
        self.assertEqual(
            (bay5["left_half_kind"], bay5["right_half_kind"]),
            ("terminal", "terminal"),
        )
        self.assertEqual(
            report["printed_piece_counts"]["terminal_integrated_half_decks"], 4
        )
        self.assertEqual(
            report["printed_piece_counts"]["regular_integrated_half_decks"], 8
        )
        self.assertEqual(report["printed_piece_counts"]["kit_articles"], 28)
        self.assertEqual(
            report["printed_piece_counts"]["simultaneously_installed_articles"],
            27,
        )
        self.assertEqual(report["hardware_candidate_counts"]["wall_fasteners"], 21)
        starts = report["print_start_estimate"]
        self.assertEqual(starts["safe_unbatched_starts"], 28)
        self.assertEqual(starts["target_batched_starts"], 21)
        self.assertFalse(starts["plate_nesting_verified"])
        self.assertIsNone(starts["verified_production_starts"])

    def test_exact_eight_article_contract_is_stable(self) -> None:
        self.assertEqual(len(release_status.PART_ORDER), 8)
        self.assertEqual(len(set(release_status.PART_ORDER)), 8)
        self.assertEqual(
            release_status.STRUCTURAL_PROVIDER_PART_ORDER,
            (
                release_status.LEFT_TERMINAL_HALF_PART,
                release_status.RIGHT_TERMINAL_HALF_PART,
                release_status.KEYSTONE_PART,
            ),
        )
        self.assertNotIn("regular", release_status.LEFT_TERMINAL_HALF_PART)
        self.assertNotIn("regular", release_status.RIGHT_TERMINAL_HALF_PART)

    def test_missing_support_cable_provider_is_an_explicit_geometry_blocker(self) -> None:
        gate = self.pending["geometry_gate"]
        if gate["passed"]:
            self.assertEqual(tuple(gate["available_part_order"]), release_status.PART_ORDER)
            return
        self.assertTrue(gate["analytic_blockers"])
        self.assertFalse(self.pending["first_outer_actual_bay_neutral_bundle_complete"])

    def test_source_closure_requires_the_separate_support_cable_source(self) -> None:
        provider = R11_ROOT / "support_cable_geometry.py"
        if provider.is_file():
            records = release_status.source_records()
            self.assertIn(
                "development/r11/support_cable_geometry.py",
                {record["path"] for record in records},
            )
            return
        with self.assertRaisesRegex(ValueError, "support_cable_geometry.py"):
            release_status.source_records()

    def test_source_closure_binds_every_controlling_r11_input(self) -> None:
        paths = {record["path"] for record in release_status.source_records()}
        for relative in (
            "requirements.txt",
            "development/r8/model_io.py",
            "development/r9/model_io.py",
            "development/r10/model_io.py",
            "development/r11/ASSEMBLY.md",
            "development/r11/CUSTOMIZATION.md",
            "development/r11/DESIGN_REQUIREMENTS.md",
            "development/r11/FROZEN_BASELINES.json",
            "development/r11/GUIDELINES.md",
            "development/r11/LOAD_QUALIFICATION.md",
            "development/r11/MATERIALS_AND_HARDWARE.md",
            "development/r11/PLAN.md",
            "development/r11/PRINT_FIRST.md",
            "development/r11/README.md",
            "development/r11/config.json",
            "development/r11/generate_qualification.py",
            "development/r11/integrated_geometry.py",
            "development/r11/layout.py",
            "development/r11/model_io.py",
            "development/r11/release_status.py",
            "development/r11/support_cable_geometry.py",
            "development/r11/visuals/r11_first_outer_bay_exploded_and_wall_topology.svg",
        ):
            self.assertIn(relative, paths)

    def test_assembly_visual_is_byte_bound_parsed_and_label_audited(self) -> None:
        visual = R11_ROOT / release_status.ASSEMBLY_VISUAL_RELATIVE_PATH
        report = release_status.inspect_assembly_visual(visual)
        self.assertEqual(
            report["sha256"], release_status.EXPECTED_ASSEMBLY_VISUAL_SHA256
        )
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(
            tuple(report["required_labels"]),
            release_status.ASSEMBLY_VISUAL_REQUIRED_LABELS,
        )
        with tempfile.TemporaryDirectory() as directory:
            tampered = Path(directory) / "tampered.svg"
            payload = visual.read_bytes().replace(b"NO PRINT", b"GO PRINT", 1)
            tampered.write_bytes(payload)
            with mock.patch.object(
                release_status,
                "EXPECTED_ASSEMBLY_VISUAL_SHA256",
                hashlib.sha256(payload).hexdigest(),
            ):
                with self.assertRaisesRegex(ValueError, "missing_labels"):
                    release_status.inspect_assembly_visual(tampered)

    def test_strict_json_rejects_duplicate_and_non_finite_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"a": 1, "a": 2}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                release_status.strict_json(duplicate)
            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"a": NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Non-finite JSON value"):
                release_status.strict_json(nonfinite)

    def test_runtime_provenance_names_frozen_r10_writer_and_exact_mesh_stack(self) -> None:
        provenance = release_status.runtime_provenance()
        for key in (
            "python_version",
            "requirements_txt_sha256",
            "numpy_version",
            "trimesh_version",
            "shapely_version",
            "manifold3d_version",
            "r10_model_io_sha256_verified_before_execution",
        ):
            self.assertTrue(provenance[key])
        self.assertTrue(provenance["requirements_runtime_exact_match"])


if __name__ == "__main__":
    unittest.main()
