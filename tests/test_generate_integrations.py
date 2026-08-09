#!/usr/bin/env python3
"""Generator integration regressions for the rail-free RC and ornament."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

import generate_all_petg_r6 as generator  # noqa: E402


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    output: dict = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key {key!r}")
        output[key] = value
    return output


def file_digests(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class R6GeneratorRailOrnamentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(
            (R6 / "config.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
        cls.geometry, _warnings = generator.calculate_development_geometry(cls.cfg)
        cls.plan = cls.geometry["plan_object"]
        cls.rails = []
        cls.rail_report = generator.installed_rail_baseline_report(
            cls.cfg, selected_levels=2
        )
        cls.ornament, cls.ornament_report = generator.removable_ornament_parts(
            cls.cfg,
            selected_levels=2,
        )
        cls.release_report = generator.integrated_release_reconciliation(
            cls.cfg,
            plan=cls.plan,
            selected_levels=2,
            rail_report=cls.rail_report,
            ornament_report=cls.ornament_report,
        )
        cls.parts = cls.rails + cls.ornament

    def test_exact_unique_mesh_families_and_repeat_counts(self) -> None:
        self.assertEqual(len(self.rails), 0)
        self.assertEqual(len(self.ornament), 10)
        self.assertEqual(len(self.parts), 10)
        self.assertEqual(len({part.name for part in self.parts}), 10)
        self.assertFalse(self.rail_report["installed_in_release_candidate"])
        self.assertEqual(self.rail_report["unique_installed_rail_mesh_count"], 0)
        self.assertEqual(
            self.rail_report["installed_counts_per_level"],
            {
                "stitch_rail_segment": 0,
                "stitch_rail_joint_pin": 0,
                "run_end_tie_block": 0,
            },
        )
        self.assertEqual(
            self.rail_report["installed_counts_selected_levels"],
            {
                "stitch_rail_segment": 0,
                "stitch_rail_joint_pin": 0,
                "run_end_tie_block": 0,
            },
        )
        self.assertEqual(self.ornament_report["unique_installed_mesh_family_count"], 8)
        self.assertEqual(self.ornament_report["installed_object_count_per_level"], 33)
        self.assertEqual(
            self.ornament_report["installed_object_count_selected_levels"], 66
        )
        self.assertEqual(
            self.ornament_report["unique_print_first_coupon_mesh_count"], 2
        )

    def test_optional_rail_study_is_topology_derived_and_release_excluded(self) -> None:
        parts, report = generator.stitch_rail_parts(
            self.cfg,
            plan=self.plan,
            selected_levels=2,
        )
        expected = self.cfg["structure"]["stitch_rail_planner"][
            "expected_per_level"
        ]
        self.assertEqual(report["planner_topology_per_level"], expected)
        self.assertEqual(report["unique_position_specific_segment_mesh_count"], 41)
        self.assertEqual(report["unique_optional_research_mesh_count"], 43)
        self.assertEqual(
            report["line_segment_counts_per_level"],
            {
                "long_wall_5ft:front": 14,
                "long_wall_5ft:rear": 14,
                "short_wall_3ft:front": 6,
                "short_wall_3ft:rear": 7,
            },
        )
        self.assertEqual(
            report["optional_research_counts_per_level"],
            {
                "stitch_rail_segment": 41,
                "stitch_rail_joint_pin": 74,
                "run_end_tie_block": 4,
            },
        )
        self.assertEqual(sum(report["optional_research_counts_per_level"].values()), 119)
        self.assertTrue(all(value == 0 for value in report["installed_counts_per_level"].values()))
        self.assertEqual(len(parts), 43)
        self.assertTrue(
            all(
                part.design_metrics["installed_in_release_candidate"] is False
                for part in parts
            )
        )
        pin = next(
            part
            for part in parts
            if part.name == "R6_DEV_STITCH_RAIL_SHARED_JOINT_PIN"
        )
        self.assertIn("plain tip on the build plate", pin.saved_orientation)
        self.assertIn("pull head is uppermost", pin.saved_orientation)
        self.assertEqual(pin.design_metrics["installed_repeat_count_per_level"], 0)

    def test_metadata_never_double_counts_sources_or_credits_ornament(self) -> None:
        self.assertEqual(self.rails, [])
        self.assertFalse(self.rail_report["optional_research_geometry_emitted"])
        installed_ornament = [
            part for part in self.ornament if part.design_metrics["installed"]
        ]
        coupons = [
            part for part in self.ornament if part.design_metrics["print_first_coupon"]
        ]
        self.assertEqual((len(installed_ornament), len(coupons)), (8, 2))
        self.assertTrue(
            all(part.design_metrics["structural_credit"] is False for part in self.ornament)
        )
        self.assertTrue(
            all(part.design_metrics["installed_repeat_count_per_level"] == 0 for part in coupons)
        )
        self.assertEqual(
            sum(part.design_metrics["test_coupon_print_count"] for part in coupons), 2
        )

    def test_visual_arch_and_physical_carrier_seams_are_embodied(self) -> None:
        carriers = {
            part.design_metrics["ornament_geometry_family_id"]: part
            for part in self.ornament
            if "carrier" in part.design_metrics["ornament_geometry_family_id"]
        }
        self.assertEqual(len(carriers), 4)
        visual = self.cfg["palatine"]["visual_carrier_contract"]
        expected_widths = {
            "through_carrier_left": float(
                visual["through_physical_carrier_width_mm"]
            ),
            "through_carrier_right": float(
                visual["through_physical_carrier_width_mm"]
            ),
            "return_carrier_left": float(
                visual["return_physical_carrier_width_mm"]
            ),
            "return_carrier_right": float(
                visual["return_physical_carrier_width_mm"]
            ),
        }
        for family_id, expected_width in expected_widths.items():
            part = carriers[family_id]
            self.assertAlmostEqual(float(part.mesh.extents[0]), expected_width, places=5)
            self.assertAlmostEqual(part.design_metrics["width_mm"], expected_width)
            self.assertAlmostEqual(part.design_metrics["visual_spring_e_mm"], 60.0)
            self.assertAlmostEqual(part.design_metrics["visual_crown_e_mm"], 152.0)
            self.assertAlmostEqual(part.design_metrics["visual_rise_mm"], 92.0)
            self.assertAlmostEqual(part.design_metrics["visual_seam_mm"], 0.6)
            self.assertAlmostEqual(
                part.design_metrics["centered_inset_each_nominal_end_mm"], 0.3
            )
            self.assertTrue(part.mesh.is_watertight)
            self.assertEqual(part.mesh.body_count, 1)

    def test_all_integrated_meshes_validate_in_memory_and_inventory_reconciles(self) -> None:
        envelope = np.asarray(
            self.cfg["printer"]["minimum_model_build_envelope_mm"], dtype=float
        )
        density = float(self.cfg["material"]["petg_density_g_cm3"])
        records = [
            generator.validate_part(part, envelope_mm=envelope, density_g_cm3=density)
            for part in self.parts
        ]
        self.assertTrue(
            all(item["development_mesh_validation_passed"] for item in records)
        )
        configured_totals = self.cfg["nominal_geometry_snapshot"][
            "baseline_complete_physical_object_counts"
        ]
        self.assertEqual(
            self.release_report["authoritative_inventory_physical_objects_per_level"],
            configured_totals["complete_per_level"],
        )
        self.assertEqual(
            self.release_report[
                "authoritative_inventory_physical_objects_selected_levels"
            ],
            configured_totals["complete_selected_two_levels"],
        )
        self.assertEqual(
            self.release_report["integrated_installed_object_count_per_level"], 33
        )
        self.assertEqual(
            self.release_report["integrated_installed_object_count_selected_levels"],
            66,
        )
        self.assertEqual(
            self.release_report["authoritative_inventory_contradictions"],
            {"one_level": [], "selected_levels": []},
        )
        self.assertTrue(
            self.release_report[
                "canonical_software_model_package_inventory_reconciled"
            ]
        )
        self.assertEqual(generator.UNRESOLVED_INTERFACE_BLOCKERS, ())
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "software_model_package_eligible"
            ]
        )
        self.assertFalse(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "physical_installation_qualified"
            ]
        )
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "configured_bottom_skin_present_in_current_position_specific_meshes"
            ]
        )
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "current_saved_orientation_verified_top_skin_on_build_plate"
            ]
        )
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "authoritative_installed_solid_collision_gate_passed"
            ]
        )
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "authoritative_full_vertical_lift_collision_gate_passed"
            ]
        )
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "all_22_static_lock_mates_collision_free"
            ]
        )
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "straight_lock_service_corridor_collision_free"
            ]
        )
        self.assertEqual(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "compressed_lock_service_sweep_boolean_pair_count"
            ],
            8316,
        )
        self.assertTrue(
            generator.CASSETTE_COMPLETION_BLOCKER[
                "expanded_tail_flex_coupon_required"
            ]
        )

    def test_individual_stl_and_model_only_3mf_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-integrated-") as directory:
            output = Path(directory)
            stl_output = output / "stl"
            model_output = output / "model_only_3mf"
            individual_output = output / "individual_model_only_3mf"
            stl_output.mkdir()
            model_output.mkdir()
            individual_output.mkdir()
            with (
                mock.patch.object(generator, "OUT", output),
                mock.patch.object(generator, "STL_OUT", stl_output),
                mock.patch.object(generator, "MODEL_3MF_OUT", model_output),
                mock.patch.object(
                    generator,
                    "INDIVIDUAL_MODEL_3MF_OUT",
                    individual_output,
                ),
            ):
                generator.write_part_files(self.parts, self.cfg)
                first = file_digests(output)
                audits = [
                    generator.audit_3mf(path)
                    for path in sorted(individual_output.glob("*.3mf"))
                ]
                generator.write_part_files(self.parts, self.cfg)
                second = file_digests(output)
            self.assertEqual(len(list(stl_output.glob("R6_DEV_*.stl"))), 10)
            self.assertEqual(len(list(individual_output.glob("*.3mf"))), 10)
            self.assertEqual(len(list(model_output.glob("*.3mf"))), 0)
            self.assertEqual(first, second)
            self.assertTrue(all(item["model_only_audit_passed"] for item in audits))
            self.assertTrue(all(not item["embedded_gcode_entries"] for item in audits))
            self.assertTrue(
                all(
                    all(item["required_description_tokens_present"].values())
                    for item in audits
                )
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
