#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import unittest


R10_ROOT = Path(__file__).resolve().parents[1]
if str(R10_ROOT) not in sys.path:
    sys.path.insert(0, str(R10_ROOT))

import release_status  # noqa: E402


class R10ReleaseStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pending = release_status.build_release_status()

    def test_pending_bundle_fails_closed_across_all_release_transitions(self) -> None:
        self.assertFalse(self.pending["qualification_bundle_analytically_complete"])
        self.assertFalse(self.pending["all_physical_gates_complete"])
        self.assertFalse(self.pending["production_ready"])
        self.assertFalse(self.pending["wall_installation_authorized"])
        self.assertFalse(self.pending["drilling_schedule_released"])
        self.assertFalse(self.pending["print_authorized"])
        self.assertTrue(
            self.pending["fresh_human_permission_required_before_every_print"]
        )
        self.assertEqual(
            (self.pending["rated_load_kg"], self.pending["rated_load_lb"]),
            (0.0, 0.0),
        )

    def test_config_geometry_and_cable_contracts_are_independently_visible(self) -> None:
        self.assertTrue(self.pending["config_gate"]["passed"])
        self.assertEqual(
            self.pending["config_gate"]["canonical_config_sha256"],
            release_status.EXPECTED_R10_CONFIG_CANONICAL_SHA256,
        )
        self.assertTrue(self.pending["geometry_gate"]["passed"])
        self.assertTrue(self.pending["cable_gate"]["passed"])
        self.assertTrue(
            self.pending["geometry_gate"]["checks"][
                "frozen_geometry_source_hash_matches"
            ]
        )
        self.assertTrue(
            self.pending["cable_gate"]["checks"][
                "frozen_cable_source_hash_matches"
            ]
        )
        self.assertEqual(len(self.pending["geometry_gate"]["one_bay_part_names"]), 12)
        self.assertEqual(len(self.pending["cable_gate"]["saved_part_names"]), 4)
        self.assertGreater(
            len(self.pending["config_gate"]["open_physical_gates"]), 0
        )
        self.assertIn(
            "no deterministic R10 qualification bundle was supplied",
            self.pending["open_release_blockers"],
        )

    def test_complete_neutral_artifact_gate_does_not_self_authorize_printing(self) -> None:
        artifact = release_status.complete_artifact_gate(
            individual_mesh_count=16,
            catalog_object_count=16,
            neutral_3mf_audit_passed=True,
            stl_geometry_matches_3mf=True,
            source_snapshot_matches_live_tree=True,
            runtime_provenance_present=True,
        )
        status = release_status.build_release_status(artifact_gate=artifact)
        self.assertTrue(status["qualification_bundle_analytically_complete"])
        self.assertFalse(status["all_physical_gates_complete"])
        self.assertFalse(status["print_authorized"])
        self.assertFalse(status["wall_installation_authorized"])
        self.assertEqual(status["rated_load_kg"], 0.0)

    def test_runtime_provenance_names_the_frozen_writer_and_mesh_stack(self) -> None:
        provenance = release_status.runtime_provenance()
        for key in (
            "python_version",
            "requirements_txt_sha256",
            "numpy_version",
            "trimesh_version",
            "shapely_version",
            "manifold3d_version",
            "r9_model_io_sha256_verified_before_execution",
        ):
            self.assertTrue(provenance[key])
        self.assertTrue(provenance["requirements_runtime_exact_match"])
        self.assertEqual(
            provenance["requirements_versions"]["trimesh"],
            provenance["trimesh_version"],
        )


if __name__ == "__main__":
    unittest.main()
