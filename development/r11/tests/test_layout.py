from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


R11_ROOT = Path(__file__).resolve().parents[1]
if str(R11_ROOT) not in sys.path:
    sys.path.insert(0, str(R11_ROOT))

import layout  # noqa: E402


class R11LayoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = layout.load_config()
        cls.plan = layout.build_plan(cls.config)

    def test_exact_61p25_in_six_bay_closure(self) -> None:
        result = self.plan["layout"]
        self.assertEqual(result["clear_wall_length_mm"], 1555.75)
        self.assertEqual(result["support_run_width_mm"], 31.75)
        self.assertEqual(result["maximum_bay_pitch_mm"], 254.0)
        self.assertEqual(result["bay_count"], 6)
        self.assertEqual(result["support_count"], 7)
        self.assertEqual(result["actual_pitch_mm"], 254.0)
        self.assertEqual(
            [item["center_mm"] for item in result["support_stations"]],
            [15.875, 269.875, 523.875, 777.875, 1031.875, 1285.875, 1539.875],
        )
        closure = result["exact_wall_closure"]
        self.assertEqual(closure["clear_wall_length_in"], 61.25)
        self.assertEqual(closure["decomposition"], "L = W + bay_count * actual_pitch")
        self.assertEqual(closure["support_width_term_mm"], 31.75)
        self.assertEqual(closure["bay_pitch_term_count"], 6)
        self.assertEqual(closure["bay_pitch_term_mm"], 254.0)
        self.assertEqual(closure["reconstructed_wall_length_mm"], 1555.75)
        self.assertEqual(closure["closure_residual_mm"], 0.0)
        self.assertEqual(closure["regular_physical_bay_span_mm"], 253.65)
        self.assertEqual(closure["terminal_physical_bay_span_mm"], 269.35)
        self.assertEqual(closure["terminal_bay_count"], 2)
        self.assertEqual(closure["regular_bay_count"], 4)
        self.assertEqual(closure["inter_bay_gap_count"], 5)
        self.assertEqual(closure["endpoint_gap_count"], 2)
        self.assertEqual(closure["module_reconstructed_wall_length_mm"], 1555.75)
        self.assertEqual(closure["module_closure_residual_mm"], 0.0)
        self.assertEqual(result["support_stations"][0]["footprint_start_mm"], 0.0)
        self.assertEqual(result["support_stations"][-1]["footprint_end_mm"], 1555.75)

    def test_55_mm_candidate_joinery_math_is_exact_and_unreleased(self) -> None:
        joinery = self.plan["joinery_candidate"]
        self.assertEqual(joinery["integrated_reciprocal_overlap_mm"], 55.0)
        self.assertEqual(joinery["joint_clearance_mm"], 0.35)
        self.assertEqual(joinery["regular_half_deck_length_mm"], 154.325)
        self.assertEqual(joinery["terminal_extension_mm"], 7.85)
        self.assertEqual(joinery["terminal_half_deck_length_mm"], 162.175)
        self.assertEqual(joinery["bearing_per_support_side_mm"], 15.7)
        self.assertEqual(joinery["minimum_bearing_per_support_side_mm"], 15.7)
        self.assertTrue(joinery["overlap_is_initial_candidate_only"])
        self.assertFalse(joinery["overlap_physical_gate_passed"])
        self.assertFalse(joinery["integral_bay_local_support_capture_validated"])
        self.assertTrue(joinery["piece_reduction_contingent_on_capture_validation"])
        self.assertFalse(joinery["structural_credit_from_friction_snap_glue_or_wedge"])

    def test_exact_piece_hardware_and_conservative_start_formulas(self) -> None:
        self.assertEqual(self.plan["printed_piece_counts"]["supports"], 7)
        self.assertEqual(
            self.plan["printed_piece_counts"]["integrated_half_decks"], 12
        )
        self.assertEqual(
            self.plan["printed_piece_counts"]["terminal_integrated_half_decks"],
            4,
        )
        self.assertEqual(
            self.plan["printed_piece_counts"]["regular_integrated_half_decks"],
            8,
        )
        self.assertEqual(
            self.plan["printed_piece_counts"]["positive_bay_wedges"], 6
        )
        self.assertEqual(self.plan["printed_piece_counts"]["cable_modules"], 3)
        self.assertEqual(self.plan["printed_piece_counts"]["kit_articles"], 28)
        self.assertEqual(
            self.plan["printed_piece_counts"]["simultaneously_installed_articles"],
            27,
        )
        self.assertFalse(self.plan["printed_piece_counts"]["count_is_releasable"])
        starts = self.plan["print_start_estimate"]
        self.assertEqual(starts["individual_support_starts"], 7)
        self.assertEqual(starts["individual_half_deck_starts"], 12)
        self.assertEqual(starts["candidate_wedge_plate_starts"], 1)
        self.assertEqual(starts["candidate_cable_plate_starts"], 1)
        self.assertEqual(starts["target_batched_starts"], 21)
        self.assertEqual(starts["safe_unbatched_starts"], 28)
        self.assertIsNone(starts["verified_production_starts"])
        self.assertFalse(starts["plate_nesting_verified"])
        self.assertEqual(
            self.plan["hardware_candidate_counts"]["wall_fasteners"], 21
        )
        self.assertEqual(self.plan["hardware_candidate_counts"]["washers"], 21)
        self.assertEqual(
            self.plan["exact_formulas"]["kit_articles"],
            "supports + 2 * bays + 1 * bays + supplied_cable_modules",
        )
        self.assertEqual(
            self.plan["exact_formulas"]["target_batched_starts"],
            starts["formula"],
        )

    def test_flat_print_envelopes_include_full_14p2_mm_xy_allowance(self) -> None:
        printer = self.plan["printer_evidence"]
        self.assertEqual(printer["xy_allowance_each_axis_mm"], 14.2)
        self.assertEqual(
            printer["parts"]["regular_integrated_half_deck"][
                "required_build_envelope_mm"
            ],
            [168.525, 166.6, 32.0],
        )
        self.assertEqual(
            printer["parts"]["terminal_integrated_half_deck"][
                "required_build_envelope_mm"
            ],
            [176.375, 166.6, 32.0],
        )
        self.assertTrue(printer["all_declared_candidate_envelopes_fit"])
        self.assertFalse(printer["release_fit_proven"])

    def test_default_is_zero_rated_and_install_request_is_refused(self) -> None:
        self.assertTrue(self.plan["qualification_only"])
        self.assertEqual(
            (self.plan["rated_load_kg"], self.plan["rated_load_lb"]), (0.0, 0.0)
        )
        self.assertFalse(self.plan["release"]["installation_ready"])
        self.assertFalse(self.plan["release"]["wall_installation_authorized"])
        self.assertFalse(self.plan["release"]["drilling_coordinates_released"])
        self.assertTrue(
            self.plan["release"][
                "checked_neutral_qualification_artifact_generation_allowed"
            ]
        )
        with self.assertRaises(layout.InstallationRefused) as caught:
            layout.build_plan(self.config, request_install=True)
        self.assertIn("keepout survey is incomplete", caught.exception.blockers)
        self.assertFalse(self.plan["keepout_evidence"]["candidate_clear"])
        self.assertIn("continuous blocking is not confirmed", caught.exception.blockers)
        self.assertIn(
            "integral bay-local support capture is not validated",
            caught.exception.blockers,
        )

    def test_general_wall_solver_recomputes_counts_without_hardcoding_six_bays(self) -> None:
        cfg = deepcopy(self.config)
        cfg["wall_input"].update(
            {
                "clear_length_mm": 1000.0,
                "support_run_width_mm": 40.0,
                "maximum_bay_pitch_mm": 230.0,
            }
        )
        cfg["field_measurement_input"]["clear_length_samples_mm"] = [1000.0, 1000.0]
        result = layout.build_plan(cfg)
        self.assertEqual(result["layout"]["bay_count"], 5)
        self.assertEqual(result["layout"]["support_count"], 6)
        self.assertEqual(result["layout"]["actual_pitch_mm"], 192.0)
        self.assertEqual(
            result["layout"]["exact_wall_closure"]["reconstructed_wall_length_mm"],
            1000.0,
        )
        self.assertEqual(result["joinery_candidate"]["regular_half_deck_length_mm"], 123.325)
        self.assertEqual(result["joinery_candidate"]["terminal_extension_mm"], 9.9125)
        self.assertEqual(result["joinery_candidate"]["terminal_half_deck_length_mm"], 133.2375)
        self.assertEqual(result["printed_piece_counts"]["kit_articles"], 24)
        self.assertEqual(
            result["printed_piece_counts"]["simultaneously_installed_articles"],
            23,
        )
        self.assertEqual(
            result["printed_piece_counts"]["terminal_integrated_half_decks"], 4
        )
        self.assertEqual(
            result["printed_piece_counts"]["regular_integrated_half_decks"], 6
        )
        self.assertEqual(result["print_start_estimate"]["target_batched_starts"], 18)
        self.assertEqual(result["print_start_estimate"]["safe_unbatched_starts"], 24)
        self.assertEqual(result["hardware_candidate_counts"]["wall_fasteners"], 18)
        self.assertEqual(result["hardware_candidate_counts"]["washers"], 18)

    def test_printer_envelope_and_keepout_collisions_fail_closed(self) -> None:
        cfg = deepcopy(self.config)
        cfg["printer_input"]["build_volume_mm"] = [175.0, 175.0, 180.0]
        cfg["keepout_input"].update(
            {
                "measurement_complete": True,
                "zones": [
                    {
                        "name": "verified outlet service zone",
                        "start_mm": 260.0,
                        "end_mm": 280.0,
                        "clearance_mm": 0.0,
                        "verified": True,
                        "applies_to": ["support"],
                    }
                ],
            }
        )
        result = layout.build_plan(cfg)
        terminal = result["printer_evidence"]["parts"][
            "terminal_integrated_half_deck"
        ]
        self.assertFalse(terminal["fits_declared_build_volume_with_xy_rotation"])
        self.assertEqual(
            result["keepout_evidence"]["collisions"],
            [
                {
                    "zone": "verified outlet service zone",
                    "support_indices": [1],
                    "continuous_shelf_collision": False,
                }
            ],
        )
        self.assertIn(
            "terminal_integrated_half_deck does not fit the declared printer envelope",
            result["release"]["blockers"],
        )

    def test_even_complete_candidate_evidence_cannot_authorize_installation(self) -> None:
        cfg = deepcopy(self.config)
        cfg["project"]["geometry_release_complete"] = True
        cfg["joinery_candidate"].update(
            {
                "overlap_physical_gate_passed": True,
                "integral_bay_local_support_capture_validated": True,
                "gravity_bearing_surfaces_validated": True,
            }
        )
        cfg["piece_contract"].update(
            {
                "wedge_plate_nesting_verified": True,
                "cable_plate_nesting_verified": True,
            }
        )
        cfg["printer_input"].update(
            {
                "actual_saved_mesh_envelopes_verified": True,
                "all_auxiliary_plate_envelopes_verified": True,
            }
        )
        cfg["field_measurement_input"].update(
            {
                "measurement_uncertainty_mm": 0.5,
                "wall_plane_bow_mm": 1.0,
                "endpoint_trim_clearance_mm": 3.0,
                "measurement_instrument": "steel tape and laser cross-check",
                "instrument_resolution_mm": 0.5,
                "measurement_date": "2026-08-11",
                "observer": "field operator",
            }
        )
        cfg["environment_input"].update(
            {
                "maximum_expected_service_temperature_c": 30.0,
                "minimum_expected_service_temperature_c": 15.0,
                "minimum_expected_relative_humidity_percent": 30.0,
                "maximum_expected_relative_humidity_percent": 65.0,
                "measurement_instrument": "temperature-humidity logger",
                "measurement_start_date": "2026-08-04",
                "measurement_end_date": "2026-08-11",
                "direct_sun_exposure_assessed": True,
                "nearby_heat_sources_assessed": True,
                "service_environment_record_complete": True,
            }
        )
        cfg["keepout_input"].update(
            {
                "measurement_complete": True,
                "explicit_no_keepouts_confirmed": True,
            }
        )
        cfg["blocking_input"].update(
            {
                "survey_complete": True,
                "continuous_blocking_confirmed": True,
                "utilities_scan_complete": True,
                "exact_screw_axes_clear_of_utilities": True,
                "wall_substrate_material": "field-recorded substrate",
                "wall_substrate_thickness_mm": 12.7,
                "blocking_material_species_grade": "field-recorded blocking",
                "blocking_thickness_mm": 38.1,
                "blocking_vertical_start_mm": 1550.0,
                "blocking_vertical_end_mm": 1750.0,
                "screw_axis_elevations_mm": [1708.15, 1647.825, 1587.5],
                "segments": [
                    {
                        "start_mm": 0.0,
                        "end_mm": 1555.75,
                        "verified": True,
                    }
                ],
                "exact_fastener_schedule_approved": True,
            }
        )
        result = layout.build_plan(cfg)
        self.assertTrue(result["keepout_evidence"]["candidate_clear"])
        self.assertFalse(result["release"]["print_authorized"])
        self.assertFalse(result["release"]["installation_ready"])
        self.assertFalse(result["release"]["wall_installation_authorized"])
        self.assertFalse(result["release"]["drilling_coordinates_released"])
        self.assertTrue(result["printed_piece_counts"]["count_is_releasable"])
        self.assertEqual(
            result["blocking_evidence"]["candidate_screw_axis_count"], 21
        )
        self.assertEqual(
            result["blocking_evidence"]["required_candidate_screw_axis_count"],
            21,
        )
        with self.assertRaisesRegex(
            layout.InstallationRefused,
            "R11 v1 never releases drilling or installation",
        ):
            layout.build_plan(cfg, request_install=True)

    def test_source_config_cannot_self_authorize_unsafe_release_states(self) -> None:
        unsafe = {
            "qualification_only": False,
            "print_authorized": True,
            "production_ready": True,
            "wall_installation_authorized": True,
            "drilling_coordinates_released": True,
            "test_load_authorized": True,
            "independent_engineering_review_approved": True,
            "physical_load_qualification_passed": True,
            "tested_load_rating_exists": True,
        }
        for key, value in unsafe.items():
            with self.subTest(key=key):
                cfg = deepcopy(self.config)
                cfg["project"][key] = value
                with self.assertRaises(layout.LayoutContractError):
                    layout.build_plan(cfg)
        for key in ("rated_load_kg", "rated_load_lb"):
            with self.subTest(key=key):
                cfg = deepcopy(self.config)
                cfg["project"][key] = 0.001
                with self.assertRaises(layout.LayoutContractError):
                    layout.build_plan(cfg)

    def test_missing_input_is_rejected_instead_of_inferred(self) -> None:
        cfg = deepcopy(self.config)
        del cfg["blocking_input"]["segments"]
        with self.assertRaisesRegex(layout.LayoutContractError, "segments"):
            layout.build_plan(cfg)

    def test_unknown_fields_and_numeric_strings_are_rejected(self) -> None:
        cfg = deepcopy(self.config)
        cfg["project"]["mispelled_authorization"] = False
        with self.assertRaisesRegex(layout.LayoutContractError, "unknown"):
            layout.build_plan(cfg)

    def test_every_config_leaf_rejects_an_obviously_wrong_type(self) -> None:
        mutations: list[tuple[tuple[object, ...], object]] = []

        def collect(value: object, path: tuple[object, ...]) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    collect(child, (*path, key))
                return
            if isinstance(value, list):
                mutations.append((path, {"wrong": "container"}))
                for index, child in enumerate(value):
                    collect(child, (*path, index))
                return
            if isinstance(value, bool):
                replacement: object = "not-a-boolean"
            elif isinstance(value, (int, float)):
                replacement = "not-a-number"
            elif isinstance(value, str):
                replacement = ["not-text"]
            elif value is None:
                replacement = ["not-null-or-expected-value"]
            else:  # pragma: no cover - strict JSON excludes other leaf types
                self.fail(f"unexpected config leaf type at {path}: {type(value)}")
            mutations.append((path, replacement))

        collect(self.config, ())
        self.assertGreater(len(mutations), 80)
        for path, replacement in mutations:
            with self.subTest(path=path):
                cfg = deepcopy(self.config)
                cursor: object = cfg
                for part in path[:-1]:
                    cursor = cursor[part]  # type: ignore[index]
                cursor[path[-1]] = replacement  # type: ignore[index]
                with self.assertRaises(layout.LayoutContractError):
                    layout.build_plan(cfg)
        cfg = deepcopy(self.config)
        cfg["wall_input"]["clear_length_mm"] = "1555.75"
        with self.assertRaisesRegex(layout.LayoutContractError, "finite number"):
            layout.build_plan(cfg)

    def test_json_loader_rejects_duplicate_and_nonfinite_values(self) -> None:
        documents = (
            '{"schema_version": 1, "schema_version": 2}',
            '{"schema_version": NaN}',
            '{"schema_version": Infinity}',
        )
        for document in documents:
            with self.subTest(document=document):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "config.json"
                    path.write_text(document, encoding="utf-8")
                    with self.assertRaises(layout.LayoutContractError):
                        layout.load_config(path)

    def test_zero_field_values_signed_temperatures_and_humidity_are_validated(self) -> None:
        cfg = deepcopy(self.config)
        cfg["field_measurement_input"].update(
            {
                "measurement_uncertainty_mm": 0.0,
                "wall_plane_bow_mm": 0.0,
                "endpoint_trim_clearance_mm": 0.0,
            }
        )
        cfg["environment_input"].update(
            {
                "minimum_expected_service_temperature_c": -5.0,
                "maximum_expected_service_temperature_c": 35.0,
                "minimum_expected_relative_humidity_percent": 0.0,
                "maximum_expected_relative_humidity_percent": 100.0,
            }
        )
        layout.build_plan(cfg)

        reversed_temperature = deepcopy(cfg)
        reversed_temperature["environment_input"].update(
            {
                "minimum_expected_service_temperature_c": 40.0,
                "maximum_expected_service_temperature_c": 20.0,
            }
        )
        with self.assertRaisesRegex(
            layout.LayoutContractError, "minimum service temperature"
        ):
            layout.build_plan(reversed_temperature)

        reversed_humidity = deepcopy(cfg)
        reversed_humidity["environment_input"].update(
            {
                "minimum_expected_relative_humidity_percent": 70.0,
                "maximum_expected_relative_humidity_percent": 30.0,
            }
        )
        with self.assertRaisesRegex(
            layout.LayoutContractError, "minimum relative humidity"
        ):
            layout.build_plan(reversed_humidity)

    def test_all_three_vertical_axes_expand_to_twenty_one_candidate_axes(self) -> None:
        cfg = deepcopy(self.config)
        cfg["blocking_input"]["screw_axis_elevations_mm"] = [1708.15]
        one_axis = layout.build_plan(cfg)
        self.assertIn(
            "exactly three distinct screw-axis elevations are required per support",
            one_axis["release"]["blockers"],
        )
        self.assertEqual(
            one_axis["blocking_evidence"]["candidate_screw_axis_count"], 7
        )

        cfg["blocking_input"]["screw_axis_elevations_mm"] = [
            1708.15,
            1647.825,
            1587.5,
        ]
        three_axes = layout.build_plan(cfg)
        self.assertNotIn(
            "exactly three distinct screw-axis elevations are required per support",
            three_axes["release"]["blockers"],
        )
        self.assertEqual(
            three_axes["blocking_evidence"]["candidate_screw_axis_count"], 21
        )

    def test_pitch_must_leave_a_positive_clear_bay(self) -> None:
        cfg = deepcopy(self.config)
        cfg["wall_input"].update(
            {
                "clear_length_mm": 95.25,
                "support_run_width_mm": 31.75,
                "maximum_bay_pitch_mm": 31.75,
            }
        )
        cfg["field_measurement_input"]["clear_length_samples_mm"] = [95.25, 95.25]
        with self.assertRaisesRegex(layout.LayoutContractError, "positive clear bay"):
            layout.build_plan(cfg)

    def test_bearing_floor_and_overlap_range_are_enforced(self) -> None:
        cfg = deepcopy(self.config)
        cfg["wall_input"]["support_run_width_mm"] = 20.0
        with self.assertRaisesRegex(layout.LayoutContractError, "bearing"):
            layout.build_plan(cfg)
        cfg = deepcopy(self.config)
        cfg["joinery_candidate"]["integrated_reciprocal_overlap_mm"] = 254.0
        with self.assertRaisesRegex(layout.LayoutContractError, "overlap"):
            layout.build_plan(cfg)

    def test_single_bay_layout_is_refused_until_a_two_endpoint_terminal_exists(self) -> None:
        cfg = deepcopy(self.config)
        cfg["wall_input"]["clear_length_mm"] = 200.0
        cfg["field_measurement_input"]["clear_length_samples_mm"] = [200.0, 200.0]
        with self.assertRaisesRegex(
            layout.LayoutContractError, "requires at least two bays"
        ):
            layout.build_plan(cfg)

    def test_frozen_r10_baseline_record_and_executable_hash_check(self) -> None:
        record = json.loads(
            (R11_ROOT / "FROZEN_BASELINES.json").read_text(encoding="utf-8")
        )["baselines"]["r10"]
        self.assertEqual(record["file_count"], 73)
        self.assertEqual(record["byte_count"], 3639668)
        self.assertEqual(
            record["tree_sha256"],
            "8146ceac7d392529cc41ce75fbd01ecf8a160a742843b074f4822d7c62f3b5a2",
        )
        self.assertEqual(
            record["config_sha256"],
            "64aad8eee3bc7bbc7b75f7bb7e77fce94cfd8232d13a77c149b91685e3dcd081",
        )
        self.assertEqual(
            record["source_commit"],
            "9a36df75ac1979193fbd56637c0dfa0aff1ce285",
        )
        self.assertEqual(
            record["git_tree_sha1"],
            "c4989cebcd990011f6255d00fea15060d00c6c85",
        )
        r10_root = R11_ROOT.parent / "r10"
        if r10_root.is_dir():
            self.assertTrue(layout.verify_frozen_r10(r10_root)["verified"])

    def test_cli_is_deterministic(self) -> None:
        command = [sys.executable, "-B", str(R11_ROOT / "layout.py")]
        first = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), json.loads(json.dumps(self.plan)))


if __name__ == "__main__":
    unittest.main()
