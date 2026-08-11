#!/usr/bin/env python3
"""Authoritative physical-object inventory regressions for Story Corner r6."""

from __future__ import annotations

import csv
import io
import json
import sys
import unittest
from collections import Counter
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from design_math import calculate_plan  # noqa: E402
from release_inventory import (  # noqa: E402
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS,
    ORIENTATIONS,
    ORNAMENT_BLUEPRINT_FAMILY_COUNTS,
    PROVISIONAL_STATUS,
    count_by,
    count_integral_features,
    enumerate_integral_features,
    enumerate_level_inventory,
    enumerate_selected_integral_features,
    enumerate_selected_inventory,
    integral_features_to_json,
    inventory_reconciliation,
    records_to_csv,
    records_to_json,
    selected_level_specs,
)


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


class R6ReleaseInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(
            (R6 / "config.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
        cls.plan = calculate_plan(cls.cfg)
        cls.lower = enumerate_level_inventory(cls.cfg, "lower", cls.plan)
        cls.selected = enumerate_selected_inventory(cls.cfg, cls.plan)

    def test_unique_positive_unit_records_and_exact_totals(self) -> None:
        self.assertEqual(len(self.lower), 258)
        self.assertEqual(len({item.logical_id for item in self.lower}), 258)
        self.assertTrue(all(item.quantity == 1 for item in self.lower))
        self.assertEqual(len(self.selected), 516)
        self.assertEqual(len({item.logical_id for item in self.selected}), 516)
        self.assertEqual(count_by(self.selected, "level"), {"lower": 258, "upper": 258})

    def test_retention_and_ornament_orientations_use_current_physical_topology(self) -> None:
        keeper = ORIENTATIONS["keeper"].lower()
        ornament = ORIENTATIONS["ornament"].lower()
        crown_pin = ORIENTATIONS["pin"].lower()
        self.assertIn("one rear-bayonet tongue", keeper)
        self.assertIn("separate keeper-reach indexed quarter-turn pin", keeper)
        self.assertIn("actual-parent receiver orientation", keeper)
        self.assertIn("decorated d=0 face", ornament)
        self.assertIn("receiver housings upward", ornament)
        self.assertIn("not a flat-back print", ornament)
        self.assertIn("shaft axis parallel to the build plate", crown_pin)
        self.assertIn("split plane perpendicular to the plate", crown_pin)
        self.assertIn("round head and circular cross-section vertical/tangent", crown_pin)
        for obsolete in (
            "integral flex hooks",
            "integral catches",
            "flat carrier back",
            "shaft vertical",
        ):
            self.assertNotIn(obsolete, keeper + "\n" + ornament + "\n" + crown_pin)

    def test_ornament_mapping_status_separates_software_from_physical_release(self) -> None:
        status = self.cfg["nominal_geometry_snapshot"][
            "baseline_complete_physical_object_counts"
        ]["ornament_connector_release_status"]
        self.assertIn("SOFTWARE_MODEL_MAPPING_COMPLETE_AFTER_GENERATOR_RUNTIME_PROOF", status)
        self.assertIn("physical actual-parent-orientation coupons", status)
        self.assertIn("production release remain blocked", status)
        self.assertNotIn("BLOCKED until all eight per-parent boss placement maps", status)

    def test_two_levels_are_exact_independent_doubles(self) -> None:
        lower = [item for item in self.selected if item.level == "lower"]
        upper = [item for item in self.selected if item.level == "upper"]
        normalized_lower = sorted(
            (item.logical_id.replace("lower::", "LEVEL::", 1), item.family, item.variant)
            for item in lower
        )
        normalized_upper = sorted(
            (item.logical_id.replace("upper::", "LEVEL::", 1), item.family, item.variant)
            for item in upper
        )
        self.assertEqual(normalized_lower, normalized_upper)
        self.assertTrue(all(item.level_independent for item in self.selected))

    def test_exact_family_taxonomy_reconciles_225_plus_33(self) -> None:
        families = count_by(self.lower, "family")
        self.assertEqual(families, EXPECTED_ONE_LEVEL_FAMILY_COUNTS)
        ornament = sum(
            quantity
            for family, quantity in families.items()
            if family in ORNAMENT_BLUEPRINT_FAMILY_COUNTS
        )
        self.assertEqual(ornament, 33)
        self.assertEqual(sum(families.values()) - ornament, 225)
        self.assertEqual(sum(families.values()), 258)
        reconciliation = inventory_reconciliation(self.cfg, self.lower)
        self.assertEqual(reconciliation["contradictions"], [])
        self.assertEqual(reconciliation["physical_count_ambiguities"], [])
        selected_reconciliation = inventory_reconciliation(self.cfg, self.selected)
        self.assertEqual(selected_reconciliation["contradictions"], [])
        self.assertEqual(selected_reconciliation["physical_object_count"], 516)
        self.assertFalse(reconciliation["production_release_allowed"])
        self.assertFalse(reconciliation["tested_load_rating_exists"])

    def test_bays_cassettes_arch_handed_families_and_supports(self) -> None:
        families = count_by(self.lower, "family")
        self.assertEqual(families["deck_cassette"], 18)
        self.assertEqual(families["arcade_half"], 18)
        self.assertEqual(
            Counter(item.variant for item in self.lower if item.family == "arcade_half"),
            {
                "through_left_half": 6,
                "through_right_half": 6,
                "return_left_half": 3,
                "return_right_half": 3,
            },
        )
        support_records = [
            item for item in self.lower if item.family == "structural_pier_x_corbel"
        ]
        self.assertEqual(
            Counter(item.run for item in support_records),
            {"long_wall_5ft": 7, "short_wall_3ft": 4},
        )
        self.assertNotIn("sliding_saddle", families)
        self.assertNotIn("saddle_pin", families)
        self.assertEqual(families["cassette_lock"], 22)

        # Arcade placement is the installed spring/support datum, never the
        # cassette interval start. Handed transforms then run toward crown.
        first_arch = next(
            item
            for item in self.lower
            if item.logical_id == "lower::long_wall_5ft::arcade_half::01"
        )
        self.assertAlmostEqual(first_arch.position_local_mm, 31.4325, places=7)
        self.assertNotEqual(first_arch.position_local_mm, 0.0)

    def test_seams_keys_bridges_and_wedges_are_actual_objects(self) -> None:
        families = count_by(self.lower, "family")
        self.assertEqual(families["cassette_top_retention_wedge"], 36)
        self.assertEqual(families["spring_retention_wedge"], 18)
        self.assertEqual(families["diaphragm_bowtie_key"], 48)
        self.assertEqual(families["fixed_crown_diaphragm_keeper_strip"], 9)
        self.assertEqual(families["fixed_crown_entablature_tie_key"], 9)
        self.assertNotIn("floating_pier_entablature_alignment_key", families)
        self.assertEqual(families["crown_bridge"], 9)
        self.assertEqual(families["crown_bridge_retention_pin"], 9)
        self.assertEqual(families["indexed_vertical_quarter_turn_pin"], 18)
        shared_pins = [
            item
            for item in self.lower
            if item.family == "indexed_vertical_quarter_turn_pin"
        ]
        self.assertEqual(
            Counter(item.variant for item in shared_pins),
            {"keeper_reach": 9, "front_tie_reach": 9},
        )
        self.assertEqual(
            Counter(item.run for item in shared_pins),
            {"long_wall_5ft": 12, "short_wall_3ft": 6},
        )
        shared_pin_source = self.cfg["joinery"][
            "shared_keeper_and_front_tie_quarter_turn_pin"
        ]
        self.assertTrue(shared_pin_source["software_model_mapping_contract_required"])
        self.assertFalse(shared_pin_source["physical_installation_mapping_qualified"])
        self.assertFalse(shared_pin_source["production_release_eligible"])
        parent_by_id = {item.logical_id: item for item in self.lower}
        for pin in shared_pins:
            self.assertIn(pin.interface_ref, parent_by_id)
            parent = parent_by_id[pin.interface_ref]
            expected_parent_family = (
                "fixed_crown_diaphragm_keeper_strip"
                if pin.variant == "keeper_reach"
                else "fixed_crown_entablature_tie_key"
            )
            self.assertEqual(parent.family, expected_parent_family)
            self.assertEqual(parent.level, pin.level)
            self.assertEqual(parent.run, pin.run)
            self.assertAlmostEqual(parent.position_local_mm, pin.position_local_mm)
        explicit_zero = {
            "cassette_top_retention_wedge",
            "spring_retention_wedge",
            "crown_bridge_retention_pin",
            "fixed_crown_diaphragm_keeper_strip",
            "indexed_vertical_quarter_turn_pin",
        }
        self.assertTrue(
            all(
                item.zero_structural_credit and item.zero_credit_scope
                for item in self.lower
                if item.family in explicit_zero
            )
        )

    def test_disconnected_stitch_rail_study_is_not_in_installed_baseline(self) -> None:
        families = count_by(self.lower, "family")
        self.assertNotIn("stitch_rail_segment", families)
        self.assertNotIn("stitch_rail_joint_pin", families)
        self.assertNotIn("run_end_tie_block", families)
        self.assertFalse(
            any("stitch_rail" in item.logical_id or "run_end_tie" in item.logical_id for item in self.selected)
        )

    def test_ornament_contract_is_18_plus_11_plus_2_plus_2(self) -> None:
        actual = {
            family: count_by(self.lower, "family")[family]
            for family in ORNAMENT_BLUEPRINT_FAMILY_COUNTS
        }
        self.assertEqual(actual, ORNAMENT_BLUEPRINT_FAMILY_COUNTS)
        ornaments = [item for item in self.lower if item.classification == "ornament"]
        self.assertEqual(len(ornaments), 33)
        self.assertTrue(all(item.zero_structural_credit for item in ornaments))
        self.assertEqual(len(ORNAMENT_BLUEPRINT_FAMILY_COUNTS), 8)
        corner = [
            item
            for item in ornaments
            if item.family in {"corner_fixed_rosette", "corner_floating_mate"}
        ]
        self.assertEqual(
            {item.variant for item in corner},
            {"through_fixed_nine_petal_rosette", "return_floating_mate"},
        )

    def test_integral_tenons_and_receivers_are_not_physical_objects(self) -> None:
        features = enumerate_integral_features(self.cfg, "lower", self.plan)
        self.assertEqual(
            count_integral_features(features),
            {
                "cassette_open_bottom_receiver": 36,
                "cassette_vertical_tenon": 36,
                "spring_open_bottom_receiver": 18,
                "spring_vertical_tenon": 18,
            },
        )
        self.assertTrue(all(not item.printed_separately for item in features))
        selected = enumerate_selected_integral_features(self.cfg, self.plan)
        self.assertEqual(len(selected), 216)
        self.assertFalse(
            {item.feature_family for item in selected}
            & set(count_by(self.selected, "family"))
        )
        self.assertEqual(
            json.loads(integral_features_to_json(features))[0]["quantity"], 1
        )

    def test_no_cross_level_tie_wall_bore_or_printed_anchor_part(self) -> None:
        forbidden = ("cross_level", "vertical_tie", "wall_bore", "wall_anchor")
        for item in self.selected:
            searchable = f"{item.logical_id} {item.family} {item.variant}".lower()
            self.assertFalse(any(token in searchable for token in forbidden), searchable)
        rule = self.cfg["closet"]["vertical_layout"]["level_independence_rule"]
        self.assertIn("no printed column, rail, arch, or key transfers", rule)
        self.assertFalse(self.cfg["support"]["printed_wall_anchors_allowed"])
        self.assertFalse(self.cfg["corbel"]["production_fastener_geometry_allowed"])

    def test_status_and_selected_placements_remain_provisional(self) -> None:
        self.assertTrue(
            all(item.provisional_status == PROVISIONAL_STATUS for item in self.selected)
        )
        levels = selected_level_specs(self.cfg)
        self.assertEqual(
            [(level.level_id, level.shelf_top_offset_above_outlet_in) for level in levels],
            [("lower", 12.0), ("upper", 33.0)],
        )
        self.assertTrue(all(level.placement_status == "PROVISIONAL" for level in levels))
        self.assertFalse(self.cfg["project"]["production_release_allowed"])
        self.assertFalse(self.cfg["test_protocol"]["tested_load_rating_exists"])

    def test_json_and_csv_serializers_are_deterministic_and_complete(self) -> None:
        json_a = records_to_json(self.lower)
        json_b = records_to_json(tuple(self.lower))
        self.assertEqual(json_a, json_b)
        self.assertEqual(len(json.loads(json_a)), 258)
        csv_a = records_to_csv(self.lower)
        csv_b = records_to_csv(tuple(self.lower))
        self.assertEqual(csv_a, csv_b)
        rows = list(csv.DictReader(io.StringIO(csv_a)))
        self.assertEqual(len(rows), 258)
        self.assertEqual({row["quantity"] for row in rows}, {"1"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
