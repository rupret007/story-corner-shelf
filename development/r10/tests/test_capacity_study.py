from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest


R10_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = R10_ROOT.parents[1]
sys.path.insert(0, str(R10_ROOT))

import capacity_study as study  # noqa: E402


class CapacityStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = study.load_config()

    def test_report_is_zero_rated_and_predominantly_printed(self) -> None:
        report = study.build_report(self.config)
        self.assertTrue(report["qualification_only"])
        self.assertEqual((report["rated_load_kg"], report["rated_load_lb"]), (0.0, 0.0))
        self.assertIn("mass context, not capacity", report["critical_correction"])
        self.assertFalse(report["printed_architecture"]["metal_shelf_chassis_present"])
        self.assertTrue(report["physical_target"]["target_is_not_a_rating"])

    def test_exact_seven_support_ten_inch_arcade(self) -> None:
        layout = study.derive_layout(self.config)
        self.assertEqual(layout.support_count, 7)
        self.assertEqual(layout.bay_count, 6)
        self.assertEqual(
            layout.centers_mm,
            (15.875, 269.875, 523.875, 777.875, 1031.875, 1285.875, 1539.875),
        )
        self.assertEqual(layout.support_pitch_mm, 254.0)
        self.assertEqual(layout.support_pitch_in, 10.0)
        self.assertTrue(layout.support_faces_flush_with_wall_ends)
        self.assertEqual(layout.pitch_reduction_percent, 16.652994)
        self.assertEqual(layout.nominal_support_share_reduction_percent, 14.285714)
        self.assertEqual(layout.support_roles_left_to_right[0], "outer_bookend_with_cable_receiver")
        self.assertEqual(
            layout.support_roles_left_to_right[-1],
            "through_side_terminal_corner_placeholder",
        )
        self.assertEqual(layout.support_roles_left_to_right.count("compact_arcade"), 5)

    def test_all_largest_structural_articles_fit_a1_with_full_margins(self) -> None:
        evidence = study.derive_printed_architecture(self.config)
        self.assertEqual(evidence.support_required_envelope_mm, (166.6, 172.95, 31.75))
        self.assertEqual(
            evidence.largest_cassette_half_required_envelope_mm,
            (156.55, 46.2, 152.4),
        )
        self.assertEqual(evidence.splice_log_required_envelope_mm, (173.3, 34.2, 24.0))
        self.assertTrue(evidence.nominal_core_envelopes_fit_with_margins)
        self.assertFalse(evidence.actual_saved_mesh_release_fit_proven)
        self.assertEqual(evidence.independent_bays, 6)
        self.assertEqual(evidence.splice_logs_per_bay, 3)
        self.assertEqual(evidence.printed_primary_bearing_piece_count, 37)
        self.assertEqual(evidence.printed_retention_key_count, 30)
        self.assertEqual(evidence.printed_load_path_piece_count, 67)

    def test_log_section_properties_use_true_notched_mesh_proxy_only(self) -> None:
        evidence = study.derive_printed_architecture(self.config)
        self.assertEqual(evidence.per_log_gross_area_mm2, 464.0)
        self.assertEqual(evidence.per_log_net_area_mm2, 334.800014)
        self.assertEqual(evidence.per_log_gross_second_moment_mm4, 22428.688697)
        self.assertEqual(evidence.per_log_net_second_moment_mm4, 8263.957405)
        self.assertEqual(evidence.per_log_gross_section_modulus_mm3, 1848.036857)
        self.assertEqual(evidence.per_log_net_section_modulus_mm3, 949.015628)
        self.assertEqual(evidence.net_to_gross_area_ratio, 0.721551755)
        self.assertEqual(evidence.net_to_gross_second_moment_ratio, 0.368454773)
        self.assertEqual(evidence.net_to_gross_section_modulus_ratio, 0.513526353)
        self.assertEqual(
            evidence.three_log_net_second_moment_geometry_proxy_mm4,
            24791.872215,
        )
        self.assertFalse(evidence.midpoint_section_material_capacity_claimed)

    def test_cable_system_is_never_forgotten_or_credited(self) -> None:
        memory = study.build_report(self.config)["cable_memory"]
        self.assertEqual(memory["full_l_outer_bookends_per_level"], 2)
        self.assertEqual(memory["first_wall_active_bookends"], 1)
        self.assertEqual(memory["sockets_per_bookend"], 2)
        self.assertTrue(memory["flush_blank_and_comb_hook_required"])
        self.assertEqual(memory["first_wall_flush_blank_quantity"], 2)
        self.assertEqual(memory["first_wall_comb_hook_quantity"], 1)
        self.assertTrue(memory["intermediate_and_corner_hardware_forbidden"])
        self.assertFalse(memory["structural_credit"])

    def test_wall_bores_are_geometry_candidates_not_drilling_authorization(self) -> None:
        report = study.build_report(self.config)
        bore = report["wall_bore_candidate"]
        self.assertEqual(bore["count_per_support"], 3)
        self.assertEqual(bore["diameter_mm"], 7.0)
        self.assertEqual(bore["drops_below_shelf_underside_mm"], [19.05, 79.375, 139.7])
        self.assertEqual(bore["washer_bearing_land_outer_diameter_mm"], 27.025)
        self.assertFalse(bore["drilling_authorized"])

    def test_exact_hardware_candidate_and_controlled_lot_reconcile(self) -> None:
        arcade = self.config["printed_arcade"]
        fastener = arcade["wall_fastener_candidate"]
        washer = arcade["washer_candidate"]
        plan = arcade["hardware_procurement_plan"]
        self.assertIn("part 90306", fastener["product"])
        self.assertFalse(fastener["esr_2442_covers_petg_or_loose_washer_stack"])
        self.assertIsNone(fastener["received_thread_length_mm"])
        self.assertEqual((washer["manufacturer"], washer["part_number"]), ("L.H. Dottie", "FW14"))
        self.assertTrue(washer["loose_washer_stack_is_outside_esr_2442"])
        self.assertEqual(plan["initial_controlled_lot_purchase_quantity"], 100)
        self.assertEqual(plan["minimum_reserved_quantity_before_retests"], 96)
        self.assertEqual(plan["initial_unallocated_spare_quantity"], 4)

    def test_creep_gate_requires_temperature_and_one_thousand_hours(self) -> None:
        target = study.build_report(self.config)["physical_target"]
        self.assertEqual(target["sustained_creep_hours"], 1000)
        self.assertIsNone(target["maximum_service_temperature_c"])
        self.assertIsNone(target["qualification_temperature_c"])
        self.assertIn(
            "one_thousand_hour_creep_passed",
            study.build_report(self.config)["release_blockers"],
        )
        self.assertIn("- measured shelf dead mass", target["external_proof_ballast_formula"])
        self.assertIn(
            "0.5 * measured shelf dead mass",
            target["external_point_proof_ballast_formula"],
        )
        self.assertIn("1.5 * 9 kg", target["external_point_proof_ballast_formula"])

    def test_outlet_screen_is_vertical_only_and_horizontal_data_stay_unresolved(self) -> None:
        screen = study.build_report(self.config)["field_clearance_screen"]
        self.assertEqual(screen["shelf_underside_elevation_in"], 66.740157)
        self.assertEqual(screen["structural_strap_bottom_elevation_in"], 60.490157)
        self.assertEqual(screen["vertical_gap_above_outlet_top_in"], 6.990157)
        self.assertTrue(screen["vertical_only"])
        self.assertFalse(screen["horizontal_outlet_plug_cord_trim_clearance_verified"])

    def test_complete_printed_load_path_and_blockers_are_preserved(self) -> None:
        report = study.build_report(self.config)
        for phrase in (
            "printed cassette skins/webs",
            "three captured PETG splice logs",
            "seven Palatine PETG supports",
            "21 GRK/washer candidates",
            "verified continuous blocking",
        ):
            self.assertIn(phrase, report["load_path"])
        self.assertEqual(set(report["release_blockers"]), set(self.config["physical_gates"]))

    def test_frozen_r9_dependencies_match_bytes(self) -> None:
        study.validate_config(self.config)
        self.assertEqual(
            study.canonical_config_sha256(self.config),
            study.EXPECTED_CONFIG_CANONICAL_SHA256,
        )
        for relative, expected in self.config["frozen_r9_inputs"].items():
            self.assertEqual(study._sha256(REPOSITORY_ROOT / relative), expected)

    def test_unsafe_mutations_fail_closed(self) -> None:
        mutations = (
            (("project", "rated_load_kg"), 45.0),
            (("project", "wall_installation_authorized"), True),
            (("field_reference", "support_count"), 6),
            (("field_reference", "supports_evenly_spaced"), False),
            (("field_reference", "continuous_blocking_required"), False),
            (("field_reference", "hollow_wall_anchor_primary_load_path_allowed"), True),
            (("field_reference", "unresolved_inputs", "outlet_horizontal_bounds_mm"), [1, 2]),
            (("qualification_target", "rating_created_by_target"), True),
            (("qualification_target", "sustained_creep_hours"), 720),
            (("qualification_target", "maximum_service_temperature_c"), 25.0),
            (("printed_arcade", "metal_shelf_chassis_present"), True),
            (("printed_arcade", "compact_visible_corbel_drop_mm"), 158.75),
            (("printed_arcade", "wall_strap_total_drop_from_shelf_underside_mm"), 76.2),
            (("printed_arcade", "splice_log", "quantity"), 12),
            (("printed_arcade", "splice_log", "engagement_per_cassette_half_mm"), 1.0),
            (("printed_arcade", "splice_log", "positive_body_shoulder"), False),
            (("printed_arcade", "support_capture_key", "quantity"), 7),
            (("printed_arcade", "support_capture_key", "retention_only"), False),
            (("printed_arcade", "transverse_lock_key", "quantity"), 6),
            (("printed_arcade", "transverse_lock_key", "one_log_per_key"), False),
            (("printed_arcade", "cassette_half", "total_height_mm"), 31.75),
            (("printed_arcade", "cassette_half", "midpoint_seam_gap_mm"), 0.0),
            (("printed_arcade", "cassette_half", "load_web_thickness_mm"), 0.1),
            (("printed_arcade", "cassette_half", "minimum_cassette_bearing_contact_mm"), 0.0),
            (("printed_arcade", "splice_log", "structural_credit_from_friction_or_snap"), True),
            (("printed_arcade", "wall_bore_candidate", "counterbore_allowed"), True),
            (("printed_arcade", "cable_system", "sockets_per_bookend"), 0),
            (("printed_arcade", "cable_system", "first_wall_flush_blank_quantity"), 1),
            (("printed_arcade", "cable_system", "active_first_wall_support_indices"), [6]),
            (("printed_arcade", "cable_system", "allowed_on_intermediate_supports"), True),
            (("printed_arcade", "wall_fastener_candidate", "quantity_installed"), 18),
            (
                (
                    "printed_arcade",
                    "hardware_procurement_plan",
                    "initial_controlled_lot_purchase_quantity",
                ),
                30,
            ),
            (
                (
                    "printed_arcade",
                    "wall_fastener_candidate",
                    "final_schedule_requires_actual_blocking_and_substrate",
                ),
                False,
            ),
            (("physical_gates", "proof_load_passed"), True),
        )
        for path, value in mutations:
            with self.subTest(path=path):
                mutated = deepcopy(self.config)
                target = mutated
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(study.CapacityStudyError):
                    study.validate_config(mutated)

        extra = deepcopy(self.config)
        extra["unreviewed_extra_leaf"] = True
        with self.assertRaises(study.CapacityStudyError):
            study.validate_config(extra)

    def test_strict_json_and_cli_determinism(self) -> None:
        with self.assertRaises(study.CapacityStudyError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=study._object_pairs)
        with self.assertRaises(study.CapacityStudyError):
            json.loads('{"value":NaN}', parse_constant=study._reject_constant)
        command = [sys.executable, "-B", str(R10_ROOT / "capacity_study.py")]
        first = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), json.loads(json.dumps(study.build_report(self.config))))


if __name__ == "__main__":
    unittest.main()
