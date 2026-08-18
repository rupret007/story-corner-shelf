from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import io
import os
from pathlib import Path
import pwd
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


V2_ROOT = Path(__file__).resolve().parents[1]
if str(V2_ROOT) not in sys.path:
    sys.path.insert(0, str(V2_ROOT))

import control_contract as control  # noqa: E402
import generate_controlled_release as generator  # noqa: E402


NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)
HASHES = [f"{index:064x}" for index in range(1, 30)]


def sample_attempt(*, attempt_id: str = "r11-gate-a-left-testattempt01") -> dict:
    selected = control.strict_json(control.BASELINE_LOCK_PATH)["selected_article"]
    value = {
        "schema_version": control.ATTEMPT_SCHEMA_VERSION,
        "attempt_id": attempt_id,
        "captured_at_utc": "2026-08-11T11:59:00Z",
        "selected_article": {
            "article_id": selected["article_id"],
            "model_3mf_relative_path": selected["model_3mf_relative_path"],
            "model_3mf_sha256": selected["model_3mf_sha256"],
            "model_3mf_bytes": selected["model_3mf_bytes"],
            "stl_sha256": selected["stl_sha256"],
            "canonical_geometry_sha256": selected["canonical_geometry_sha256"],
        },
        "slicer": {
            "application": "Bambu Studio",
            "version": "02.07.01.62",
            "application_executable_sha256": "b022be6750898454803e9e07178b7c7446c0e5b4d148c593b4b56efde09ba281",
            "temporary_project_sha256": HASHES[0],
            "sliced_plate_file_sha256": HASHES[1],
            "sliced_plate_file_bytes": 1234567,
            "gcode_payload_sha256": HASHES[2],
            "gcode_config_block_sha256": HASHES[3],
            "printer_profile_export_sha256": HASHES[4],
            "filament_profile_export_sha256": HASHES[5],
            "process_profile_export_sha256": HASHES[6],
            "printer_profile_snapshot_sha256": HASHES[15],
            "filament_profile_snapshot_sha256": HASHES[16],
            "process_profile_snapshot_sha256": HASHES[17],
            "printer_model": "Bambu Lab A1 mini",
            "nozzle_diameter_mm": 0.4,
            "nozzle_flow": "standard",
            "plate_type": "Textured PEI Plate",
            "process_preset": "0.20mm Strength @BBL A1M",
            "layer_height_mm": 0.2,
            "initial_layer_height_mm": 0.2,
            "wall_loops": 6,
            "sparse_infill_density_percent": 25,
            "sparse_infill_pattern": "grid",
            "top_shell_layers": 5,
            "bottom_shell_layers": 3,
            "support_enabled": False,
            "support_build_plate_only": False,
            "support_critical_regions_only": False,
            "support_remove_small_overhang": True,
            "brim_type": "outer",
            "brim_width_mm": 5.0,
            "brim_object_gap_mm": 0.1,
            "nozzle_temperature_first_layer_c": 250,
            "nozzle_temperature_other_layers_c": 245,
            "bed_temperature_first_layer_c": 60,
            "bed_temperature_other_layers_c": 60,
            "flow_ratio": 0.94,
            "maximum_volumetric_speed_mm3_s": 9.0,
            "part_cooling_fan_min_percent": 10,
            "part_cooling_fan_max_percent": 30,
            "overhang_fan_percent": 90,
            "bridge_speed_mm_s": 50,
            "overhang_0_25_speed_mm_s": 0,
            "overhang_25_50_speed_mm_s": 50,
            "overhang_50_75_speed_mm_s": 30,
            "overhang_75_100_speed_mm_s": 10,
            "machine_start_gcode_sha256": "98b77ddf8f9dd85612adf93c87d82cb6618e952968ff12ada7f7109bfe4a977e",
            "machine_end_gcode_sha256": "10a6b35a5b0236cc338b0e323a57255cd76a7b6bb7fceefaadce5d55dc30c877",
            "change_filament_gcode_sha256": "7d97876d466c074e7ff166a29a790928e6cb2219b2cbc6c9896da2e986e55a65",
            "layer_change_gcode_sha256": "137df44edc98f7192367ef747fa45b94e38f29286791277b8eccf64dc5af227e",
            "time_lapse_gcode_sha256": "01b3039a61b288a88931d5ece9f2c41eb77753deaacaf617d4813e97cdd11a52",
        },
        "plate_object": {
            "plate_object_count": 1,
            "copy_count": 1,
            "article_id": selected["article_id"],
            "scale_percent_xyz": [100.0, 100.0, 100.0],
            "rotation_degrees_xyz": [0.0, 0.0, 0.0],
            "mirrored": False,
            "auto_oriented": False,
            "repaired": False,
            "modifier_present": False,
            "negative_volume_present": False,
            "support_enforcer_present": False,
        },
        "slice_result": {
            "layer_count": 160,
            "print_time_seconds": 24298,
            "filament_mass_g": 205.68,
            "filament_length_mm": 69000.0,
            "bed_envelope_violation": False,
            "support_toolpaths_present": False,
            "detached_islands_present": False,
            "capture_geometry_blocked": False,
            "walls_omitted": False,
            "unintended_bridges_present": False,
            "undocumented_repairs_present": False,
            "all_slicer_warnings_recorded": True,
            "warnings": [],
        },
        "screenshots": {
            "prepare_and_transform_sha256": HASHES[7],
            "effective_settings_sha256": HASHES[8],
            "slice_summary_and_warnings_sha256": HASHES[9],
            "first_layer_sha256": HASHES[10],
            "critical_capture_layer_sha256": HASHES[11],
            "cross_lap_layer_sha256": HASHES[12],
            "final_layers_sha256": HASHES[13],
            "current_printer_and_filament_state_sha256": HASHES[14],
        },
        "live_state": {
            "captured_at_utc": "2026-08-11T11:59:20Z",
            "plate_physically_empty": True,
            "plate_clean": True,
            "plate_correctly_seated": True,
            "printer_idle": True,
            "printer_error_free": True,
            "physical_printer_model": "Bambu Lab A1 mini",
            "printer_serial_sha256": "a3c07a6f58e39c108ea8f0ee1d96e9582d00a8b9c7973195e26fe2625ff525d8",
            "firmware_version": "01.08.01.00",
            "module_firmware": {
                "esp32_software_version": "01.16.41.96",
                "esp32_hardware_revision": "AP05",
                "motion_controller_software_version": "00.00.34.17",
                "motion_controller_hardware_revision": "MC02",
                "motion_controller_loader_revision_suffix": ".32",
                "toolhead_software_version": "00.01.07.73",
                "toolhead_hardware_revision": "TH03",
                "toolhead_loader_revision_suffix": ".26",
            },
            "physical_nozzle_diameter_mm": 0.4,
            "physical_nozzle_material": "stainless_steel",
            "physical_nozzle_flow": "standard",
            "physical_plate_type": "Textured PEI Plate",
            "filament": {
                "brand": "SUNLU",
                "material": "PETG",
                "color": "black",
                "diameter_mm": 1.75,
                "product_asin": "B0D1KC72YP",
                "lot_id": "LOT-TEST-01",
                "drying_record": {
                    "dried": True,
                    "method": "vented filament dryer",
                    "temperature_c": 50.0,
                    "duration_hours": 6.0,
                    "completed_at_utc": "2026-08-11T10:00:00Z",
                },
                "external_spool_mapping_verified": True,
                "project_filament_mapping": "SUNLU PETG @BBL A1M 0.4 nozzle",
            },
        },
        "provenance": {
            "printer_telemetry": {
                "source_kind": "read_only_printer_telemetry",
                "captured_at_utc": "2026-08-11T11:59:20Z",
                "sha256": HASHES[18],
            },
            "plate_observation": {
                "source_kind": "fresh_human_plate_observation",
                "captured_at_utc": "2026-08-11T11:59:20Z",
                "sha256": HASHES[19],
            },
            "nozzle_observation": {
                "source_kind": "fresh_human_nozzle_observation",
                "captured_at_utc": "2026-08-11T11:59:20Z",
                "sha256": HASHES[22],
            },
            "spool_label": {
                "source_kind": "photographed_physical_spool_label",
                "captured_at_utc": "2026-08-11T11:59:10Z",
                "sha256": HASHES[20],
            },
            "drying_log": {
                "source_kind": "dryer_log_or_photographed_display",
                "captured_at_utc": "2026-08-11T10:00:00Z",
                "sha256": HASHES[21],
            },
        },
        "evidence_files": {},
        "reviewed_job_digest": "pending",
    }
    evidence_bindings = {
        "temporary_project": value["slicer"]["temporary_project_sha256"],
        "sliced_plate_file": value["slicer"]["sliced_plate_file_sha256"],
        "gcode_payload": value["slicer"]["gcode_payload_sha256"],
        "gcode_config_block": value["slicer"]["gcode_config_block_sha256"],
        "printer_profile_export": value["slicer"]["printer_profile_export_sha256"],
        "filament_profile_export": value["slicer"]["filament_profile_export_sha256"],
        "process_profile_export": value["slicer"]["process_profile_export_sha256"],
        "printer_profile_snapshot": value["slicer"]["printer_profile_snapshot_sha256"],
        "filament_profile_snapshot": value["slicer"]["filament_profile_snapshot_sha256"],
        "process_profile_snapshot": value["slicer"]["process_profile_snapshot_sha256"],
        "prepare_and_transform_screenshot": value["screenshots"]["prepare_and_transform_sha256"],
        "effective_settings_screenshot": value["screenshots"]["effective_settings_sha256"],
        "slice_summary_and_warnings_screenshot": value["screenshots"]["slice_summary_and_warnings_sha256"],
        "first_layer_screenshot": value["screenshots"]["first_layer_sha256"],
        "critical_capture_layer_screenshot": value["screenshots"]["critical_capture_layer_sha256"],
        "cross_lap_layer_screenshot": value["screenshots"]["cross_lap_layer_sha256"],
        "final_layers_screenshot": value["screenshots"]["final_layers_sha256"],
        "current_printer_and_filament_state_screenshot": value["screenshots"][
            "current_printer_and_filament_state_sha256"
        ],
        "printer_telemetry_snapshot": value["provenance"]["printer_telemetry"]["sha256"],
        "plate_observation_record": value["provenance"]["plate_observation"]["sha256"],
        "nozzle_observation_record": value["provenance"]["nozzle_observation"]["sha256"],
        "spool_label_evidence": value["provenance"]["spool_label"]["sha256"],
        "drying_log_evidence": value["provenance"]["drying_log"]["sha256"],
    }
    value["evidence_files"] = {
        key: {
            "relative_path": f"evidence/{key}.bin",
            "bytes": value["slicer"]["sliced_plate_file_bytes"] if key == "sliced_plate_file" else 1,
            "sha256": digest,
        }
        for key, digest in evidence_bindings.items()
    }
    value["reviewed_job_digest"] = control.compute_reviewed_job_digest(value)
    return value


def sample_permission(attempt: dict, attempt_path: Path) -> dict:
    return {
        "schema_version": control.PERMISSION_SCHEMA_VERSION,
        "permission_id": "r11-permission-testpermission01",
        "attempt_id": attempt["attempt_id"],
        "attempt_evidence_sha256": control.sha256_file(attempt_path),
        "reviewed_job_digest": attempt["reviewed_job_digest"],
        "question_exact": "Start this exact one-piece Gate A-left qualification print now?",
        "response_exact": "yes",
        "granted": True,
        "granted_by": "human_user",
        "granted_at_utc": "2026-08-11T11:59:30Z",
        "expires_at_utc": "2026-08-11T12:03:30Z",
    }


def materialize_evidence(root: Path, attempt: dict) -> None:
    contract = control.strict_json(control.RELEASE_CONTRACT_PATH)
    config_values = contract["effective_profile_proof_contract"][
        "gcode_config_exact_controlled_values"
    ]
    config = (
        control.GCODE_CONFIG_START
        + b"".join(f"; {key} = {value}\n".encode("utf-8") for key, value in config_values.items())
        + control.GCODE_CONFIG_END
    )
    gcode = (
        b"; HEADER_BLOCK_START\n; BambuStudio 02.07.01.62\n; HEADER_BLOCK_END\n"
        b"G90\n"
        + config
        + b"M104 S0\n"
    )
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo("Metadata/plate_1.gcode")
        info.date_time = (2020, 1, 1, 0, 0, 0)
        info.external_attr = 0o100600 << 16
        archive.writestr(info, gcode)
    sliced_archive = archive_buffer.getvalue()

    native_profiles: dict[str, bytes] = {}
    canonical_profiles: dict[str, bytes] = {}
    for kind in control.PROFILE_KINDS:
        native = control.json_bytes(
            contract["effective_profile_proof_contract"][kind]
        )
        native_profiles[kind] = native
        canonical_profiles[kind] = control.json_bytes(
            {
                "schema_version": control.PROFILE_SNAPSHOT_SCHEMA_VERSION,
                "profile_kind": kind,
                "native_export_sha256": hashlib.sha256(native).hexdigest(),
                "native_export_bytes": len(native),
                "effective_settings": contract["effective_profile_proof_contract"][kind][
                    "effective_settings"
                ],
            }
        )

    hash_targets = {
        "temporary_project": (attempt["slicer"], "temporary_project_sha256"),
        "sliced_plate_file": (attempt["slicer"], "sliced_plate_file_sha256"),
        "gcode_payload": (attempt["slicer"], "gcode_payload_sha256"),
        "gcode_config_block": (attempt["slicer"], "gcode_config_block_sha256"),
        "printer_profile_export": (attempt["slicer"], "printer_profile_export_sha256"),
        "filament_profile_export": (attempt["slicer"], "filament_profile_export_sha256"),
        "process_profile_export": (attempt["slicer"], "process_profile_export_sha256"),
        "prepare_and_transform_screenshot": (attempt["screenshots"], "prepare_and_transform_sha256"),
        "effective_settings_screenshot": (attempt["screenshots"], "effective_settings_sha256"),
        "slice_summary_and_warnings_screenshot": (attempt["screenshots"], "slice_summary_and_warnings_sha256"),
        "first_layer_screenshot": (attempt["screenshots"], "first_layer_sha256"),
        "critical_capture_layer_screenshot": (attempt["screenshots"], "critical_capture_layer_sha256"),
        "cross_lap_layer_screenshot": (attempt["screenshots"], "cross_lap_layer_sha256"),
        "final_layers_screenshot": (attempt["screenshots"], "final_layers_sha256"),
        "current_printer_and_filament_state_screenshot": (
            attempt["screenshots"], "current_printer_and_filament_state_sha256"
        ),
        "printer_telemetry_snapshot": (
            attempt["provenance"]["printer_telemetry"], "sha256"
        ),
        "plate_observation_record": (
            attempt["provenance"]["plate_observation"], "sha256"
        ),
        "nozzle_observation_record": (
            attempt["provenance"]["nozzle_observation"], "sha256"
        ),
        "spool_label_evidence": (attempt["provenance"]["spool_label"], "sha256"),
        "drying_log_evidence": (attempt["provenance"]["drying_log"], "sha256"),
    }
    payloads = {
        "sliced_plate_file": sliced_archive,
        "gcode_payload": gcode,
        "gcode_config_block": config,
        **{f"{kind}_profile_export": native_profiles[kind] for kind in control.PROFILE_KINDS},
        **{f"{kind}_profile_snapshot": canonical_profiles[kind] for kind in control.PROFILE_KINDS},
    }
    for kind in control.PROFILE_KINDS:
        hash_targets[f"{kind}_profile_snapshot"] = (
            attempt["slicer"], f"{kind}_profile_snapshot_sha256"
        )
    for key, (container, field) in hash_targets.items():
        payload = payloads.get(
            key, (f"external reviewed evidence: {key}\n").encode("utf-8")
        )
        relative = Path("evidence") / f"{key}.bin"
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        digest = control.sha256_file(destination)
        container[field] = digest
        attempt["evidence_files"][key] = {
            "relative_path": relative.as_posix(),
            "bytes": len(payload),
            "sha256": digest,
        }
        if key == "sliced_plate_file":
            attempt["slicer"]["sliced_plate_file_bytes"] = len(payload)
    attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)


def write_json(path: Path, value: object) -> None:
    path.write_bytes(control.json_bytes(value))


def replace_gcode_evidence(
    root: Path, attempt: dict, gcode: bytes, *, wrapper_tag: str = ""
) -> None:
    start = gcode.index(control.GCODE_CONFIG_START)
    end = gcode.index(control.GCODE_CONFIG_END, start) + len(control.GCODE_CONFIG_END)
    config = gcode[start:end]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo("Metadata/plate_1.gcode")
        info.date_time = (2020, 1, 1, 0, 0, 0)
        info.external_attr = 0o100600 << 16
        archive.writestr(info, gcode)
        if wrapper_tag:
            archive.writestr("Metadata/wrapper-tag.txt", wrapper_tag.encode("utf-8"))
    payloads = {
        "sliced_plate_file": buffer.getvalue(),
        "gcode_payload": gcode,
        "gcode_config_block": config,
    }
    fields = {
        "sliced_plate_file": "sliced_plate_file_sha256",
        "gcode_payload": "gcode_payload_sha256",
        "gcode_config_block": "gcode_config_block_sha256",
    }
    for key, payload in payloads.items():
        destination = root / attempt["evidence_files"][key]["relative_path"]
        destination.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        attempt["evidence_files"][key]["bytes"] = len(payload)
        attempt["evidence_files"][key]["sha256"] = digest
        attempt["slicer"][fields[key]] = digest
        if key == "sliced_plate_file":
            attempt["slicer"]["sliced_plate_file_bytes"] = len(payload)
    attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)


class FrozenBaselineAndStaticPackageTests(unittest.TestCase):
    def test_workflow_binds_runner_temp_inside_a_step(self) -> None:
        workflow = (V2_ROOT.parents[1] / ".github" / "workflows" / "validate-r11-print-v2.yml").read_text(
            encoding="utf-8"
        )
        job_env = workflow.split("    steps:", 1)[0]
        self.assertNotIn("${{ runner.temp }}", job_env)
        self.assertIn("Bind runner-local validation paths", workflow)
        for variable in (
            "R11_V1_BEFORE",
            "R11_V1_AFTER",
            "R11_V2_BUILD_ONE",
            "R11_V2_BUILD_TWO",
        ):
            self.assertIn(f'echo "{variable}=$RUNNER_TEMP/', workflow)
        self.assertIn('>> "$GITHUB_ENV"', workflow)

    def test_exact_v1_pins_and_false_physical_boundary(self) -> None:
        evidence = control.verify_frozen_v1()
        self.assertTrue(evidence["verified"])
        self.assertEqual(
            evidence["manifest_sha256"],
            "bc267498314d37f1528b20e46727d90e8184270351f6a4e6fda7bcf82f986661",
        )
        self.assertEqual(
            evidence["tree"]["tree_sha256"],
            "af5f8a4b97e857fb0aeb08c40b5b576c05efe7b651d6555151518180377eec99",
        )
        self.assertFalse(evidence["v1_print_authorized"])

    def test_each_v1_live_source_byte_is_rebound_and_mutation_is_rejected(self) -> None:
        manifest = control.strict_json(control.V1_ROOT / "manifest.json")
        records = manifest["source_records"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for record in records:
                source = control.PROJECT_ROOT / record["path"]
                destination = root / record["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            evidence = control.verify_live_source_records(
                records,
                manifest["source_tree_evidence"],
                project_root=root,
            )
            self.assertEqual(evidence, manifest["source_tree_evidence"])
            victim = root / records[0]["path"]
            victim.write_bytes(victim.read_bytes() + b"tamper")
            with self.assertRaisesRegex(control.ContractError, "live source bytes changed"):
                control.verify_live_source_records(
                    records,
                    manifest["source_tree_evidence"],
                    project_root=root,
                )

    def test_static_package_is_exact_non_authorizing_and_payload_free(self) -> None:
        manifest = control.validate_static_package()
        status = control.strict_json(control.DEFAULT_STATIC_PACKAGE / "status.json")
        self.assertFalse(manifest["static_print_authorized"])
        self.assertFalse(manifest["static_effective_print_authorized"])
        self.assertFalse(status["print_authorized"])
        self.assertFalse(status["effective_print_authorized"])
        self.assertEqual(status["hard_boundary"], control.HARD_BOUNDARY)
        names = [path.name.lower() for path in control.DEFAULT_STATIC_PACKAGE.rglob("*")]
        self.assertFalse(any(name.endswith((".3mf", ".stl", ".gcode", ".bgcode")) for name in names))

    def test_two_builds_are_byte_identical_no_replace_and_preserve_every_v1_byte(self) -> None:
        before = control.artifact_records(control.V1_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            first = generator.build_package(root / "first")
            second = generator.build_package(root / "second")
            self.assertEqual(control.tree_evidence(first), control.tree_evidence(second))
            for relative in (
                path.relative_to(first)
                for path in first.rglob("*")
                if path.is_file()
            ):
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())
            with self.assertRaises(FileExistsError):
                generator.build_package(first)
        self.assertEqual(before, control.artifact_records(control.V1_ROOT))

    def test_static_tampering_and_unknown_injection_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tampered = Path(directory).resolve() / "tampered"
            shutil.copytree(control.DEFAULT_STATIC_PACKAGE, tampered)
            (tampered / "status.json").write_bytes(
                (tampered / "status.json").read_bytes() + b" \n"
            )
            with self.assertRaises(control.ContractError):
                control.validate_static_package(tampered)
            injected = Path(directory).resolve() / "injected"
            shutil.copytree(control.DEFAULT_STATIC_PACKAGE, injected)
            (injected / "attempt.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(control.ContractError):
                control.validate_static_package(injected)

    def test_manifest_and_status_cannot_inject_print_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manifest_injected = root / "manifest-injected"
            shutil.copytree(control.DEFAULT_STATIC_PACKAGE, manifest_injected)
            manifest_path = manifest_injected / "manifest.json"
            manifest = control.strict_json(manifest_path)
            manifest["print_authorized"] = True
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(control.ContractError, "static_manifest keys differ"):
                control.validate_static_package(manifest_injected)

            status_injected = root / "status-injected"
            shutil.copytree(control.DEFAULT_STATIC_PACKAGE, status_injected)
            status_path = status_injected / "status.json"
            status = control.strict_json(status_path)
            status["production_ready"] = True
            write_json(status_path, status)
            changed_manifest_path = status_injected / "manifest.json"
            changed_manifest = control.strict_json(changed_manifest_path)
            for record in changed_manifest["hashed_artifacts_excluding_manifest"]:
                if record["path"] == "status.json":
                    record["bytes"] = status_path.stat().st_size
                    record["sha256"] = control.sha256_file(status_path)
            write_json(changed_manifest_path, changed_manifest)
            with self.assertRaisesRegex(control.ContractError, "static_status keys differ"):
                control.validate_static_package(status_injected)

    def test_source_mutation_during_staging_fails_closed(self) -> None:
        before = control.v2_source_records()
        changed = deepcopy(before)
        changed[0] = {**changed[0], "sha256": "f" * 64}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / "must-not-exist"
            with mock.patch.object(
                control,
                "v2_source_records",
                side_effect=(before, changed),
            ):
                with self.assertRaisesRegex(control.ContractError, "changed while staging"):
                    generator.build_package(target)
            self.assertFalse(target.exists())

    def test_supplied_schemas_are_strict_objects(self) -> None:
        for path in (
            control.ATTEMPT_SCHEMA_PATH,
            control.PERMISSION_SCHEMA_PATH,
            control.PERMIT_SCHEMA_PATH,
            control.CONSUMPTION_SCHEMA_PATH,
        ):
            schema = control.strict_json(path)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertFalse(schema["additionalProperties"])

    def test_complete_emitted_gcode_config_is_pinned(self) -> None:
        approved = control.strict_json(control.RELEASE_CONTRACT_PATH)[
            "effective_profile_proof_contract"
        ]["approved_emitted_gcode_config"]
        self.assertEqual(approved["bytes"], 40428)
        self.assertEqual(
            approved["sha256"],
            "339fde3346204d32dd72ed466a4b14b1c5a16f21c9f4f6855f4f064ac50f8eea",
        )
        with self.assertRaisesRegex(control.ContractError, "exact approved closure"):
            control._require_approved_gcode_config(b"synthetic config")


class ExactAttemptTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(
            control, "_require_approved_gcode_config", return_value=None
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        executable_patcher = mock.patch.object(
            control, "verify_installed_bambu_executable", return_value="0" * 64
        )
        executable_patcher.start()
        self.addCleanup(executable_patcher.stop)

    def test_exact_attempt_passes_and_review_stays_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "attempt.json"
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            write_json(path, attempt)
            review = control.review_attempt(path)
            self.assertTrue(review["exact_left_quantity_one_review_passed"])
            self.assertTrue(review["fresh_permission_still_required"])
            self.assertFalse(review["print_authorized"])
            self.assertFalse(review["effective_print_authorized"])

    def test_alternate_part_catalog_extra_object_transform_or_repair_fail(self) -> None:
        mutations = (
            ("alternate", lambda x: x["selected_article"].__setitem__("article_id", "other")),
            ("catalog", lambda x: x["plate_object"].__setitem__("article_id", "CATALOG")),
            ("extra", lambda x: x["plate_object"].__setitem__("plate_object_count", 2)),
            ("copy", lambda x: x["plate_object"].__setitem__("copy_count", 2)),
            ("scale", lambda x: x["plate_object"].__setitem__("scale_percent_xyz", [99.0, 100.0, 100.0])),
            ("rotate", lambda x: x["plate_object"].__setitem__("rotation_degrees_xyz", [0.0, 0.0, 90.0])),
            ("repair", lambda x: x["plate_object"].__setitem__("repaired", True)),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                attempt = sample_attempt()
                mutate(attempt)
                attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)
                with self.assertRaises(control.ContractError):
                    control.validate_attempt(attempt)

    def test_missing_unknown_unresolved_warning_and_changed_setting_fail(self) -> None:
        missing = sample_attempt()
        missing["slicer"].pop("wall_loops")
        unknown = sample_attempt()
        unknown["unexpected"] = False
        warning = sample_attempt()
        warning["slice_result"]["warnings"] = [
            {"exact_text": "warning", "layer_level_disposition": "not reviewed", "resolved": False}
        ]
        setting = sample_attempt()
        setting["slicer"]["wall_loops"] = 5
        for value in (missing, unknown, warning, setting):
            value["reviewed_job_digest"] = control.compute_reviewed_job_digest(value)
            with self.assertRaises(control.ContractError):
                control.validate_attempt(value)

    def test_undried_or_unstructured_drying_record_cannot_claim_gate_a(self) -> None:
        undried = sample_attempt()
        undried["live_state"]["filament"]["drying_record"]["dried"] = False
        unstructured = sample_attempt()
        unstructured["live_state"]["filament"]["drying_record"] = "not dried"
        for value in (undried, unstructured):
            value["reviewed_job_digest"] = control.compute_reviewed_job_digest(value)
            with self.assertRaises(control.ContractError):
                control.validate_attempt(value)

    def test_unapproved_drying_temperature_duration_or_bambu_version_fail(self) -> None:
        too_hot = sample_attempt()
        too_hot["live_state"]["filament"]["drying_record"]["temperature_c"] = 500.0
        too_short = sample_attempt()
        too_short["live_state"]["filament"]["drying_record"]["duration_hours"] = 0.1
        wrong_version = sample_attempt()
        wrong_version["slicer"]["version"] = "02.07.01.63"
        wrong_executable = sample_attempt()
        wrong_executable["slicer"]["application_executable_sha256"] = HASHES[16]
        wrong_temperature = sample_attempt()
        wrong_temperature["slicer"]["nozzle_temperature_other_layers_c"] = 250
        wrong_firmware = sample_attempt()
        wrong_firmware["live_state"]["firmware_version"] = "01.08.01.01"
        wrong_device = sample_attempt()
        wrong_device["live_state"]["printer_serial_sha256"] = HASHES[16]
        wrong_nozzle = sample_attempt()
        wrong_nozzle["live_state"]["physical_nozzle_material"] = "hardened_steel"
        for value in (
            too_hot, too_short, wrong_version, wrong_executable,
            wrong_temperature, wrong_firmware, wrong_device, wrong_nozzle,
        ):
            value["reviewed_job_digest"] = control.compute_reviewed_job_digest(value)
            with self.assertRaises(control.ContractError):
                control.validate_attempt(value)

    def test_drying_must_complete_before_both_captures(self) -> None:
        attempt = sample_attempt()
        attempt["live_state"]["filament"]["drying_record"][
            "completed_at_utc"
        ] = "2026-08-11T11:59:30Z"
        attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)
        with self.assertRaisesRegex(control.ContractError, "before attempt and live-state"):
            control.validate_attempt(attempt)

    def test_final_sliced_payload_hashes_are_required_and_job_bound(self) -> None:
        attempt = sample_attempt()
        original = attempt["reviewed_job_digest"]
        attempt["slicer"]["gcode_payload_sha256"] = HASHES[18]
        attempt["evidence_files"]["gcode_payload"]["sha256"] = HASHES[18]
        with self.assertRaisesRegex(control.ContractError, "reviewed_job_digest"):
            control.validate_attempt(attempt)
        attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)
        self.assertNotEqual(original, attempt["reviewed_job_digest"])
        control.validate_attempt(attempt)

    def test_screenshot_evidence_classes_must_be_pairwise_distinct(self) -> None:
        attempt = sample_attempt()
        attempt["screenshots"]["final_layers_sha256"] = attempt["screenshots"][
            "first_layer_sha256"
        ]
        attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)
        with self.assertRaisesRegex(control.ContractError, "pairwise distinct"):
            control.validate_attempt(attempt)

    def test_live_state_requires_bound_independent_provenance(self) -> None:
        attempt = sample_attempt()
        changed = deepcopy(attempt)
        changed["provenance"]["plate_observation"]["captured_at_utc"] = (
            "2026-08-11T11:59:19Z"
        )
        changed["reviewed_job_digest"] = control.compute_reviewed_job_digest(changed)
        with self.assertRaisesRegex(control.ContractError, "human plate observation"):
            control.validate_attempt(changed)
        changed = deepcopy(attempt)
        changed["provenance"]["spool_label"]["sha256"] = "f" * 64
        changed["reviewed_job_digest"] = control.compute_reviewed_job_digest(changed)
        with self.assertRaisesRegex(control.ContractError, "hash does not match"):
            control.validate_attempt(changed)
        changed = deepcopy(attempt)
        duplicate = changed["provenance"]["plate_observation"]["sha256"]
        changed["provenance"]["nozzle_observation"]["sha256"] = duplicate
        changed["evidence_files"]["nozzle_observation_record"]["sha256"] = duplicate
        changed["reviewed_job_digest"] = control.compute_reviewed_job_digest(changed)
        with self.assertRaisesRegex(control.ContractError, "pairwise distinct"):
            control.validate_attempt(changed)

    def test_external_evidence_files_must_exist_and_match_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            attempt_path = root / "attempt.json"
            write_json(attempt_path, attempt)
            missing = root / attempt["evidence_files"]["gcode_payload"]["relative_path"]
            missing.unlink()
            with self.assertRaisesRegex(control.ContractError, "missing, unsafe, or has a symlink"):
                control.review_attempt(attempt_path)
            materialize_evidence(root, attempt)
            write_json(attempt_path, attempt)
            tampered = root / attempt["evidence_files"]["first_layer_screenshot"]["relative_path"]
            tampered.write_bytes(tampered.read_bytes() + b"tamper")
            with self.assertRaisesRegex(control.ContractError, "bytes changed"):
                control.review_attempt(attempt_path)

    def test_ancestor_symlink_in_evidence_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            real = base / "real"
            real.mkdir()
            attempt = sample_attempt()
            materialize_evidence(real, attempt)
            write_json(real / "attempt.json", attempt)
            alias = base / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(control.ContractError, "symlink"):
                control.review_attempt(alias / "attempt.json")

    def test_final_evidence_file_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            attempt_path = root / "attempt.json"
            write_json(attempt_path, attempt)
            control.load_attempt_bundle(attempt_path)
            binding = attempt["evidence_files"]["temporary_project"]
            evidence_path = root / binding["relative_path"]
            target = root / "ordinary-target.bin"
            target.write_bytes(evidence_path.read_bytes())
            evidence_path.unlink()
            evidence_path.symlink_to(target)
            with self.assertRaisesRegex(control.ContractError, "symlink"):
                control.load_attempt_bundle(attempt_path)

    def test_archive_derived_gcode_and_config_must_match_separate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            payload_path = root / attempt["evidence_files"]["gcode_payload"]["relative_path"]
            replacement = payload_path.read_bytes() + b"; unrelated payload\n"
            payload_path.write_bytes(replacement)
            digest = hashlib.sha256(replacement).hexdigest()
            attempt["slicer"]["gcode_payload_sha256"] = digest
            attempt["evidence_files"]["gcode_payload"].update(
                {"bytes": len(replacement), "sha256": digest}
            )
            attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)
            write_json(root / "attempt.json", attempt)
            with self.assertRaisesRegex(control.ContractError, "archive-derived G-code"):
                control.load_attempt_bundle(root / "attempt.json")

    def test_arbitrary_or_mutated_profile_export_and_snapshot_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            native_path = root / attempt["evidence_files"]["process_profile_export"][
                "relative_path"
            ]
            native = control.strict_json(native_path)
            native["effective_settings"]["wall_loops"] = 5
            native_bytes = control.json_bytes(native)
            native_path.write_bytes(native_bytes)
            native_hash = hashlib.sha256(native_bytes).hexdigest()
            attempt["slicer"]["process_profile_export_sha256"] = native_hash
            attempt["evidence_files"]["process_profile_export"].update(
                {"bytes": len(native_bytes), "sha256": native_hash}
            )
            snapshot_path = root / attempt["evidence_files"]["process_profile_snapshot"][
                "relative_path"
            ]
            snapshot = {
                "schema_version": control.PROFILE_SNAPSHOT_SCHEMA_VERSION,
                "profile_kind": "process",
                "native_export_sha256": native_hash,
                "native_export_bytes": len(native_bytes),
                "effective_settings": native["effective_settings"],
            }
            snapshot_bytes = control.json_bytes(snapshot)
            snapshot_path.write_bytes(snapshot_bytes)
            snapshot_hash = hashlib.sha256(snapshot_bytes).hexdigest()
            attempt["slicer"]["process_profile_snapshot_sha256"] = snapshot_hash
            attempt["evidence_files"]["process_profile_snapshot"].update(
                {"bytes": len(snapshot_bytes), "sha256": snapshot_hash}
            )
            attempt["reviewed_job_digest"] = control.compute_reviewed_job_digest(attempt)
            write_json(root / "attempt.json", attempt)
            with self.assertRaisesRegex(
                control.ContractError,
                "bytes/hash are not approved|exact approved effective export",
            ):
                control.load_attempt_bundle(root / "attempt.json")

    def test_controlled_gcode_setting_drift_is_rejected_even_when_all_hashes_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            gcode_path = root / attempt["evidence_files"]["gcode_payload"]["relative_path"]
            gcode = gcode_path.read_bytes().replace(
                b"; wall_loops = 6\n", b"; wall_loops = 5\n"
            )
            replace_gcode_evidence(root, attempt, gcode)
            write_json(root / "attempt.json", attempt)
            with self.assertRaisesRegex(control.ContractError, "controlled value changed: wall_loops"):
                control.load_attempt_bundle(root / "attempt.json")

    def test_genuine_bambu_header_form_is_exact_and_hyphen_variant_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            attempt_path = root / "attempt.json"
            write_json(attempt_path, attempt)
            control.load_attempt_bundle(attempt_path)
            gcode_path = root / attempt["evidence_files"]["gcode_payload"]["relative_path"]
            changed = gcode_path.read_bytes().replace(
                b"; BambuStudio 02.07.01.62\n",
                b"; BambuStudio-02.07.01.62\n",
            )
            replace_gcode_evidence(root, attempt, changed)
            write_json(attempt_path, attempt)
            with self.assertRaisesRegex(control.ContractError, "pinned Bambu Studio version"):
                control.load_attempt_bundle(attempt_path)

    def test_prepare_external_evidence_derives_archive_and_profiles_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt = sample_attempt()
            materialize_evidence(root, attempt)
            sliced = root / attempt["evidence_files"]["sliced_plate_file"]["relative_path"]
            destination = root / "prepared"
            with mock.patch.object(
                control,
                "verify_installed_native_profile_sources",
                return_value={kind: "0" * 64 for kind in control.PROFILE_KINDS},
            ):
                report = control.prepare_external_evidence_payloads(sliced, destination)
                with self.assertRaisesRegex(control.ContractError, "already exists"):
                    control.prepare_external_evidence_payloads(sliced, destination)
            self.assertFalse(report["print_authorized"])
            expected = {
                "gcode_payload", "gcode_config_block",
                "printer_profile_export", "filament_profile_export",
                "process_profile_export", "printer_profile_snapshot",
                "filament_profile_snapshot", "process_profile_snapshot",
            }
            self.assertEqual(set(report["derived_evidence"]), expected)
            archive = control.snapshot_file(sliced)
            gcode = control._extract_gcode_from_sliced_archive(archive)
            self.assertEqual((destination / "gcode_payload.gcode").read_bytes(), gcode)
            self.assertEqual(
                (destination / "gcode_config_block.txt").read_bytes(),
                control._extract_and_validate_gcode_config(gcode),
            )


class PermitLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        config_patcher = mock.patch.object(
            control, "_require_approved_gcode_config", return_value=None
        )
        config_patcher.start()
        self.addCleanup(config_patcher.stop)
        native_patcher = mock.patch.object(
            control,
            "verify_installed_native_profile_sources",
            return_value={kind: "0" * 64 for kind in control.PROFILE_KINDS},
        )
        native_patcher.start()
        self.addCleanup(native_patcher.stop)
        executable_patcher = mock.patch.object(
            control, "verify_installed_bambu_executable", return_value="0" * 64
        )
        executable_patcher.start()
        self.addCleanup(executable_patcher.stop)

    def _ledger(self, root: Path) -> control.LedgerStore:
        store = control.LedgerStore._test_store(root / "state")
        store.initialize(now=NOW - timedelta(minutes=1))
        patcher = mock.patch.object(control.LedgerStore, "canonical", return_value=store)
        patcher.start()
        self.addCleanup(patcher.stop)
        return store

    def _files(self, root: Path) -> tuple[dict, Path, dict, Path]:
        attempt = sample_attempt()
        materialize_evidence(root, attempt)
        attempt_path = root / "attempt.json"
        write_json(attempt_path, attempt)
        permission = sample_permission(attempt, attempt_path)
        permission_path = root / "permission.json"
        write_json(permission_path, permission)
        return attempt, attempt_path, permission, permission_path

    def test_canonical_ledger_ignores_home_and_missing_ledger_blocks(self) -> None:
        real = Path(pwd.getpwuid(os.getuid()).pw_dir) / control.LEDGER_RELATIVE_PATH
        with mock.patch.dict(os.environ, {"HOME": "/private/tmp/attacker-home"}):
            self.assertEqual(control.canonical_ledger_root(), real)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _, attempt_path, _, permission_path = self._files(root)
            missing = control.LedgerStore._test_store(root / "never-initialized")
            with mock.patch.object(control.LedgerStore, "canonical", return_value=missing):
                with self.assertRaisesRegex(control.ContractError, "explicit one-time initialization"):
                    control.issue_permit(attempt_path, permission_path, now=NOW)

    def test_ledger_ancestor_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            real = root / "real"
            real.mkdir()
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            store = control.LedgerStore._test_store(alias / "ledger")
            with self.assertRaisesRegex(control.ContractError, "unsafe"):
                store.initialize(now=NOW)

    def test_fresh_exact_permission_issues_once_and_atomic_send_consumes_forever(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt, attempt_path, permission, permission_path = self._files(root)
            store = self._ledger(root)
            permit = control.issue_permit(
                attempt_path, permission_path, now=NOW
            )
            try:
                self.assertTrue(
                    control.evaluate_permit(
                        permit, attempt_path, now=NOW
                    )[
                        "effective_print_authorized"
                    ]
                )
                ticket = control.consume_and_open_send_payload(
                    permit, attempt_path, now=NOW
                )
                record = control.strict_json(ticket.consumption_path)
                self.assertTrue(record["permit_consumed"])
                self.assertFalse(record["effective_print_authorized"])
                self.assertTrue(record["failed_cancelled_rejected_or_ambiguous_still_consumed"])
                self.assertEqual(ticket.payload_sha256, attempt["slicer"]["gcode_payload_sha256"])
                self.assertFalse(
                    control.evaluate_permit(
                        permit, attempt_path, now=NOW
                    )[
                        "effective_print_authorized"
                    ]
                )
                with self.assertRaises(control.ContractError):
                    control.consume_and_open_send_payload(
                        permit, attempt_path, now=NOW
                    )
                replacement = deepcopy(permission)
                replacement["permission_id"] = "r11-permission-newpermission02"
                replacement_path = root / "replacement-permission.json"
                write_json(replacement_path, replacement)
                with self.assertRaises(FileExistsError):
                    control.issue_permit(
                        attempt_path, replacement_path, now=NOW
                    )
                with self.assertRaises(TypeError):
                    control.issue_permit(attempt_path, permission_path, root / "other")
            finally:
                ticket.close()

    def test_concurrent_consume_has_exactly_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _, attempt_path, _, permission_path = self._files(root)
            store = self._ledger(root)
            permit = control.issue_permit(
                attempt_path, permission_path, now=NOW
            )
            def consume() -> bool:
                try:
                    ticket = control.consume_and_open_send_payload(
                        permit, attempt_path, now=NOW
                    )
                    ticket.close()
                    return True
                except (control.ContractError, FileExistsError):
                    return False

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: consume(), range(2)))
            self.assertEqual(results.count(True), 1)
            self.assertEqual(results.count(False), 1)

    def test_wrong_job_stale_permission_copied_or_expired_permit_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt, attempt_path, permission, permission_path = self._files(root)
            wrong = deepcopy(permission)
            wrong["reviewed_job_digest"] = HASHES[17]
            write_json(permission_path, wrong)
            store = self._ledger(root)
            with self.subTest(store=store.root):
                with self.assertRaises(control.ContractError):
                    control.issue_permit(
                        attempt_path, permission_path, now=NOW
                    )

                write_json(permission_path, permission)
                stale_now = NOW + timedelta(minutes=10)
                with self.assertRaises(control.ContractError):
                    control.issue_permit(
                        attempt_path, permission_path, now=stale_now
                    )

                permit = control.issue_permit(
                    attempt_path, permission_path, now=NOW
                )
                copied = root / "copied"
                copied.mkdir()
                copied_permit = copied / permit.name
                shutil.copyfile(permit, copied_permit)
                with self.assertRaises(control.ContractError):
                    control.evaluate_permit(
                        copied_permit, attempt_path, now=NOW
                    )
                expired = NOW + timedelta(minutes=4)
                self.assertFalse(
                    control.evaluate_permit(
                        permit, attempt_path, now=expired
                    )[
                        "effective_print_authorized"
                    ]
                )

    def test_permission_before_attempt_or_live_capture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _, attempt_path, permission, permission_path = self._files(root)
            permission["granted_at_utc"] = "2026-08-11T11:59:10Z"
            write_json(permission_path, permission)
            store = self._ledger(root)
            with self.subTest(store=store.root):
                with self.assertRaisesRegex(control.ContractError, "after attempt and live-state"):
                    control.issue_permit(
                        attempt_path, permission_path, now=NOW
                    )

    def test_permission_parse_and_hash_use_the_same_single_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _, attempt_path, permission, permission_path = self._files(root)
            store = self._ledger(root)
            approved_snapshot = control.snapshot_file(permission_path)
            original = control.snapshot_json
            replaced = False

            def snapshot_and_replace(path: Path):
                nonlocal replaced
                value, snapshot = original(path)
                if Path(path) == permission_path and not replaced:
                    denial = deepcopy(permission)
                    denial["granted"] = False
                    write_json(permission_path, denial)
                    replaced = True
                return value, snapshot

            with mock.patch.object(control, "snapshot_json", side_effect=snapshot_and_replace):
                permit = control.issue_permit(attempt_path, permission_path, now=NOW)
            permit_record = control.strict_json(permit)
            self.assertEqual(
                permit_record["permission_evidence_sha256"], approved_snapshot.sha256
            )
            self.assertNotEqual(
                permit_record["permission_evidence_sha256"],
                control.sha256_file(permission_path),
            )

    def test_evidence_drift_before_consume_blocks_without_authorizing_send(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            attempt, attempt_path, _, permission_path = self._files(root)
            store = self._ledger(root)
            permit = control.issue_permit(attempt_path, permission_path, now=NOW)
            original = control.load_attempt_bundle
            calls = 0

            def snapshot_then_drift(path: Path):
                nonlocal calls
                bundle = original(path)
                calls += 1
                if calls == 1:
                    victim = root / attempt["evidence_files"][
                        "first_layer_screenshot"
                    ]["relative_path"]
                    victim.write_bytes(victim.read_bytes() + b"drift")
                return bundle

            with mock.patch.object(
                control, "load_attempt_bundle", side_effect=snapshot_then_drift
            ):
                with self.assertRaises(control.ContractError):
                    control.consume_and_open_send_payload(
                        permit, attempt_path, now=NOW
                    )
            self.assertFalse((store.root / f"{permit.stem.removesuffix('.permit')}.consumed.json").exists())

    def test_new_retry_attempt_cannot_reuse_previous_permission_or_permit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _, attempt_path, _, permission_path = self._files(root)
            store = self._ledger(root)
            with self.subTest(store=store.root):
                permit = control.issue_permit(
                    attempt_path, permission_path, now=NOW
                )
                retry = sample_attempt(attempt_id="r11-gate-a-left-retryattempt02")
                retry_root = root / "retry-evidence"
                retry_root.mkdir()
                materialize_evidence(retry_root, retry)
                retry_path = retry_root / "retry.json"
                write_json(retry_path, retry)
                retry_permission = sample_permission(retry, retry_path)
                retry_permission["permission_id"] = "r11-permission-retrypermission02"
                retry_permission_path = retry_root / "permission.json"
                write_json(retry_permission_path, retry_permission)
                with self.assertRaises(control.ContractError):
                    control.evaluate_permit(
                        permit, retry_path, now=NOW
                    )
                with self.assertRaises(FileExistsError):
                    control.issue_permit(
                        retry_path, retry_permission_path, now=NOW
                    )

    def test_new_wrapper_cannot_reissue_identical_archive_derived_gcode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _, attempt_path, _, permission_path = self._files(root)
            store = self._ledger(root)
            control.issue_permit(attempt_path, permission_path, now=NOW)
            retry_root = root / "new-wrapper"
            retry_root.mkdir()
            retry = sample_attempt(attempt_id="r11-gate-a-left-wrapperattempt03")
            materialize_evidence(retry_root, retry)
            gcode = (
                retry_root / retry["evidence_files"]["gcode_payload"]["relative_path"]
            ).read_bytes()
            old_wrapper = retry["slicer"]["sliced_plate_file_sha256"]
            replace_gcode_evidence(retry_root, retry, gcode, wrapper_tag="new-wrapper")
            self.assertNotEqual(old_wrapper, retry["slicer"]["sliced_plate_file_sha256"])
            retry_path = retry_root / "attempt.json"
            write_json(retry_path, retry)
            permission = sample_permission(retry, retry_path)
            permission["permission_id"] = "r11-permission-wrapperpermission03"
            permission_path = retry_root / "permission.json"
            write_json(permission_path, permission)
            with self.assertRaises(FileExistsError):
                control.issue_permit(retry_path, permission_path, now=NOW)
            marker = store.root / f"gcode-payload-{retry['slicer']['gcode_payload_sha256']}.spent.json"
            self.assertTrue(marker.is_file())

    def test_path_only_consume_is_permanently_disabled(self) -> None:
        with self.assertRaisesRegex(control.ContractError, "path-only consume is disabled"):
            control.consume_before_send_attempt(Path("permit"), Path("attempt"))


if __name__ == "__main__":
    unittest.main()
