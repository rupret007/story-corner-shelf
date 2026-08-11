#!/usr/bin/env python3
"""Exact layout, envelope, baseline, and fail-closed tests for R8."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


R8 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R8))

from design_math import calculate_plan, print_envelope, production_blockers  # noqa: E402


CONFIG_PATH = R8 / "config.json"
BASELINES_PATH = R8 / "FROZEN_BASELINES.json"


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )


def tree_digest(root: Path) -> tuple[int, int, str]:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and path.name != ".DS_Store"
    )
    aggregate = hashlib.sha256()
    total_bytes = 0
    for path in files:
        payload = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(payload).hexdigest()
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(len(payload)).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        total_bytes += len(payload)
    return len(files), total_bytes, aggregate.hexdigest()


def all_leaf_values(value: object) -> list[object]:
    if isinstance(value, dict):
        leaves: list[object] = []
        for child in value.values():
            leaves.extend(all_leaf_values(child))
        return leaves
    return [value]


class R8DesignMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = load_json(CONFIG_PATH)
        cls.baselines = load_json(BASELINES_PATH)
        cls.plan = calculate_plan(cls.cfg)

    def test_frozen_dimensions_and_petg_process(self) -> None:
        self.assertEqual(self.plan.depth_mm, 152.4)
        self.assertEqual(self.plan.cassette_height_mm, 30.0)
        self.assertEqual(self.plan.d_frame_envelope_mm, (152.4, 160.0, 32.0))
        frame = self.cfg["d_frame"]
        self.assertEqual(
            (frame["top_chord_mm"], frame["wall_chord_mm"], frame["curved_web_mm"]),
            (16.0, 16.0, 16.0),
        )
        self.assertEqual(frame["root_radius_mm"], 10.0)
        self.assertEqual(frame["shelf_bearing_cap_width_across_run_mm"], 32.0)
        self.assertEqual(self.cfg["material"]["primary_part_material"], "PETG")
        self.assertFalse(self.cfg["material"]["pla_allowed_in_primary_or_load_path_parts"])
        printing = self.cfg["printer"]
        self.assertEqual(printing["model"], "A1 mini")
        self.assertEqual(printing["printable_volume_mm"], [180.0, 180.0, 180.0])
        self.assertEqual(printing["nozzle_mm"], 0.4)
        self.assertEqual(printing["layer_height_mm"], 0.2)
        self.assertEqual(printing["wall_loops"], 6)
        self.assertEqual(printing["top_shell_layers"], 5)
        self.assertEqual(printing["bottom_shell_layers"], 3)
        self.assertEqual(printing["infill_percent"], 25)
        self.assertEqual(printing["infill_pattern"], "grid")
        self.assertEqual(printing["brim_mm"], 5.0)
        self.assertEqual(printing["brim_object_gap_mm"], 0.1)
        self.assertEqual(printing["filament_preset"], "SUNLU PETG @BBL A1M 0.4 nozzle")
        self.assertEqual(printing["filament_asin"], "B0D1KC72YP")
        self.assertEqual(
            printing["filament_product_url"],
            "https://www.amazon.com/dp/B0D1KC72YP?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1",
        )
        self.assertEqual(
            printing["filament_selected_variant"],
            "4 kg bundle; 2 Black + 2 Black (four 1 kg black spools); 1.75 mm +/-0.02 mm",
        )
        self.assertTrue(printing["filament_lot_record_required"])
        self.assertIsNone(printing["filament_lot"])
        self.assertEqual(printing["drying_temperature_range_c"], [50.0, 50.0])
        self.assertEqual(printing["drying_duration_range_h"], [6.0, 8.0])
        self.assertEqual(
            printing["drying_guidance_source_url"],
            "https://store.sunlu.com/products/over-6kg-bundle-sale-petg-3d-printer-filament-1-75mm-1kg-roll",
        )
        self.assertTrue(printing["drying_received_spool_label_controls"])
        self.assertTrue(printing["drying_dryer_limit_controls"])
        self.assertTrue(printing["drying_never_exceed_lower_stated_limit"])
        self.assertTrue(printing["drying_record_required"])
        self.assertIsNone(printing["drying_record"])
        self.assertEqual(
            (
                printing["first_layer_nozzle_temperature_c"],
                printing["other_layer_nozzle_temperature_c"],
                printing["textured_pei_bed_temperature_c"],
                printing["flow_ratio"],
                printing["maximum_volumetric_speed_mm3_s"],
            ),
            (250.0, 245.0, 60.0, 0.94, 9.0),
        )

    def test_material_docs_do_not_promise_matte_or_overheat_standard_petg(self) -> None:
        readme = (R8 / "README.md").read_text(encoding="utf-8")
        self.assertIn("Black is the color direction, not a guaranteed matte finish", readme)
        self.assertIn("not SUNLU High-Speed Matte PETG", readme)
        self.assertIn("lists **50 C** for a blast drying oven", readme)
        self.assertIn("never exceed the lower temperature limit", readme)
        self.assertIn("record the spool lot, dryer, temperature", readme)
        self.assertNotIn("Dry PETG at 60-65 C", readme)
        self.assertNotIn("selected matte-black", readme)

    def test_exact_run_layout_and_counts(self) -> None:
        through = self.plan.through
        return_run = self.plan.return_run
        self.assertEqual((through.length_mm, return_run.length_mm), (1514.475, 751.275))
        self.assertEqual(
            (through.cassette_module_count, through.corbel_count), (8, 9)
        )
        self.assertEqual(
            (return_run.cassette_module_count, return_run.corbel_count), (4, 5)
        )
        self.assertEqual(
            (through.terminal_corbel_center_inset_mm, return_run.terminal_corbel_center_inset_mm),
            (16.0, 16.0),
        )
        self.assertAlmostEqual(through.equal_corbel_pitch_mm, 185.309375, places=9)
        self.assertAlmostEqual(return_run.equal_corbel_pitch_mm, 179.81875, places=9)
        self.assertEqual(len(through.nominal_module_widths_mm), 8)
        self.assertEqual(len(return_run.nominal_module_widths_mm), 4)
        self.assertAlmostEqual(through.nominal_module_widths_mm[0], 201.309375, places=9)
        self.assertAlmostEqual(through.nominal_module_widths_mm[-1], 201.309375, places=9)
        self.assertTrue(
            all(
                abs(width - 185.309375) < 1.0e-9
                for width in through.nominal_module_widths_mm[1:-1]
            )
        )
        self.assertAlmostEqual(return_run.nominal_module_widths_mm[0], 195.81875, places=9)
        self.assertAlmostEqual(return_run.nominal_module_widths_mm[-1], 195.81875, places=9)
        self.assertTrue(
            all(
                abs(width - 179.81875) < 1.0e-9
                for width in return_run.nominal_module_widths_mm[1:-1]
            )
        )

    def test_every_seam_is_centered_on_a_32_mm_cap(self) -> None:
        seam = self.cfg["shelf"]["between_module_seam_mm"]
        self.assertEqual(seam, 0.35)
        for run in (self.plan.through, self.plan.return_run):
            self.assertEqual(run.seam_centers_mm, run.corbel_centers_mm[1:-1])
            self.assertEqual(len(run.seam_centers_mm), run.cassette_module_count - 1)
            self.assertEqual(run.corbel_cap_bounds_mm[0], (0.0, 32.0))
            self.assertAlmostEqual(run.corbel_cap_bounds_mm[-1][0], run.length_mm - 32.0)
            self.assertAlmostEqual(run.corbel_cap_bounds_mm[-1][1], run.length_mm)
            self.assertAlmostEqual(
                run.minimum_cap_bearing_each_side_of_seam_mm, 15.825, places=9
            )
            for index, seam_center in enumerate(run.seam_centers_mm, start=1):
                cap_left, cap_right = run.corbel_cap_bounds_mm[index]
                left_part_end = run.physical_module_bounds_mm[index - 1][1]
                right_part_start = run.physical_module_bounds_mm[index][0]
                self.assertAlmostEqual(seam_center - cap_left, 16.0, places=9)
                self.assertAlmostEqual(cap_right - seam_center, 16.0, places=9)
                self.assertAlmostEqual(right_part_start - left_part_end, seam, places=9)
                self.assertGreaterEqual(left_part_end - cap_left, 15.825 - 1.0e-9)
                self.assertGreaterEqual(cap_right - right_part_start, 15.825 - 1.0e-9)
            self.assertAlmostEqual(
                sum(run.physical_module_widths_mm) + seam * len(run.seam_centers_mm),
                run.length_mm,
                places=9,
            )

    def test_accessory_counts_are_derived_from_support_topology(self) -> None:
        through = self.plan.through
        return_run = self.plan.return_run
        self.assertEqual(through.accessory_eligible_corbel_indices, tuple(range(1, 8)))
        self.assertEqual(return_run.accessory_eligible_corbel_indices, tuple(range(1, 4)))
        self.assertNotIn(0, through.accessory_eligible_corbel_indices)
        self.assertNotIn(through.corbel_count - 1, through.accessory_eligible_corbel_indices)
        self.assertNotIn(0, return_run.accessory_eligible_corbel_indices)
        self.assertNotIn(return_run.corbel_count - 1, return_run.accessory_eligible_corbel_indices)
        expected_per_level = (through.corbel_count - 2) + (return_run.corbel_count - 2)
        self.assertEqual(self.plan.accessory_eligible_corbels_per_level, expected_per_level)
        self.assertEqual(
            self.plan.accessory_eligible_corbels_selected_levels,
            expected_per_level * self.plan.selected_level_count,
        )
        self.assertEqual(
            self.plan.accessory_socket_count_per_level,
            expected_per_level * self.cfg["accessory_system"]["sockets_per_eligible_corbel"],
        )
        self.assertEqual(self.plan.accessory_default_rails_per_level, 6)
        self.assertEqual(self.plan.accessory_default_rails_selected_levels, 12)
        self.assertEqual(self.plan.accessory_default_socket_count_per_level, 18)
        self.assertEqual(self.plan.accessory_default_socket_count_selected_levels, 36)
        self.assertEqual(self.plan.structural_corbels_per_level, 14)
        self.assertEqual(self.plan.structural_corbels_selected_levels, 28)
        self.assertEqual(self.plan.minimum_metal_screws_per_corbel, 3)
        self.assertEqual(self.plan.minimum_metal_screws_per_level, 42)
        self.assertEqual(self.plan.minimum_metal_screws_selected_levels, 84)

    def test_d_frame_and_edge_yawed_cassette_fit_a1_mini(self) -> None:
        envelope = self.plan.d_frame_saved_print_envelope
        self.assertEqual(envelope.part_mm, (156.4, 164.0, 32.0))
        self.assertEqual(envelope.with_brim_mm, (166.6, 174.2, 32.0))
        self.assertTrue(envelope.fits)
        self.assertEqual(
            dict(self.plan.cassette_flat_plate_fit_by_run),
            {"through": False, "return": False},
        )
        edge = dict(self.plan.cassette_edge_yaw_envelope_by_run)
        self.assertTrue(edge["through"].fits)
        self.assertTrue(edge["return"].fits)
        self.assertAlmostEqual(edge["through"].with_brim_mm[0], 177.6366839278, places=8)
        self.assertEqual(edge["through"].with_brim_mm[2], 152.4)
        orientation = self.cfg["shelf"]["cassette_saved_orientation_candidate"]
        self.assertTrue(orientation["software_envelope_proven"])
        self.assertFalse(orientation["physical_printability_qualified"])

    def test_brim_object_gap_is_part_of_each_bed_axis_footprint(self) -> None:
        without_gap = print_envelope(
            (20.0, 30.0, 40.0),
            printable_volume_mm=(180.0, 180.0, 180.0),
            brim_mm=5.0,
            brim_object_gap_mm=0.0,
        )
        with_gap = print_envelope(
            (20.0, 30.0, 40.0),
            printable_volume_mm=(180.0, 180.0, 180.0),
            brim_mm=5.0,
            brim_object_gap_mm=0.1,
        )
        self.assertEqual(without_gap.with_brim_mm, (30.0, 40.0, 40.0))
        self.assertEqual(with_gap.with_brim_mm, (30.2, 40.2, 40.0))
        for bad_gap in (-0.1, float("nan")):
            with self.subTest(bad_gap=bad_gap):
                with self.assertRaisesRegex(ValueError, "Brim-object gap"):
                    print_envelope(
                        (20.0, 30.0, 40.0),
                        printable_volume_mm=(180.0, 180.0, 180.0),
                        brim_mm=5.0,
                        brim_object_gap_mm=bad_gap,
                    )

    def test_unresolved_schema_uses_canonical_field_and_hardware_names(self) -> None:
        unresolved = self.cfg["unresolved_inputs"]
        self.assertEqual(
            tuple(unresolved["field"]),
            (
                "through_clear_length_mm",
                "return_clear_length_mm",
                "inside_corner_angle_deg",
                "maximum_wall_bow_mm",
                "corner_datum_uncertainty_mm",
                "lower_shelf_top_elevation_mm",
                "upper_shelf_top_elevation_mm",
                "door_trim_clearance_mm",
                "outlet_clearance_mm",
            ),
        )
        self.assertNotIn("substrate_thickness_mm", unresolved["wall"])
        for key in (
            "structural_screw_head_height_mm",
            "washer_inner_diameter_mm",
            "washer_thickness_mm",
            "wall_substrate_thickness_mm",
        ):
            self.assertIn(key, unresolved["hardware"])
            self.assertIsNone(unresolved["hardware"][key])

    def test_release_and_load_state_is_fail_closed(self) -> None:
        project = self.cfg["project"]
        self.assertTrue(project["qualification_only"])
        for key in (
            "installed_release_allowed",
            "physical_qualification_complete",
            "production_ready",
            "load_rating_allowed",
            "tested_load_rating_exists",
            "wall_bores_emitted",
            "embedded_gcode_allowed",
        ):
            self.assertFalse(project[key], key)
        self.assertEqual((project["rated_load_kg"], project["rated_load_lb"]), (0.0, 0.0))
        self.assertEqual(
            (
                self.cfg["accessory_system"]["rated_load_kg"],
                self.cfg["accessory_system"]["rated_load_lb"],
            ),
            (0.0, 0.0),
        )
        for group in ("wall", "hardware", "field"):
            self.assertTrue(
                all(value is None for value in all_leaf_values(self.cfg["unresolved_inputs"][group])),
                group,
            )
        blockers = production_blockers(self.cfg)
        self.assertIn("project.zero_rated_load", blockers)
        self.assertIn("unresolved_inputs.wall.construction", blockers)
        self.assertIn("unresolved_inputs.hardware.approved_fastener_schedule", blockers)
        self.assertIn(
            "unresolved_inputs.hardware.structural_screw_head_height_mm", blockers
        )
        self.assertIn("unresolved_inputs.hardware.washer_inner_diameter_mm", blockers)
        self.assertIn("unresolved_inputs.hardware.washer_thickness_mm", blockers)
        self.assertIn(
            "unresolved_inputs.hardware.wall_substrate_thickness_mm", blockers
        )
        self.assertIn("unresolved_inputs.field.through_clear_length_mm", blockers)
        self.assertIn("unresolved_inputs.field.return_clear_length_mm", blockers)
        self.assertIn("unresolved_inputs.field.inside_corner_angle_deg", blockers)
        self.assertIn("qualification.target_contents_load_lb", blockers)
        self.assertIn("printer.filament_lot", blockers)
        self.assertIn("printer.drying_record", blockers)
        self.assertIn("printer.flow_calibration_record", blockers)
        self.assertIn(
            "shelf.cassette_saved_orientation_candidate.physical_printability_qualified",
            blockers,
        )
        self.assertNotIn("shelf.cassette_edge_yaw_envelope_exceeds_a1_mini", blockers)
        self.assertIn(
            "shelf.selected_cassette_physical_qualification_complete", blockers
        )
        self.assertIn(
            "wall_attachment.continuous_blocking_or_verified_equivalent_confirmed",
            blockers,
        )
        self.assertGreaterEqual(len(blockers), 30)

    def test_r6_and_r7_frozen_tree_hashes_still_match(self) -> None:
        self.assertEqual(self.baselines["hash_algorithm"], "sha256")
        for revision in ("r6", "r7"):
            baseline = self.baselines["baselines"][revision]
            root = (R8 / baseline["path"]).resolve()
            observed_count, observed_bytes, observed_tree_hash = tree_digest(root)
            self.assertEqual(observed_count, baseline["file_count"], revision)
            self.assertEqual(observed_bytes, baseline["byte_count"], revision)
            self.assertEqual(observed_tree_hash, baseline["tree_sha256"], revision)
            self.assertEqual(
                hashlib.sha256((root / "config.json").read_bytes()).hexdigest(),
                baseline["config_sha256"],
                revision,
            )


if __name__ == "__main__":
    unittest.main()
