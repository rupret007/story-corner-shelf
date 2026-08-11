#!/usr/bin/env python3
"""Measurement, topology, hardware-gate, BOM, and mass tests for R8."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
import math
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


R8 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R8))

from design_math import calculate_run_layout  # noqa: E402
import production_plan as planner  # noqa: E402
from production_plan import (  # noqa: E402
    ARTIFACT_CONFIG_IDENTITY_BLOCKER,
    FROZEN_ARTIFACT_CONFIG_CANONICAL_SHA256,
    FROZEN_CAP_WIDTH_MM,
    FROZEN_REGISTRATION_REMAINING_BOTTOM_SKIN_MM,
    FROZEN_SEAM_MM,
    FROZEN_TERMINAL_INSET_MM,
    GEOMETRY_FEASIBILITY_UNVALIDATED_BLOCKER,
    HardwareEnvelopeInput,
    PlanningBlocked,
    RETAINED_BLANK_RAW_ENVELOPE_MM,
    RETAINED_MODULE_SAVED_ORIENTATION,
    _selected_u_box_seed_volume_mm3,
    _selected_u_box_volume_mm3,
    assess_hardware_envelope,
    build_measurement_driven_plan,
    derive_cassette_print_ceiling,
    derive_minimum_run_plan,
    derive_rail_kit_plate_geometry,
    validate_plate_geometry_proof,
    validate_artifact_coupled_config_identity,
)


CONFIG_PATH = R8 / "config.json"


def approved_hardware() -> HardwareEnvelopeInput:
    return HardwareEnvelopeInput(
        structural_screw_diameter_mm=6.0,
        structural_screw_length_mm=90.0,
        structural_screw_head_diameter_mm=12.0,
        structural_screw_head_height_mm=5.0,
        washer_outer_diameter_mm=18.0,
        washer_inner_diameter_mm=6.4,
        washer_thickness_mm=1.6,
        wall_substrate_thickness_mm=12.7,
        minimum_verified_embedment_mm=50.0,
        pilot_diameter_mm=4.0,
        driver_access_envelope_mm=(24.0, 24.0, 80.0),
        approved_fastener_schedule="QUALIFICATION FIXTURE SCHEDULE QF-01",
        approval_confirmed=True,
    )


class R8ProductionPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def build_nominal(self):
        return build_measurement_driven_plan(
            self.cfg,
            through_clear_length_mm=1514.475,
            return_clear_length_mm=751.275,
            hardware=approved_hardware(),
            framing_confirmed=True,
            framing_confirmation_record="Continuous blocking field record FR-01",
        )

    def test_public_artifact_identity_freezes_every_config_leaf_and_shape(self) -> None:
        self.assertEqual(
            validate_artifact_coupled_config_identity(self.cfg),
            FROZEN_ARTIFACT_CONFIG_CANONICAL_SHA256,
        )

        def leaves(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield from leaves(child, (*path, key))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from leaves(child, (*path, index))
            else:
                yield path, value

        def drift(value):
            if value is None:
                return "RECORDED-DRIFT"
            if isinstance(value, bool):
                return not value
            if isinstance(value, int):
                return value + 1
            if isinstance(value, float):
                return value + 0.125
            if isinstance(value, str):
                return value + " DRIFT"
            raise AssertionError(f"Unhandled JSON leaf: {type(value)!r}")

        for path, original in leaves(self.cfg):
            candidate = deepcopy(self.cfg)
            target = candidate
            for component in path[:-1]:
                target = target[component]
            target[path[-1]] = drift(original)
            with self.subTest(path=".".join(str(item) for item in path)):
                with self.assertRaises(PlanningBlocked) as blocked:
                    validate_artifact_coupled_config_identity(candidate)
                self.assertEqual(
                    blocked.exception.blockers,
                    (ARTIFACT_CONFIG_IDENTITY_BLOCKER,),
                )

        extra = deepcopy(self.cfg)
        extra["unexpected_artifact_field"] = None
        with self.assertRaises(PlanningBlocked):
            validate_artifact_coupled_config_identity(extra)
        missing = deepcopy(self.cfg)
        del missing["qualification"]
        with self.assertRaises(PlanningBlocked):
            validate_artifact_coupled_config_identity(missing)

    def test_printable_ceiling_is_derived_from_a1_process_envelope(self) -> None:
        ceiling = derive_cassette_print_ceiling(self.cfg)
        expected = (
            math.sqrt(2.0)
            * (
                180.0
                - 2.0
                * (
                    self.cfg["printer"]["brim_mm"]
                    + self.cfg["printer"]["brim_object_gap_mm"]
                    + self.cfg["shelf"]["cassette_saved_orientation_candidate"][
                        "edge_reserve_each_side_mm"
                    ]
                )
            )
            - self.cfg["shelf"]["cassette_total_height_mm"]
        )
        self.assertAlmostEqual(
            ceiling.maximum_physical_cassette_width_mm, expected, places=10
        )
        self.assertAlmostEqual(expected, 204.4766086414592, places=10)
        self.assertEqual(ceiling.brim_object_gap_mm, 0.1)
        self.assertTrue(ceiling.fits_build_height)

        changed = deepcopy(self.cfg)
        changed["printer"]["printable_volume_mm"] = [170.0, 170.0, 180.0]
        smaller = derive_cassette_print_ceiling(changed)
        self.assertLess(
            smaller.maximum_physical_cassette_width_mm,
            ceiling.maximum_physical_cassette_width_mm,
        )
        self.assertAlmostEqual(
            ceiling.maximum_physical_cassette_width_mm
            - smaller.maximum_physical_cassette_width_mm,
            10.0 * math.sqrt(2.0),
            places=9,
        )

        zero_gap_cfg = deepcopy(self.cfg)
        zero_gap_cfg["printer"]["brim_object_gap_mm"] = 0.0
        zero_gap = derive_cassette_print_ceiling(zero_gap_cfg)
        self.assertAlmostEqual(
            zero_gap.maximum_physical_cassette_width_mm
            - ceiling.maximum_physical_cassette_width_mm,
            0.2 * math.sqrt(2.0),
            places=10,
        )

    def test_nominal_measurements_rederive_eight_four_modules_and_seam_caps(self) -> None:
        plan = self.build_nominal()
        self.assertEqual(plan.through.layout.cassette_module_count, 8)
        self.assertEqual(plan.through.layout.corbel_count, 9)
        self.assertEqual(plan.return_run.layout.cassette_module_count, 4)
        self.assertEqual(plan.return_run.layout.corbel_count, 5)
        for run in (plan.through, plan.return_run):
            self.assertLessEqual(
                run.longest_physical_cassette_mm,
                plan.print_ceiling.maximum_physical_cassette_width_mm + 1.0e-9,
            )
            self.assertTrue(run.module_count_is_minimum)
            self.assertEqual(
                run.layout.terminal_corbel_center_inset_mm,
                FROZEN_TERMINAL_INSET_MM,
            )
            self.assertEqual(run.layout.corbel_cap_bounds_mm[0], (0.0, 32.0))
            self.assertAlmostEqual(
                run.layout.corbel_cap_bounds_mm[-1][1],
                run.measured_clear_length_mm,
                places=9,
            )
            for index, seam in enumerate(run.layout.seam_centers_mm, start=1):
                cap = run.layout.corbel_cap_bounds_mm[index]
                self.assertAlmostEqual(seam, sum(cap) / 2.0, places=10)
                self.assertAlmostEqual(cap[1] - cap[0], FROZEN_CAP_WIDTH_MM)
            for left, right in zip(
                run.layout.physical_module_bounds_mm,
                run.layout.physical_module_bounds_mm[1:],
            ):
                self.assertAlmostEqual(right[0] - left[1], FROZEN_SEAM_MM)

            if run.layout.cassette_module_count > 1:
                previous = calculate_run_layout(
                    {
                        "id": run.run_id,
                        "nominal_length_mm": run.measured_clear_length_mm,
                        "cassette_module_count": run.layout.cassette_module_count - 1,
                        "corbel_count": run.layout.corbel_count - 1,
                    },
                    seam_mm=FROZEN_SEAM_MM,
                    terminal_inset_mm=FROZEN_TERMINAL_INSET_MM,
                    cap_width_mm=FROZEN_CAP_WIDTH_MM,
                )
                self.assertGreater(
                    max(previous.physical_module_widths_mm),
                    plan.print_ceiling.maximum_physical_cassette_width_mm,
                )

    def test_counts_and_accessory_stations_follow_arbitrary_measurements(self) -> None:
        plan = build_measurement_driven_plan(
            self.cfg,
            through_clear_length_mm=2100.0,
            return_clear_length_mm=1050.0,
            hardware=approved_hardware(),
            framing_confirmed=True,
            framing_confirmation_record="Continuous blocking field record FR-02",
        )
        ceiling = plan.print_ceiling
        through = plan.through
        return_run = plan.return_run
        self.assertNotEqual(through.layout.corbel_count, 9)
        self.assertNotEqual(return_run.layout.corbel_count, 5)
        for run in (through, return_run):
            expected_eligible = tuple(range(1, run.layout.corbel_count - 1))
            self.assertEqual(run.accessory_eligible_support_indices, expected_eligible)
            self.assertEqual(
                run.accessory_default_alternating_support_indices,
                expected_eligible[::2],
            )
            self.assertNotIn(0, run.accessory_eligible_support_indices)
            self.assertNotIn(
                run.layout.corbel_count - 1,
                run.accessory_eligible_support_indices,
            )
            self.assertLessEqual(
                max(run.layout.physical_module_widths_mm),
                ceiling.maximum_physical_cassette_width_mm + 1.0e-9,
            )
        derived_rail_count = sum(
            len(run.accessory_default_alternating_support_indices)
            for run in (through, return_run)
        ) * plan.level_count
        rail_recipe = next(
            item
            for item in plan.plate_recipes
            if item.recipe_id == "one_default_rail_kit_per_plate"
        )
        self.assertNotEqual(derived_rail_count, 12)
        self.assertEqual(rail_recipe.plate_count, derived_rail_count)

    def test_penultimate_support_variant_follows_alternating_station_parity(self) -> None:
        plan = build_measurement_driven_plan(
            self.cfg,
            through_clear_length_mm=500.0,
            return_clear_length_mm=500.0,
            hardware=approved_hardware(),
            framing_confirmed=True,
            framing_confirmation_record="Continuous blocking field record FR-05",
        )
        self.assertEqual(plan.through.layout.cassette_module_count, 3)
        self.assertEqual(plan.return_run.layout.cassette_module_count, 3)
        topology = plan.support_topology
        self.assertEqual(topology.clean_one_key_terminal_start_count, 4)
        self.assertEqual(topology.clean_one_key_terminal_end_count, 4)
        self.assertEqual(topology.clean_one_key_terminal_count, 8)
        self.assertEqual(topology.smooth_interior_one_keeper_count, 0)
        self.assertEqual(topology.bossed_interior_one_keeper_count, 4)
        self.assertEqual(topology.smooth_penultimate_two_keeper_count, 4)
        self.assertEqual(topology.bossed_penultimate_two_keeper_count, 0)
        self.assertEqual(topology.total_support_count, 16)
        self.assertEqual(topology.total_integral_keeper_count, 12)
        self.assertEqual(
            topology.penultimate_station_by_run,
            (("through", 2, False), ("return", 2, False)),
        )
        items = {item.item_id: item.quantity for item in plan.bom}
        self.assertEqual(
            items["smooth_penultimate_two_keeper_d_frame_corbel"], 4
        )
        self.assertEqual(
            items["bossed_penultimate_two_keeper_d_frame_corbel"], 0
        )

    def test_single_module_run_is_blocked_until_retention_is_authored(self) -> None:
        ceiling = derive_cassette_print_ceiling(self.cfg)
        with self.assertRaises(PlanningBlocked) as direct:
            derive_minimum_run_plan(
                "short",
                100.0,
                cassette_ceiling_mm=(
                    ceiling.maximum_physical_cassette_width_mm
                ),
            )
        blocker = "retention.single_module_run_requires_unauthored_terminal_keeper"
        self.assertIn(blocker, direct.exception.blockers)

        with self.assertRaises(PlanningBlocked) as complete:
            build_measurement_driven_plan(
                self.cfg,
                through_clear_length_mm=100.0,
                return_clear_length_mm=500.0,
                hardware=approved_hardware(),
                framing_confirmed=True,
                framing_confirmation_record="Continuous blocking field record FR-06",
            )
        self.assertIn(blocker, complete.exception.blockers)

    def test_hardware_api_suppresses_bore_inputs_until_every_gate_is_complete(self) -> None:
        partial = assess_hardware_envelope(
            HardwareEnvelopeInput(structural_screw_diameter_mm=6.0),
            framing_confirmed=False,
            framing_confirmation_record=None,
        )
        self.assertFalse(partial.inputs_complete_for_geometry_study)
        self.assertFalse(partial.geometric_fit_validated)
        self.assertFalse(partial.ready_for_wall_bore_authoring)
        self.assertIsNone(partial.wall_bore_input_envelope)
        self.assertFalse(partial.wall_bore_geometry_emitted)
        self.assertIn("hardware.structural_screw_length_mm.missing", partial.blockers)
        self.assertIn(
            "framing.continuous_blocking_or_verified_equivalent_unconfirmed",
            partial.blockers,
        )

        complete = assess_hardware_envelope(
            approved_hardware(),
            framing_confirmed=True,
            framing_confirmation_record="Continuous blocking field record FR-01",
        )
        self.assertEqual(complete.blockers, ())
        self.assertTrue(complete.inputs_complete_for_geometry_study)
        self.assertFalse(complete.geometric_fit_validated)
        self.assertFalse(complete.ready_for_wall_bore_authoring)
        self.assertIsNotNone(complete.wall_bore_input_envelope)
        self.assertEqual(complete.wall_bore_input_envelope.pilot_diameter_mm, 4.0)
        self.assertEqual(
            complete.wall_bore_input_envelope.driver_access_envelope_mm,
            (24.0, 24.0, 80.0),
        )
        self.assertEqual(complete.wall_bore_input_envelope.printed_wall_chord_mm, 16.0)
        self.assertEqual(
            complete.wall_bore_input_envelope.minimum_required_screw_length_mm,
            80.3,
        )
        self.assertEqual(
            complete.wall_bore_input_envelope.minimum_driver_cross_section_mm,
            18.0,
        )
        self.assertEqual(
            complete.wall_bore_input_envelope.driver_required_approach_beyond_head_mm,
            18.0,
        )
        self.assertEqual(
            complete.wall_bore_input_envelope.minimum_driver_axial_length_mm,
            23.0,
        )
        self.assertFalse(complete.wall_bore_input_envelope.geometric_fit_validated)
        self.assertFalse(complete.wall_bore_input_envelope.geometry_emitted)
        self.assertEqual(
            complete.geometry_feasibility_release_blockers,
            (GEOMETRY_FEASIBILITY_UNVALIDATED_BLOCKER,),
        )
        self.assertFalse(complete.wall_bore_geometry_emitted)

    def test_hardware_stack_and_washer_ordering_fail_closed(self) -> None:
        common = {
            "framing_confirmed": True,
            "framing_confirmation_record": "Continuous blocking field record FR-03",
        }
        too_short = replace(
            approved_hardware(),
            structural_screw_length_mm=51.0,
            minimum_verified_embedment_mm=50.0,
        )
        short_assessment = assess_hardware_envelope(too_short, **common)
        self.assertIn(
            "hardware.screw_length_below_embedment_plus_wall_chord_washer_and_substrate",
            short_assessment.blockers,
        )
        self.assertFalse(short_assessment.ready_for_wall_bore_authoring)
        self.assertIsNone(short_assessment.wall_bore_input_envelope)
        self.assertFalse(short_assessment.wall_bore_geometry_emitted)

        missing_substrate = replace(
            approved_hardware(),
            wall_substrate_thickness_mm=None,
        )
        missing_assessment = assess_hardware_envelope(missing_substrate, **common)
        self.assertIn(
            "hardware.wall_substrate_thickness_mm.missing",
            missing_assessment.blockers,
        )
        self.assertFalse(missing_assessment.ready_for_wall_bore_authoring)
        self.assertIsNone(missing_assessment.wall_bore_input_envelope)

        invalid_substrate = replace(
            approved_hardware(),
            wall_substrate_thickness_mm=0.0,
        )
        invalid_assessment = assess_hardware_envelope(invalid_substrate, **common)
        self.assertIn(
            "hardware.wall_substrate_thickness_mm.must_be_positive_finite",
            invalid_assessment.blockers,
        )
        self.assertFalse(invalid_assessment.ready_for_wall_bore_authoring)

        pass_through_washer = replace(
            approved_hardware(),
            washer_inner_diameter_mm=12.0,
        )
        washer_assessment = assess_hardware_envelope(pass_through_washer, **common)
        self.assertIn(
            "hardware.washer_inner_diameter_must_be_smaller_than_screw_head",
            washer_assessment.blockers,
        )
        self.assertFalse(washer_assessment.ready_for_wall_bore_authoring)
        self.assertIsNone(washer_assessment.wall_bore_input_envelope)

        exact_stack = replace(
            approved_hardware(),
            structural_screw_length_mm=80.3,
        )
        exact_assessment = assess_hardware_envelope(exact_stack, **common)
        self.assertEqual(exact_assessment.blockers, ())
        self.assertTrue(exact_assessment.inputs_complete_for_geometry_study)
        self.assertFalse(exact_assessment.geometric_fit_validated)
        self.assertFalse(exact_assessment.ready_for_wall_bore_authoring)
        self.assertEqual(
            exact_assessment.wall_bore_input_envelope.minimum_required_screw_length_mm,
            80.3,
        )
        self.assertFalse(exact_assessment.wall_bore_geometry_emitted)

        exact_driver_boundary = replace(
            approved_hardware(),
            driver_access_envelope_mm=(18.0, 18.0, 23.0),
        )
        driver_boundary_assessment = assess_hardware_envelope(
            exact_driver_boundary, **common
        )
        self.assertEqual(driver_boundary_assessment.blockers, ())
        self.assertTrue(
            driver_boundary_assessment.inputs_complete_for_geometry_study
        )
        self.assertFalse(driver_boundary_assessment.ready_for_wall_bore_authoring)

        impossible_driver = replace(
            approved_hardware(),
            structural_screw_length_mm=100.0,
            structural_screw_head_diameter_mm=120.0,
            washer_outer_diameter_mm=130.0,
            driver_access_envelope_mm=(0.1, 0.1, 0.1),
        )
        impossible_assessment = assess_hardware_envelope(
            impossible_driver, **common
        )
        self.assertIn(
            "hardware.driver_access_cross_section_below_head_or_washer",
            impossible_assessment.blockers,
        )
        self.assertIn(
            "hardware.driver_access_axial_below_head_plus_required_approach",
            impossible_assessment.blockers,
        )
        self.assertFalse(impossible_assessment.inputs_complete_for_geometry_study)
        self.assertFalse(impossible_assessment.geometric_fit_validated)
        self.assertFalse(impossible_assessment.ready_for_wall_bore_authoring)
        self.assertIsNone(impossible_assessment.wall_bore_input_envelope)

    def test_plan_fails_closed_on_measurement_hardware_or_framing_uncertainty(self) -> None:
        common = dict(
            cfg=self.cfg,
            through_clear_length_mm=1514.475,
            return_clear_length_mm=751.275,
            hardware=approved_hardware(),
            framing_confirmed=True,
            framing_confirmation_record="Continuous blocking field record FR-01",
        )
        for bad in (None, math.nan, math.inf, -1.0, True):
            args = dict(common)
            args["through_clear_length_mm"] = bad
            with self.assertRaises(PlanningBlocked):
                build_measurement_driven_plan(**args)

        args = dict(common)
        args["hardware"] = HardwareEnvelopeInput()
        with self.assertRaises(PlanningBlocked) as missing_hardware:
            build_measurement_driven_plan(**args)
        self.assertIn(
            "hardware.structural_screw_diameter_mm.missing",
            missing_hardware.exception.blockers,
        )

        args = dict(common)
        args["framing_confirmed"] = False
        with self.assertRaises(PlanningBlocked) as missing_framing:
            build_measurement_driven_plan(**args)
        self.assertIn(
            "framing.continuous_blocking_or_verified_equivalent_unconfirmed",
            missing_framing.exception.blockers,
        )

        invalid = approved_hardware()
        invalid = HardwareEnvelopeInput(
            **{
                **invalid.__dict__,
                "pilot_diameter_mm": invalid.structural_screw_diameter_mm,
            }
        )
        args = dict(common)
        args["hardware"] = invalid
        with self.assertRaises(PlanningBlocked) as bad_pilot:
            build_measurement_driven_plan(**args)
        self.assertIn(
            "hardware.pilot_diameter_must_be_smaller_than_screw",
            bad_pilot.exception.blockers,
        )

    def test_petg_only_contract_rejects_any_pla_or_filament_drift(self) -> None:
        mutations = (
            (
                ("material", "printed_material"),
                "PLA",
                "material.printed_material_must_be_petg_only",
            ),
            (
                ("material", "primary_part_material"),
                "PLA",
                "material.primary_part_material_must_be_petg",
            ),
            (
                ("material", "pla_allowed_in_primary_or_load_path_parts"),
                True,
                "material.pla_in_primary_or_load_path_must_remain_prohibited",
            ),
            (
                ("printer", "filament_product"),
                "PLA",
                "printer.filament_product_must_be_petg",
            ),
            (
                ("printer", "filament_preset"),
                "Generic PLA",
                "printer.filament_preset_must_be_petg",
            ),
        )
        for path, value, blocker in mutations:
            cfg = deepcopy(self.cfg)
            cfg[path[0]][path[1]] = value
            with self.subTest(path=path, value=value):
                with self.assertRaises(PlanningBlocked) as blocked:
                    build_measurement_driven_plan(
                        cfg,
                        through_clear_length_mm=1514.475,
                        return_clear_length_mm=751.275,
                        hardware=approved_hardware(),
                        framing_confirmed=True,
                        framing_confirmation_record=(
                            "Continuous blocking material record FR-07"
                        ),
                    )
                self.assertIn(blocker, blocked.exception.blockers)

        combined = deepcopy(self.cfg)
        combined["material"]["printed_material"] = "PLA"
        combined["material"]["pla_allowed_in_primary_or_load_path_parts"] = True
        combined["printer"]["filament_product"] = "PLA"
        with self.assertRaises(PlanningBlocked) as blocked:
            build_measurement_driven_plan(
                combined,
                through_clear_length_mm=1514.475,
                return_clear_length_mm=751.275,
                hardware=approved_hardware(),
                framing_confirmed=True,
                framing_confirmation_record="Continuous blocking record FR-08",
            )
        self.assertGreaterEqual(len(blocked.exception.blockers), 3)

    def test_declared_safety_flags_and_zero_ratings_are_type_strict(self) -> None:
        mutations = (
            (
                ("project", "physical_qualification_complete"),
                True,
                "project.physical_qualification_complete_must_remain_false",
            ),
            (
                ("shelf", "selected_cassette_physical_qualification_complete"),
                True,
                (
                    "shelf.selected_cassette_physical_qualification_complete_"
                    "must_remain_false"
                ),
            ),
            (
                (
                    "shelf",
                    "cassette_saved_orientation_candidate",
                    "software_envelope_proven",
                ),
                False,
                (
                    "shelf.cassette_saved_orientation_candidate."
                    "software_envelope_proven_must_remain_true"
                ),
            ),
            (
                (
                    "shelf",
                    "cassette_saved_orientation_candidate",
                    "physical_printability_qualified",
                ),
                True,
                (
                    "shelf.cassette_saved_orientation_candidate."
                    "physical_printability_qualified_must_remain_false"
                ),
            ),
            (
                ("d_frame", "structural_capacity_credit_allowed"),
                True,
                "d_frame.structural_capacity_credit_allowed_must_remain_false",
            ),
            (
                ("material", "structural_credit_from_accessories_allowed"),
                True,
                "material.structural_credit_from_accessories_allowed_must_remain_false",
            ),
            (
                ("material", "printed_wall_anchors_allowed"),
                True,
                "material.printed_wall_anchors_allowed_must_remain_false",
            ),
            (
                (
                    "material",
                    "hollow_wall_anchors_allowed_in_primary_load_path",
                ),
                True,
                (
                    "material.hollow_wall_anchors_allowed_in_primary_load_path_"
                    "must_remain_false"
                ),
            ),
            (
                (
                    "wall_attachment",
                    "continuous_blocking_or_verified_equivalent_required",
                ),
                False,
                (
                    "wall_attachment."
                    "continuous_blocking_or_verified_equivalent_required"
                ),
            ),
            (
                (
                    "wall_attachment",
                    "printed_fastener_or_anchor_substitution_allowed",
                ),
                True,
                (
                    "wall_attachment."
                    "printed_fastener_or_anchor_substitution_must_remain_false"
                ),
            ),
            (
                ("accessory_system", "structural_or_shelf_load_credit"),
                True,
                (
                    "accessory_system."
                    "structural_or_shelf_load_credit_must_remain_false"
                ),
            ),
            (
                ("project", "rated_load_kg"),
                False,
                "project.rated_load_kg_must_remain_zero",
            ),
            (
                ("project", "rated_load_lb"),
                "0",
                "project.rated_load_lb_must_remain_zero",
            ),
            (
                ("accessory_system", "rated_load_kg"),
                False,
                "accessory_system.rated_load_kg_must_remain_zero",
            ),
            (
                ("accessory_system", "rated_load_lb"),
                "0",
                "accessory_system.rated_load_lb_must_remain_zero",
            ),
        )
        for path, value, blocker in mutations:
            cfg = deepcopy(self.cfg)
            target = cfg
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path, value=value):
                with self.assertRaises(PlanningBlocked) as blocked:
                    build_measurement_driven_plan(
                        cfg,
                        through_clear_length_mm=1514.475,
                        return_clear_length_mm=751.275,
                        hardware=approved_hardware(),
                        framing_confirmed=True,
                        framing_confirmation_record=(
                            "Continuous blocking scope record FR-09"
                        ),
                    )
                self.assertIn(blocker, blocked.exception.blockers)

        integer_zero = deepcopy(self.cfg)
        for section in ("project", "accessory_system"):
            integer_zero[section]["rated_load_kg"] = 0
            integer_zero[section]["rated_load_lb"] = 0
        with self.assertRaises(PlanningBlocked) as exact_type_blocked:
            build_measurement_driven_plan(
                integer_zero,
                through_clear_length_mm=1514.475,
                return_clear_length_mm=751.275,
                hardware=approved_hardware(),
                framing_confirmed=True,
                framing_confirmation_record="Continuous blocking scope record FR-10",
            )
        self.assertIn(
            ARTIFACT_CONFIG_IDENTITY_BLOCKER,
            exact_type_blocked.exception.blockers,
        )

    def test_canonical_cad_coupled_config_drift_is_rejected(self) -> None:
        mutations = (
            (("printer", "manufacturer"), "Other"),
            (("printer", "model"), "A1"),
            (("printer", "printable_volume_mm"), [256.0, 256.0, 256.0]),
            (("printer", "nozzle_mm"), 0.6),
            (("shelf", "selected_level_count"), 3),
            (("shelf", "depth_mm"), 153.0),
            (("shelf", "cassette_total_height_mm"), 31.0),
            (("shelf", "selected_cassette_candidate"), "other"),
            (
                ("shelf", "selected_cassette_geometry_mm", "top_skin"),
                3.3,
            ),
            (
                ("shelf", "selected_cassette_geometry_mm", "bottom_skin"),
                2.5,
            ),
            (
                (
                    "shelf",
                    "selected_cassette_geometry_mm",
                    "visible_front_wall",
                ),
                4.1,
            ),
            (
                (
                    "shelf",
                    "selected_cassette_geometry_mm",
                    "full_depth_end_land",
                ),
                6.5,
            ),
            (
                ("shelf", "selected_cassette_geometry_mm", "internal_web"),
                2.5,
            ),
            (
                (
                    "shelf",
                    "selected_cassette_geometry_mm",
                    "internal_web_count",
                ),
                4,
            ),
            (("d_frame", "prototype_envelope_mm"), [152.4, 160.0, 31.0]),
            (("d_frame", "wall_chord_mm"), 15.0),
            (("d_frame", "curved_web_mm"), 15.0),
            (("accessory_system", "rail_envelope_mm"), [40.0, 90.0, 9.0]),
            (
                (
                    "accessory_system",
                    "rail_installed_lower_edge_mm_above_corbel_bottom",
                ),
                49.0,
            ),
            (("accessory_system", "module_service_lift_mm"), 9.0),
            (("accessory_system", "rail_service_lift_mm"), 5.0),
            (("accessory_system", "nominal_clearance_per_face_mm"), 0.5),
            (("accessory_system", "latch_comparison_strain_proxy"), 0.025),
            (
                ("accessory_system", "clearance_ladder_per_face_mm"),
                [0.2, 0.3, 0.4, 0.6],
            ),
            (("accessory_system", "positive_release_latch_authored"), False),
            (
                ("accessory_system", "default_equipped_station_indices"),
                {"through": [2, 4], "return": [2]},
            ),
            (
                ("accessory_system", "available_modules"),
                [
                    "blank",
                    "single cable peg",
                    "three-position cable comb",
                    "cable coil hook",
                    "unpriced giant hook",
                ],
            ),
        )
        for path, value in mutations:
            cfg = deepcopy(self.cfg)
            target = cfg
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path, value=value):
                with self.assertRaises(PlanningBlocked):
                    build_measurement_driven_plan(
                        cfg,
                        through_clear_length_mm=1514.475,
                        return_clear_length_mm=751.275,
                        hardware=approved_hardware(),
                        framing_confirmed=True,
                        framing_confirmation_record=(
                            "Continuous blocking artifact record FR-11"
                        ),
                    )

        coordinated_socket_drift = deepcopy(self.cfg)
        coordinated_socket_drift["accessory_system"][
            "sockets_per_eligible_corbel"
        ] = 2
        coordinated_socket_drift["accessory_system"][
            "socket_centers_from_rail_bottom_mm"
        ] = [20.0, 46.0]
        with self.assertRaises(PlanningBlocked) as blocked:
            build_measurement_driven_plan(
                coordinated_socket_drift,
                through_clear_length_mm=1514.475,
                return_clear_length_mm=751.275,
                hardware=approved_hardware(),
                framing_confirmed=True,
                framing_confirmation_record="Continuous blocking record FR-12",
            )
        self.assertIn(
            "accessory_system.sockets_per_eligible_corbel_must_equal_3",
            blocked.exception.blockers,
        )
        self.assertIn(
            "accessory_system.socket_centers_must_match_canonical",
            blocked.exception.blockers,
        )

    def test_bom_plate_count_and_mass_are_derived_from_topology(self) -> None:
        plan = self.build_nominal()
        items = {item.item_id: item for item in plan.bom}
        eligible = sum(
            len(run.accessory_eligible_support_indices)
            for run in (plan.through, plan.return_run)
        ) * plan.level_count
        default_equipped = sum(
            len(run.accessory_default_alternating_support_indices)
            for run in (plan.through, plan.return_run)
        ) * plan.level_count
        self.assertEqual(eligible, 20)
        self.assertEqual(default_equipped, 12)
        self.assertEqual(
            items["clean_one_key_terminal_start_d_frame_corbel"].quantity, 4
        )
        self.assertEqual(
            items["clean_one_key_terminal_end_d_frame_corbel"].quantity, 4
        )
        self.assertEqual(
            items["smooth_interior_one_keeper_d_frame_corbel"].quantity, 8
        )
        self.assertEqual(
            items["bossed_interior_one_keeper_d_frame_corbel"].quantity, 8
        )
        self.assertEqual(
            items["smooth_penultimate_two_keeper_d_frame_corbel"].quantity, 0
        )
        self.assertEqual(
            items["bossed_penultimate_two_keeper_d_frame_corbel"].quantity, 4
        )
        support_ids = (
            "clean_one_key_terminal_start_d_frame_corbel",
            "clean_one_key_terminal_end_d_frame_corbel",
            "smooth_interior_one_keeper_d_frame_corbel",
            "bossed_interior_one_keeper_d_frame_corbel",
            "smooth_penultimate_two_keeper_d_frame_corbel",
            "bossed_penultimate_two_keeper_d_frame_corbel",
        )
        self.assertEqual(sum(items[item].quantity for item in support_ids), 28)
        self.assertTrue(
            all(items[item].nominal_unit_solid_volume_mm3 is None for item in support_ids)
        )
        self.assertTrue(
            all(
                items[item].nominal_total_solid_volume_mm3 is None
                for item in support_ids
            )
        )
        self.assertEqual(items["selected_front_first_u_box_cassette"].quantity, 24)
        self.assertEqual(items["mounted_retention_rail"].quantity, 12)
        self.assertEqual(items["retained_socket_blank"].quantity, 36)
        self.assertIsNone(
            items["mounted_retention_rail"].nominal_unit_solid_volume_mm3
        )
        self.assertIsNone(
            items["mounted_retention_rail"].nominal_total_solid_volume_mm3
        )
        self.assertFalse(
            items["mounted_retention_rail"].included_in_petg_mass_budget
        )
        self.assertIsNone(
            items["retained_socket_blank"].nominal_unit_solid_volume_mm3
        )
        self.assertIsNone(
            items["retained_socket_blank"].nominal_total_solid_volume_mm3
        )
        self.assertFalse(
            items["retained_socket_blank"].included_in_petg_mass_budget
        )
        self.assertEqual(items["approved_metal_structural_screw"].quantity, 84)
        self.assertEqual(items["approved_metal_washer"].quantity, 84)
        self.assertEqual(plan.support_topology.total_support_count, 28)
        self.assertEqual(
            plan.support_topology.clean_one_key_terminal_start_count, 4
        )
        self.assertEqual(
            plan.support_topology.clean_one_key_terminal_end_count, 4
        )
        self.assertEqual(plan.support_topology.clean_one_key_terminal_count, 8)
        self.assertEqual(plan.support_topology.total_integral_keeper_count, 24)
        self.assertEqual(
            plan.support_topology.penultimate_station_by_run,
            (("through", 7, True), ("return", 3, True)),
        )
        self.assertEqual(plan.nominal_plate_count, 28 + 24 + 12)
        self.assertEqual(
            plan.nominal_plate_count,
            sum(recipe.plate_count for recipe in plan.plate_recipes),
        )

        included_volume = sum(
            item.nominal_total_solid_volume_mm3 or 0.0
            for item in plan.bom
            if item.included_in_petg_mass_budget
        )
        self.assertAlmostEqual(
            included_volume,
            plan.mass_budget.known_registered_cassette_volume_mm3,
            places=5,
        )
        self.assertAlmostEqual(
            plan.mass_budget.known_registered_cassette_mass_g,
            included_volume * 1.27 / 1000.0,
            places=7,
        )
        self.assertIsNone(
            plan.mass_budget.known_non_support_blank_configuration_volume_mm3
        )
        self.assertIsNone(
            plan.mass_budget.known_non_support_blank_configuration_mass_g
        )
        self.assertIsNone(
            plan.mass_budget.known_non_support_maximum_populated_volume_mm3
        )
        self.assertIsNone(
            plan.mass_budget.known_non_support_maximum_populated_mass_g
        )
        self.assertTrue(plan.mass_budget.support_reference_volumes_pending)
        self.assertTrue(
            plan.mass_budget.rail_and_accessory_reference_volumes_pending
        )
        self.assertIsNone(plan.mass_budget.base_blank_configuration_volume_mm3)
        self.assertIsNone(plan.mass_budget.base_blank_configuration_mass_g)
        self.assertIsNone(
            plan.mass_budget.maximum_populated_configuration_volume_mm3
        )
        self.assertIsNone(plan.mass_budget.maximum_populated_configuration_mass_g)
        self.assertIsNone(plan.mass_budget.maximum_volume_accessory_kind)
        self.assertIn(
            "qualification-v1",
            plan.mass_budget.rail_and_accessory_reference_volume_basis,
        )
        self.assertIn(
            "pending",
            plan.mass_budget.rail_and_accessory_reference_volume_basis,
        )
        self.assertFalse(plan.mass_budget.hardware_mass_included)
        self.assertTrue(plan.mass_budget.slicer_filament_mass_required_for_purchasing)
        self.assertIn("quarantined", plan.mass_budget.caveat)

    def test_protected_v1_rail_and_accessory_mass_refs_are_quarantined(self) -> None:
        references = planner._cad_reference_volumes()
        self.assertIsNone(references.retention_rail_mm3)
        self.assertEqual(
            references.retained_accessory_mm3,
            (
                ("blank", None),
                ("single_peg", None),
                ("three_cable_comb", None),
                ("coil_j_hook", None),
            ),
        )

        source = Path(planner.__file__).read_text(encoding="utf-8")
        protected_v1_values = (
            "23414.352125",
            "1568.039940",
            "2475.338640",
            "3827.549078",
            "3634.958659",
        )
        for stale_value in protected_v1_values:
            with self.subTest(stale_value=stale_value):
                self.assertNotIn(stale_value, source)

    def test_complete_support_refs_reconcile_bom_and_base_mass_budget(self) -> None:
        complete_refs = planner._CadReferenceVolumes(
            clean_one_key_terminal_start_d_frame_mm3=100.0,
            clean_one_key_terminal_end_d_frame_mm3=101.0,
            smooth_interior_one_keeper_d_frame_mm3=102.0,
            bossed_interior_one_keeper_d_frame_mm3=103.0,
            smooth_penultimate_two_keeper_d_frame_mm3=104.0,
            bossed_penultimate_two_keeper_d_frame_mm3=105.0,
            retention_rail_mm3=200.0,
            retained_accessory_mm3=(
                ("blank", 10.0),
                ("single_peg", 11.0),
                ("three_cable_comb", 13.0),
                ("coil_j_hook", 12.0),
            ),
        )
        with patch.object(
            planner, "_cad_reference_volumes", return_value=complete_refs
        ):
            plan = self.build_nominal()
        self.assertFalse(plan.mass_budget.support_reference_volumes_pending)
        self.assertFalse(
            plan.mass_budget.rail_and_accessory_reference_volumes_pending
        )
        self.assertIsNotNone(plan.mass_budget.base_blank_configuration_volume_mm3)
        support_items = tuple(
            item
            for item in plan.bom
            if "d_frame_corbel" in item.item_id
        )
        self.assertEqual(len(support_items), 6)
        self.assertTrue(
            all(item.included_in_petg_mass_budget for item in support_items)
        )
        self.assertTrue(
            all(item.nominal_total_solid_volume_mm3 is not None for item in support_items)
        )
        self.assertTrue(all("pending" not in item.note.lower() for item in support_items))
        included_volume = sum(
            item.nominal_total_solid_volume_mm3 or 0.0
            for item in plan.bom
            if item.included_in_petg_mass_budget
        )
        self.assertAlmostEqual(
            included_volume,
            plan.mass_budget.base_blank_configuration_volume_mm3,
            places=7,
        )
        self.assertIn("All versioned canonical", plan.mass_budget.caveat)

        invalid_refs = replace(
            complete_refs,
            smooth_interior_one_keeper_d_frame_mm3=0.0,
        )
        with patch.object(
            planner, "_cad_reference_volumes", return_value=invalid_refs
        ):
            with self.assertRaisesRegex(ValueError, "support volume references"):
                self.build_nominal()

    def test_rail_kit_plate_has_exact_coordinate_and_brim_gap_proof(self) -> None:
        plan = self.build_nominal()
        recipe = next(
            item
            for item in plan.plate_recipes
            if item.recipe_id == "one_default_rail_kit_per_plate"
        )
        proof = recipe.geometry_proof
        self.assertIsNotNone(proof)
        validate_plate_geometry_proof(proof)
        self.assertEqual(proof.printable_volume_mm, (180.0, 180.0, 180.0))
        self.assertEqual(proof.brim_each_side_mm, 5.0)
        self.assertEqual(proof.brim_object_gap_mm, 0.1)
        self.assertEqual(proof.edge_reserve_each_side_mm, 2.0)
        self.assertEqual(proof.minimum_brim_to_brim_gap_mm, 2.0)
        self.assertEqual(proof.complete_kit_count, 1)
        self.assertEqual(proof.retained_blank_count_per_kit, 3)
        self.assertTrue(proof.geometry_proven)
        self.assertTrue(proof.all_placements_contained)
        self.assertTrue(proof.all_build_heights_contained)
        self.assertTrue(proof.all_pairwise_gaps_satisfied)
        self.assertEqual(len(proof.pairwise_brim_gaps_mm), 6)
        self.assertAlmostEqual(
            proof.minimum_observed_brim_to_brim_gap_mm, 2.0, places=12
        )

        rail, *blanks = proof.placements
        self.assertEqual(rail.raw_envelope_mm, (36.0, 88.0, 8.8))
        self.assertFalse(rail.support_required)
        self.assertEqual(rail.brim_footprint_mm, (46.2, 98.2))
        self.assertEqual(rail.brim_bounds_mm, (2.0, 2.0, 48.2, 100.2))
        expected_blank_bounds = (
            (50.2, 2.0, 82.8, 23.9),
            (50.2, 25.9, 82.8, 47.8),
            (50.2, 49.8, 82.8, 71.7),
        )
        self.assertEqual(
            RETAINED_MODULE_SAVED_ORIENTATION,
            "local_xy_bed_local_negative_z_build",
        )
        for blank, expected_bounds in zip(blanks, expected_blank_bounds):
            self.assertEqual(blank.saved_orientation, RETAINED_MODULE_SAVED_ORIENTATION)
            self.assertFalse(blank.support_required)
            self.assertEqual(blank.raw_envelope_mm, RETAINED_BLANK_RAW_ENVELOPE_MM)
            for observed, expected in zip(
                blank.brim_footprint_mm, (32.6, 21.9)
            ):
                self.assertAlmostEqual(observed, expected, places=12)
            for observed, expected in zip(blank.brim_bounds_mm, expected_bounds):
                self.assertAlmostEqual(observed, expected, places=12)

        rail_quantity = next(
            item.quantity
            for item in plan.bom
            if item.item_id == "mounted_retention_rail"
        )
        expected_plate_count = -(-rail_quantity // proof.complete_kit_count)
        self.assertEqual(recipe.plate_count, expected_plate_count)

    def test_rail_kit_plate_proof_fails_closed_under_geometry_mutations(self) -> None:
        proof = derive_rail_kit_plate_geometry(self.cfg)
        moved_blank = replace(
            proof.placements[1],
            brim_bounds_mm=(47.0, 2.0, 79.6, 23.9),
        )
        overlapping = replace(
            proof,
            placements=(proof.placements[0], moved_blank, *proof.placements[2:]),
        )
        with self.assertRaisesRegex(ValueError, "brim_to_brim_gap"):
            validate_plate_geometry_proof(overlapping)

        outside_bed = replace(proof, printable_volume_mm=(80.0, 180.0, 180.0))
        with self.assertRaisesRegex(ValueError, "outside_edge_reserve"):
            validate_plate_geometry_proof(outside_bed)

        stale_orientation = replace(
            proof.placements[1], saved_orientation="local_xz_bed_local_y_build"
        )
        wrong_orientation = replace(
            proof,
            placements=(
                proof.placements[0],
                stale_orientation,
                *proof.placements[2:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "saved_orientation_mismatch"):
            validate_plate_geometry_proof(wrong_orientation)

        wrong_support_class = replace(
            proof.placements[1], support_required=True
        )
        wrong_support_proof = replace(
            proof,
            placements=(
                proof.placements[0],
                wrong_support_class,
                *proof.placements[2:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "support_classification_mismatch"):
            validate_plate_geometry_proof(wrong_support_proof)

        mutations = (
            (("printer", "printable_volume_mm"), [80.0, 180.0, 180.0]),
            (("printer", "minimum_brim_to_brim_gap_mm"), 100.0),
            (("printer", "brim_mm"), math.nan),
            (("printer", "brim_object_gap_mm"), -0.1),
            (("accessory_system", "rail_envelope_mm"), [170.0, 88.0, 8.8]),
            (("accessory_system", "sockets_per_eligible_corbel"), 4),
        )
        for path, value in mutations:
            cfg = deepcopy(self.cfg)
            cfg[path[0]][path[1]] = value
            with self.subTest(path=path, value=value):
                with self.assertRaises(ValueError):
                    derive_rail_kit_plate_geometry(cfg)

    def test_registered_cassette_mass_subtracts_disjoint_width_invariant_cuts(self) -> None:
        plan = self.build_nominal()
        proof = plan.mass_budget.registered_cassette_volume_proof
        self.assertEqual(proof.registration_pocket_count_per_cassette, 2)
        self.assertAlmostEqual(proof.registration_pocket_volume_each_mm3, 71.68)
        self.assertAlmostEqual(proof.keeper_slot_volume_each_mm3, 11.52)
        self.assertAlmostEqual(proof.cutout_volume_per_cassette_mm3, 154.88)
        self.assertEqual(proof.production_cassette_count, 24)
        self.assertAlmostEqual(proof.total_cutout_volume_mm3, 3717.12)
        self.assertAlmostEqual(proof.solid_petg_mass_delta_g, 4.7207424)
        self.assertTrue(proof.cutouts_pairwise_disjoint)
        self.assertTrue(proof.cutout_volume_independent_of_cassette_width)

        widths = tuple(
            width
            for run in (plan.through, plan.return_run)
            for width in run.layout.physical_module_widths_mm
        )
        for width in (min(widths), max(widths)):
            removed = _selected_u_box_seed_volume_mm3(
                width, self.cfg
            ) - _selected_u_box_volume_mm3(width, self.cfg)
            self.assertAlmostEqual(removed, 154.88, places=9)

        cassette_item = next(
            item
            for item in plan.bom
            if item.item_id == "selected_front_first_u_box_cassette"
        )
        pre_registration_total = (
            sum(_selected_u_box_seed_volume_mm3(width, self.cfg) for width in widths)
            * plan.level_count
        )
        self.assertAlmostEqual(
            cassette_item.nominal_total_solid_volume_mm3,
            pre_registration_total - proof.total_cutout_volume_mm3,
            places=6,
        )

        exact_skin = deepcopy(self.cfg)
        exact_skin["shelf"]["selected_cassette_geometry_mm"][
            "bottom_skin"
        ] = 2.4
        self.assertEqual(FROZEN_REGISTRATION_REMAINING_BOTTOM_SKIN_MM, 1.0)
        exact_removed = _selected_u_box_seed_volume_mm3(
            widths[0], exact_skin
        ) - _selected_u_box_volume_mm3(widths[0], exact_skin)
        self.assertAlmostEqual(exact_removed, 154.88, places=9)

        for bottom_skin in (2.399, 1.4):
            too_thin = deepcopy(self.cfg)
            too_thin["shelf"]["selected_cassette_geometry_mm"][
                "bottom_skin"
            ] = bottom_skin
            with self.subTest(bottom_skin=bottom_skin):
                with self.assertRaisesRegex(ValueError, "remaining bottom skin"):
                    _selected_u_box_volume_mm3(widths[0], too_thin)

        exact_end_land = deepcopy(self.cfg)
        exact_end_land["shelf"]["selected_cassette_geometry_mm"][
            "full_depth_end_land"
        ] = 5.2
        exact_end_removed = _selected_u_box_seed_volume_mm3(
            widths[0], exact_end_land
        ) - _selected_u_box_volume_mm3(widths[0], exact_end_land)
        self.assertAlmostEqual(exact_end_removed, 154.88, places=9)

        short_end_land = deepcopy(self.cfg)
        short_end_land["shelf"]["selected_cassette_geometry_mm"][
            "full_depth_end_land"
        ] = 5.199
        with self.assertRaisesRegex(ValueError, "full-depth end land"):
            _selected_u_box_volume_mm3(widths[0], short_end_land)

    def test_plan_remains_petg_qualification_only_zero_rated_and_bore_free(self) -> None:
        plan = self.build_nominal()
        self.assertTrue(plan.qualification_only)
        self.assertFalse(plan.production_ready)
        self.assertFalse(plan.installed_release_allowed)
        self.assertFalse(plan.wall_bore_geometry_emitted)
        self.assertTrue(plan.hardware.inputs_complete_for_geometry_study)
        self.assertFalse(plan.hardware.geometric_fit_validated)
        self.assertFalse(plan.hardware.ready_for_wall_bore_authoring)
        self.assertIn(
            GEOMETRY_FEASIBILITY_UNVALIDATED_BLOCKER,
            plan.release_blockers,
        )
        self.assertEqual((plan.rated_load_kg, plan.rated_load_lb), (0.0, 0.0))
        self.assertGreaterEqual(len(plan.release_blockers), 5)
        printed_items = [item for item in plan.bom if item.included_in_petg_mass_budget]
        self.assertTrue(printed_items)
        self.assertTrue(all(item.material == "PETG" for item in printed_items))

    def test_frozen_seam_cap_and_terminal_inset_drift_is_rejected(self) -> None:
        for path, value in (
            (("shelf", "between_module_seam_mm"), 0.4),
            (("shelf", "terminal_corbel_center_inset_mm"), 15.0),
            (("d_frame", "shelf_bearing_cap_width_across_run_mm"), 30.0),
        ):
            cfg = deepcopy(self.cfg)
            cfg[path[0]][path[1]] = value
            with self.assertRaises(ValueError):
                build_measurement_driven_plan(
                    cfg,
                    through_clear_length_mm=1514.475,
                    return_clear_length_mm=751.275,
                    hardware=approved_hardware(),
                    framing_confirmed=True,
                    framing_confirmation_record="Continuous blocking record FR-01",
                )

    def test_fractional_and_boolean_bom_counts_are_rejected_without_coercion(self) -> None:
        mutations = (
            (("shelf", "selected_level_count"), 2.9),
            (("shelf", "selected_level_count"), True),
            (("accessory_system", "sockets_per_eligible_corbel"), 3.9),
            (("accessory_system", "sockets_per_eligible_corbel"), True),
            (
                (
                    "wall_attachment",
                    "minimum_metal_structural_screws_per_corbel",
                ),
                3.9,
            ),
            (
                (
                    "wall_attachment",
                    "minimum_metal_structural_screws_per_corbel",
                ),
                True,
            ),
        )
        for path, value in mutations:
            cfg = deepcopy(self.cfg)
            cfg[path[0]][path[1]] = value
            with self.subTest(path=path, value=value):
                with self.assertRaises(ValueError):
                    build_measurement_driven_plan(
                        cfg,
                        through_clear_length_mm=1514.475,
                        return_clear_length_mm=751.275,
                        hardware=approved_hardware(),
                        framing_confirmed=True,
                        framing_confirmation_record=(
                            "Continuous blocking mutation-test record FR-04"
                        ),
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
