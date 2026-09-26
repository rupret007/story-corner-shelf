from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_shelf_parts as generator  # noqa: E402


class ParametricDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

    def dimensions(self, config: dict | None = None) -> dict[str, dict]:
        cfg = config or self.config
        return {
            run["id"]: generator.run_dimensions(cfg, run)
            for run in cfg["closet"]["runs"]
        }

    def run_config(self, config: dict, run_id: str) -> dict:
        return next(run for run in config["closet"]["runs"] if run["id"] == run_id)

    def validation(self) -> dict:
        return json.loads((ROOT / "generated" / "validation.json").read_text(encoding="utf-8"))

    def assert_top_tile_radius(self, mesh, expected_radius_mm: float) -> None:
        min_x, min_y, _ = mesh.bounds[0]
        left_edge_y = [
            float(vertex[1])
            for vertex in mesh.vertices
            if abs(float(vertex[0]) - float(min_x)) < 1e-8
        ]
        bottom_edge_x = [
            float(vertex[0])
            for vertex in mesh.vertices
            if abs(float(vertex[1]) - float(min_y)) < 1e-8
        ]
        self.assertTrue(left_edge_y)
        self.assertTrue(bottom_edge_x)
        self.assertAlmostEqual(min(left_edge_y) - float(min_y), expected_radius_mm, places=6)
        self.assertAlmostEqual(min(bottom_edge_x) - float(min_x), expected_radius_mm, places=6)

    def test_nominal_through_return_decks_do_not_overlap(self) -> None:
        dimensions = self.dimensions()
        through = dimensions["long_wall_5ft"]
        return_run = dimensions["short_wall_3ft"]
        self.assertAlmostEqual(through["deck_start_from_inside_corner_in"], 0.6875, places=6)
        self.assertAlmostEqual(through["deck_length_in"], 60.6875, places=6)
        self.assertAlmostEqual(through["corner_front_plane_from_inside_corner_in"], 8.6875, places=6)
        self.assertAlmostEqual(return_run["deck_start_from_inside_corner_in"], 8.75049212598, places=6)
        self.assertAlmostEqual(return_run["deck_length_in"], 27.1245078740, places=6)
        self.assertAlmostEqual(
            return_run["deck_start_from_inside_corner_in"]
            - through["corner_front_plane_from_inside_corner_in"],
            self.config["closet"]["inside_corner"]["deck_joint_gap_mm"] / 25.4,
            places=8,
        )

    def test_component_layouts_preserve_universal_centers(self) -> None:
        dimensions = self.dimensions()
        short = dimensions["short_wall_3ft"]
        long = dimensions["long_wall_5ft"]
        for run in dimensions.values():
            for key in ("top_layout", "rear_curb_layout"):
                self.assertAlmostEqual(run[key]["center_module_width_mm"], 151.8, places=6)
        self.assertEqual((short["top_layout"]["columns"], long["top_layout"]["columns"]), (5, 9))
        self.assertAlmostEqual(short["top_layout"]["parametric_end_module_width_mm"], 116.08125, places=5)
        self.assertAlmostEqual(long["top_layout"]["parametric_end_module_width_mm"], 135.13125, places=5)
        self.assertAlmostEqual(short["palatine_arcade_layout"]["half_arch_width_mm"], 113.82708333, places=5)
        self.assertAlmostEqual(long["palatine_arcade_layout"]["half_arch_width_mm"], 110.721875, places=5)
        self.assertEqual((short["rear_curb_layout"]["center_columns"], long["rear_curb_layout"]["center_columns"]), (3, 8))
        self.assertAlmostEqual(short["rear_curb_layout"]["parametric_end_module_width_mm"], 115.58125, places=5)
        self.assertAlmostEqual(long["rear_curb_layout"]["parametric_end_module_width_mm"], 145.53125, places=5)

    def test_corner_quadrants_close_the_eight_inch_square(self) -> None:
        depth_mm = generator.inches(self.config["closet"]["shelf_depth_in"])
        gap = self.config["skin"]["tile_gap_mm"]
        quadrant = (depth_mm - gap) / 2.0
        self.assertAlmostEqual(quadrant, 101.3, places=6)
        self.assertAlmostEqual(2.0 * quadrant + gap, depth_mm, places=6)
        self.assertLessEqual(quadrant, self.config["printer"]["minimum_model_build_envelope_mm"][0])

    def test_every_top_tile_uses_the_near_square_mating_radius(self) -> None:
        skin = self.config["skin"]
        radius = float(skin["top_tile_plan_radius_mm"])
        self.assertAlmostEqual(radius, 0.25, places=6)
        self.assertAlmostEqual(float(skin["corner_mating_radius_mm"]), radius, places=6)
        self.assertLessEqual(radius, float(skin["tile_gap_mm"]) / 2.0)

        dimensions = self.dimensions()
        module_depth = dimensions["long_wall_5ft"]["top_layout"]["module_depth_mm"]
        meshes = (
            generator.top_tile(self.config, 151.8, module_depth),
            generator.top_tile(
                self.config,
                dimensions["short_wall_3ft"]["top_layout"]["parametric_end_module_width_mm"],
                module_depth,
            ),
            generator.corner_top_quadrant(self.config),
        )
        for mesh in meshes:
            with self.subTest(size=mesh.extents.tolist()):
                self.assert_top_tile_radius(mesh, radius)

    def test_split_rear_curbs_terminate_on_their_own_structural_surfaces(self) -> None:
        dimensions = self.dimensions()
        through = dimensions["long_wall_5ft"]
        return_run = dimensions["short_wall_3ft"]
        replacement_and_seam_mm = (
            float(self.config["skin"]["rear_curb_inside_corner_leg_mm"])
            + float(self.config["skin"]["tile_gap_mm"])
        )
        expected_long_start = through["deck_start_from_inside_corner_in"] + replacement_and_seam_mm / 25.4
        expected_corner_side_start = through["installed_shelf_back_offset_in"] + replacement_and_seam_mm / 25.4

        self.assertAlmostEqual(through["rear_curb_start_from_inside_corner_in"], expected_long_start, places=8)
        self.assertAlmostEqual(return_run["rear_curb_start_from_inside_corner_in"], return_run["deck_start_from_inside_corner_in"], places=8)
        self.assertAlmostEqual(through["corner_side_rear_curb_start_from_inside_corner_in"], expected_corner_side_start, places=8)
        self.assertAlmostEqual(
            through["corner_side_rear_curb_end_from_inside_corner_in"],
            through["installed_shelf_back_offset_in"] + self.config["closet"]["shelf_depth_in"],
            places=8,
        )
        self.assertAlmostEqual(through["corner_side_rear_curb_length_mm"], 172.6, places=6)
        self.assertAlmostEqual(
            (
                return_run["rear_curb_start_from_inside_corner_in"]
                - through["corner_side_rear_curb_end_from_inside_corner_in"]
            )
            * 25.4,
            self.config["closet"]["inside_corner"]["deck_joint_gap_mm"],
            places=6,
        )
        self.assertNotAlmostEqual(
            through["rear_curb_start_from_inside_corner_in"],
            return_run["rear_curb_start_from_inside_corner_in"],
            places=3,
        )

        for run in dimensions.values():
            self.assertAlmostEqual(run["corner_to_top_arm_finish_seam_mm"], 0.6, places=6)
            self.assertAlmostEqual(
                run["front_perimeter_end_from_inside_corner_in"]
                - run["fascia_straight_end_from_inside_corner_in"],
                self.config["fascia"]["endcap_thickness_mm"] / 25.4,
                places=8,
            )
        self.assertAlmostEqual(
            return_run["top_inner_overhang_into_wood_joint_mm"],
            self.config["closet"]["inside_corner"]["deck_joint_gap_mm"]
            - self.config["skin"]["tile_gap_mm"],
            places=6,
        )
        self.assertAlmostEqual(
            through["top_inner_overhang_into_wood_joint_mm"],
            0.0,
            places=6,
        )

    def test_independent_field_width_changes_only_parametric_ends(self) -> None:
        config = copy.deepcopy(self.config)
        config["closet"]["runs"][0]["field_verified_min_clear_wall_width_in"] = 35.875
        dimensions = self.dimensions(config)
        short = dimensions["short_wall_3ft"]
        long = dimensions["long_wall_5ft"]
        self.assertAlmostEqual(
            short["top_layout"]["center_module_width_mm"],
            long["top_layout"]["center_module_width_mm"],
            places=6,
        )
        self.assertNotAlmostEqual(
            short["top_layout"]["parametric_end_module_width_mm"],
            116.08125,
            places=3,
        )
        self.assertEqual(short["clear_width_source"], "field_verified_minimum_across_adjustment_zone")

    def test_per_wall_back_offsets_control_their_cross_axis_corner_planes(self) -> None:
        config = copy.deepcopy(self.config)
        through_config = self.run_config(config, "long_wall_5ft")
        return_config = self.run_config(config, "short_wall_3ft")
        through_config["field_verified_installed_shelf_back_offset_in"] = 0.70
        return_config["field_verified_installed_shelf_back_offset_in"] = 0.76
        dimensions = self.dimensions(config)
        through = dimensions["long_wall_5ft"]
        return_run = dimensions["short_wall_3ft"]
        joint_gap_in = config["closet"]["inside_corner"]["deck_joint_gap_mm"] / 25.4

        self.assertAlmostEqual(through["installed_shelf_back_offset_in"], 0.70, places=6)
        self.assertAlmostEqual(through["perpendicular_wall_installed_shelf_back_offset_in"], 0.76, places=6)
        self.assertAlmostEqual(through["deck_start_from_inside_corner_in"], 0.76, places=6)
        self.assertAlmostEqual(through["corner_front_plane_from_inside_corner_in"], 8.76, places=6)
        self.assertAlmostEqual(return_run["installed_shelf_back_offset_in"], 0.76, places=6)
        self.assertAlmostEqual(return_run["perpendicular_wall_installed_shelf_back_offset_in"], 0.70, places=6)
        self.assertAlmostEqual(
            return_run["deck_start_from_inside_corner_in"],
            8.70 + joint_gap_in,
            places=6,
        )
        self.assertAlmostEqual(return_run["corner_front_plane_from_inside_corner_in"], 8.70, places=6)
        self.assertEqual(through["installed_shelf_back_offset_source"], "field_verified_per_wall")
        self.assertEqual(return_run["installed_shelf_back_offset_source"], "field_verified_per_wall")

        corner = generator.corner_geometry(config, dimensions)
        self.assertEqual(
            corner["installed_shelf_back_offsets_in"],
            {"long_wall_5ft": 0.70, "short_wall_3ft": 0.76},
        )
        self.assertEqual(corner["corner_zone_bounds_in"]["long_wall_axis"], [0.76, 8.76])
        self.assertEqual(corner["corner_zone_bounds_in"]["short_wall_axis"], [0.70, 8.70])
        self.assertEqual(
            corner["corner_front_planes_in"],
            {"long_wall_axis": 8.76, "short_wall_axis": 8.70},
        )

    def test_nominal_supports_respect_spacing_overhang_and_corner_clearance(self) -> None:
        dimensions = self.dimensions()
        through = dimensions["long_wall_5ft"]
        return_run = dimensions["short_wall_3ft"]
        self.assertEqual(through["nominal_support_centers_in"], [6.0, 17.0, 32.5, 48.5, 60.5])
        self.assertEqual(
            through["support_geometry_source"],
            "planned_mixed_verified_studs_and_required_blocking",
        )
        self.assertAlmostEqual(return_run["nominal_support_centers_in"][0], 10.75049212598, places=6)
        self.assertAlmostEqual(return_run["nominal_support_centers_in"][-1], 33.875, places=6)
        self.assertLessEqual(max(through["support_spacings_in"]), 16.0)
        self.assertLessEqual(max(return_run["support_spacings_in"]), 16.0)
        corner = generator.corner_geometry(self.config, dimensions)
        self.assertGreater(corner["nominal_nearest_bracket_body_clearance_in"], 1.0)
        self.assertGreater(corner["nominal_nearest_conservative_8in_shelf_envelope_clearance_in"], 1.0)

    def test_field_support_centers_are_absolute_from_inside_corner(self) -> None:
        config = copy.deepcopy(self.config)
        run = config["closet"]["runs"][0]
        run["field_verified_support_centers_in"] = [10.75, 22.25, 33.75]
        dimensions = generator.run_dimensions(config, run)
        self.assertEqual(dimensions["support_geometry_source"], "field_verified")
        self.assertEqual(dimensions["nominal_support_centers_in"], [10.75, 22.25, 33.75])
        self.assertAlmostEqual(
            dimensions["support_centers_local_to_deck_start_in"][0],
            10.75 - dimensions["deck_start_from_inside_corner_in"],
            places=6,
        )

    def test_excessive_field_support_spacing_is_rejected(self) -> None:
        config = copy.deepcopy(self.config)
        run = config["closet"]["runs"][1]
        run.pop("support_lines", None)
        run["field_verified_support_centers_in"] = [6.25, 23.25, 40.25, 54.0]
        with self.assertRaisesRegex(ValueError, "support spacing exceeds"):
            generator.run_dimensions(config, run)

    def test_duplicate_and_too_close_field_support_centers_are_rejected(self) -> None:
        for centers in (
            [10.75, 10.75, 22.25],
            [10.75, 12.749, 22.25],
        ):
            config = copy.deepcopy(self.config)
            run = self.run_config(config, "short_wall_3ft")
            run["field_verified_support_centers_in"] = centers
            with self.subTest(centers=centers):
                with self.assertRaisesRegex(ValueError, "duplicated or closer"):
                    generator.run_dimensions(config, run)

    def test_support_center_distinctness_boundary_is_accepted(self) -> None:
        config = copy.deepcopy(self.config)
        run = self.run_config(config, "long_wall_5ft")
        run.pop("support_lines", None)
        run["field_verified_support_centers_in"] = [6.0, 8.0, 24.0, 40.0, 56.0]
        dimensions = generator.run_dimensions(config, run)
        self.assertEqual(dimensions["support_geometry_source"], "field_verified")
        self.assertAlmostEqual(min(dimensions["support_spacings_in"]), 2.0, places=8)

    def test_nonfinite_field_support_centers_are_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            config = copy.deepcopy(self.config)
            run = self.run_config(config, "short_wall_3ft")
            run["field_verified_support_centers_in"] = [10.75, value, 33.75]
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite numbers"):
                    generator.run_dimensions(config, run)

    def test_out_of_tolerance_verified_corner_requires_template_revision(self) -> None:
        config = copy.deepcopy(self.config)
        config["closet"]["inside_corner"]["field_verified_angle_deg"] = 89.749
        dimensions = self.dimensions(config)
        with self.assertRaisesRegex(ValueError, "square-deck prototype limit"):
            generator.corner_geometry(config, dimensions)

    def test_corner_angle_gate_is_derived_from_joint_gap_and_residual_policy(self) -> None:
        corner_config = self.config["closet"]["inside_corner"]
        depth_mm = generator.inches(self.config["closet"]["shelf_depth_in"])
        joint_gap_mm = float(corner_config["deck_joint_gap_mm"])
        minimum_residual_mm = float(corner_config["minimum_residual_joint_clearance_mm"])
        expected_physical_limit = math.degrees(math.atan(joint_gap_mm / depth_mm))
        expected_policy_limit = math.degrees(
            math.atan((joint_gap_mm - minimum_residual_mm) / depth_mm)
        )
        corner = generator.corner_geometry(self.config, self.dimensions())
        self.assertAlmostEqual(corner["physical_overlap_limit_from_joint_gap_deg"], expected_physical_limit, places=9)
        self.assertAlmostEqual(corner["residual_clearance_policy_limit_deg"], expected_policy_limit, places=9)
        self.assertLessEqual(corner_config["maximum_square_corner_deviation_deg"], expected_policy_limit)

        invalid = copy.deepcopy(self.config)
        invalid["closet"]["inside_corner"]["maximum_square_corner_deviation_deg"] = expected_policy_limit + 0.001
        with self.assertRaisesRegex(ValueError, "would leave less than"):
            generator.corner_geometry(invalid, self.dimensions(invalid))

    def test_limit_corner_angles_keep_corner_parts_single_watertight_bodies(self) -> None:
        depth_mm = generator.inches(self.config["closet"]["shelf_depth_in"])
        expected_shift = depth_mm * math.tan(math.radians(0.25))
        expected_remaining = self.config["closet"]["inside_corner"]["deck_joint_gap_mm"] - expected_shift
        for angle in (89.75, 90.25):
            config = copy.deepcopy(self.config)
            config["closet"]["inside_corner"]["field_verified_angle_deg"] = angle
            corner = generator.corner_geometry(config, self.dimensions(config))
            self.assertAlmostEqual(corner["angular_edge_shift_across_depth_mm"], expected_shift, places=6)
            self.assertAlmostEqual(corner["remaining_nominal_joint_clearance_mm"], expected_remaining, places=6)
            self.assertGreaterEqual(
                corner["remaining_nominal_joint_clearance_mm"],
                config["closet"]["inside_corner"]["minimum_residual_joint_clearance_mm"],
            )
            meshes = (
                generator.fascia_outside_corner_cover(config),
                generator.rear_curb_inside_corner_connector(config),
                generator.corner_fit_gauge(config),
            )
            for mesh in meshes:
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_volume)
                self.assertEqual(len(mesh.split(only_watertight=False)), 1)

    def test_nominal_palatine_package_contains_exactly_102_objects(self) -> None:
        validation = self.validation()
        self.assertEqual(validation["revision"], "triadic_palatine_fitted_l_corner_r12_final_durable")
        self.assertEqual(validation["modularity"]["full_set_object_count"], 102)
        self.assertEqual(sum(mesh["repeat_count"] for mesh in validation["meshes"]), 102)
        by_name = {mesh["name"]: mesh for mesh in validation["meshes"]}
        self.assertEqual(by_name["PETG_RearCurb_Center_6inPitch"]["repeat_count"], 11)
        self.assertEqual(by_name["PETG_RearCurb_CornerSide_ThroughZone"]["repeat_count"], 1)
        self.assertEqual(by_name["PETG_RearCurb_ParametricEnd_short_wall_3ft"]["repeat_count"], 2)
        self.assertEqual(by_name["PETG_RearCurb_ParametricEnd_long_wall_5ft"]["repeat_count"], 2)
        self.assertEqual(by_name["PETG_Palatine_Keystone_SeamCover"]["repeat_count"], 9)
        self.assertEqual(
            generator.PARTS_CATALOG_3MF_NAME,
            "MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_PARTS_CATALOG.3mf",
        )
        self.assertEqual(
            generator.FULL_PRINT_SET_3MF_NAME,
            "MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_FULL_PRINT_SET.3mf",
        )

    def test_palatine_geometry_preserves_the_three_six_nine_grammar(self) -> None:
        palatine = self.config["palatine"]
        dimensions = self.dimensions()
        short = dimensions["short_wall_3ft"]["palatine_arcade_layout"]
        long = dimensions["long_wall_5ft"]["palatine_arcade_layout"]
        self.assertEqual((short["bay_count"], long["bay_count"]), (3, 6))
        self.assertEqual(short["bay_count"] + long["bay_count"], 9)
        self.assertEqual((short["segment_count"], long["segment_count"]), (6, 12))
        self.assertEqual((short["left_half_count"], short["right_half_count"]), (3, 3))
        self.assertEqual((long["left_half_count"], long["right_half_count"]), (6, 6))
        self.assertEqual(palatine["total_arcade_bays"], 9)
        self.assertEqual(palatine["dentil_group_count"], 3)
        self.assertEqual(palatine["cornice_step_count"], 3)
        self.assertEqual(palatine["pier_flute_count"], 6)
        self.assertEqual(palatine["corner_rosette_petals"], 9)
        self.assertEqual(palatine["dentils_per_half_arch"], 9)
        self.assertEqual(palatine["corbel_triangle_ratio"], [3, 4, 5])
        for layout in (short, long):
            reconstructed = (
                layout["segment_count"] * layout["half_arch_width_mm"]
                + (layout["segment_count"] - 1) * layout["segment_seam_mm"]
            )
            self.assertAlmostEqual(reconstructed, layout["length_mm"], places=6)

        corner = generator.corner_geometry(self.config, dimensions)
        self.assertEqual(corner["palatine_arcade_total_bays"], 9)

    def test_palatine_groin_vault_preserves_bracket_clearance(self) -> None:
        dimensions = self.dimensions()
        corner = generator.corner_geometry(self.config, dimensions)
        clearance = corner["palatine_groin_vault_bracket_clearance_mm"]
        required = corner["minimum_palatine_groin_vault_bracket_clearance_mm"]
        self.assertGreaterEqual(clearance, required)
        footprint = corner["palatine_groin_vault_footprint_station_in"]
        self.assertAlmostEqual(
            (footprint[1] - footprint[0]) * 25.4,
            self.config["palatine"]["groin_vault_size_mm"],
            places=6,
        )
        through = dimensions["long_wall_5ft"]
        expected_nearest = max(
            center
            for center in through["nominal_support_centers_in"]
            if center < through["corner_front_plane_from_inside_corner_in"]
        )
        self.assertAlmostEqual(corner["palatine_groin_vault_nearest_support_station_in"], expected_nearest, places=8)

        invalid = copy.deepcopy(self.config)
        invalid["palatine"]["minimum_groin_vault_bracket_clearance_mm"] = clearance + 0.01
        with self.assertRaisesRegex(ValueError, "groin-vault soffit"):
            generator.corner_geometry(invalid, self.dimensions(invalid))

    def test_captured_fascia_and_slotted_retention_meshes_fit_the_envelope(self) -> None:
        fascia_width = 151.8
        fascia = generator.fascia(self.config, fascia_width)
        slotted_curb = generator.rear_curb(self.config, fascia_width)
        slotted_corner_curb = generator.rear_curb_inside_corner_connector(self.config)
        slotted_groin = generator.palatine_groin_vault_corner_soffit(self.config)
        fascia_config = self.config["fascia"]
        skin = self.config["skin"]
        solid_curb = generator.boolean_union(
            [
                generator.cuboid((fascia_width, skin["rear_curb_base_depth_mm"], skin["rear_curb_thickness_mm"])),
                generator.cuboid((fascia_width, skin["rear_curb_thickness_mm"], skin["rear_curb_height_mm"])),
            ]
        )

        # The fascia is a holeless, single-body C channel. Its exact union
        # volume catches accidental face perforations while its extents and
        # configured opening protect the full-depth lower capture and the
        # shallower upper tile-capture flange.
        face_t = float(fascia_config["face_thickness_mm"])
        flange_t = float(fascia_config["flange_thickness_mm"])
        channel_depth = float(fascia_config["channel_depth_mm"])
        top_depth = float(fascia_config["top_flange_depth_mm"])
        opening = generator.fascia_opening_height(self.config)
        expected_total_height = 2.0 * flange_t + opening + float(fascia_config["front_lip_height_mm"])
        expected_solid_volume = (
            fascia_width * expected_total_height * face_t
            + fascia_width * flange_t * (channel_depth - face_t)
            + fascia_width * flange_t * (top_depth - face_t)
        )
        self.assertTrue(fascia.is_watertight)
        self.assertTrue(fascia.is_volume)
        self.assertEqual(len(fascia.split(only_watertight=False)), 1)
        self.assertEqual(fascia.euler_number, 2, "the captured fascia must not contain a through-slot")
        self.assertAlmostEqual(fascia.extents[0], fascia_width, places=4)
        self.assertAlmostEqual(fascia.extents[1], expected_total_height, places=4)
        self.assertAlmostEqual(fascia.extents[2], 29.0, places=6)
        self.assertAlmostEqual(channel_depth, 29.0, places=6)
        self.assertGreater(fascia.volume, expected_solid_volume * 0.98)
        self.assertLess(fascia.volume, expected_solid_volume * 1.10)
        self.assertEqual(face_t, 3.2)
        self.assertEqual(flange_t, 3.2)
        self.assertIn("mechanically capture", self.config["finish_attachment"]["fascia_method"])
        self.assertIn("do not drill or notch", self.config["finish_attachment"]["fascia_method"])

        # Rear curbs keep their explicit fastener slots, and the groin-vault
        # soffit keeps two. Euler number is a topology-level regression for
        # those through-openings rather than a filename or triangle-count test.
        slot = generator.horizontal_slot_cutter(
            skin["rear_curb_fastener_slot_length_mm"],
            skin["rear_curb_fastener_slot_width_mm"],
            skin["rear_curb_thickness_mm"] + 2.0,
            center=(fascia_width / 2.0, 12.0, skin["rear_curb_thickness_mm"] / 2.0),
        )
        self.assertAlmostEqual(slot.extents[0], 8.0, places=6)
        self.assertAlmostEqual(slot.extents[1], 4.4, places=6)
        self.assertLess(slotted_curb.volume, solid_curb.volume)
        self.assertEqual(slotted_curb.euler_number, 0)
        self.assertEqual(slotted_corner_curb.euler_number, -2)
        self.assertEqual(slotted_groin.euler_number, -2)
        for mesh in (slot, fascia, slotted_curb, slotted_corner_curb, slotted_groin):
            self.assertTrue(mesh.is_watertight)
            self.assertTrue(mesh.is_volume)
            self.assertEqual(len(mesh.split(only_watertight=False)), 1)

        validation = self.validation()
        build = self.config["printer"]["minimum_model_build_envelope_mm"]
        self.assertEqual(len(validation["meshes"]), 23)
        for mesh in validation["meshes"]:
            with self.subTest(mesh=mesh["name"]):
                self.assertTrue(mesh["watertight"])
                self.assertEqual(mesh["body_count"], 1)
                self.assertTrue(mesh["fits_minimum_180mm_envelope_in_saved_orientation"])
                self.assertTrue(all(size <= limit + 1e-6 for size, limit in zip(mesh["size_mm"], build)))

    def test_validation_distinguishes_packaged_and_installed_petg_mass(self) -> None:
        validation = self.validation()
        packaged = validation["estimated_packaged_petg_mass_kg"]
        installed = validation["estimated_installed_petg_mass_kg"]
        self.assertGreater(packaged, installed)
        self.assertGreater(installed, 0.0)
        self.assertNotIn("estimated_total_petg_kg", validation)
        coupon_mass_kg = sum(
            mesh["estimated_petg_g_each"] * mesh["repeat_count"]
            for mesh in validation["meshes"]
            if mesh["name"].startswith("PRINT_FIRST_")
        ) / 1000.0
        self.assertAlmostEqual(packaged - installed, coupon_mass_kg, delta=0.011)
        self.assertIn("excludes purge", validation["mass_estimate_note"])
        for run in self.config["closet"]["runs"]:
            self.assertIsNone(run["field_verified_shelf_arm_dead_load_lb"])

        sanity = json.loads(
            (ROOT / "generated" / "structural_sanity_check.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            sanity["inputs"]["development_line_load_proxy_lb_per_ft"],
            self.config["structural"]["serviceability_check_development_line_load_proxy_lb_per_ft"],
        )
        self.assertIn("not a measured dead load", sanity["load_scope_note"])

    def test_field_verified_dead_load_raises_governing_line_load(self) -> None:
        import tempfile

        config = copy.deepcopy(self.config)
        through = self.run_config(config, "long_wall_5ft")
        through["field_verified_shelf_arm_dead_load_lb"] = 40.0
        dimensions = self.dimensions(config)
        deck_length_ft = dimensions["long_wall_5ft"]["deck_length_in"] / 12.0
        expected = (through["design_target_contents_lb_edl"] + 40.0) / deck_length_ft
        proxy = config["structural"]["serviceability_check_development_line_load_proxy_lb_per_ft"]
        self.assertGreater(expected, proxy)

        original_out = generator.OUT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                generator.OUT = Path(tmp)
                generator.write_structural_sanity_check(config, dimensions)
                sanity = json.loads(
                    (Path(tmp) / "structural_sanity_check.json").read_text(encoding="utf-8")
                )
        finally:
            generator.OUT = original_out

        inputs = sanity["inputs"]
        self.assertAlmostEqual(inputs["governing_line_load_lb_per_ft"], expected, places=3)
        self.assertEqual(inputs["governing_line_load_source"], "field_verified_dead_load_long_wall_5ft")
        self.assertEqual(len(inputs["field_verified_arm_dead_loads"]), 1)
        self.assertEqual(inputs["development_line_load_proxy_lb_per_ft"], proxy)

        # A small measured dead load must never relax the check below the proxy.
        through["field_verified_shelf_arm_dead_load_lb"] = 1.0
        try:
            with tempfile.TemporaryDirectory() as tmp:
                generator.OUT = Path(tmp)
                generator.write_structural_sanity_check(config, self.dimensions(config))
                sanity = json.loads(
                    (Path(tmp) / "structural_sanity_check.json").read_text(encoding="utf-8")
                )
        finally:
            generator.OUT = original_out
        self.assertEqual(sanity["inputs"]["governing_line_load_lb_per_ft"], proxy)
        self.assertEqual(sanity["inputs"]["governing_line_load_source"], "development_line_load_proxy")

    def test_fascia_opening_includes_top_tile_and_saved_cover_lies_flat(self) -> None:
        expected = (
            generator.inches(self.config["structural"]["deck_thickness_in"])
            + generator.inches(1.0)
            + self.config["skin"]["tile_thickness_mm"]
            + self.config["fascia"]["fitting_clearance_mm"]
        )
        self.assertAlmostEqual(generator.fascia_opening_height(self.config), expected, places=6)
        cover = generator.fascia_outside_corner_cover(self.config)
        self.assertLessEqual(cover.extents[2], self.config["skin"]["fascia_outside_corner_cover_leg_mm"] + 1e-6)
        self.assertGreater(cover.extents[1], 70.0)


if __name__ == "__main__":
    unittest.main()
