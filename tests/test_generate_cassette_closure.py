#!/usr/bin/env python3
"""Real-mesh regressions for the r6 position-specific two-skin cassettes."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import trimesh


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


def horizontal_section_area(mesh: trimesh.Trimesh, z_mm: float) -> float:
    section = mesh.section(
        plane_origin=(0.0, 0.0, z_mm),
        plane_normal=(0.0, 0.0, 1.0),
    )
    if section is None:
        return 0.0
    planar, _transform = section.to_2D()
    return float(planar.area)


def horizontal_slab_area(
    mesh: trimesh.Trimesh, z_mm: float, thickness_mm: float = 0.2
) -> float:
    bounds = np.asarray(mesh.bounds, dtype=float)
    probe = generator.cuboid(
        (
            float(bounds[1][0] - bounds[0][0]),
            float(bounds[1][1] - bounds[0][1]),
            thickness_mm,
        ),
        origin=(
            float(bounds[0][0]),
            float(bounds[0][1]),
            z_mm - thickness_mm / 2.0,
        ),
    )
    intersection = trimesh.boolean.intersection(
        [mesh, probe], engine="manifold", check_volume=True
    )
    return abs(float(intersection.volume)) / thickness_mm


def probe_intersection_volume(
    mesh: trimesh.Trimesh,
    *,
    center_x: float,
    center_y: float,
    z0: float,
    size: float = 0.4,
) -> float:
    probe = generator.cuboid(
        (size, size, size),
        origin=(center_x - size / 2.0, center_y - size / 2.0, z0),
    )
    intersection = trimesh.boolean.intersection(
        [mesh, probe], engine="manifold", check_volume=True
    )
    if intersection is None or len(intersection.faces) == 0:
        return 0.0
    return abs(float(intersection.volume))


class R6CassetteClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(
            (R6 / "config.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
        geometry, _warnings = generator.calculate_development_geometry(cls.cfg)
        cls.plan = geometry["plan_object"]
        cls.parts, cls.report = generator.cassette_chassis_family(
            cls.cfg, plan=cls.plan
        )

    def test_generator_imports_project_owned_neutral_helpers_not_r5(self) -> None:
        source = (R6 / "generate_all_petg_r6.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        self.assertIn("model_io", imported_modules)
        self.assertFalse(
            any("reference.hybrid" in module or module.endswith("generate_all_petg") for module in imported_modules)
        )

    def test_all_18_are_watertight_single_surface_bodies_and_exact_envelopes(self) -> None:
        self.assertEqual(len(self.parts), 18)
        self.assertEqual(len({part.name for part in self.parts}), 18)
        for part in self.parts:
            metrics = part.design_metrics
            mesh = part.mesh
            self.assertTrue(mesh.is_watertight, part.name)
            self.assertTrue(mesh.is_winding_consistent, part.name)
            self.assertTrue(mesh.is_volume, part.name)
            self.assertEqual(len(mesh.split(only_watertight=False)), 1, part.name)
            self.assertTrue(
                np.allclose(
                    mesh.extents,
                    metrics["overall_saved_envelope_mm"],
                    atol=1.0e-4,
                    rtol=0.0,
                ),
                part.name,
            )
            self.assertAlmostEqual(
                mesh.extents[0], metrics["exact_physical_width_mm"], delta=1.0e-4
            )
            self.assertAlmostEqual(metrics["depth_mm"], 152.4, places=7)
            self.assertEqual(metrics["height_mm"], 30.0)
            self.assertTrue(metrics["configured_bottom_skin_present"])
            self.assertLessEqual(metrics["maximum_actual_clear_coffer_span_mm"], 14.0)
            self.assertFalse(metrics["separate_longitudinal_rail_bypass_present"])
            for seam in metrics["seams"].values():
                self.assertEqual(
                    seam["receiver_pocket_count"],
                    {
                        "outer_end": 0,
                        "floating_supported_pier": 3,
                        "fixed_crown": 4,
                    }[seam["class"]],
                    part.name,
                )

    def test_connected_access_corridors_are_not_reported_as_independent_collisions(self) -> None:
        self.assertEqual(
            self.report["expected_connected_access_corridor_count_all_18"],
            9,
        )
        self.assertEqual(self.report["connected_access_corridor_count_all_18"], 9)
        self.assertEqual(
            self.report["independent_underside_access_collision_count_all_18"],
            0,
        )
        self.assertGreaterEqual(
            self.report[
                "minimum_pairwise_independent_underside_access_plan_ligament_mm"
            ],
            3.2,
        )
        self.assertTrue(self.report["software_chassis_geometry_complete"])
        self.assertFalse(self.report["physical_chassis_qualification_complete"])
        self.assertNotIn("release_chassis_geometry_complete", self.report)
        for part in self.parts:
            metrics = part.design_metrics
            self.assertEqual(
                metrics["connected_access_corridor_count"],
                metrics["expected_connected_access_corridor_count"],
                part.name,
            )
            self.assertEqual(
                metrics["independent_underside_access_collision_count"],
                0,
                part.name,
            )
            self.assertGreaterEqual(
                metrics[
                    "minimum_pairwise_independent_underside_access_plan_ligament_mm"
                ],
                3.2,
                part.name,
            )
            for corridor in metrics["connected_access_corridors"]:
                self.assertEqual(
                    corridor["classification"],
                    "expected same-channel entry-to-final-throat corridor",
                    part.name,
                )

    def test_all_18_individual_stl_and_model_only_3mf_exports_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-cassettes-") as directory:
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
            self.assertEqual(len(list(stl_output.glob("R6_DEV_*.stl"))), 18)
            self.assertEqual(len(list(individual_output.glob("*.3mf"))), 18)
            self.assertEqual(len(list(model_output.glob("*.3mf"))), 0)
            self.assertEqual(first, second)
            self.assertTrue(all(item["model_only_audit_passed"] for item in audits))
            self.assertTrue(all(not item["embedded_gcode_entries"] for item in audits))

    def test_integrated_cap_pockets_embody_fixed_and_floating_thermal_ownership(self) -> None:
        configured_travel = float(
            self.cfg["corbel"]["floating_pier_total_axial_travel_mm"]
        )
        self.assertEqual(
            configured_travel,
            float(
                self.cfg["corbel"][
                    "floating_pier_lock_slot_total_axial_travel_mm"
                ]
            ),
        )
        floating_pockets = 0
        tight_pockets = 0
        for part in self.parts:
            self.assertGreaterEqual(
                part.design_metrics[
                    "minimum_saddle_locator_to_seam_receiver_plan_ligament_mm"
                ],
                3.2,
                part.name,
            )
            for pocket in part.design_metrics["saddle_locator_pockets"]:
                self.assertEqual(pocket["pocket_depth_along_shelf_mm"], 11.3)
                self.assertIn(pocket["center_y_from_rear_mm"], (57.55, 95.45))
                if pocket["floating_total_axial_travel_mm"] > 0.0:
                    self.assertEqual(pocket["pocket_width_along_run_mm"], 12.0)
                    self.assertEqual(
                        pocket["floating_total_axial_travel_mm"], configured_travel
                    )
                    self.assertIn("floating", pocket["thermal_ownership"])
                    floating_pockets += 1
                else:
                    self.assertEqual(pocket["pocket_width_along_run_mm"], 10.8)
                    self.assertEqual(pocket["floating_total_axial_travel_mm"], 0.0)
                    tight_pockets += 1
        self.assertEqual(floating_pockets, 18)
        self.assertEqual(tight_pockets, 18)

    def test_floating_receiver_travel_requires_the_active_corbel_contract(self) -> None:
        missing = copy.deepcopy(self.cfg)
        del missing["corbel"]["floating_pier_total_axial_travel_mm"]
        with self.assertRaises((KeyError, ValueError)):
            generator.cassette_chassis_family(missing, plan=self.plan)

        mismatched = copy.deepcopy(self.cfg)
        mismatched["corbel"]["floating_pier_total_axial_travel_mm"] = 1.4
        with self.assertRaises(ValueError):
            generator.cassette_chassis_family(mismatched, plan=self.plan)

    def test_each_bay_has_one_tight_cornerward_and_one_floating_outboard_endpoint(self) -> None:
        by_run: dict[str, list[object]] = {}
        for part in self.parts:
            by_run.setdefault(str(part.design_metrics["run_id"]), []).append(part)
        self.assertEqual({key: len(value) for key, value in by_run.items()}, {
            "long_wall_5ft": 12,
            "short_wall_3ft": 6,
        })
        checked_bays = 0
        for run_parts in by_run.values():
            ordered = sorted(
                run_parts,
                key=lambda part: int(part.design_metrics["position_index_1_based"]),
            )
            for index in range(0, len(ordered), 2):
                cornerward = ordered[index]
                outboard = ordered[index + 1]
                cornerward_modes = {
                    float(record["floating_total_axial_travel_mm"])
                    for record in cornerward.design_metrics["saddle_locator_pockets"]
                }
                outboard_modes = {
                    float(record["floating_total_axial_travel_mm"])
                    for record in outboard.design_metrics["saddle_locator_pockets"]
                }
                self.assertEqual(cornerward_modes, {0.0}, cornerward.name)
                self.assertEqual(outboard_modes, {1.2}, outboard.name)
                checked_bays += 1
        self.assertEqual(checked_bays, 9)

    def test_all_22_lock_receivers_have_real_tail_chambers_and_exact_thermal_modes(self) -> None:
        records = [
            record
            for part in self.parts
            for record in part.design_metrics[
                "integrated_cap_cassette_lock_receivers"
            ]
        ]
        self.assertEqual(len(records), 22)
        self.assertEqual(
            sum(record["floating_total_axial_travel_mm"] == 1.2 for record in records),
            11,
        )
        self.assertEqual(
            sum(record["floating_total_axial_travel_mm"] == 0.0 for record in records),
            11,
        )
        for record in records:
            self.assertTrue(record["open_bottom_insertion"])
            self.assertTrue(record["positive_tail_capture_modeled"])
            self.assertEqual(record["tail_capture_shoulder_local_z_envelope_mm"], [7.4, 10.6])
            self.assertEqual(record["tail_expansion_chamber_local_z_envelope_mm"], [10.6, 13.8])

    def test_saved_build_face_is_the_real_continuous_top_skin_not_ribs(self) -> None:
        for part in self.parts:
            metrics = part.design_metrics
            top_skin = float(metrics["top_skin_mm"])
            width = float(metrics["exact_physical_width_mm"])
            depth = float(metrics["depth_mm"])
            # A horizontal cut halfway through saved z=0..top_skin must be one
            # completely filled rectangle.  Ribs alone cannot pass this test.
            actual_area = horizontal_section_area(part.mesh, top_skin / 2.0)
            self.assertAlmostEqual(actual_area, width * depth, delta=0.02, msg=part.name)
            transform = np.asarray(
                metrics["saved_print_transform"]["saved_from_installed_matrix_row_major"],
                dtype=float,
            )
            self.assertTrue(np.allclose(transform @ transform, np.eye(4), atol=1.0e-9))
            self.assertTrue(np.allclose(transform[0], [1.0, 0.0, 0.0, 0.0]))

    def test_installed_bottom_skin_is_real_material_with_local_real_voids(self) -> None:
        required_categories = {
            "diaphragm_seam_receiver",
            "final_x_top_tenon_receiver",
            "saddle_locator_receiver",
            "upper_x_buffered_cradle",
            "coffer_pressure_equalization_vent",
        }
        observed_categories: set[str] = set()
        for part in self.parts:
            metrics = part.design_metrics
            installed = part.mesh.copy()
            installed.apply_transform(
                np.asarray(
                    metrics["saved_print_transform"][
                        "installed_from_saved_matrix_row_major"
                    ],
                    dtype=float,
                )
            )
            bottom_skin = float(metrics["bottom_skin_mm"])
            width = float(metrics["exact_physical_width_mm"])
            depth = float(metrics["depth_mm"])
            area = horizontal_slab_area(installed, bottom_skin / 2.0)
            self.assertGreater(area, 0.45 * width * depth, part.name)
            self.assertLess(area, width * depth, part.name)
            for record in metrics["localized_underside_access_openings"]:
                category = str(record["category"])
                observed_categories.add(category)
                if category in required_categories:
                    x0, x1 = record["x_interval_mm"]
                    y0, y1 = record["y_interval_from_rear_mm"]
                    volume = probe_intersection_volume(
                        installed,
                        center_x=(float(x0) + float(x1)) / 2.0,
                        center_y=(float(y0) + float(y1)) / 2.0,
                        z0=bottom_skin / 2.0 - 0.2,
                    )
                    self.assertLess(volume, 1.0e-7, f"{part.name}: {record['source']}")
        self.assertTrue(required_categories.issubset(observed_categories))

    def test_fixed_crown_front_tie_receivers_are_front_open_not_bottom_inserted(self) -> None:
        checked = 0
        for part in self.parts:
            metrics = part.design_metrics
            installed = part.mesh.copy()
            installed.apply_transform(
                np.asarray(
                    metrics["saved_print_transform"][
                        "installed_from_saved_matrix_row_major"
                    ],
                    dtype=float,
                )
            )
            width = float(metrics["exact_physical_width_mm"])
            for side in metrics["receiver_sides"]:
                for pocket in side["pockets"]:
                    if pocket["type"] != "front_entablature_visible_front_inserted":
                        continue
                    self.assertEqual(
                        [pocket["front_open_q_min_mm"], pocket["front_open_q_max_mm"]],
                        [134.4, 152.4],
                    )
                    self.assertFalse(
                        pocket["positive_catch_receiver_notches_generated"]
                    )
                    face_x = 0.0 if side["side"] == "left" else width
                    inward = 4.0 if side["side"] == "left" else -4.0
                    self.assertLess(
                        probe_intersection_volume(
                            installed,
                            center_x=face_x + inward,
                            center_y=151.8,
                            z0=5.8,
                        ),
                        1.0e-7,
                        part.name,
                    )
                    checked += 1
        self.assertEqual(checked, 18)

    def test_upper_x_cradle_is_a_real_open_bottom_void_below_the_top_skin(self) -> None:
        for part in self.parts:
            metrics = part.design_metrics
            cradle = metrics["upper_x_buffered_cradle"]
            self.assertTrue(cradle["generated"])
            self.assertTrue(cradle["open_bottom"])
            self.assertFalse(cradle["continuous_top_skin_cut"])
            self.assertAlmostEqual(cradle["maximum_q_from_rear_mm"], 25.383333, places=6)
            self.assertGreaterEqual(
                metrics["upper_x_cradle_to_first_diaphragm_plan_ligament_mm"],
                3.2,
            )
            self.assertGreaterEqual(
                cradle["minimum_solid_to_top_surface_mm"],
                cradle["configured_minimum_top_skin_clearance_mm"],
            )
            installed = part.mesh.copy()
            installed.apply_transform(
                np.asarray(
                    metrics["saved_print_transform"][
                        "installed_from_saved_matrix_row_major"
                    ],
                    dtype=float,
                )
            )
            x0, x1 = cradle["run_interval_relative_to_physical_part_mm"]
            x = (float(x0) + float(x1)) / 2.0
            # The cradle is open at the bottom through its q interval.
            self.assertLess(
                probe_intersection_volume(
                    installed,
                    center_x=x,
                    center_y=5.0,
                    z0=0.2,
                ),
                1.0e-7,
                part.name,
            )
            # The continuous top skin remains real material directly above it.
            top_probe = generator.cuboid(
                (0.4, 0.4, 0.4),
                origin=(x - 0.2, 5.0 - 0.2, metrics["height_mm"] - 1.8),
            )
            overlap = trimesh.boolean.intersection(
                [installed, top_probe], engine="manifold", check_volume=True
            )
            self.assertIsNotNone(overlap, part.name)
            self.assertGreater(abs(float(overlap.volume)), 0.05, part.name)

    def test_sparse_coffer_network_prevents_trapped_internal_shells(self) -> None:
        for part in self.parts:
            metrics = part.design_metrics
            retained = metrics["coffer_void_components_retained_count"]
            solidified = metrics[
                "coffer_components_solidified_to_preserve_ligament_count"
            ]
            self.assertEqual(
                retained + solidified,
                metrics["coffer_void_component_count"],
                part.name,
            )
            # Every retained cell is connected by a deterministic spanning tree,
            # and the complete network has one printable exterior vent.  Existing
            # receiver openings may also intersect cells, but are not double-counted
            # as separate coffer vents.
            self.assertEqual(
                metrics["coffer_internal_communication_port_count"],
                retained - 1,
                part.name,
            )
            self.assertEqual(metrics["coffer_pressure_equalization_vent_count"], 1)
            self.assertGreaterEqual(
                metrics["coffer_pressure_equalization_vent_diameter_mm"], 3.2
            )
            self.assertGreaterEqual(metrics["coffer_vent_minimum_edge_ligament_mm"], 3.2)
            self.assertGreaterEqual(
                metrics["coffer_internal_communication_minimum_skin_ligament_mm"],
                3.2,
            )
            self.assertTrue(
                metrics["coffer_internal_communication_grid_adjacency_only"]
            )
            self.assertEqual(
                metrics[
                    "coffer_internal_communication_maximum_grid_ribs_crossed_per_port"
                ],
                1,
            )
            self.assertLessEqual(
                metrics["coffer_internal_communication_maximum_rib_span_mm"],
                3.2 + 1.0e-6,
            )
            self.assertGreaterEqual(
                metrics[
                    "coffer_internal_communication_minimum_current_keepout_clearance_mm"
                ],
                3.2,
            )
            self.assertEqual(
                metrics["coffer_internal_communication_land_intersection_area_mm2"],
                0.0,
            )
            self.assertEqual(
                metrics[
                    "coffer_internal_communication_access_intersection_area_mm2"
                ],
                0.0,
            )
            self.assertIn("no per-cell microvent array", metrics["coffer_network_policy"])

    def test_positive_cross_keys_have_exact_broad_flat_saved_envelope_and_inverse_transform(self) -> None:
        wedges = generator.final_x_retention_wedges(self.cfg, selected_levels=2)
        self.assertEqual(len(wedges), 2)
        saved_contract = self.cfg["tied_arcade"]["retention_wedge"][
            "saved_print_orientation"
        ]
        expected_bare = np.asarray(saved_contract["bare_key_envelope_mm"], dtype=float)
        expected_brim = [
            float(value) for value in saved_contract["envelope_with_brim_mm"]
        ]
        handle = self.cfg["tied_arcade"]["retention_wedge"][
            "visible_handle_and_positive_index"
        ]
        for wedge in wedges:
            metrics = wedge.design_metrics
            self.assertTrue(
                np.allclose(wedge.mesh.extents, expected_bare, atol=1.0e-6)
            )
            actual_contact = horizontal_slab_area(wedge.mesh, 0.1, thickness_mm=0.1)
            self.assertGreater(actual_contact, 45.0)
            saved = np.asarray(
                metrics["saved_from_installed_matrix_row_major"], dtype=float
            )
            installed = np.asarray(
                metrics["installed_from_saved_matrix_row_major"], dtype=float
            )
            self.assertTrue(np.allclose(saved @ installed, np.eye(4), atol=1.0e-9))
            self.assertTrue(metrics["fits_180_mm_envelope_with_recommended_brim"])
            self.assertEqual(
                metrics["optional_brim_bounding_envelope_mm"],
                expected_brim,
            )
            self.assertEqual(metrics["family_id"], "positive_quarter_turn_cross_key")
            self.assertFalse(metrics["legacy_straight_wedge_present"])
            self.assertTrue(metrics["positive_quarter_turn_bayonet_encoded"])
            self.assertFalse(metrics["production_orientation_allowed"])
            self.assertTrue(
                np.allclose(
                    metrics["authored_folded_u_centerline_segment_lengths_mm"],
                    handle["authored_folded_u_centerline_segment_lengths_mm"],
                    atol=1.0e-7,
                    rtol=0.0,
                )
            )
            self.assertAlmostEqual(
                metrics["integral_u_routed_flexure_developed_length_mm"],
                float(handle["authored_folded_u_centerline_length_mm"]),
                places=7,
            )
            self.assertAlmostEqual(
                metrics["conservative_effective_flexure_length_mm"],
                float(handle["integral_u_flexure_developed_length_mm"]),
                places=7,
            )
            self.assertAlmostEqual(
                metrics["computed_nominal_outer_fiber_strain"],
                float(handle["nominal_outer_fiber_strain"]),
                places=12,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
