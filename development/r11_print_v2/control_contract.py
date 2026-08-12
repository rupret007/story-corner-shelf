#!/usr/bin/env python3
"""Fail-closed controls shared by the R11 Gate A-left v2 overlay.

This module reads the immutable R11 v1 bundle, validates strict external
evidence, and manages a single-use external permit ledger.  It never talks to
a printer and never emits geometry, slicer projects, profiles, or toolpaths.
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from contextlib import contextmanager
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path
import pwd
import re
import secrets
import stat
import subprocess
import zipfile
from typing import Any, Iterable, Mapping, Sequence


V2_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = V2_ROOT.parents[1]
V1_ROOT = PROJECT_ROOT / "development/r11/generated/first_outer_actual_bay_qualification_v1"
DEFAULT_STATIC_PACKAGE = V2_ROOT / "generated/gate_a_left_controlled_qualification_print_v2"
LEDGER_RELATIVE_PATH = Path(
    ".local/state/office-closet-project/r11-gate-a-left-v2"
)
LEDGER_IDENTITY_SCHEMA_VERSION = "r11.gate-a-left-ledger-identity.v1"

BASELINE_LOCK_PATH = V2_ROOT / "baseline_lock.json"
RELEASE_CONTRACT_PATH = V2_ROOT / "release_contract.json"
ATTEMPT_SCHEMA_PATH = V2_ROOT / "schemas/attempt_evidence.schema.json"
PERMISSION_SCHEMA_PATH = V2_ROOT / "schemas/fresh_permission.schema.json"
PERMIT_SCHEMA_PATH = V2_ROOT / "schemas/ephemeral_permit.schema.json"
CONSUMPTION_SCHEMA_PATH = V2_ROOT / "schemas/send_attempt_consumption.schema.json"

ATTEMPT_SCHEMA_VERSION = "r11.gate-a-left-attempt-evidence.v1"
PERMISSION_SCHEMA_VERSION = "r11.gate-a-left-fresh-permission.v1"
PERMIT_SCHEMA_VERSION = "r11.gate-a-left-ephemeral-permit.v1"
CONSUMPTION_SCHEMA_VERSION = "r11.gate-a-left-send-attempt-consumption.v1"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ATTEMPT_ID_RE = re.compile(r"^r11-gate-a-left-[A-Za-z0-9][A-Za-z0-9._-]{7,95}$")
PERMISSION_ID_RE = re.compile(r"^r11-permission-[A-Za-z0-9][A-Za-z0-9._-]{7,95}$")
UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$"
)

HARD_BOUNDARY = {
    "drilling_coordinates_released": False,
    "drilling_schedule_released": False,
    "wall_installation_authorized": False,
    "test_load_authorized": False,
    "stored_load_authorized": False,
    "production_printing_authorized": False,
    "full_wall_printing_authorized": False,
    "rated_load_kg": 0.0,
    "rated_load_lb": 0.0,
}

EVIDENCE_FILE_KEYS = (
    "temporary_project",
    "sliced_plate_file",
    "gcode_payload",
    "gcode_config_block",
    "printer_profile_export",
    "filament_profile_export",
    "process_profile_export",
    "printer_profile_snapshot",
    "filament_profile_snapshot",
    "process_profile_snapshot",
    "prepare_and_transform_screenshot",
    "effective_settings_screenshot",
    "slice_summary_and_warnings_screenshot",
    "first_layer_screenshot",
    "critical_capture_layer_screenshot",
    "cross_lap_layer_screenshot",
    "final_layers_screenshot",
    "current_printer_and_filament_state_screenshot",
    "printer_telemetry_snapshot",
    "plate_observation_record",
    "nozzle_observation_record",
    "spool_label_evidence",
    "drying_log_evidence",
)

PROFILE_KINDS = ("printer", "filament", "process")
PROFILE_SNAPSHOT_SCHEMA_VERSION = "r11.gate-a-left-effective-profile-snapshot.v1"
GCODE_CONFIG_START = b"; CONFIG_BLOCK_START\n"
GCODE_CONFIG_END = b"; CONFIG_BLOCK_END\n"


@dataclass(frozen=True)
class FileSnapshot:
    """Immutable bytes and identity captured from one O_NOFOLLOW file open."""

    path: Path
    payload: bytes
    bytes: int
    sha256: str
    device: int
    inode: int
    mtime_ns: int
    ctime_ns: int
    link_count: int


@dataclass
class SendPayloadTicket:
    """Consumed permit plus the exact still-open content-addressed G-code blob."""

    permit_id: str
    consumption_path: Path
    payload_path: Path
    payload_fd: int
    payload_sha256: str
    payload_bytes: int

    def close(self) -> None:
        if self.payload_fd >= 0:
            os.close(self.payload_fd)
            self.payload_fd = -1

    def __enter__(self) -> "SendPayloadTicket":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class ContractError(ValueError):
    """Raised when any release, evidence, or permit contract fails closed."""


def _strict_json_payload(payload: bytes, label: str) -> Any:
    """Parse the exact supplied bytes with duplicate/NaN rejection."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ContractError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ContractError(f"non-finite JSON value in {label}: {value}")

    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractError(f"invalid strict JSON: {label}") from error


def _absolute_unresolved(path: Path) -> Path:
    source = Path(path)
    if not source.is_absolute():
        source = Path.cwd() / source
    parts = source.parts
    if any(part in (".", "..") for part in parts):
        raise ContractError(f"path contains a noncanonical component: {path}")
    return source


def _open_directory_fd(path: Path) -> int:
    """Walk every absolute directory component with openat/O_NOFOLLOW."""

    absolute = _absolute_unresolved(path)
    if absolute == Path("/"):
        return os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in absolute.parts[1:]:
            next_descriptor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except (OSError, ValueError) as error:
        os.close(descriptor)
        raise ContractError(f"directory path is missing, unsafe, or contains a symlink: {path}") from error


def _snapshot_from_fd(descriptor: int, path: Path) -> FileSnapshot:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        raise ContractError(f"input must be a regular file: {path}")
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
        digest.update(chunk)
    after = os.fstat(descriptor)
    identity_before = (
        before.st_dev, before.st_ino, before.st_size,
        before.st_mtime_ns, before.st_ctime_ns,
    )
    identity_after = (
        after.st_dev, after.st_ino, after.st_size,
        after.st_mtime_ns, after.st_ctime_ns,
    )
    payload = b"".join(chunks)
    if identity_before != identity_after or len(payload) != before.st_size:
        raise ContractError(f"file changed while it was being snapshotted: {path}")
    return FileSnapshot(
        path=Path(path), payload=payload, bytes=len(payload),
        sha256=digest.hexdigest(), device=before.st_dev, inode=before.st_ino,
        mtime_ns=before.st_mtime_ns, ctime_ns=before.st_ctime_ns,
        link_count=before.st_nlink,
    )


def _snapshot_relative(root_fd: int, relative: Path, display_root: Path) -> FileSnapshot:
    if relative.is_absolute() or not relative.parts or any(
        part in ("", ".", "..") for part in relative.parts
    ):
        raise ContractError(f"unsafe relative evidence path: {relative}")
    directory_fd = os.dup(root_fd)
    try:
        for component in relative.parts[:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
        try:
            return _snapshot_from_fd(descriptor, display_root / relative)
        finally:
            os.close(descriptor)
    except (OSError, ValueError) as error:
        raise ContractError(
            f"file is missing, unsafe, or has a symlink path component: {display_root / relative}"
        ) from error
    finally:
        os.close(directory_fd)


def snapshot_file(path: Path) -> FileSnapshot:
    """Snapshot one regular file without following any path-component symlink."""

    absolute = _absolute_unresolved(path)
    parent_fd = _open_directory_fd(absolute.parent)
    try:
        return _snapshot_relative(parent_fd, Path(absolute.name), absolute.parent)
    finally:
        os.close(parent_fd)


def snapshot_json(path: Path) -> tuple[Any, FileSnapshot]:
    snapshot = snapshot_file(path)
    return _strict_json_payload(snapshot.payload, str(snapshot.path)), snapshot


def strict_json(path: Path) -> Any:
    """Read and parse JSON from one safe file snapshot."""

    value, _ = snapshot_json(path)
    return value


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return snapshot_file(path).sha256


def tree_evidence(root: Path) -> dict[str, Any]:
    base = Path(root)
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(item for item in base.rglob("*") if item.is_file()):
        if path.is_symlink():
            raise ContractError(f"tree contains a symlink: {path}")
        payload = path.read_bytes()
        relative = path.relative_to(base).as_posix()
        file_digest = hashlib.sha256(payload).hexdigest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
        count += 1
        total += len(payload)
    return {
        "file_count": count,
        "total_bytes": total,
        "tree_sha256": digest.hexdigest(),
    }


def verify_live_source_records(
    records: Any,
    expected_evidence: Any,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Bind a manifest source snapshot to every current live source byte."""

    if type(records) is not list or not records:
        raise ContractError("v1 source records must be a non-empty array")
    live_records: list[dict[str, Any]] = []
    root = Path(project_root).resolve()
    seen: set[str] = set()
    for index, value in enumerate(records):
        record = _require_exact_keys(
            value, ("path", "bytes", "sha256"), f"v1.source_records[{index}]"
        )
        relative_text = _require_string(record["path"], f"v1.source_records[{index}].path")
        relative = Path(relative_text)
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_text:
            raise ContractError("v1 source record contains an unsafe/noncanonical path")
        if relative_text in seen:
            raise ContractError("v1 source records contain a duplicate path")
        seen.add(relative_text)
        source = root / relative
        if not source.is_file() or source.is_symlink() or root not in source.resolve().parents:
            raise ContractError(f"v1 live source is missing, unsafe, or a symlink: {relative_text}")
        expected_bytes = record["bytes"]
        if type(expected_bytes) is not int or expected_bytes < 0:
            raise ContractError("v1 source record byte count is invalid")
        _require_string(record["sha256"], f"v1.source_records[{index}].sha256", pattern=SHA256_RE)
        snapshot = snapshot_file(source)
        live = {
            "path": relative_text,
            "bytes": snapshot.bytes,
            "sha256": snapshot.sha256,
        }
        if live != dict(record):
            raise ContractError(f"v1 live source bytes changed: {relative_text}")
        live_records.append(live)
    if live_records != sorted(live_records, key=lambda item: item["path"]):
        raise ContractError("v1 source records are not in canonical path order")
    live_evidence = source_tree_evidence(live_records)
    if live_evidence != expected_evidence:
        raise ContractError("v1 live source-tree evidence changed")
    return live_evidence


def artifact_records(root: Path, *, omit: Iterable[str] = ()) -> list[dict[str, Any]]:
    omitted = set(omit)
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(item for item in Path(root).rglob("*") if item.is_file())
        if path.relative_to(root).as_posix() not in omitted
    ]


def _require_exact_keys(value: Any, expected: Sequence[str], path: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise ContractError(f"{path} must be an object")
    expected_set = set(expected)
    actual = set(value)
    if actual != expected_set:
        raise ContractError(
            f"{path} keys differ; missing={sorted(expected_set - actual)}, "
            f"unknown={sorted(actual - expected_set)}"
        )
    return value


def _require_string(value: Any, path: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str or not value or len(value) > 4096:
        raise ContractError(f"{path} must be a non-empty bounded string")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ContractError(f"{path} has an invalid format")
    return value


def _require_bool(value: Any, expected: bool, path: str) -> None:
    if type(value) is not bool or value is not expected:
        raise ContractError(f"{path} must be exactly {expected!r}")


def _require_number(value: Any, path: str, *, positive: bool = False) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ContractError(f"{path} must be a finite number")
    number = float(value)
    if positive and not number > 0:
        raise ContractError(f"{path} must be positive")
    return number


def _require_exact_number(value: Any, expected: float | int, path: str) -> None:
    number = _require_number(value, path)
    if number != float(expected):
        raise ContractError(f"{path} must be exactly {expected}")


def _require_positive_integer(value: Any, path: str) -> int:
    if type(value) is not int or value < 1:
        raise ContractError(f"{path} must be a positive integer")
    return value


def _parse_utc(value: Any, path: str) -> datetime:
    text = _require_string(value, path, pattern=UTC_RE)
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as error:
        raise ContractError(f"{path} is not a real UTC timestamp") from error
    if parsed.tzinfo != timezone.utc:
        raise ContractError(f"{path} must use UTC Z notation")
    return parsed


def utc_text(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


def _external_runtime_path(path: Path) -> Path:
    source = _absolute_unresolved(path)
    project = PROJECT_ROOT.resolve()
    # Never resolve the final component: doing so would turn a rejected symlink
    # into an apparently ordinary target path.  The eventual openat snapshot
    # checks the final component with O_NOFOLLOW.
    descriptor = _open_directory_fd(source.parent)
    os.close(descriptor)
    if source == project or project in source.parents:
        raise ContractError(f"runtime evidence/state must remain outside repository: {source}")
    return source


def _real_account_home() -> Path:
    """Return the OS account database home; caller-controlled HOME is ignored."""

    try:
        record = pwd.getpwuid(os.getuid())
    except (KeyError, OSError) as error:
        raise ContractError("cannot resolve the real OS account identity") from error
    home = Path(record.pw_dir)
    if not home.is_absolute():
        raise ContractError("OS account database returned a non-absolute home")
    descriptor = _open_directory_fd(home)
    try:
        metadata = os.fstat(descriptor)
        if metadata.st_uid != os.getuid():
            raise ContractError("real account home is not owned by the current uid")
    finally:
        os.close(descriptor)
    return home


def canonical_ledger_root() -> Path:
    return _real_account_home() / LEDGER_RELATIVE_PATH


def _host_identity_sha256() -> str:
    """Hash a stable platform identity without storing the raw identifier."""

    candidates: list[bytes] = []
    if sys_platform := os.uname().sysname.lower():
        if sys_platform == "darwin":
            try:
                value = subprocess.check_output(
                    ("sysctl", "-n", "kern.uuid"),
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                ).strip()
                if value:
                    candidates.append(value)
            except (OSError, subprocess.SubprocessError):
                pass
        elif Path("/etc/machine-id").exists():
            try:
                candidates.append(snapshot_file(Path("/etc/machine-id")).payload.strip())
            except ContractError:
                pass
    if not candidates:
        raise ContractError("stable host identity is unavailable; ledger cannot be trusted")
    return hashlib.sha256(b"r11-ledger-host-v1\0" + candidates[0]).hexdigest()


def verify_frozen_v1() -> dict[str, Any]:
    """Verify every required v1 lock without importing or modifying v1."""

    lock = strict_json(BASELINE_LOCK_PATH)
    bundle_lock = lock["v1_bundle"]
    actual_tree = tree_evidence(V1_ROOT)
    expected_tree = {
        "file_count": bundle_lock["file_count"],
        "total_bytes": bundle_lock["total_bytes"],
        "tree_sha256": bundle_lock["tree_sha256"],
    }
    if actual_tree != expected_tree:
        raise ContractError(f"frozen v1 bundle tree changed: {actual_tree}")
    manifest_path = V1_ROOT / "manifest.json"
    if sha256_file(manifest_path) != bundle_lock["manifest_sha256"]:
        raise ContractError("frozen v1 manifest hash changed")
    manifest = strict_json(manifest_path)
    if manifest["package_id"] != bundle_lock["package_id"]:
        raise ContractError("frozen v1 package identity changed")
    source_lock = lock["v1_source_closure"]
    if manifest["source_tree_evidence"] != {
        "source_file_count": source_lock["file_count"],
        "source_bytes": source_lock["source_bytes"],
        "source_tree_sha256": source_lock["tree_sha256"],
    }:
        raise ContractError("frozen v1 source-closure identity changed")
    verify_live_source_records(
        manifest["source_records"],
        manifest["source_tree_evidence"],
        project_root=PROJECT_ROOT,
    )
    if manifest["canonical_config_sha256"] != lock["v1_config"]["canonical_sha256"]:
        raise ContractError("frozen v1 canonical config identity changed")
    selected = lock["selected_article"]
    model_path = V1_ROOT / selected["model_3mf_relative_path"]
    stl_path = V1_ROOT / selected["stl_relative_path"]
    if (
        model_path.stat().st_size != selected["model_3mf_bytes"]
        or sha256_file(model_path) != selected["model_3mf_sha256"]
    ):
        raise ContractError("frozen v1 selected 3MF changed")
    if (
        stl_path.stat().st_size != selected["stl_bytes"]
        or sha256_file(stl_path) != selected["stl_sha256"]
    ):
        raise ContractError("frozen v1 selected STL changed")
    if (
        manifest["geometry_digests_by_mesh_id"].get(selected["article_id"])
        != selected["canonical_geometry_sha256"]
    ):
        raise ContractError("frozen v1 selected canonical geometry changed")
    status = strict_json(V1_ROOT / "release_status.json")
    validation = strict_json(V1_ROOT / "validation.json")
    false_status = (
        "all_physical_gates_complete",
        "production_ready",
        "wall_installation_authorized",
        "drilling_coordinates_released",
        "drilling_schedule_released",
        "print_authorized",
        "test_load_authorized",
    )
    if any(status.get(key) is not False for key in false_status):
        raise ContractError("frozen v1 physical authorization boundary changed")
    false_validation = (
        "print_authorized",
        "wall_installation_authorized",
        "drilling_coordinates_released",
        "drilling_schedule_released",
        "test_load_authorized",
    )
    if any(validation.get(key) is not False for key in false_validation):
        raise ContractError("frozen v1 validation boundary changed")
    if (validation.get("rated_load_kg"), validation.get("rated_load_lb")) != (0.0, 0.0):
        raise ContractError("frozen v1 load rating is not zero")
    return {
        "verified": True,
        "package_id": manifest["package_id"],
        "manifest_sha256": bundle_lock["manifest_sha256"],
        "tree": actual_tree,
        "source_tree": manifest["source_tree_evidence"],
        "canonical_config_sha256": manifest["canonical_config_sha256"],
        "selected_article": selected,
        "v1_print_authorized": False,
    }


def v2_source_paths() -> tuple[Path, ...]:
    required = (
        V2_ROOT / "README.md",
        V2_ROOT / "PRINT_GATE_A_LEFT.md",
        BASELINE_LOCK_PATH,
        RELEASE_CONTRACT_PATH,
        V2_ROOT / "control_contract.py",
        V2_ROOT / "evaluate_attempt.py",
        V2_ROOT / "generate_controlled_release.py",
        ATTEMPT_SCHEMA_PATH,
        PERMISSION_SCHEMA_PATH,
        PERMIT_SCHEMA_PATH,
        CONSUMPTION_SCHEMA_PATH,
    )
    missing = [str(path) for path in required if not path.is_file() or path.is_symlink()]
    if missing:
        raise ContractError(f"v2 source closure is incomplete: {missing}")
    return tuple(sorted(required))


def v2_source_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in v2_source_paths():
        snapshot = snapshot_file(path)
        records.append(
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "bytes": snapshot.bytes,
                "sha256": snapshot.sha256,
            }
        )
    return records


def source_tree_evidence(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    digest = hashlib.sha256()
    total = 0
    for record in records:
        digest.update(str(record["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\n")
        total += int(record["bytes"])
    return {
        "source_file_count": len(records),
        "source_bytes": total,
        "source_tree_sha256": digest.hexdigest(),
    }


def _validate_selected_article(value: Any) -> None:
    selected = strict_json(BASELINE_LOCK_PATH)["selected_article"]
    obj = _require_exact_keys(
        value,
        (
            "article_id",
            "model_3mf_relative_path",
            "model_3mf_sha256",
            "model_3mf_bytes",
            "stl_sha256",
            "canonical_geometry_sha256",
        ),
        "selected_article",
    )
    expected = {
        key: selected[key]
        for key in obj
    }
    if dict(obj) != expected:
        raise ContractError("selected_article is not the exact frozen Gate A-left article")


def compute_reviewed_job_digest(attempt: Mapping[str, Any]) -> str:
    material = dict(attempt)
    material.pop("reviewed_job_digest", None)
    return canonical_json_sha256(material)


def validate_attempt(value: Any) -> dict[str, Any]:
    """Strictly validate exact-left, quantity-one reviewed slice evidence."""

    top = _require_exact_keys(
        value,
        (
            "schema_version",
            "attempt_id",
            "captured_at_utc",
            "selected_article",
            "slicer",
            "plate_object",
            "slice_result",
            "screenshots",
            "live_state",
            "provenance",
            "evidence_files",
            "reviewed_job_digest",
        ),
        "attempt",
    )
    if top["schema_version"] != ATTEMPT_SCHEMA_VERSION:
        raise ContractError("attempt.schema_version is unsupported")
    _require_string(top["attempt_id"], "attempt.attempt_id", pattern=ATTEMPT_ID_RE)
    _parse_utc(top["captured_at_utc"], "attempt.captured_at_utc")
    _validate_selected_article(top["selected_article"])

    slicer = _require_exact_keys(
        top["slicer"],
        (
            "application", "version", "application_executable_sha256",
            "temporary_project_sha256",
            "sliced_plate_file_sha256", "sliced_plate_file_bytes",
            "gcode_payload_sha256", "gcode_config_block_sha256",
            "printer_profile_export_sha256", "filament_profile_export_sha256",
            "process_profile_export_sha256",
            "printer_profile_snapshot_sha256", "filament_profile_snapshot_sha256",
            "process_profile_snapshot_sha256",
            "printer_model", "nozzle_diameter_mm",
            "nozzle_flow", "plate_type", "process_preset", "layer_height_mm",
            "initial_layer_height_mm",
            "wall_loops", "sparse_infill_density_percent", "sparse_infill_pattern",
            "top_shell_layers", "bottom_shell_layers", "support_enabled",
            "support_build_plate_only", "support_critical_regions_only",
            "support_remove_small_overhang",
            "brim_type", "brim_width_mm", "brim_object_gap_mm",
            "nozzle_temperature_first_layer_c", "nozzle_temperature_other_layers_c",
            "bed_temperature_first_layer_c", "bed_temperature_other_layers_c",
            "flow_ratio", "maximum_volumetric_speed_mm3_s",
            "part_cooling_fan_min_percent", "part_cooling_fan_max_percent",
            "overhang_fan_percent", "bridge_speed_mm_s",
            "overhang_0_25_speed_mm_s", "overhang_25_50_speed_mm_s",
            "overhang_50_75_speed_mm_s", "overhang_75_100_speed_mm_s",
            "machine_start_gcode_sha256", "machine_end_gcode_sha256",
            "change_filament_gcode_sha256", "layer_change_gcode_sha256",
            "time_lapse_gcode_sha256",
        ),
        "attempt.slicer",
    )
    exact_slicer = {
        "application": "Bambu Studio",
        "version": "02.07.01.62",
        "application_executable_sha256": "b022be6750898454803e9e07178b7c7446c0e5b4d148c593b4b56efde09ba281",
        "printer_model": "Bambu Lab A1 mini",
        "nozzle_flow": "standard",
        "plate_type": "Textured PEI Plate",
        "process_preset": "0.20mm Strength @BBL A1M",
        "sparse_infill_pattern": "grid",
        "brim_type": "outer",
    }
    for key, expected in exact_slicer.items():
        if slicer[key] != expected:
            raise ContractError(f"attempt.slicer.{key} must be exactly {expected!r}")
    for key in (
        "temporary_project_sha256", "sliced_plate_file_sha256",
        "gcode_payload_sha256", "gcode_config_block_sha256",
        "printer_profile_export_sha256",
        "filament_profile_export_sha256", "process_profile_export_sha256",
        "printer_profile_snapshot_sha256", "filament_profile_snapshot_sha256",
        "process_profile_snapshot_sha256", "machine_start_gcode_sha256",
        "machine_end_gcode_sha256", "change_filament_gcode_sha256",
        "layer_change_gcode_sha256", "time_lapse_gcode_sha256",
    ):
        _require_string(slicer[key], f"attempt.slicer.{key}", pattern=SHA256_RE)
    _require_positive_integer(
        slicer["sliced_plate_file_bytes"],
        "attempt.slicer.sliced_plate_file_bytes",
    )
    for key, expected in (
        ("nozzle_diameter_mm", 0.4), ("layer_height_mm", 0.2),
        ("initial_layer_height_mm", 0.2),
        ("wall_loops", 6), ("sparse_infill_density_percent", 25),
        ("top_shell_layers", 5), ("bottom_shell_layers", 3),
        ("brim_width_mm", 5.0), ("brim_object_gap_mm", 0.1),
        ("nozzle_temperature_first_layer_c", 250),
        ("nozzle_temperature_other_layers_c", 245),
        ("bed_temperature_first_layer_c", 60),
        ("bed_temperature_other_layers_c", 60),
        ("flow_ratio", 0.94),
        ("maximum_volumetric_speed_mm3_s", 9.0),
        ("part_cooling_fan_min_percent", 10),
        ("part_cooling_fan_max_percent", 30),
        ("overhang_fan_percent", 90),
        ("bridge_speed_mm_s", 50),
        ("overhang_0_25_speed_mm_s", 0),
        ("overhang_25_50_speed_mm_s", 50),
        ("overhang_50_75_speed_mm_s", 30),
        ("overhang_75_100_speed_mm_s", 10),
    ):
        _require_exact_number(slicer[key], expected, f"attempt.slicer.{key}")
    _require_bool(slicer["support_enabled"], False, "attempt.slicer.support_enabled")
    for key in ("support_build_plate_only", "support_critical_regions_only"):
        _require_bool(slicer[key], False, f"attempt.slicer.{key}")
    _require_bool(
        slicer["support_remove_small_overhang"], True,
        "attempt.slicer.support_remove_small_overhang",
    )
    contract_slice = strict_json(RELEASE_CONTRACT_PATH)["slice_contract"]
    for key in (
        "machine_start_gcode_sha256", "machine_end_gcode_sha256",
        "change_filament_gcode_sha256", "layer_change_gcode_sha256",
        "time_lapse_gcode_sha256",
    ):
        if slicer[key] != contract_slice[key]:
            raise ContractError(f"attempt.slicer.{key} differs from the approved digest")

    plate = _require_exact_keys(
        top["plate_object"],
        (
            "plate_object_count", "copy_count", "article_id", "scale_percent_xyz",
            "rotation_degrees_xyz", "mirrored", "auto_oriented", "repaired",
            "modifier_present", "negative_volume_present", "support_enforcer_present",
        ),
        "attempt.plate_object",
    )
    _require_exact_number(plate["plate_object_count"], 1, "plate_object.plate_object_count")
    _require_exact_number(plate["copy_count"], 1, "plate_object.copy_count")
    if plate["article_id"] != strict_json(BASELINE_LOCK_PATH)["selected_article"]["article_id"]:
        raise ContractError("plate contains an alternate article")
    if plate["scale_percent_xyz"] != [100.0, 100.0, 100.0]:
        raise ContractError("plate object scale must be exactly 100% XYZ")
    if plate["rotation_degrees_xyz"] != [0.0, 0.0, 0.0]:
        raise ContractError("plate object rotation must be identity")
    for key in (
        "mirrored", "auto_oriented", "repaired", "modifier_present",
        "negative_volume_present", "support_enforcer_present",
    ):
        _require_bool(plate[key], False, f"attempt.plate_object.{key}")

    sliced = _require_exact_keys(
        top["slice_result"],
        (
            "layer_count", "print_time_seconds", "filament_mass_g",
            "filament_length_mm", "bed_envelope_violation",
            "support_toolpaths_present", "detached_islands_present",
            "capture_geometry_blocked", "walls_omitted", "unintended_bridges_present",
            "undocumented_repairs_present", "all_slicer_warnings_recorded", "warnings",
        ),
        "attempt.slice_result",
    )
    _require_positive_integer(sliced["layer_count"], "slice_result.layer_count")
    _require_positive_integer(sliced["print_time_seconds"], "slice_result.print_time_seconds")
    _require_number(sliced["filament_mass_g"], "slice_result.filament_mass_g", positive=True)
    _require_number(sliced["filament_length_mm"], "slice_result.filament_length_mm", positive=True)
    for key in (
        "bed_envelope_violation", "support_toolpaths_present", "detached_islands_present",
        "capture_geometry_blocked", "walls_omitted", "unintended_bridges_present",
        "undocumented_repairs_present",
    ):
        _require_bool(sliced[key], False, f"attempt.slice_result.{key}")
    _require_bool(
        sliced["all_slicer_warnings_recorded"], True,
        "attempt.slice_result.all_slicer_warnings_recorded",
    )
    if type(sliced["warnings"]) is not list:
        raise ContractError("attempt.slice_result.warnings must be an array")
    for index, warning_value in enumerate(sliced["warnings"]):
        warning = _require_exact_keys(
            warning_value, ("exact_text", "layer_level_disposition", "resolved"),
            f"attempt.slice_result.warnings[{index}]",
        )
        _require_string(warning["exact_text"], f"warnings[{index}].exact_text")
        _require_string(
            warning["layer_level_disposition"],
            f"warnings[{index}].layer_level_disposition",
        )
        _require_bool(warning["resolved"], True, f"warnings[{index}].resolved")

    screenshot_keys = (
        "prepare_and_transform_sha256", "effective_settings_sha256",
        "slice_summary_and_warnings_sha256", "first_layer_sha256",
        "critical_capture_layer_sha256", "cross_lap_layer_sha256",
        "final_layers_sha256", "current_printer_and_filament_state_sha256",
    )
    screenshots = _require_exact_keys(top["screenshots"], screenshot_keys, "attempt.screenshots")
    for key in screenshot_keys:
        _require_string(screenshots[key], f"attempt.screenshots.{key}", pattern=SHA256_RE)
    if len(set(screenshots.values())) != len(screenshot_keys):
        raise ContractError("all eight screenshot evidence hashes must be pairwise distinct")

    live = _require_exact_keys(
        top["live_state"],
        (
            "captured_at_utc", "plate_physically_empty", "plate_clean",
            "plate_correctly_seated", "printer_idle", "printer_error_free",
            "physical_printer_model", "printer_serial_sha256", "firmware_version",
            "module_firmware", "physical_nozzle_diameter_mm",
            "physical_nozzle_material", "physical_nozzle_flow",
            "physical_plate_type", "filament",
        ),
        "attempt.live_state",
    )
    _parse_utc(live["captured_at_utc"], "attempt.live_state.captured_at_utc")
    for key in (
        "plate_physically_empty", "plate_clean", "plate_correctly_seated",
        "printer_idle", "printer_error_free",
    ):
        _require_bool(live[key], True, f"attempt.live_state.{key}")
    if live["physical_printer_model"] != "Bambu Lab A1 mini":
        raise ContractError("physical printer must be the reviewed Bambu Lab A1 mini")
    if live["printer_serial_sha256"] != "a3c07a6f58e39c108ea8f0ee1d96e9582d00a8b9c7973195e26fe2625ff525d8":
        raise ContractError("physical printer serial hash differs from the approved device")
    if live["firmware_version"] != "01.08.01.00":
        raise ContractError("physical printer base firmware differs from the approved version")
    expected_modules = {
        "esp32_software_version": "01.16.41.96",
        "esp32_hardware_revision": "AP05",
        "motion_controller_software_version": "00.00.34.17",
        "motion_controller_hardware_revision": "MC02",
        "motion_controller_loader_revision_suffix": ".32",
        "toolhead_software_version": "00.01.07.73",
        "toolhead_hardware_revision": "TH03",
        "toolhead_loader_revision_suffix": ".26",
    }
    if live["module_firmware"] != expected_modules:
        raise ContractError("physical printer module firmware/hardware map changed")
    _require_exact_number(
        live["physical_nozzle_diameter_mm"], 0.4,
        "attempt.live_state.physical_nozzle_diameter_mm",
    )
    if live["physical_nozzle_material"] != "stainless_steel":
        raise ContractError("physical nozzle material must be stainless steel")
    if live["physical_nozzle_flow"] != "standard":
        raise ContractError("physical nozzle must be standard flow")
    if live["physical_plate_type"] != "Textured PEI Plate":
        raise ContractError("physical plate must be Textured PEI Plate")
    filament = _require_exact_keys(
        live["filament"],
        (
            "brand", "material", "color", "diameter_mm", "product_asin",
            "lot_id", "drying_record",
            "external_spool_mapping_verified", "project_filament_mapping",
        ),
        "attempt.live_state.filament",
    )
    for key, expected in (
        ("brand", "SUNLU"), ("material", "PETG"), ("color", "black"),
        ("product_asin", "B0D1KC72YP"),
        ("project_filament_mapping", "SUNLU PETG @BBL A1M 0.4 nozzle"),
    ):
        if filament[key] != expected:
            raise ContractError(f"attempt.live_state.filament.{key} changed")
    _require_exact_number(
        filament["diameter_mm"], 1.75,
        "attempt.live_state.filament.diameter_mm",
    )
    _require_string(filament["lot_id"], "attempt.live_state.filament.lot_id")
    drying = _require_exact_keys(
        filament["drying_record"],
        ("dried", "method", "temperature_c", "duration_hours", "completed_at_utc"),
        "attempt.live_state.filament.drying_record",
    )
    _require_bool(drying["dried"], True, "attempt.live_state.filament.drying_record.dried")
    _require_string(drying["method"], "attempt.live_state.filament.drying_record.method")
    _require_exact_number(
        drying["temperature_c"], 50.0,
        "attempt.live_state.filament.drying_record.temperature_c",
    )
    duration = _require_number(
        drying["duration_hours"],
        "attempt.live_state.filament.drying_record.duration_hours",
        positive=True,
    )
    if not 6.0 <= duration <= 8.0:
        raise ContractError("drying duration must be within the approved 6-8 hour window")
    drying_completed = _parse_utc(
        drying["completed_at_utc"],
        "attempt.live_state.filament.drying_record.completed_at_utc",
    )
    _require_bool(
        filament["external_spool_mapping_verified"], True,
        "attempt.live_state.filament.external_spool_mapping_verified",
    )

    provenance_specs = {
        "printer_telemetry": (
            "read_only_printer_telemetry", "printer_telemetry_snapshot"
        ),
        "plate_observation": (
            "fresh_human_plate_observation", "plate_observation_record"
        ),
        "nozzle_observation": (
            "fresh_human_nozzle_observation", "nozzle_observation_record"
        ),
        "spool_label": (
            "photographed_physical_spool_label", "spool_label_evidence"
        ),
        "drying_log": (
            "dryer_log_or_photographed_display", "drying_log_evidence"
        ),
    }
    provenance = _require_exact_keys(
        top["provenance"], tuple(provenance_specs), "attempt.provenance"
    )
    provenance_times: dict[str, datetime] = {}
    for key, (source_kind, _) in provenance_specs.items():
        record = _require_exact_keys(
            provenance[key], ("source_kind", "captured_at_utc", "sha256"),
            f"attempt.provenance.{key}",
        )
        if record["source_kind"] != source_kind:
            raise ContractError(f"attempt.provenance.{key}.source_kind changed")
        provenance_times[key] = _parse_utc(
            record["captured_at_utc"], f"attempt.provenance.{key}.captured_at_utc"
        )
        _require_string(
            record["sha256"], f"attempt.provenance.{key}.sha256", pattern=SHA256_RE
        )
    provenance_hashes = [provenance[key]["sha256"] for key in provenance_specs]
    if (
        len(set(provenance_hashes)) != len(provenance_hashes)
        or set(provenance_hashes) & set(screenshots.values())
    ):
        raise ContractError(
            "live provenance files must be pairwise distinct and separate from screenshots"
        )

    evidence = _require_exact_keys(
        top["evidence_files"], EVIDENCE_FILE_KEYS, "attempt.evidence_files"
    )
    relative_paths: set[str] = set()
    for key in EVIDENCE_FILE_KEYS:
        record = _require_exact_keys(
            evidence[key], ("relative_path", "bytes", "sha256"),
            f"attempt.evidence_files.{key}",
        )
        relative_text = _require_string(
            record["relative_path"], f"attempt.evidence_files.{key}.relative_path"
        )
        relative = Path(relative_text)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != relative_text
            or relative_text in relative_paths
        ):
            raise ContractError("evidence file paths must be unique canonical relative paths")
        relative_paths.add(relative_text)
        _require_positive_integer(record["bytes"], f"attempt.evidence_files.{key}.bytes")
        _require_string(
            record["sha256"], f"attempt.evidence_files.{key}.sha256", pattern=SHA256_RE
        )
    evidence_hash_bindings = {
        "temporary_project": slicer["temporary_project_sha256"],
        "sliced_plate_file": slicer["sliced_plate_file_sha256"],
        "gcode_payload": slicer["gcode_payload_sha256"],
        "gcode_config_block": slicer["gcode_config_block_sha256"],
        "printer_profile_export": slicer["printer_profile_export_sha256"],
        "filament_profile_export": slicer["filament_profile_export_sha256"],
        "process_profile_export": slicer["process_profile_export_sha256"],
        "printer_profile_snapshot": slicer["printer_profile_snapshot_sha256"],
        "filament_profile_snapshot": slicer["filament_profile_snapshot_sha256"],
        "process_profile_snapshot": slicer["process_profile_snapshot_sha256"],
        "prepare_and_transform_screenshot": screenshots["prepare_and_transform_sha256"],
        "effective_settings_screenshot": screenshots["effective_settings_sha256"],
        "slice_summary_and_warnings_screenshot": screenshots["slice_summary_and_warnings_sha256"],
        "first_layer_screenshot": screenshots["first_layer_sha256"],
        "critical_capture_layer_screenshot": screenshots["critical_capture_layer_sha256"],
        "cross_lap_layer_screenshot": screenshots["cross_lap_layer_sha256"],
        "final_layers_screenshot": screenshots["final_layers_sha256"],
        "current_printer_and_filament_state_screenshot": screenshots[
            "current_printer_and_filament_state_sha256"
        ],
        **{
            evidence_key: provenance[key]["sha256"]
            for key, (_, evidence_key) in provenance_specs.items()
        },
    }
    for key, digest in evidence_hash_bindings.items():
        if evidence[key]["sha256"] != digest:
            raise ContractError(f"evidence file hash does not match reviewed field: {key}")
    if evidence["sliced_plate_file"]["bytes"] != slicer["sliced_plate_file_bytes"]:
        raise ContractError("sliced plate evidence byte count does not match slicer record")

    attempt_capture = _parse_utc(top["captured_at_utc"], "attempt.captured_at_utc")
    live_capture = _parse_utc(live["captured_at_utc"], "attempt.live_state.captured_at_utc")
    if drying_completed > min(attempt_capture, live_capture):
        raise ContractError("drying must be complete before attempt and live-state capture")
    if provenance_times["printer_telemetry"] != live_capture:
        raise ContractError("printer telemetry must be captured at the bound live-state time")
    if provenance_times["plate_observation"] != live_capture:
        raise ContractError("human plate observation must be captured at the bound live-state time")
    if provenance_times["nozzle_observation"] != live_capture:
        raise ContractError("human nozzle observation must be captured at the bound live-state time")
    if not (
        provenance_times["spool_label"] <= live_capture
        and (live_capture - provenance_times["spool_label"]).total_seconds() <= 300
    ):
        raise ContractError("physical spool-label evidence must be fresh at live-state capture")
    if provenance_times["drying_log"] != drying_completed:
        raise ContractError("drying-log evidence timestamp must equal drying completion")

    _require_string(top["reviewed_job_digest"], "attempt.reviewed_job_digest", pattern=SHA256_RE)
    expected_digest = compute_reviewed_job_digest(top)
    if top["reviewed_job_digest"] != expected_digest:
        raise ContractError("reviewed_job_digest does not bind the exact attempt evidence")
    return dict(top)


@dataclass(frozen=True)
class AttemptBundle:
    attempt: dict[str, Any]
    attempt_snapshot: FileSnapshot
    evidence: Mapping[str, FileSnapshot]
    extracted_gcode: bytes
    extracted_gcode_sha256: str
    extracted_config: bytes
    extracted_config_sha256: str
    profile_closure_sha256: str
    job_identity_sha256: str


def _extract_gcode_from_sliced_archive(snapshot: FileSnapshot) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(snapshot.payload), "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ContractError("sliced archive contains duplicate member names")
            for info in infos:
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise ContractError("sliced archive contains a symlink member")
                member = Path(info.filename)
                if member.is_absolute() or ".." in member.parts:
                    raise ContractError("sliced archive contains an unsafe member path")
            gcode_infos = [
                info for info in infos
                if not info.is_dir() and info.filename.lower().endswith(".gcode")
            ]
            if len(gcode_infos) != 1:
                raise ContractError("sliced archive must contain exactly one G-code payload")
            info = gcode_infos[0]
            if info.file_size <= 0 or info.file_size > 1024 * 1024 * 1024:
                raise ContractError("embedded G-code size is outside the approved bound")
            return archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, OSError) as error:
        raise ContractError("sliced plate evidence is not a valid trusted ZIP archive") from error


def _extract_and_validate_gcode_config(gcode: bytes) -> bytes:
    if b"\0" in gcode:
        raise ContractError("embedded G-code contains a NUL byte")
    header_lines = gcode[:16384].splitlines()
    if b"; BambuStudio 02.07.01.62" not in header_lines:
        raise ContractError("embedded G-code does not identify the pinned Bambu Studio version")
    if gcode.count(GCODE_CONFIG_START) != 1 or gcode.count(GCODE_CONFIG_END) != 1:
        raise ContractError("embedded G-code must contain one exact config block")
    start = gcode.index(GCODE_CONFIG_START)
    end = gcode.index(GCODE_CONFIG_END, start) + len(GCODE_CONFIG_END)
    block = gcode[start:end]
    try:
        lines = block.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise ContractError("embedded G-code config block is not UTF-8") from error
    parsed: dict[str, str] = {}
    for line in lines[1:-1]:
        if not line:
            continue
        match = re.fullmatch(r"; ([A-Za-z0-9_]+) = (.*)", line)
        if match is None:
            raise ContractError("embedded G-code config has a malformed line")
        key, value = match.groups()
        if key in parsed:
            raise ContractError(f"embedded G-code config has a duplicate key: {key}")
        parsed[key] = value
    expected = strict_json(RELEASE_CONTRACT_PATH)[
        "effective_profile_proof_contract"
    ]["gcode_config_exact_controlled_values"]
    for key, value in expected.items():
        if key not in parsed:
            raise ContractError(f"embedded G-code config is missing controlled key: {key}")
        if parsed[key] != value:
            raise ContractError(f"embedded G-code config controlled value changed: {key}")
    _require_approved_gcode_config(block)
    return block


def _require_approved_gcode_config(block: bytes) -> None:
    """Require the complete emitted config bytes, not only a controlled subset."""

    approved = strict_json(RELEASE_CONTRACT_PATH)[
        "effective_profile_proof_contract"
    ]["approved_emitted_gcode_config"]
    if (
        len(block) != approved["bytes"]
        or hashlib.sha256(block).hexdigest() != approved["sha256"]
    ):
        raise ContractError("complete emitted G-code config is not the exact approved closure")


def _validate_profile_closure(
    attempt: Mapping[str, Any], evidence: Mapping[str, FileSnapshot]
) -> str:
    contract = strict_json(RELEASE_CONTRACT_PATH)["effective_profile_proof_contract"]
    closure: dict[str, Any] = {}
    for kind in PROFILE_KINDS:
        export_key = f"{kind}_profile_export"
        snapshot_key = f"{kind}_profile_snapshot"
        native = _strict_json_payload(
            evidence[export_key].payload, str(evidence[export_key].path)
        )
        expected_native = contract[kind]
        approved = contract["approved_native_exports"][kind]
        if (
            evidence[export_key].bytes != approved["bytes"]
            or evidence[export_key].sha256 != approved["sha256"]
        ):
            raise ContractError(f"native {kind} profile bytes/hash are not approved")
        _require_exact_keys(
            native, tuple(expected_native), f"native_{kind}_profile_export"
        )
        if native != expected_native:
            raise ContractError(f"native {kind} profile is not the exact approved effective export")
        derived = {
            "schema_version": PROFILE_SNAPSHOT_SCHEMA_VERSION,
            "profile_kind": kind,
            "native_export_sha256": evidence[export_key].sha256,
            "native_export_bytes": evidence[export_key].bytes,
            "effective_settings": expected_native["effective_settings"],
        }
        if evidence[snapshot_key].payload != json_bytes(derived):
            raise ContractError(
                f"{kind} profile snapshot is not the deterministic trusted derivation"
            )
        closure[kind] = {
            "native_export_sha256": evidence[export_key].sha256,
            "native_export_bytes": evidence[export_key].bytes,
            "canonical_snapshot_sha256": evidence[snapshot_key].sha256,
            "canonical_snapshot_bytes": evidence[snapshot_key].bytes,
            "effective_settings": expected_native["effective_settings"],
        }
    slicer = attempt["slicer"]
    for kind in PROFILE_KINDS:
        if slicer[f"{kind}_profile_export_sha256"] != evidence[
            f"{kind}_profile_export"
        ].sha256:
            raise ContractError(f"{kind} native export hash binding changed")
        if slicer[f"{kind}_profile_snapshot_sha256"] != evidence[
            f"{kind}_profile_snapshot"
        ].sha256:
            raise ContractError(f"{kind} canonical snapshot hash binding changed")
    return canonical_json_sha256(closure)


def verify_installed_native_profile_sources() -> dict[str, str]:
    """Pin the genuine native Bambu system profile sources for this process."""

    contract = strict_json(RELEASE_CONTRACT_PATH)["effective_profile_proof_contract"]
    root = Path("/Applications/BambuStudio.app")
    result: dict[str, str] = {}
    for kind in PROFILE_KINDS:
        pin = contract["installed_native_source_pins"][kind]
        snapshot = snapshot_file(root / pin["application_relative_path"])
        if snapshot.bytes != pin["bytes"] or snapshot.sha256 != pin["sha256"]:
            raise ContractError(f"installed native Bambu {kind} profile source changed")
        result[kind] = snapshot.sha256
    return result


def verify_installed_bambu_executable() -> str:
    """Rehash the exact installed Bambu Studio executable for this process."""

    contract = strict_json(RELEASE_CONTRACT_PATH)["slice_contract"]
    snapshot = snapshot_file(
        Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
    )
    if (
        snapshot.bytes != contract["application_executable_bytes"]
        or snapshot.sha256 != contract["application_executable_sha256"]
    ):
        raise ContractError("installed Bambu Studio executable changed")
    return snapshot.sha256


def prepare_external_evidence_payloads(
    sliced_plate_path: Path,
    output_directory: Path,
) -> dict[str, Any]:
    """Safely materialize trusted slice/profile evidence outside the repository.

    The destination must not exist.  Every file is created with O_EXCL and the
    G-code/config bytes are derived from the sole member of the exact supplied
    sliced archive.  Profile payloads are emitted only from the frozen approved
    closure after the installed native Bambu sources have been reverified.
    """

    sliced_source = _external_runtime_path(sliced_plate_path)
    sliced_snapshot = snapshot_file(sliced_source)
    if sliced_snapshot.link_count != 1:
        raise ContractError("external sliced archive must have exactly one hard link")
    gcode = _extract_gcode_from_sliced_archive(sliced_snapshot)
    config = _extract_and_validate_gcode_config(gcode)
    executable_sha256 = verify_installed_bambu_executable()
    native_source_hashes = verify_installed_native_profile_sources()
    contract = strict_json(RELEASE_CONTRACT_PATH)["effective_profile_proof_contract"]

    payloads: dict[str, tuple[str, bytes]] = {
        "gcode_payload": ("gcode_payload.gcode", gcode),
        "gcode_config_block": ("gcode_config_block.txt", config),
    }
    for kind in PROFILE_KINDS:
        export = json_bytes(contract[kind])
        approved = contract["approved_native_exports"][kind]
        if len(export) != approved["bytes"] or hashlib.sha256(export).hexdigest() != approved["sha256"]:
            raise ContractError(f"frozen approved {kind} profile closure is internally inconsistent")
        snapshot = json_bytes(
            {
                "schema_version": PROFILE_SNAPSHOT_SCHEMA_VERSION,
                "profile_kind": kind,
                "native_export_sha256": approved["sha256"],
                "native_export_bytes": approved["bytes"],
                "effective_settings": contract[kind]["effective_settings"],
            }
        )
        payloads[f"{kind}_profile_export"] = (f"{kind}_profile_export.json", export)
        payloads[f"{kind}_profile_snapshot"] = (
            f"{kind}_profile_snapshot.json", snapshot
        )

    destination = _external_runtime_path(output_directory)
    parent_fd = _open_directory_fd(destination.parent)
    destination_fd = -1
    try:
        try:
            os.mkdir(destination.name, 0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
        except FileExistsError as error:
            raise ContractError(
                "prepared-evidence destination already exists; choose a fresh directory"
            ) from error
        destination_fd = os.open(
            destination.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        metadata = os.fstat(destination_fd)
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise ContractError("prepared-evidence destination owner/mode is not exact uid/0700")
        records: dict[str, dict[str, Any]] = {}
        for evidence_key, (filename, payload) in payloads.items():
            _atomic_create_at(destination_fd, filename, payload)
            snapshot = _snapshot_relative(destination_fd, Path(filename), destination)
            if snapshot.link_count != 1:
                raise ContractError(f"prepared evidence has multiple hard links: {evidence_key}")
            records[evidence_key] = {
                "relative_filename": filename,
                "bytes": snapshot.bytes,
                "sha256": snapshot.sha256,
            }
    finally:
        if destination_fd >= 0:
            os.close(destination_fd)
        os.close(parent_fd)
    return {
        "schema_version": "r11.gate-a-left-prepared-evidence-report.v1",
        "sliced_plate_file": {
            "path": str(sliced_source),
            "bytes": sliced_snapshot.bytes,
            "sha256": sliced_snapshot.sha256,
        },
        "installed_native_profile_source_sha256": native_source_hashes,
        "installed_bambu_executable_sha256": executable_sha256,
        "output_directory": str(destination),
        "derived_evidence": records,
        "print_authorized": False,
        "fresh_attempt_review_and_permission_still_required": True,
    }


def _derive_job_identity(
    attempt: Mapping[str, Any], *, gcode_sha256: str, gcode_bytes: int,
    config_sha256: str, config_bytes: int, profile_closure_sha256: str,
) -> str:
    return canonical_json_sha256(
        {
            "schema_version": "r11.gate-a-left-job-identity.v1",
            "selected_article": attempt["selected_article"],
            "plate_object": attempt["plate_object"],
            "slice_result": attempt["slice_result"],
            "slicer": attempt["slicer"],
            "live_printer_identity": {
                key: attempt["live_state"][key]
                for key in (
                    "physical_printer_model", "printer_serial_sha256",
                    "firmware_version", "module_firmware",
                    "physical_nozzle_diameter_mm", "physical_nozzle_material",
                    "physical_nozzle_flow", "physical_plate_type",
                )
            },
            "sliced_archive_sha256": attempt["slicer"]["sliced_plate_file_sha256"],
            "sliced_archive_bytes": attempt["slicer"]["sliced_plate_file_bytes"],
            "extracted_gcode_sha256": gcode_sha256,
            "extracted_gcode_bytes": gcode_bytes,
            "extracted_config_sha256": config_sha256,
            "extracted_config_bytes": config_bytes,
            "profile_closure_sha256": profile_closure_sha256,
        }
    )


def load_attempt_bundle(attempt_path: Path) -> AttemptBundle:
    """Read attempt+all evidence once, then derive archive/profile/job identity."""

    attempt_source = _external_runtime_path(attempt_path)
    root_fd = _open_directory_fd(attempt_source.parent)
    try:
        attempt_snapshot = _snapshot_relative(
            root_fd, Path(attempt_source.name), attempt_source.parent
        )
        if attempt_snapshot.link_count != 1:
            raise ContractError("external attempt JSON must have exactly one hard link")
        attempt = validate_attempt(
            _strict_json_payload(attempt_snapshot.payload, str(attempt_source))
        )
        snapshots: dict[str, FileSnapshot] = {}
        for key in EVIDENCE_FILE_KEYS:
            expected = attempt["evidence_files"][key]
            snapshot = _snapshot_relative(
                root_fd, Path(expected["relative_path"]), attempt_source.parent
            )
            if snapshot.link_count != 1:
                raise ContractError(f"external evidence must have exactly one hard link: {key}")
            actual = {
                "relative_path": expected["relative_path"],
                "bytes": snapshot.bytes,
                "sha256": snapshot.sha256,
            }
            if actual != expected:
                raise ContractError(f"external evidence file bytes changed: {key}")
            snapshots[key] = snapshot
    finally:
        os.close(root_fd)

    gcode = _extract_gcode_from_sliced_archive(snapshots["sliced_plate_file"])
    gcode_sha256 = hashlib.sha256(gcode).hexdigest()
    if (
        snapshots["gcode_payload"].payload != gcode
        or snapshots["gcode_payload"].sha256 != gcode_sha256
    ):
        raise ContractError("separate G-code payload does not equal archive-derived G-code")
    config = _extract_and_validate_gcode_config(gcode)
    config_sha256 = hashlib.sha256(config).hexdigest()
    if (
        snapshots["gcode_config_block"].payload != config
        or snapshots["gcode_config_block"].sha256 != config_sha256
    ):
        raise ContractError("separate config block does not equal G-code-derived config")
    profile_closure = _validate_profile_closure(attempt, snapshots)
    job_identity = _derive_job_identity(
        attempt, gcode_sha256=gcode_sha256, gcode_bytes=len(gcode),
        config_sha256=config_sha256, config_bytes=len(config),
        profile_closure_sha256=profile_closure,
    )
    return AttemptBundle(
        attempt=attempt, attempt_snapshot=attempt_snapshot, evidence=snapshots,
        extracted_gcode=gcode, extracted_gcode_sha256=gcode_sha256,
        extracted_config=config, extracted_config_sha256=config_sha256,
        profile_closure_sha256=profile_closure,
        job_identity_sha256=job_identity,
    )


def verify_external_evidence_files(
    attempt: Mapping[str, Any], attempt_path: Path
) -> list[dict[str, Any]]:
    """Compatibility wrapper backed by one-open trusted bundle derivation."""

    bundle = load_attempt_bundle(attempt_path)
    if bundle.attempt != dict(attempt):
        raise ContractError("supplied attempt differs from snapshotted attempt bytes")
    return [
        {
            "evidence_key": key,
            "relative_path": bundle.attempt["evidence_files"][key]["relative_path"],
            "bytes": bundle.evidence[key].bytes,
            "sha256": bundle.evidence[key].sha256,
        }
        for key in EVIDENCE_FILE_KEYS
    ]


def validate_permission(value: Any) -> dict[str, Any]:
    permission = _require_exact_keys(
        value,
        (
            "schema_version", "permission_id", "attempt_id",
            "attempt_evidence_sha256", "reviewed_job_digest", "question_exact",
            "response_exact", "granted", "granted_by", "granted_at_utc",
            "expires_at_utc",
        ),
        "permission",
    )
    if permission["schema_version"] != PERMISSION_SCHEMA_VERSION:
        raise ContractError("permission.schema_version is unsupported")
    _require_string(permission["permission_id"], "permission.permission_id", pattern=PERMISSION_ID_RE)
    _require_string(permission["attempt_id"], "permission.attempt_id", pattern=ATTEMPT_ID_RE)
    _require_string(
        permission["attempt_evidence_sha256"], "permission.attempt_evidence_sha256",
        pattern=SHA256_RE,
    )
    _require_string(permission["reviewed_job_digest"], "permission.reviewed_job_digest", pattern=SHA256_RE)
    contract = strict_json(RELEASE_CONTRACT_PATH)["permission_contract"]
    if permission["question_exact"] != contract["exact_question"]:
        raise ContractError("permission question is not exact")
    if permission["response_exact"] != contract["exact_affirmative_response"]:
        raise ContractError("permission response is not the exact fresh affirmative")
    _require_bool(permission["granted"], True, "permission.granted")
    if permission["granted_by"] != "human_user":
        raise ContractError("permission must be granted by the human user")
    granted = _parse_utc(permission["granted_at_utc"], "permission.granted_at_utc")
    expires = _parse_utc(permission["expires_at_utc"], "permission.expires_at_utc")
    if not expires > granted:
        raise ContractError("permission expiry must follow grant time")
    if (expires - granted).total_seconds() > contract["maximum_age_seconds"]:
        raise ContractError("permission validity interval is too long")
    return dict(permission)


def _assert_fresh(attempt: Mapping[str, Any], permission: Mapping[str, Any], now: datetime) -> None:
    maximum = strict_json(RELEASE_CONTRACT_PATH)["permission_contract"]["maximum_age_seconds"]
    current = now.astimezone(timezone.utc)
    for value, label in (
        (attempt["captured_at_utc"], "attempt capture"),
        (attempt["live_state"]["captured_at_utc"], "live-state capture"),
        (permission["granted_at_utc"], "permission grant"),
    ):
        timestamp = _parse_utc(value, label)
        age = (current - timestamp).total_seconds()
        if age < 0 or age > maximum:
            raise ContractError(f"{label} is not fresh at permit issue time")
    if current >= _parse_utc(permission["expires_at_utc"], "permission expiry"):
        raise ContractError("fresh permission has expired")
    granted = _parse_utc(permission["granted_at_utc"], "permission grant")
    attempt_capture = _parse_utc(attempt["captured_at_utc"], "attempt capture")
    live_capture = _parse_utc(attempt["live_state"]["captured_at_utc"], "live-state capture")
    if granted < max(attempt_capture, live_capture):
        raise ContractError("permission must be granted after attempt and live-state capture")


def static_manifest_sha256() -> str:
    validate_static_package(DEFAULT_STATIC_PACKAGE)
    return sha256_file(DEFAULT_STATIC_PACKAGE / "manifest.json")


def expected_static_status(v1: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    selected = v1["selected_article"]
    return {
        "schema_version": "r11.gate-a-left-static-status.v2",
        "package_id": contract["package_id"],
        "immutable_v1_verified": True,
        "v1_manifest_sha256": v1["manifest_sha256"],
        "selected_article_id": selected["article_id"],
        "selected_model_3mf_sha256": selected["model_3mf_sha256"],
        "selected_copy_count": 1,
        "static_release_complete": True,
        "exact_reviewed_slice_present": False,
        "fresh_human_permission_present": False,
        "ephemeral_single_use_permit_present": False,
        "print_authorized": False,
        "effective_print_authorized": False,
        "right_half_authorized": False,
        "catalog_authorized": False,
        "fresh_human_permission_required_before_every_print": True,
        "runtime_evidence_must_remain_outside_repository": True,
        "hard_boundary": HARD_BOUNDARY,
        "blockers": [
            "exact current Bambu slice evidence has not been supplied externally",
            "fresh exact-job human permission has not been supplied externally",
            "single-use external permit has not been issued and consumed for one Send attempt",
        ],
    }


def validate_static_package(root: Path = DEFAULT_STATIC_PACKAGE) -> dict[str, Any]:
    package = Path(root)
    contract = strict_json(RELEASE_CONTRACT_PATH)
    expected_paths = sorted(contract["static_package_allowlist"])
    actual_paths = sorted(
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file()
    )
    if actual_paths != expected_paths:
        raise ContractError("static v2 package file allowlist changed")
    if any(path.is_symlink() for path in package.rglob("*")):
        raise ContractError("static v2 package contains a symlink")
    manifest = _require_exact_keys(
        strict_json(package / "manifest.json"),
        (
            "schema_version", "package_id", "exact_file_allowlist", "immutable_v1",
            "selection", "slice_contract", "hard_boundary",
            "static_print_authorized", "static_effective_print_authorized",
            "hashed_artifacts_excluding_manifest", "source_records",
            "source_tree_evidence",
        ),
        "static_manifest",
    )
    if manifest["schema_version"] != "r11.gate-a-left-static-manifest.v2":
        raise ContractError("static v2 manifest schema version changed")
    if manifest["package_id"] != contract["package_id"]:
        raise ContractError("static v2 package identity changed")
    if manifest["exact_file_allowlist"] != expected_paths:
        raise ContractError("static v2 manifest allowlist changed")
    records = artifact_records(package, omit=("manifest.json",))
    if manifest["hashed_artifacts_excluding_manifest"] != records:
        raise ContractError("static v2 artifact hashes changed")
    source_before = v2_source_records()
    if manifest["source_records"] != source_before:
        raise ContractError("static v2 source snapshot changed")
    if manifest["source_tree_evidence"] != source_tree_evidence(source_before):
        raise ContractError("static v2 source-tree identity changed")
    copied_sources = {
        "baseline_lock.json": BASELINE_LOCK_PATH,
        "release_contract.json": RELEASE_CONTRACT_PATH,
        "schemas/attempt_evidence.schema.json": ATTEMPT_SCHEMA_PATH,
        "schemas/fresh_permission.schema.json": PERMISSION_SCHEMA_PATH,
        "schemas/ephemeral_permit.schema.json": PERMIT_SCHEMA_PATH,
        "schemas/send_attempt_consumption.schema.json": CONSUMPTION_SCHEMA_PATH,
    }
    for relative, source in copied_sources.items():
        bundled = package / relative
        if (
            bundled.read_bytes() != source.read_bytes()
            or sha256_file(bundled) != sha256_file(source)
        ):
            raise ContractError(f"static v2 copied source drifted: {relative}")
    v1 = verify_frozen_v1()
    expected_immutable = {
        "package_id": v1["package_id"],
        "manifest_sha256": v1["manifest_sha256"],
        "tree": v1["tree"],
        "source_tree": v1["source_tree"],
        "canonical_config_sha256": v1["canonical_config_sha256"],
        "selected_article": v1["selected_article"],
    }
    if manifest["immutable_v1"] != expected_immutable:
        raise ContractError("static v2 immutable-v1 binding changed")
    if manifest["selection"] != contract["selection"]:
        raise ContractError("static v2 selection contract changed")
    if manifest["slice_contract"] != contract["slice_contract"]:
        raise ContractError("static v2 slice contract changed")
    if (
        manifest["static_print_authorized"] is not False
        or manifest["static_effective_print_authorized"] is not False
    ):
        raise ContractError("static v2 manifest may never self-authorize")
    status = _require_exact_keys(
        strict_json(package / "status.json"),
        tuple(expected_static_status(v1, contract)),
        "static_status",
    )
    if dict(status) != expected_static_status(v1, contract):
        raise ContractError("static v2 status is not the exact hard-false status")
    if status["hard_boundary"] != HARD_BOUNDARY or manifest["hard_boundary"] != HARD_BOUNDARY:
        raise ContractError("static v2 hard boundary changed")
    forbidden_suffixes = (".3mf", ".stl", ".gcode", ".bgcode", ".gco")
    if any(path.name.lower().endswith(forbidden_suffixes) for path in package.rglob("*")):
        raise ContractError("static v2 package contains geometry or toolpath data")
    if v2_source_records() != source_before:
        raise ContractError("v2 source changed during static package validation")
    return dict(manifest)


def review_attempt(attempt_path: Path) -> dict[str, Any]:
    bundle = load_attempt_bundle(attempt_path)
    attempt = bundle.attempt
    verify_frozen_v1()
    manifest_digest = static_manifest_sha256()
    return {
        "schema_version": "r11.gate-a-left-attempt-review.v1",
        "attempt_id": attempt["attempt_id"],
        "reviewed_job_digest": attempt["reviewed_job_digest"],
        "attempt_evidence_sha256": bundle.attempt_snapshot.sha256,
        "external_evidence_file_count": len(bundle.evidence),
        "archive_derived_gcode_sha256": bundle.extracted_gcode_sha256,
        "archive_derived_config_sha256": bundle.extracted_config_sha256,
        "profile_closure_sha256": bundle.profile_closure_sha256,
        "job_identity_sha256": bundle.job_identity_sha256,
        "exact_left_quantity_one_review_passed": True,
        "static_package_manifest_sha256": manifest_digest,
        "fresh_permission_still_required": True,
        "print_authorized": False,
        "effective_print_authorized": False,
        "hard_boundary": HARD_BOUNDARY,
    }


def _atomic_create_at(directory_fd: int, name: str, payload: bytes) -> None:
    if Path(name).name != name or name in (".", ".."):
        raise ContractError("ledger record name is unsafe")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(directory_fd)


def _mkdir_chain_absolute(path: Path) -> int:
    """Explicit initializer helper; safely create missing components at 0700."""

    absolute = _absolute_unresolved(path)
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in absolute.parts[1:]:
            try:
                next_fd = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                os.mkdir(component, 0o700, dir_fd=descriptor)
                os.fsync(descriptor)
                next_fd = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            os.close(descriptor)
            descriptor = next_fd
        return descriptor
    except (OSError, ValueError) as error:
        os.close(descriptor)
        raise ContractError(f"ledger initialization path is unsafe: {path}") from error


class LedgerStore:
    """Locked, identity-bound external ledger accessed only through directory FDs."""

    def __init__(self, root: Path, *, uid: int, host_identity_sha256: str) -> None:
        self.root = _absolute_unresolved(root)
        self.uid = uid
        self.host_identity_sha256 = _require_string(
            host_identity_sha256, "ledger.host_identity_sha256", pattern=SHA256_RE
        )

    @classmethod
    def canonical(cls) -> "LedgerStore":
        return cls(
            canonical_ledger_root(), uid=os.getuid(),
            host_identity_sha256=_host_identity_sha256(),
        )

    @classmethod
    def _test_store(cls, root: Path) -> "LedgerStore":
        """Unit-test seam; production CLI never accepts or exposes a root."""

        return cls(root, uid=os.getuid(), host_identity_sha256="f" * 64)

    def _expected_identity(self, instance_id: str, created_at_utc: str) -> dict[str, Any]:
        return {
            "schema_version": LEDGER_IDENTITY_SCHEMA_VERSION,
            "package_id": strict_json(RELEASE_CONTRACT_PATH)["package_id"],
            "uid": self.uid,
            "host_identity_sha256": self.host_identity_sha256,
            "ledger_instance_id": instance_id,
            "created_at_utc": created_at_utc,
        }

    def initialize(self, *, now: datetime | None = None) -> None:
        """Manually initialize once; ordinary issue/evaluate never create/reset it."""

        root_fd = _mkdir_chain_absolute(self.root)
        try:
            metadata = os.fstat(root_fd)
            if metadata.st_uid != self.uid:
                raise ContractError("ledger directory owner differs from the real uid")
            os.fchmod(root_fd, 0o700)
            identity = self._expected_identity(
                secrets.token_hex(32),
                utc_text((now or datetime.now(timezone.utc)).astimezone(timezone.utc)),
            )
            _atomic_create_at(root_fd, "ledger-identity.json", json_bytes(identity))
            _atomic_create_at(root_fd, ".ledger.lock", b"r11-gate-a-left-ledger-lock-v1\n")
            try:
                os.mkdir("blobs", 0o700, dir_fd=root_fd)
                os.fsync(root_fd)
            except FileExistsError as error:
                raise ContractError("ledger blob directory already exists") from error
        finally:
            os.close(root_fd)

    def _open_root(self) -> int:
        try:
            root_fd = _open_directory_fd(self.root)
        except ContractError as error:
            raise ContractError(
                "canonical ledger is missing; explicit one-time initialization is required"
            ) from error
        metadata = os.fstat(root_fd)
        if (
            metadata.st_uid != self.uid
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or not stat.S_ISDIR(metadata.st_mode)
        ):
            os.close(root_fd)
            raise ContractError("canonical ledger owner/mode/type is not exact uid/0700/directory")
        try:
            identity_snapshot = _snapshot_relative(
                root_fd, Path("ledger-identity.json"), self.root
            )
            if identity_snapshot.link_count != 1:
                raise ContractError("ledger identity record has multiple hard links")
            identity = _strict_json_payload(
                identity_snapshot.payload, str(identity_snapshot.path)
            )
            exact = _require_exact_keys(
                identity,
                (
                    "schema_version", "package_id", "uid", "host_identity_sha256",
                    "ledger_instance_id", "created_at_utc",
                ),
                "ledger_identity",
            )
            _require_string(
                exact["ledger_instance_id"], "ledger_identity.ledger_instance_id",
                pattern=re.compile(r"^[0-9a-f]{64}$"),
            )
            _parse_utc(exact["created_at_utc"], "ledger_identity.created_at_utc")
            expected = self._expected_identity(
                exact["ledger_instance_id"], exact["created_at_utc"]
            )
            if dict(exact) != expected:
                raise ContractError("canonical ledger identity does not match this uid/host/project")
            blob_fd = os.open(
                "blobs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
            try:
                blob_meta = os.fstat(blob_fd)
                if blob_meta.st_uid != self.uid or stat.S_IMODE(blob_meta.st_mode) != 0o700:
                    raise ContractError("ledger blob directory owner/mode is invalid")
            finally:
                os.close(blob_fd)
            return root_fd
        except Exception:
            os.close(root_fd)
            raise

    @contextmanager
    def locked(self) -> Iterable[int]:
        root_fd = self._open_root()
        try:
            lock_fd = os.open(
                ".ledger.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
            lock_meta = os.fstat(lock_fd)
            if (
                not stat.S_ISREG(lock_meta.st_mode)
                or lock_meta.st_uid != self.uid
                or stat.S_IMODE(lock_meta.st_mode) != 0o600
                or lock_meta.st_nlink != 1
            ):
                os.close(lock_fd)
                raise ContractError("ledger lock owner/mode/type is invalid")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                yield root_fd
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
        finally:
            os.close(root_fd)

    def create_record(self, root_fd: int, name: str, value: Mapping[str, Any]) -> FileSnapshot:
        _atomic_create_at(root_fd, name, json_bytes(value))
        return _snapshot_relative(root_fd, Path(name), self.root)

    def read_record(self, root_fd: int, name: str) -> tuple[dict[str, Any], FileSnapshot]:
        snapshot = _snapshot_relative(root_fd, Path(name), self.root)
        if snapshot.link_count != 1:
            raise ContractError(f"ledger record has multiple hard links: {name}")
        value = _strict_json_payload(snapshot.payload, str(snapshot.path))
        if type(value) is not dict:
            raise ContractError(f"ledger record must be an object: {name}")
        return value, snapshot

    def store_blob(self, root_fd: int, digest: str, payload: bytes) -> FileSnapshot:
        _require_string(digest, "blob digest", pattern=SHA256_RE)
        blob_fd = os.open(
            "blobs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=root_fd,
        )
        try:
            name = f"{digest}.gcode"
            try:
                _atomic_create_at(blob_fd, name, payload)
                os.chmod(name, 0o400, dir_fd=blob_fd, follow_symlinks=False)
                os.fsync(blob_fd)
            except FileExistsError:
                pass
            snapshot = _snapshot_relative(blob_fd, Path(name), self.root / "blobs")
            blob_stat = os.stat(name, dir_fd=blob_fd, follow_symlinks=False)
            if (
                snapshot.sha256 != digest
                or snapshot.payload != payload
                or snapshot.link_count != 1
                or blob_stat.st_uid != self.uid
                or stat.S_IMODE(blob_stat.st_mode) != 0o400
            ):
                raise ContractError("content-addressed G-code blob differs from reviewed payload")
            return snapshot
        finally:
            os.close(blob_fd)

    def open_blob(self, root_fd: int, digest: str) -> tuple[int, FileSnapshot]:
        blob_dir_fd = os.open(
            "blobs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=root_fd,
        )
        try:
            name = f"{digest}.gcode"
            descriptor = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=blob_dir_fd,
            )
            snapshot = _snapshot_from_fd(descriptor, self.root / "blobs" / name)
            metadata = os.fstat(descriptor)
            if (
                snapshot.sha256 != digest
                or snapshot.link_count != 1
                or metadata.st_uid != self.uid
                or stat.S_IMODE(metadata.st_mode) != 0o400
            ):
                os.close(descriptor)
                raise ContractError("content-addressed G-code blob hash changed")
            os.lseek(descriptor, 0, os.SEEK_SET)
            return descriptor, snapshot
        finally:
            os.close(blob_dir_fd)


def initialize_canonical_ledger(*, now: datetime | None = None) -> Path:
    store = LedgerStore.canonical()
    store.initialize(now=now)
    return store.root


def issue_permit(
    attempt_path: Path,
    permission_path: Path,
    *,
    now: datetime | None = None,
) -> Path:
    """Issue once in the fixed identity-bound ledger; no implicit initialization."""

    bundle = load_attempt_bundle(attempt_path)
    attempt = bundle.attempt
    permission_source = _external_runtime_path(permission_path)
    permission_value, permission_snapshot = snapshot_json(permission_source)
    if permission_snapshot.link_count != 1:
        raise ContractError("external permission JSON must have exactly one hard link")
    permission = validate_permission(permission_value)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    _assert_fresh(attempt, permission, current)
    attempt_digest = bundle.attempt_snapshot.sha256
    if permission["attempt_id"] != attempt["attempt_id"]:
        raise ContractError("permission is for a different attempt")
    if permission["attempt_evidence_sha256"] != attempt_digest:
        raise ContractError("permission is not bound to these exact attempt bytes")
    if permission["reviewed_job_digest"] != attempt["reviewed_job_digest"]:
        raise ContractError("permission is for a different reviewed job")
    verify_frozen_v1()
    verify_installed_bambu_executable()
    verify_installed_native_profile_sources()
    if now is None:
        current = datetime.now(timezone.utc)
        _assert_fresh(attempt, permission, current)
    static_digest = static_manifest_sha256()
    permission_digest = permission_snapshot.sha256
    store = LedgerStore.canonical()
    common = {
        "attempt_id": attempt["attempt_id"],
        "attempt_evidence_sha256": attempt_digest,
        "permission_id": permission["permission_id"],
        "permission_evidence_sha256": permission_digest,
        "reviewed_job_digest": attempt["reviewed_job_digest"],
        "sliced_plate_file_sha256": attempt["slicer"]["sliced_plate_file_sha256"],
        "gcode_payload_sha256": bundle.extracted_gcode_sha256,
        "gcode_config_block_sha256": bundle.extracted_config_sha256,
        "profile_closure_sha256": bundle.profile_closure_sha256,
        "job_identity_sha256": bundle.job_identity_sha256,
        "spent_at_utc": utc_text(current),
    }
    marker_specs = (
        (f"gcode-payload-{bundle.extracted_gcode_sha256}.spent.json", "gcode_payload_sha256"),
        (f"job-identity-{bundle.job_identity_sha256}.spent.json", "job_identity_sha256"),
        (
            f"sliced-job-{attempt['slicer']['sliced_plate_file_sha256']}.spent.json",
            "sliced_plate_file_sha256",
        ),
        (f"reviewed-job-{attempt['reviewed_job_digest']}.spent.json", "reviewed_job_digest"),
        (f"attempt-evidence-{attempt_digest}.spent.json", "attempt_evidence_sha256"),
        (f"attempt-id-{attempt['attempt_id']}.spent.json", "attempt_id"),
        (f"permission-id-{permission['permission_id']}.spent.json", "permission_id"),
    )
    marker_hashes: dict[str, str] = {}
    with store.locked() as root_fd:
        # Claim the actual G-code identity first. Any crash after the first
        # durable ledger write permanently spends this toolpath, even if no
        # permit record is reached.
        for filename, identity_key in marker_specs:
            marker = store.create_record(
                root_fd,
                filename,
                {**common, "unique_identity_kind": identity_key},
            )
            marker_hashes[identity_key] = marker.sha256
        blob = store.store_blob(root_fd, bundle.extracted_gcode_sha256, bundle.extracted_gcode)
        nonce = secrets.token_hex(16)
        permit_id = "r11-permit-" + hashlib.sha256(
            (attempt_digest + permission_digest + nonce).encode("ascii")
        ).hexdigest()[:32]
        identity_snapshot = _snapshot_relative(
            root_fd, Path("ledger-identity.json"), store.root
        )
        permit = {
            "schema_version": PERMIT_SCHEMA_VERSION,
            "permit_id": permit_id,
            "attempt_id": attempt["attempt_id"],
            "permission_id": permission["permission_id"],
            "attempt_evidence_sha256": attempt_digest,
            "permission_evidence_sha256": permission_digest,
            "unique_marker_sha256": marker_hashes,
            "reviewed_job_digest": attempt["reviewed_job_digest"],
            "sliced_plate_file_sha256": attempt["slicer"]["sliced_plate_file_sha256"],
            "gcode_payload_sha256": bundle.extracted_gcode_sha256,
            "gcode_payload_bytes": blob.bytes,
            "gcode_config_block_sha256": bundle.extracted_config_sha256,
            "profile_closure_sha256": bundle.profile_closure_sha256,
            "job_identity_sha256": bundle.job_identity_sha256,
            "ledger_identity_sha256": identity_snapshot.sha256,
            "static_package_manifest_sha256": static_digest,
            "issued_at_utc": utc_text(current),
            "expires_at_utc": permission["expires_at_utc"],
            "ledger_nonce": nonce,
            "permit_state_at_issue": "issued_unconsumed",
            "effective_print_authorized_at_issue": True,
            "hard_boundary": HARD_BOUNDARY,
        }
        permit_snapshot = store.create_record(root_fd, f"{permit_id}.permit.json", permit)
        store.create_record(
            root_fd,
            f"{permit_id}.issued.json",
            {
                "permit_id": permit_id,
                "permit_sha256": permit_snapshot.sha256,
                "unique_marker_sha256": marker_hashes,
                "job_identity_sha256": bundle.job_identity_sha256,
                "issued_at_utc": utc_text(current),
            },
        )
    return store.root / f"{permit_id}.permit.json"


def _validate_permit_shape(value: Any) -> dict[str, Any]:
    permit = _require_exact_keys(
        value,
        (
            "schema_version", "permit_id", "attempt_id", "permission_id",
            "attempt_evidence_sha256", "permission_evidence_sha256",
            "unique_marker_sha256", "reviewed_job_digest",
            "sliced_plate_file_sha256", "gcode_payload_sha256", "gcode_payload_bytes",
            "gcode_config_block_sha256", "profile_closure_sha256",
            "job_identity_sha256", "ledger_identity_sha256",
            "static_package_manifest_sha256", "issued_at_utc",
            "expires_at_utc", "ledger_nonce", "permit_state_at_issue",
            "effective_print_authorized_at_issue", "hard_boundary",
        ),
        "permit",
    )
    if permit["schema_version"] != PERMIT_SCHEMA_VERSION:
        raise ContractError("permit.schema_version is unsupported")
    _require_string(permit["permit_id"], "permit.permit_id")
    _require_string(permit["attempt_id"], "permit.attempt_id", pattern=ATTEMPT_ID_RE)
    _require_string(permit["permission_id"], "permit.permission_id", pattern=PERMISSION_ID_RE)
    for key in (
        "attempt_evidence_sha256", "permission_evidence_sha256",
        "reviewed_job_digest", "sliced_plate_file_sha256", "gcode_payload_sha256",
        "gcode_config_block_sha256", "profile_closure_sha256",
        "job_identity_sha256", "ledger_identity_sha256",
        "static_package_manifest_sha256",
    ):
        _require_string(permit[key], f"permit.{key}", pattern=SHA256_RE)
    _require_positive_integer(permit["gcode_payload_bytes"], "permit.gcode_payload_bytes")
    marker_keys = (
        "attempt_id", "attempt_evidence_sha256", "sliced_plate_file_sha256",
        "reviewed_job_digest", "gcode_payload_sha256", "job_identity_sha256",
        "permission_id",
    )
    markers = _require_exact_keys(
        permit["unique_marker_sha256"], marker_keys, "permit.unique_marker_sha256"
    )
    for key in marker_keys:
        _require_string(markers[key], f"permit.unique_marker_sha256.{key}", pattern=SHA256_RE)
    _parse_utc(permit["issued_at_utc"], "permit.issued_at_utc")
    _parse_utc(permit["expires_at_utc"], "permit.expires_at_utc")
    if not re.fullmatch(r"[0-9a-f]{32}", str(permit["ledger_nonce"])):
        raise ContractError("permit.ledger_nonce has an invalid format")
    if permit["permit_state_at_issue"] != "issued_unconsumed":
        raise ContractError("permit initial state changed")
    _require_bool(
        permit["effective_print_authorized_at_issue"], True,
        "permit.effective_print_authorized_at_issue",
    )
    if permit["hard_boundary"] != HARD_BOUNDARY:
        raise ContractError("permit hard boundary changed")
    return dict(permit)


def _marker_filenames(permit: Mapping[str, Any]) -> dict[str, str]:
    return {
        "attempt_id": f"attempt-id-{permit['attempt_id']}.spent.json",
        "attempt_evidence_sha256": (
            f"attempt-evidence-{permit['attempt_evidence_sha256']}.spent.json"
        ),
        "sliced_plate_file_sha256": (
            f"sliced-job-{permit['sliced_plate_file_sha256']}.spent.json"
        ),
        "reviewed_job_digest": f"reviewed-job-{permit['reviewed_job_digest']}.spent.json",
        "gcode_payload_sha256": f"gcode-payload-{permit['gcode_payload_sha256']}.spent.json",
        "job_identity_sha256": f"job-identity-{permit['job_identity_sha256']}.spent.json",
        "permission_id": f"permission-id-{permit['permission_id']}.spent.json",
    }


def _evaluate_locked(
    store: LedgerStore, root_fd: int, permit_id: str,
    bundle: AttemptBundle, current: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    permit_value, permit_snapshot = store.read_record(root_fd, f"{permit_id}.permit.json")
    permit = _validate_permit_shape(permit_value)
    if permit["permit_id"] != permit_id:
        raise ContractError("permit filename is not bound to permit_id")
    issued, _ = store.read_record(root_fd, f"{permit_id}.issued.json")
    if issued != {
        "permit_id": permit_id,
        "permit_sha256": permit_snapshot.sha256,
        "unique_marker_sha256": permit["unique_marker_sha256"],
        "job_identity_sha256": permit["job_identity_sha256"],
        "issued_at_utc": permit["issued_at_utc"],
    }:
        raise ContractError("permit issuance ledger does not bind exact permit bytes")
    for kind, filename in _marker_filenames(permit).items():
        marker, marker_snapshot = store.read_record(root_fd, filename)
        if marker_snapshot.sha256 != permit["unique_marker_sha256"][kind]:
            raise ContractError(f"unique ledger marker changed: {kind}")
        exact_marker = _require_exact_keys(
            marker,
            (
                "attempt_id", "attempt_evidence_sha256", "permission_id",
                "permission_evidence_sha256", "reviewed_job_digest",
                "sliced_plate_file_sha256", "gcode_payload_sha256",
                "gcode_config_block_sha256", "profile_closure_sha256",
                "job_identity_sha256", "spent_at_utc", "unique_identity_kind",
            ),
            f"unique_marker.{kind}",
        )
        expected_marker = {
            "attempt_id": permit["attempt_id"],
            "attempt_evidence_sha256": permit["attempt_evidence_sha256"],
            "permission_id": permit["permission_id"],
            "permission_evidence_sha256": permit["permission_evidence_sha256"],
            "reviewed_job_digest": permit["reviewed_job_digest"],
            "sliced_plate_file_sha256": permit["sliced_plate_file_sha256"],
            "gcode_payload_sha256": permit["gcode_payload_sha256"],
            "gcode_config_block_sha256": permit["gcode_config_block_sha256"],
            "profile_closure_sha256": permit["profile_closure_sha256"],
            "job_identity_sha256": permit["job_identity_sha256"],
            "spent_at_utc": permit["issued_at_utc"],
            "unique_identity_kind": kind,
        }
        if dict(exact_marker) != expected_marker:
            raise ContractError(f"unique ledger marker content changed: {kind}")
    identity = _snapshot_relative(root_fd, Path("ledger-identity.json"), store.root)
    if identity.sha256 != permit["ledger_identity_sha256"]:
        raise ContractError("permit ledger identity changed")
    attempt = bundle.attempt
    exact_bindings = {
        "attempt_id": attempt["attempt_id"],
        "attempt_evidence_sha256": bundle.attempt_snapshot.sha256,
        "reviewed_job_digest": attempt["reviewed_job_digest"],
        "sliced_plate_file_sha256": attempt["slicer"]["sliced_plate_file_sha256"],
        "gcode_payload_sha256": bundle.extracted_gcode_sha256,
        "gcode_config_block_sha256": bundle.extracted_config_sha256,
        "profile_closure_sha256": bundle.profile_closure_sha256,
        "job_identity_sha256": bundle.job_identity_sha256,
    }
    for key, expected in exact_bindings.items():
        if permit[key] != expected:
            raise ContractError(f"permit exact-job binding mismatch: {key}")
    if permit["gcode_payload_bytes"] != len(bundle.extracted_gcode):
        raise ContractError("permit G-code byte count mismatch")
    if permit["static_package_manifest_sha256"] != static_manifest_sha256():
        raise ContractError("permit static release binding changed")
    blob_fd, blob = store.open_blob(root_fd, permit["gcode_payload_sha256"])
    os.close(blob_fd)
    if blob.bytes != permit["gcode_payload_bytes"] or blob.payload != bundle.extracted_gcode:
        raise ContractError("permit content-addressed blob differs from exact archive-derived G-code")
    not_expired = current < _parse_utc(permit["expires_at_utc"], "permit expiry")
    not_future = current >= _parse_utc(permit["issued_at_utc"], "permit issue")
    consumed_name = f"{permit_id}.consumed.json"
    try:
        _snapshot_relative(root_fd, Path(consumed_name), store.root)
        consumed = True
    except ContractError as error:
        try:
            os.stat(consumed_name, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            consumed = False
        else:
            raise ContractError("consumption marker exists but is unsafe or unreadable") from error
    effective = bool(not_expired and not_future and not consumed)
    evaluation = {
        "schema_version": "r11.gate-a-left-permit-evaluation.v1",
        "permit_id": permit_id,
        "attempt_id": permit["attempt_id"],
        "reviewed_job_digest": permit["reviewed_job_digest"],
        "job_identity_sha256": permit["job_identity_sha256"],
        "permit_consumed": consumed,
        "permit_expired": not not_expired,
        "effective_print_authorized": effective,
        "hard_boundary": HARD_BOUNDARY,
    }
    return permit, evaluation


def evaluate_permit(
    permit_path: Path,
    attempt_path: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Informational evaluation; only consume_and_open_send_payload is authoritative."""

    store = LedgerStore.canonical()
    permit_source = _absolute_unresolved(permit_path)
    if permit_source.parent != store.root or not permit_source.name.endswith(".permit.json"):
        raise ContractError("permit is not in the fixed canonical project ledger")
    permit_id = permit_source.name.removesuffix(".permit.json")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    with store.locked() as root_fd:
        bundle = load_attempt_bundle(attempt_path)
        _, evaluation = _evaluate_locked(store, root_fd, permit_id, bundle, current)
        return evaluation


def consume_and_open_send_payload(
    permit_path: Path,
    attempt_path: Path,
    *,
    now: datetime | None = None,
) -> SendPayloadTicket:
    """Consume under lock and return the SAME verified open G-code blob FD."""

    store = LedgerStore.canonical()
    permit_source = _absolute_unresolved(permit_path)
    if permit_source.parent != store.root or not permit_source.name.endswith(".permit.json"):
        raise ContractError("permit is not in the fixed canonical project ledger")
    permit_id = permit_source.name.removesuffix(".permit.json")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    with store.locked() as root_fd:
        first = load_attempt_bundle(attempt_path)
        permit, evaluation = _evaluate_locked(store, root_fd, permit_id, first, current)
        if evaluation["effective_print_authorized"] is not True:
            raise ContractError("permit is not currently effective and cannot be consumed")
        # A second complete no-follow snapshot is deliberately inside the same
        # ledger critical section, immediately before O_EXCL consumption.
        final = load_attempt_bundle(attempt_path)
        if (
            final.attempt_snapshot.sha256 != first.attempt_snapshot.sha256
            or final.job_identity_sha256 != first.job_identity_sha256
            or any(
                final.evidence[key].sha256 != first.evidence[key].sha256
                for key in EVIDENCE_FILE_KEYS
            )
        ):
            raise ContractError("attempt/evidence changed before atomic consumption")
        if now is None:
            current = datetime.now(timezone.utc)
            if current >= _parse_utc(permit["expires_at_utc"], "permit expiry"):
                raise ContractError("permit expired before atomic consumption")
        payload_fd, blob = store.open_blob(root_fd, permit["gcode_payload_sha256"])
        try:
            record = {
                "schema_version": CONSUMPTION_SCHEMA_VERSION,
                "permit_id": permit_id,
                "attempt_id": evaluation["attempt_id"],
                "reviewed_job_digest": evaluation["reviewed_job_digest"],
                "job_identity_sha256": permit["job_identity_sha256"],
                "gcode_payload_sha256": blob.sha256,
                "gcode_payload_bytes": blob.bytes,
                "consumed_at_utc": utc_text(current),
                "reason": "atomic_consume_and_open_exact_content_addressed_send_payload",
                "permit_consumed": True,
                "effective_print_authorized": False,
                "send_attempt_may_be_made_once_after_this_atomic_record": True,
                "failed_cancelled_rejected_or_ambiguous_still_consumed": True,
                "hard_boundary": HARD_BOUNDARY,
            }
            consumed = store.create_record(root_fd, f"{permit_id}.consumed.json", record)
            # Post-consumption recheck: drift blocks sending but can never unspend.
            after = load_attempt_bundle(attempt_path)
            if (
                after.attempt_snapshot.sha256 != final.attempt_snapshot.sha256
                or after.job_identity_sha256 != final.job_identity_sha256
            ):
                raise ContractError("attempt/evidence changed during atomic consumption")
            return SendPayloadTicket(
                permit_id=permit_id,
                consumption_path=store.root / f"{permit_id}.consumed.json",
                payload_path=store.root / "blobs" / f"{blob.sha256}.gcode",
                payload_fd=payload_fd,
                payload_sha256=blob.sha256,
                payload_bytes=blob.bytes,
            )
        except Exception:
            os.close(payload_fd)
            raise


def consume_before_send_attempt(*_: Any, **__: Any) -> None:
    """Fail closed: path-only consume cannot preserve the verified send payload FD."""

    raise ContractError(
        "path-only consume is disabled; use consume_and_open_send_payload in the same sender process"
    )
