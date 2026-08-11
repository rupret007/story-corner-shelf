"""Contract tests for the R9 compact-bookend design scaffold."""

from __future__ import annotations

from copy import deepcopy
import sys
import unittest
from pathlib import Path


R9 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R9))

import design_math  # noqa: E402


class R9DesignMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = design_math.load_config()
        cls.layout = design_math.calculate_layout(cls.config)

    def test_exact_support_roles_per_level(self) -> None:
        layout = self.layout
        self.assertEqual(layout.structural_stations_per_level, 8)
        self.assertEqual(layout.visible_supports_per_level, 6)
        self.assertEqual(layout.outer_feature_columns_per_level, 2)
        self.assertEqual(layout.ordinary_compact_supports_per_level, 4)
        self.assertEqual(layout.hidden_corner_halves_per_level, 2)
        self.assertEqual(layout.visible_inside_corner_columns_per_level, 0)
        self.assertEqual(layout.cable_rails_per_level, 2)
        self.assertEqual(layout.cable_sockets_per_level, 4)
        self.assertEqual(layout.levels, 2)
        self.assertEqual(layout.outer_feature_columns_per_level * 2, 4)

    def test_outer_bookends_and_corner_roles_are_exact(self) -> None:
        through, return_run = self.layout.runs
        self.assertEqual(through.stations[0].role, "outer_feature")
        self.assertEqual(through.stations[4].role, "hidden_corner")
        self.assertEqual(return_run.stations[0].role, "hidden_corner")
        self.assertEqual(return_run.stations[2].role, "outer_feature")
        for station in (through.stations[4], return_run.stations[0]):
            self.assertFalse(station.visible)
            self.assertFalse(station.cable_rail_allowed)
        rails = [
            station
            for run in self.layout.runs
            for station in run.stations
            if station.cable_rail_allowed
        ]
        self.assertEqual(
            [(station.run_id, station.index) for station in rails],
            [("through", 0), ("return", 2)],
        )

    def test_nominal_station_centers_preserve_every_r8_station(self) -> None:
        through, return_run = self.layout.runs
        self.assertEqual(through.coordinate_datum, "far-left outer wall end")
        self.assertEqual(through.positive_direction, "toward the inside corner")
        self.assertEqual(return_run.coordinate_datum, "inside corner")
        self.assertEqual(
            return_run.positive_direction, "toward the far-right outer wall end"
        )
        for run in (through, return_run):
            self.assertIn("run-local", run.coordinate_scope)
            self.assertIn("not an R8 global", run.coordinate_scope)
        self.assertAlmostEqual(through.pitch_mm, 370.61875, places=6)
        self.assertAlmostEqual(through.stations[0].center_mm, 16.0, places=6)
        self.assertAlmostEqual(through.stations[-1].center_mm, 1498.475, places=6)
        self.assertEqual(
            [station.source_r8_index for station in through.stations],
            [0, 2, 4, 6, 8],
        )
        self.assertAlmostEqual(return_run.pitch_mm, 359.6375, places=6)
        self.assertAlmostEqual(return_run.stations[0].center_mm, 16.0, places=6)
        self.assertAlmostEqual(return_run.stations[-1].center_mm, 735.275, places=6)
        self.assertEqual(
            [station.source_r8_index for station in return_run.stations],
            [0, 2, 4],
        )
        self.assertEqual(len(through.stations), 5)
        self.assertEqual(len(return_run.stations), 3)

    def test_accepted_field_lengths_fit_without_changing_support_topology(self) -> None:
        field = self.config["field_reference"]
        self.assertEqual(field["through_wall_clear_length_in"], 61.25)
        self.assertEqual(field["return_wall_clear_length_in"], 36.75)
        self.assertEqual(
            (
                field["through_wall_clear_length_at_lower_shelf_in"],
                field["through_wall_clear_length_at_upper_shelf_in"],
            ),
            (61.25, 61.25),
        )
        self.assertEqual(
            (
                field["return_wall_clear_length_at_lower_shelf_in"],
                field["return_wall_clear_length_at_upper_shelf_in"],
            ),
            (36.75, 36.75),
        )
        self.assertTrue(field["return_wall_length_is_conservative_working_value"])
        self.assertFalse(field["wall_length_measurements_authorize_installed_cad"])

        through, return_run = self.layout.runs
        fits = {fit.run_id: fit for fit in self.layout.field_fits}
        self.assertAlmostEqual(fits["through"].clear_length_lower_mm, 1555.75)
        self.assertAlmostEqual(fits["through"].clear_length_upper_mm, 1555.75)
        self.assertAlmostEqual(fits["through"].scaffold_length_mm, 1514.475)
        self.assertAlmostEqual(
            fits["through"].minimum_unallocated_clear_length_mm, 41.275
        )
        self.assertAlmostEqual(fits["return"].clear_length_lower_mm, 933.45)
        self.assertAlmostEqual(fits["return"].clear_length_upper_mm, 933.45)
        self.assertAlmostEqual(fits["return"].scaffold_length_mm, 751.275)
        self.assertAlmostEqual(
            fits["return"].minimum_unallocated_clear_length_mm, 182.175
        )

        # The measurements establish a fit envelope only. They do not silently
        # respan the frozen qualification scaffold or add/remove supports.
        self.assertAlmostEqual(through.pitch_mm, 370.61875, places=6)
        self.assertAlmostEqual(return_run.pitch_mm, 359.6375, places=6)
        self.assertEqual([station.role for station in through.stations], [
            "outer_feature", "compact", "compact", "compact", "hidden_corner"
        ])
        self.assertEqual([station.role for station in return_run.stations], [
            "hidden_corner", "compact", "outer_feature"
        ])

    def test_remaining_field_and_release_inputs_stay_unresolved(self) -> None:
        field = self.config["field_reference"]
        for name in (
            "outlet_center_from_through_datum_in",
            "inside_corner_angle_deg",
            "stud_or_blocking_locations_in",
            "wall_substrate_thickness_in",
        ):
            with self.subTest(field=name):
                self.assertIsNone(field[name])

        unresolved = self.config["unresolved_inputs"]
        for group in ("field", "framing", "hardware", "load_and_physical_tests"):
            with self.subTest(group=group):
                self.assertTrue(unresolved[group])
                self.assertTrue(all(value is None for value in unresolved[group].values()))

    def test_shortened_visible_drops_and_vertical_clearances(self) -> None:
        topology = self.config["support_topology"]
        self.assertEqual(topology["wall_hugging_strap_total_drop_mm"], 160.0)
        self.assertEqual(topology["outer_feature_visible_drop_mm"], 120.65)
        self.assertEqual(topology["compact_arch_visible_drop_mm"], 76.2)
        self.assertGreater(
            topology["wall_hugging_strap_total_drop_mm"],
            topology["outer_feature_visible_drop_mm"],
        )
        self.assertGreater(
            topology["outer_feature_visible_drop_mm"],
            topology["compact_arch_visible_drop_mm"],
        )
        clear = self.layout.clearances
        self.assertAlmostEqual(clear.shelf_thickness_in, 1.1811023622, places=8)
        self.assertAlmostEqual(
            clear.open_clearance_between_shelves_in, 14.8188976378, places=8
        )
        self.assertAlmostEqual(clear.upper_shelf_to_ceiling_in, 12.0, places=8)
        self.assertAlmostEqual(
            clear.outlet_to_lower_wall_strap_bottom_in, 7.0196850394, places=8
        )
        self.assertAlmostEqual(
            clear.lower_shelf_to_upper_feature_bottom_in, 10.0688976378, places=8
        )
        self.assertAlmostEqual(
            clear.lower_shelf_to_upper_compact_arch_bottom_in,
            11.8188976378,
            places=8,
        )

    def test_visual_and_r8_evidence_are_hash_bound(self) -> None:
        design_math.validate_bound_files(self.config)

    def test_r6_r7_and_r8_trees_remain_frozen(self) -> None:
        design_math.validate_frozen_baselines()

    def test_release_state_is_fail_closed_and_petg_only(self) -> None:
        project = self.config["project"]
        self.assertTrue(project["qualification_only"])
        for field in (
            "installed_release_allowed",
            "physical_qualification_complete",
            "tested_load_rating_exists",
            "production_ready",
            "load_rating_allowed",
            "wall_bores_emitted",
            "full_shelf_set_emitted",
            "embedded_gcode_allowed",
        ):
            self.assertIs(project[field], False)
        self.assertEqual(self.config["material"]["printed_material"], "PETG only")
        self.assertIs(
            self.config["material"]["pla_allowed_in_primary_or_load_path_parts"],
            False,
        )

    def test_unsafe_contract_mutations_fail(self) -> None:
        mutations = (
            ("visible corner", ("support_topology", "visible_inside_corner_columns_per_level"), 1),
            ("compact rail", ("accessory_system", "rails_or_pegs_on_compact_supports_allowed"), True),
            ("corner rail", ("accessory_system", "rails_or_pegs_at_inside_corner_allowed"), True),
            ("PLA", ("material", "printed_material"), "PLA"),
            ("PLA preset", ("printer", "filament_preset"), "Generic PLA"),
            ("missing brim", ("printer", "brim_mm"), 0.0),
            ("rated bool", ("project", "rated_load_kg"), False),
            ("production", ("project", "production_ready"), True),
            (
                "missing ledger",
                ("span_bridging_system", "rear_ledger_required"),
                False,
            ),
            (
                "fake return datum",
                ("runs", 1, "coordinate_datum"),
                "R8 global origin",
            ),
            (
                "printed wall screws",
                ("material", "required_wall_fastener_material"),
                "printed PETG screws",
            ),
            (
                "zero screws",
                ("support_topology", "minimum_metal_structural_screws_per_station"),
                0,
            ),
            (
                "blocking optional",
                ("support_topology", "continuous_blocking_or_verified_equivalent_required"),
                False,
            ),
            (
                "accessory structural credit",
                ("accessory_system", "structural_or_shelf_load_credit"),
                True,
            ),
            (
                "cassette qualified",
                ("shelf", "selected_cassette_physical_qualification_complete"),
                True,
            ),
            (
                "one corner half",
                ("corner_system", "independent_hidden_half_per_wall"),
                False,
            ),
            (
                "corner fixture optional",
                ("qualification", "two_wall_hidden_corner_fixture_required"),
                False,
            ),
            (
                "duplicated lower elevation",
                ("field_reference", "lower_shelf_top_elevation_in"),
                10.0,
            ),
            (
                "return no longer conservative",
                ("field_reference", "return_wall_length_is_conservative_working_value"),
                False,
            ),
            (
                "wall lengths authorize installed CAD",
                ("field_reference", "wall_length_measurements_authorize_installed_cad"),
                True,
            ),
            (
                "rendering claimed exact",
                ("visual_reference", "visual_intent_only"),
                False,
            ),
            (
                "solid cassette",
                ("shelf", "selected_cassette_candidate"),
                "solid slab",
            ),
            ("huge seam", ("shelf", "between_module_seam_mm"), 99.0),
            (
                "shallow shelf",
                ("support_topology", "shelf_projection_mm"),
                99.0,
            ),
            (
                "thin support",
                ("support_topology", "support_body_thickness_across_run_mm"),
                99.0,
            ),
            (
                "thick wall strap",
                ("support_topology", "wall_hugging_strap_projection_mm"),
                99.0,
            ),
            (
                "oversize ledger",
                ("span_bridging_system", "rear_ledger_segment_max_length_mm"),
                999.0,
            ),
            (
                "doorward cable service",
                ("accessory_system", "service_direction"),
                "outward into door",
            ),
            (
                "wrong plate",
                ("printer", "plate_type"),
                "Cool Plate",
            ),
            (
                "wrong process",
                ("printer", "process_preset"),
                "Draft",
            ),
            (
                "missing edge reserve",
                ("printer", "edge_reserve_each_side_mm"),
                0.0,
            ),
            (
                "printed fastener substitution",
                ("material", "printed_fastener_or_anchor_substitution_allowed"),
                True,
            ),
        )
        for name, path, value in mutations:
            mutated = deepcopy(self.config)
            if len(path) == 2:
                mutated[path[0]][path[1]] = value
            else:
                mutated[path[0]][path[1]][path[2]] = value
            with self.subTest(name=name), self.assertRaises(ValueError):
                design_math.calculate_layout(mutated)

        duplicated = deepcopy(self.config)
        duplicated["runs"][0]["compact_support_indices"] = [1, 1, 3]
        with self.assertRaises(ValueError):
            design_math.calculate_layout(duplicated)

        nonfinite = deepcopy(self.config)
        nonfinite["field_reference"]["ceiling_height_in"] = float("nan")
        with self.assertRaises(ValueError):
            design_math.calculate_layout(nonfinite)

        prematurely_filled = deepcopy(self.config)
        prematurely_filled["unresolved_inputs"]["hardware"][
            "structural_screw_length_mm"
        ] = 90.0
        with self.assertRaises(ValueError):
            design_math.calculate_layout(prematurely_filled)


if __name__ == "__main__":
    unittest.main()
