#!/usr/bin/env python3
"""Deterministic, mesh-independent plans for the Story Corner r6 packages.

The release inventory answers *what is printed*.  This module turns that
inventory into exact named 3MF build-object plans without importing the r6
generator or depending on generated files.  A generator-side resolver maps the
stable semantic family keys to meshes only after a plan has been accepted.

The virtual-canvas helpers at the end of the module are deliberately separate
from the planners.  Their output is a neutral viewing layout, never a printer
plate, slicer profile, or source of G-code.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, Literal, Mapping

import numpy as np
import trimesh

from release_inventory import (
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS,
    PROVISIONAL_STATUS,
    ReleaseRecord,
)


SAFETY_DESCRIPTION = "MODEL-ONLY; EXPERIMENTAL; UNRATED; NO G-CODE"

PRINT_FIRST_PACKAGE_ID = "print_first_prototypes"
UNIQUE_PARTS_PACKAGE_ID = "unique_parts_catalog"
QUALIFICATION_PACKAGE_ID = "worst_case_one_bay_qualification"
ONE_LEVEL_PACKAGE_ID = "one_level_l"
TWO_LEVEL_PACKAGE_ID = "two_level_full_project"

PACKAGE_ORDER: tuple[str, ...] = (
    PRINT_FIRST_PACKAGE_ID,
    UNIQUE_PARTS_PACKAGE_ID,
    QUALIFICATION_PACKAGE_ID,
    ONE_LEVEL_PACKAGE_ID,
    TWO_LEVEL_PACKAGE_ID,
)

PACKAGE_FILENAMES: dict[str, str] = {
    PRINT_FIRST_PACKAGE_ID: "MODEL_ONLY_R6_PRINT_FIRST_PROTOTYPES.3mf",
    UNIQUE_PARTS_PACKAGE_ID: "MODEL_ONLY_R6_UNIQUE_PARTS_CATALOG.3mf",
    QUALIFICATION_PACKAGE_ID: "MODEL_ONLY_R6_WORST_CASE_ONE_BAY_QUALIFICATION.3mf",
    ONE_LEVEL_PACKAGE_ID: "MODEL_ONLY_R6_ONE_LEVEL_L.3mf",
    TWO_LEVEL_PACKAGE_ID: "MODEL_ONLY_R6_TWO_LEVEL_FULL_PROJECT.3mf",
}

PackageId = Literal[
    "print_first_prototypes",
    "unique_parts_catalog",
    "worst_case_one_bay_qualification",
    "one_level_l",
    "two_level_full_project",
]

PRINT_FIRST_REQUIRED_ROLES: frozenset[str] = frozenset(
    {
        "fit_clearance",
        "pin_fit",
        "positive_cross_key_fit",
        "screw_head_bearing",
        "wall_screw_no_bore_blocker",
        "coffer_bridge_fit",
        "structural_cassette",
    }
)

EXPECTED_EMITTED_SOURCE_PART_COUNT = 49
CATALOG_SOURCE_CLASSIFICATIONS: frozenset[str] = frozenset(
    {
        "installed_current",
        "development_fit_coupon",
        "development_inspection_coupon",
        "blocked_no_bore_fastener_coupon",
    }
)

ONE_LEVEL_PHYSICAL_OBJECT_COUNT = sum(EXPECTED_ONE_LEVEL_FAMILY_COUNTS.values())
SELECTED_LEVEL_IDS: tuple[str, str] = ("lower", "upper")
SELECTED_LEVEL_COUNT = len(SELECTED_LEVEL_IDS)


def _exact_division(numerator: int, denominator: int, label: str) -> int:
    if denominator <= 0:
        raise ValueError(f"{label} denominator must be positive")
    quotient, remainder = divmod(numerator, denominator)
    if remainder:
        raise ValueError(f"{label} must be a whole-number per-half inventory ratio")
    return quotient


_TOP_WEDGES_PER_HALF = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["cassette_top_retention_wedge"],
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["arcade_half"],
    "cassette top quarter-turn cross-keys",
)
_LOCKS_PER_SUPPORT = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["cassette_lock"],
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["structural_pier_x_corbel"],
    "cassette locks",
)
_SPRING_WEDGES_PER_HALF = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["spring_retention_wedge"],
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["arcade_half"],
    "spring quarter-turn cross-keys",
)
_INTERNAL_CASSETTE_SEAMS = (
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["deck_cassette"]
    - EXPECTED_ONE_LEVEL_FAMILY_COUNTS["ordinary_outer_end_cap"]
)
_DIAPHRAGM_KEYS_PER_SEAM = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["diaphragm_bowtie_key"],
    _INTERNAL_CASSETTE_SEAMS,
    "diaphragm keys",
)
_KEEPERS_PER_CROWN = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["fixed_crown_diaphragm_keeper_strip"],
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["crown_bridge"],
    "fixed-crown keeper strips",
)
_TIE_KEYS_PER_CROWN = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["fixed_crown_entablature_tie_key"],
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["crown_bridge"],
    "fixed-crown tie keys",
)
_PINS_PER_CROWN_BRIDGE = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["crown_bridge_retention_pin"],
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["crown_bridge"],
    "crown-bridge retention pins",
)
_SHARED_KEEPER_AND_TIE_PINS_PER_CROWN = _exact_division(
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["indexed_vertical_quarter_turn_pin"],
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS["crown_bridge"],
    "shared keeper/front-tie quarter-turn pins",
)

# The exact structural/retention contents of the maximum-span long-wall bay.
# Counts are derived from the authoritative one-level taxonomy so an approved
# retention-topology change cannot leave the package layer on a stale total.
# Removable ornament is intentionally absent because it receives no structural
# credit and is irrelevant to the qualification comparison.
QUALIFICATION_FAMILY_COUNTS: dict[str, int] = {
    "arcade_half": 2,
    "cassette_lock": 2 * _LOCKS_PER_SUPPORT,
    "cassette_top_retention_wedge": 2 * _TOP_WEDGES_PER_HALF,
    "crown_bridge": 1,
    "crown_bridge_retention_pin": _PINS_PER_CROWN_BRIDGE,
    "deck_cassette": 2,
    "diaphragm_bowtie_key": _DIAPHRAGM_KEYS_PER_SEAM,
    "fixed_crown_diaphragm_keeper_strip": _KEEPERS_PER_CROWN,
    "fixed_crown_entablature_tie_key": _TIE_KEYS_PER_CROWN,
    "indexed_vertical_quarter_turn_pin": _SHARED_KEEPER_AND_TIE_PINS_PER_CROWN,
    "spring_retention_wedge": 2 * _SPRING_WEDGES_PER_HALF,
    "structural_pier_x_corbel": 2,
}

EXPECTED_EXACT_PACKAGE_COUNTS: dict[str, int] = {
    PRINT_FIRST_PACKAGE_ID: 8,
    UNIQUE_PARTS_PACKAGE_ID: EXPECTED_EMITTED_SOURCE_PART_COUNT,
    QUALIFICATION_PACKAGE_ID: sum(QUALIFICATION_FAMILY_COUNTS.values()),
    ONE_LEVEL_PACKAGE_ID: ONE_LEVEL_PHYSICAL_OBJECT_COUNT,
    TWO_LEVEL_PACKAGE_ID: SELECTED_LEVEL_COUNT * ONE_LEVEL_PHYSICAL_OBJECT_COUNT,
}

ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS: frozenset[str] = frozenset(
    {
        QUALIFICATION_PACKAGE_ID,
        ONE_LEVEL_PACKAGE_ID,
        TWO_LEVEL_PACKAGE_ID,
    }
)

_FORBIDDEN_NAME_FRAGMENTS: tuple[str, ...] = (
    "stitch_rail",
    "run_end_tie",
    "sliding_saddle",
    "saddle_pin",
    "wall_bore",
    "wall_fastener_bore",
    "production_fastener_bore",
    "printed_wall_anchor",
    "cross_level",
    "vertical_tie",
)


def _normalized_tokens(value: str) -> tuple[str, ...]:
    return tuple(token for token in re.split(r"[^a-z0-9]+", value.lower()) if token)


def forbidden_package_term(value: str) -> str | None:
    """Return the forbidden rail/saddle/bore/tie term present in ``value``."""

    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    for fragment in _FORBIDDEN_NAME_FRAGMENTS:
        if fragment in normalized:
            return fragment
    tokens = set(_normalized_tokens(value))
    if "rail" in tokens or "rails" in tokens:
        return "rail"
    if "saddle" in tokens or "saddles" in tokens:
        return "saddle"
    return None


@dataclass(frozen=True)
class PackageInstance:
    """One named physical object and its generator-resolved mesh family."""

    logical_name: str
    mesh_family: str
    level: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrototypeSpec:
    """One print-first object with the safety/fit roles it covers."""

    logical_name: str
    mesh_family: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class PackageMeshSourceAudit:
    """Generator evidence for one resolved software-model package source.

    The package layer does not infer feature semantics from a triangle soup.
    Instead, the generator supplies this compact result from its geometry and
    interface validators.  Old coupons and incomplete interface meshes are
    valid print-first sources but can never satisfy this assembly-model gate.
    Passing this gate is software/package conformance only. It never qualifies
    a physical installation or production release.
    """

    mesh_family: str
    source_part_name: str
    geometry_validation_passed: bool
    current_interface_geometry: bool
    software_model_package_eligible: bool
    physical_installation_qualified: bool
    production_release_eligible: bool
    placeholder_or_coupon: bool
    wall_bore_count: int
    rail_or_saddle_geometry: bool
    unresolved_interfaces: tuple[str, ...] = ()
    catalog_classification: str = "installed_current"
    catalog_inclusion_eligible: bool = True

    def __post_init__(self) -> None:
        if (
            not isinstance(self.mesh_family, str)
            or not self.mesh_family.strip()
            or not isinstance(self.source_part_name, str)
            or not self.source_part_name.strip()
        ):
            raise ValueError("Mesh-source audit names must be nonempty")
        flags = (
            self.geometry_validation_passed,
            self.current_interface_geometry,
            self.software_model_package_eligible,
            self.physical_installation_qualified,
            self.production_release_eligible,
            self.placeholder_or_coupon,
            self.rail_or_saddle_geometry,
            self.catalog_inclusion_eligible,
        )
        if not all(isinstance(value, bool) for value in flags):
            raise ValueError("Mesh-source audit flags must be booleans")
        if (
            isinstance(self.wall_bore_count, bool)
            or not isinstance(self.wall_bore_count, int)
            or self.wall_bore_count < 0
        ):
            raise ValueError(
                "Mesh-source wall-bore count must be a nonnegative integer"
            )
        if len(self.unresolved_interfaces) != len(set(self.unresolved_interfaces)):
            raise ValueError("Unresolved interface ids must be unique")
        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.unresolved_interfaces
        ):
            raise ValueError("Unresolved interface ids must be nonempty")
        if self.catalog_classification not in CATALOG_SOURCE_CLASSIFICATIONS:
            raise ValueError(
                "Mesh-source catalog classification is not an approved exact class"
            )
        if self.placeholder_or_coupon != (
            self.catalog_classification != "installed_current"
        ):
            raise ValueError(
                "Mesh-source placeholder/coupon flag disagrees with catalog classification"
            )


@dataclass(frozen=True)
class PackagePlan:
    """Exact ordered physical-object contract for one model-only 3MF."""

    package_id: PackageId
    title: str
    purpose: str
    instances: tuple[PackageInstance, ...]
    level_ids: tuple[str, ...] = ()
    description: str = SAFETY_DESCRIPTION

    def __post_init__(self) -> None:
        if self.package_id not in PACKAGE_ORDER:
            raise ValueError(f"Unknown r6 package id {self.package_id!r}")
        if not self.title.strip() or not self.purpose.strip():
            raise ValueError("Package title and purpose must be nonempty")
        if self.description != SAFETY_DESCRIPTION:
            raise ValueError("Package safety Description must use the exact r6 contract")
        if not self.instances:
            raise ValueError("A package plan needs at least one physical object")
        names = [item.logical_name for item in self.instances]
        if any(not value.strip() for value in names) or len(names) != len(set(names)):
            raise ValueError("Package logical names must be nonempty and unique")
        families = [item.mesh_family for item in self.instances]
        if any(not value.strip() for value in families):
            raise ValueError("Package mesh-family keys must be nonempty")
        for value in (*names, *families):
            forbidden = forbidden_package_term(value)
            if forbidden:
                raise ValueError(
                    f"Package plans may not contain {forbidden!r}: {value!r}"
                )
        actual_levels = tuple(sorted({item.level for item in self.instances if item.level}))
        if actual_levels != self.level_ids:
            raise ValueError(
                f"Package level ids {self.level_ids!r} do not match instances {actual_levels!r}"
            )
        expected_count = EXPECTED_EXACT_PACKAGE_COUNTS.get(self.package_id)
        if expected_count is not None and len(self.instances) != expected_count:
            raise ValueError(
                f"{self.package_id} requires exactly {expected_count} physical objects"
            )
        if self.package_id in {ONE_LEVEL_PACKAGE_ID, QUALIFICATION_PACKAGE_ID}:
            if len(self.level_ids) != 1:
                raise ValueError(f"{self.package_id} must describe exactly one level")
        if self.package_id == TWO_LEVEL_PACKAGE_ID and self.level_ids != SELECTED_LEVEL_IDS:
            raise ValueError("The full r6 project must contain independent lower and upper levels")
        if self.package_id in {
            QUALIFICATION_PACKAGE_ID,
            ONE_LEVEL_PACKAGE_ID,
            TWO_LEVEL_PACKAGE_ID,
        }:
            if any(
                item.level is None
                or not item.logical_name.startswith(f"{item.level}::")
                for item in self.instances
            ):
                raise ValueError("Installed package names must carry their exact level prefix")
        if self.package_id == TWO_LEVEL_PACKAGE_ID:
            normalized_by_level = {
                level: sorted(
                    (
                        item.logical_name.split("::", 1)[1],
                        item.mesh_family,
                    )
                    for item in self.instances
                    if item.level == level
                )
                for level in self.level_ids
            }
            if normalized_by_level[SELECTED_LEVEL_IDS[0]] != normalized_by_level[
                SELECTED_LEVEL_IDS[1]
            ]:
                raise ValueError(
                    "The two-level package must be an exact level-independent double"
                )

    @property
    def physical_object_count(self) -> int:
        return len(self.instances)

    @property
    def filename(self) -> str:
        return PACKAGE_FILENAMES[self.package_id]

    @property
    def mesh_families(self) -> tuple[str, ...]:
        """Return the canonical source-resource order for the 3MF writer."""

        return tuple(sorted({item.mesh_family for item in self.instances}))

    def _inventory_payload(self) -> list[dict[str, str | None]]:
        return [item.to_dict() for item in self.instances]

    @property
    def inventory_sha256(self) -> str:
        payload = json.dumps(
            self._inventory_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def plan_sha256(self) -> str:
        payload = {
            "description": self.description,
            "instances": self._inventory_payload(),
            "level_ids": self.level_ids,
            "package_id": self.package_id,
            "filename": self.filename,
            "purpose": self.purpose,
            "title": self.title,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "package_id": self.package_id,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
            "purpose": self.purpose,
            "model_only": True,
            "experimental": True,
            "unrated": True,
            "embedded_gcode_allowed": False,
            "printer_profile_allowed": False,
            "wall_bores_allowed": False,
            "rails_saddles_or_saddle_pins_allowed": False,
            "cross_level_ties_allowed": False,
            "software_model_source_audit_required": (
                self.package_id in ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS
                or self.package_id == UNIQUE_PARTS_PACKAGE_ID
            ),
            "source_audit_policy": (
                "all-emitted-source-catalog"
                if self.package_id == UNIQUE_PARTS_PACKAGE_ID
                else (
                    "current-nonplaceholder-assembly-source"
                    if self.package_id in ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS
                    else "not-applicable"
                )
            ),
            "physical_installation_qualified": False,
            "production_release_eligible": False,
            "physical_object_count": self.physical_object_count,
            "mesh_family_count": len(self.mesh_families),
            "mesh_families": list(self.mesh_families),
            "level_ids": list(self.level_ids),
            "inventory_sha256": self.inventory_sha256,
            "plan_sha256": self.plan_sha256,
            "instances": self._inventory_payload(),
        }


@dataclass(frozen=True)
class PlacedPackageInstance:
    logical_name: str
    mesh_family: str
    translation_mm: tuple[float, float, float]
    placed_bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ReleaseMeshResolver = Callable[[ReleaseRecord], str]


def release_mesh_family_key(record: ReleaseRecord) -> str:
    """Return the stable filename-independent source key for a release record."""

    return f"release::{record.family}::{record.variant}"


def _assert_release_record(record: ReleaseRecord) -> None:
    if record.quantity != 1:
        raise ValueError(f"{record.logical_id}: every inventory row must be one object")
    if not record.level_independent:
        raise ValueError(f"{record.logical_id}: cross-level dependence is forbidden")
    if record.provisional_status != PROVISIONAL_STATUS:
        raise ValueError(f"{record.logical_id}: provisional safety status drift")
    searchable = " ".join(
        (
            record.logical_id,
            record.family,
            record.variant,
            record.interface_ref or "",
        )
    )
    forbidden = forbidden_package_term(searchable)
    if forbidden:
        raise ValueError(f"{record.logical_id}: forbidden installed term {forbidden!r}")
    if record.interface_ref and "::" in record.interface_ref:
        referenced_level = record.interface_ref.split("::", 1)[0]
        if referenced_level in {"lower", "upper"} and referenced_level != record.level:
            raise ValueError(f"{record.logical_id}: interface crosses shelf levels")


def _materialize_release_records(
    records: Iterable[ReleaseRecord],
) -> tuple[ReleaseRecord, ...]:
    materialized = tuple(sorted(records, key=lambda item: item.logical_id))
    if not materialized:
        raise ValueError("A release package needs inventory records")
    if len({item.logical_id for item in materialized}) != len(materialized):
        raise ValueError("Release inventory logical ids must be unique")
    for record in materialized:
        _assert_release_record(record)
    return materialized


def _assert_exact_level_inventory(records: tuple[ReleaseRecord, ...]) -> str:
    levels = {item.level for item in records}
    if len(records) != ONE_LEVEL_PHYSICAL_OBJECT_COUNT or len(levels) != 1:
        raise ValueError(
            "One-level package input must equal the authoritative physical-object "
            "taxonomy on exactly one level"
        )
    actual = Counter(item.family for item in records)
    if dict(sorted(actual.items())) != EXPECTED_ONE_LEVEL_FAMILY_COUNTS:
        raise ValueError("One-level package input does not equal the authoritative taxonomy")
    return next(iter(levels))


def _resolve_instance(
    record: ReleaseRecord,
    mesh_family_resolver: ReleaseMeshResolver,
) -> PackageInstance:
    family = mesh_family_resolver(record)
    if not isinstance(family, str) or not family.strip():
        raise ValueError(f"{record.logical_id}: mesh resolver returned an invalid key")
    return PackageInstance(record.logical_id, family, record.level)


def build_print_first_prototypes_plan(
    prototypes: Iterable[PrototypeSpec],
    *,
    required_roles: Iterable[str] = PRINT_FIRST_REQUIRED_ROLES,
) -> PackagePlan:
    """Plan the complete pre-assembly coupon/prototype package."""

    source = tuple(sorted(prototypes, key=lambda item: item.logical_name))
    if not source:
        raise ValueError("Print-first planning needs prototype specifications")
    names = [item.logical_name for item in source]
    if len(names) != len(set(names)):
        raise ValueError("Print-first prototype logical names must be unique")
    required = frozenset(required_roles)
    if not required:
        raise ValueError("At least one print-first role must be required")
    covered: set[str] = set()
    for item in source:
        if not item.roles or any(not role.strip() for role in item.roles):
            raise ValueError(f"{item.logical_name}: prototype roles must be nonempty")
        if len(item.roles) != len(set(item.roles)):
            raise ValueError(f"{item.logical_name}: prototype roles must be unique")
        covered.update(item.roles)
    missing = sorted(required - covered)
    if missing:
        raise ValueError(f"Print-first package is missing required roles: {missing}")
    return PackagePlan(
        package_id=PRINT_FIRST_PACKAGE_ID,
        title="Story Corner r6 — print-first prototypes",
        purpose=(
            "Fit, bearing, no-bore fastener-boundary, coffer/bridge, and "
            "structural-cassette checks before any qualification assembly."
        ),
        instances=tuple(
            PackageInstance(item.logical_name, item.mesh_family) for item in source
        ),
    )


def build_unique_parts_catalog_plan(
    catalog_mesh_families: Iterable[str],
) -> PackagePlan:
    """Plan one component for every emitted development source mesh."""

    source = tuple(catalog_mesh_families)
    if len(source) != EXPECTED_EMITTED_SOURCE_PART_COUNT:
        raise ValueError(
            "The all-emitted development catalog requires exactly "
            f"{EXPECTED_EMITTED_SOURCE_PART_COUNT} source mesh families"
        )
    if len(source) != len(set(source)):
        raise ValueError("All-emitted catalog mesh-family keys must be unique")
    if any(
        not isinstance(family, str)
        or not family.startswith("source::")
        or not family.removeprefix("source::").strip()
        for family in source
    ):
        raise ValueError(
            "All-emitted catalog families must be nonempty source::<part-name> keys"
        )
    families = tuple(sorted(source))
    return PackagePlan(
        package_id=UNIQUE_PARTS_PACKAGE_ID,
        title="Story Corner r6 — all emitted development meshes catalog",
        purpose=(
            "One representative of every emitted source mesh, including explicitly "
            "classified development coupons; virtual canvas only."
        ),
        instances=tuple(
            PackageInstance(f"catalog::{index:03d}::{family}", family)
            for index, family in enumerate(families, start=1)
        ),
    )


def _same_position(left: ReleaseRecord, right: ReleaseRecord) -> bool:
    return (
        left.position_local_mm is not None
        and right.position_local_mm is not None
        and math.isclose(
            left.position_local_mm,
            right.position_local_mm,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
    )


def _worst_bay_records(
    records: tuple[ReleaseRecord, ...],
) -> tuple[ReleaseRecord, ...]:
    """Select the earliest bay among those with the maximum support span."""

    level = _assert_exact_level_inventory(records)
    candidates: list[tuple[float, str, int, tuple[ReleaseRecord, ReleaseRecord]]] = []
    for run in sorted({item.run for item in records}):
        cassettes = sorted(
            (item for item in records if item.run == run and item.family == "deck_cassette"),
            key=lambda item: item.logical_id,
        )
        if len(cassettes) % 2:
            raise ValueError(f"{run}: qualification planning needs cassette pairs")
        for offset in range(0, len(cassettes), 2):
            pair = (cassettes[offset], cassettes[offset + 1])
            arcades = [
                item
                for item in records
                if item.family == "arcade_half"
                and item.interface_ref in {p.logical_id for p in pair}
            ]
            if len(arcades) != 2 or any(
                item.position_local_mm is None for item in arcades
            ):
                raise ValueError(
                    f"{run}: cassette-to-arcade qualification mapping is incomplete"
                )
            span = abs(
                float(arcades[1].position_local_mm)
                - float(arcades[0].position_local_mm)
            )
            candidates.append((span, run, offset // 2 + 1, pair))
    if not candidates:
        raise ValueError("No complete bay exists in the one-level inventory")
    maximum_span = max(item[0] for item in candidates)
    _span, run, bay_number, cassette_pair = min(
        (
            item
            for item in candidates
            if math.isclose(item[0], maximum_span, abs_tol=1e-6)
        ),
        key=lambda item: (item[1], item[2]),
    )
    cassette_ids = {item.logical_id for item in cassette_pair}
    arcades = tuple(
        item
        for item in records
        if item.family == "arcade_half" and item.interface_ref in cassette_ids
    )
    arcade_ids = {item.logical_id for item in arcades}
    supports = tuple(
        item
        for item in records
        if item.run == run
        and item.family == "structural_pier_x_corbel"
        and any(_same_position(item, arcade) for arcade in arcades)
    )
    support_ids = {item.logical_id for item in supports}
    bridges = sorted(
        (item for item in records if item.run == run and item.family == "crown_bridge"),
        key=lambda item: (
            item.position_local_mm
            if item.position_local_mm is not None
            else math.inf
        ),
    )
    if len(bridges) < bay_number:
        raise ValueError(f"{run}: missing crown bridge for qualification bay {bay_number}")
    bridge = bridges[bay_number - 1]
    if bridge.position_local_mm is None:
        raise ValueError("Qualification crown bridge needs a position")
    crown_families = {
        "diaphragm_bowtie_key",
        "fixed_crown_diaphragm_keeper_strip",
        "fixed_crown_entablature_tie_key",
        "indexed_vertical_quarter_turn_pin",
    }
    selected = [*cassette_pair, *arcades, *supports, bridge]
    selected.extend(
        item
        for item in records
        if item.interface_ref in arcade_ids
        and item.family in {"cassette_top_retention_wedge", "spring_retention_wedge"}
    )
    selected.extend(
        item
        for item in records
        if item.interface_ref in support_ids and item.family == "cassette_lock"
    )
    selected.extend(
        item
        for item in records
        if item.interface_ref == bridge.logical_id
        and item.family == "crown_bridge_retention_pin"
    )
    selected.extend(
        item
        for item in records
        if item.run == run
        and item.family in crown_families
        and item.position_local_mm is not None
        and math.isclose(
            item.position_local_mm,
            bridge.position_local_mm,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
    )
    materialized = tuple(sorted(selected, key=lambda item: item.logical_id))
    if len({item.logical_id for item in materialized}) != len(materialized):
        raise ValueError("Qualification selection duplicated a physical object")
    actual = dict(sorted(Counter(item.family for item in materialized).items()))
    if actual != QUALIFICATION_FAMILY_COUNTS:
        raise ValueError(
            f"Worst-case bay qualification taxonomy drift for {level}/{run}/bay {bay_number}: {actual}"
        )
    return materialized


def build_worst_case_one_bay_qualification_plan(
    one_level_records: Iterable[ReleaseRecord],
    *,
    mesh_family_resolver: ReleaseMeshResolver = release_mesh_family_key,
) -> PackagePlan:
    """Plan the exact current-topology maximum-span one-bay test specimen."""

    records = _materialize_release_records(one_level_records)
    selected = _worst_bay_records(records)
    level = selected[0].level
    return PackagePlan(
        package_id=QUALIFICATION_PACKAGE_ID,
        title="Story Corner r6 — worst-case one-bay qualification assembly",
        purpose=(
            "Exact maximum-span long-wall structural/retention specimen for "
            "arch-installed versus arch-removed and destructive qualification."
        ),
        instances=tuple(_resolve_instance(item, mesh_family_resolver) for item in selected),
        level_ids=(level,),
    )


def build_one_level_l_plan(
    one_level_records: Iterable[ReleaseRecord],
    *,
    mesh_family_resolver: ReleaseMeshResolver = release_mesh_family_key,
) -> PackagePlan:
    """Plan one exact independently wall-fastened L level."""

    records = _materialize_release_records(one_level_records)
    level = _assert_exact_level_inventory(records)
    return PackagePlan(
        package_id=ONE_LEVEL_PACKAGE_ID,
        title=f"Story Corner r6 — exact {level} one-level L",
        purpose=(
            "One complete rail-free integrated-cap shelf level containing "
            f"{ONE_LEVEL_PHYSICAL_OBJECT_COUNT} named physical objects."
        ),
        instances=tuple(_resolve_instance(item, mesh_family_resolver) for item in records),
        level_ids=(level,),
    )


def _level_neutral_signature(instance: PackageInstance) -> tuple[str, str]:
    if "::" not in instance.logical_name:
        raise ValueError(f"Release object lacks a level-qualified name: {instance.logical_name}")
    _level, remainder = instance.logical_name.split("::", 1)
    return remainder, instance.mesh_family


def build_two_level_full_project_plan(
    selected_records: Iterable[ReleaseRecord],
    *,
    mesh_family_resolver: ReleaseMeshResolver = release_mesh_family_key,
) -> PackagePlan:
    """Plan both exact, independent selected shelf levels."""

    records = _materialize_release_records(selected_records)
    expected_selected_count = SELECTED_LEVEL_COUNT * ONE_LEVEL_PHYSICAL_OBJECT_COUNT
    if len(records) != expected_selected_count:
        raise ValueError(
            "The selected full-project inventory must be an exact double of the "
            "authoritative one-level taxonomy"
        )
    by_level = {
        level: tuple(item for item in records if item.level == level)
        for level in sorted({item.level for item in records})
    }
    if tuple(by_level) != SELECTED_LEVEL_IDS:
        raise ValueError("The selected project must contain lower and upper levels")
    for level_records in by_level.values():
        _assert_exact_level_inventory(level_records)
    instances = tuple(_resolve_instance(item, mesh_family_resolver) for item in records)
    lower = sorted(
        (_level_neutral_signature(item) for item in instances if item.level == "lower")
    )
    upper = sorted(
        (_level_neutral_signature(item) for item in instances if item.level == "upper")
    )
    if lower != upper:
        raise ValueError(
            "Lower and upper package inventories must be independent exact doubles"
        )
    return PackagePlan(
        package_id=TWO_LEVEL_PACKAGE_ID,
        title="Story Corner r6 — exact two-level full project",
        purpose=(
            "Two complete rail-free integrated-cap L levels, each containing "
            f"{ONE_LEVEL_PHYSICAL_OBJECT_COUNT} named physical objects, with no "
            "printed structural connection between levels."
        ),
        instances=instances,
        level_ids=SELECTED_LEVEL_IDS,
    )


def build_release_package_plans(
    *,
    prototypes: Iterable[PrototypeSpec],
    catalog_mesh_families: Iterable[str],
    one_level_records: Iterable[ReleaseRecord],
    selected_records: Iterable[ReleaseRecord],
    mesh_family_resolver: ReleaseMeshResolver = release_mesh_family_key,
    required_print_first_roles: Iterable[str] = PRINT_FIRST_REQUIRED_ROLES,
) -> tuple[PackagePlan, ...]:
    """Return the five release plans in their frozen deterministic order."""

    one_level = tuple(one_level_records)
    selected = tuple(selected_records)
    plans = (
        build_print_first_prototypes_plan(
            prototypes,
            required_roles=required_print_first_roles,
        ),
        build_unique_parts_catalog_plan(catalog_mesh_families),
        build_worst_case_one_bay_qualification_plan(
            one_level,
            mesh_family_resolver=mesh_family_resolver,
        ),
        build_one_level_l_plan(one_level, mesh_family_resolver=mesh_family_resolver),
        build_two_level_full_project_plan(
            selected,
            mesh_family_resolver=mesh_family_resolver,
        ),
    )
    if tuple(item.package_id for item in plans) != PACKAGE_ORDER:
        raise AssertionError("r6 package order drift")
    return plans


def mesh_source_audit_checks(
    plan: PackagePlan,
    source_audits: Mapping[str, PackageMeshSourceAudit] | None,
) -> dict[str, bool]:
    """Return fail-closed eligibility checks for software assembly-model sources."""

    if plan.package_id == UNIQUE_PARTS_PACKAGE_ID:
        audits = {} if source_audits is None else dict(source_audits)
        expected = set(plan.mesh_families)
        selected = [audits[family] for family in sorted(expected & set(audits))]
        source_names = [item.source_part_name for item in selected]
        installed = [
            item
            for item in selected
            if item.catalog_classification == "installed_current"
        ]
        return {
            "catalog_source_audits_supplied": source_audits is not None,
            "catalog_audit_keys_equal_all_emitted_mesh_families": (
                set(audits) == expected
            ),
            "catalog_audit_keys_equal_declared_mesh_families": all(
                key == audit.mesh_family for key, audit in audits.items()
            ),
            "catalog_source_names_are_exact_unique_family_suffixes": (
                len(source_names) == len(expected)
                and len(source_names) == len(set(source_names))
                and all(
                    audit.mesh_family == f"source::{audit.source_part_name}"
                    for audit in selected
                )
            ),
            "catalog_classifications_are_exact_and_explicit": (
                len(selected) == len(expected)
                and all(
                    item.catalog_classification in CATALOG_SOURCE_CLASSIFICATIONS
                    and item.placeholder_or_coupon
                    == (item.catalog_classification != "installed_current")
                    for item in selected
                )
            ),
            "catalog_all_source_geometry_validation_passed": (
                len(selected) == len(expected)
                and all(item.geometry_validation_passed for item in selected)
            ),
            "catalog_all_sources_inclusion_eligible": (
                len(selected) == len(expected)
                and all(item.catalog_inclusion_eligible for item in selected)
            ),
            "catalog_installed_sources_are_current_and_software_eligible": (
                bool(installed)
                and all(
                    item.current_interface_geometry
                    and item.software_model_package_eligible
                    and not item.unresolved_interfaces
                    for item in installed
                )
            ),
            "catalog_no_source_is_physical_or_production_qualified": (
                len(selected) == len(expected)
                and not any(
                    item.physical_installation_qualified
                    or item.production_release_eligible
                    for item in selected
                )
            ),
            "catalog_all_source_wall_bore_counts_are_zero": (
                len(selected) == len(expected)
                and all(item.wall_bore_count == 0 for item in selected)
            ),
            "catalog_no_source_contains_rail_or_saddle_geometry": (
                len(selected) == len(expected)
                and not any(item.rail_or_saddle_geometry for item in selected)
            ),
        }
    if plan.package_id not in ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS:
        return {"software_model_source_audit_not_applicable": True}
    audits = {} if source_audits is None else dict(source_audits)
    expected = set(plan.mesh_families)
    present = expected & set(audits)
    selected = [audits[family] for family in sorted(present)]
    source_names = [item.source_part_name for item in selected]
    return {
        "software_model_source_audits_supplied": source_audits is not None,
        "every_planned_mesh_family_audited": present == expected,
        "audit_keys_equal_declared_mesh_families": all(
            key == audit.mesh_family for key, audit in audits.items() if key in expected
        ),
        "source_part_names_present_unique_and_safe": (
            len(source_names) == len(expected)
            and len(source_names) == len(set(source_names))
            and all(
                name.strip() and forbidden_package_term(name) is None
                for name in source_names
            )
        ),
        "all_source_geometry_validation_passed": (
            len(selected) == len(expected)
            and all(item.geometry_validation_passed for item in selected)
        ),
        "all_sources_are_current_interface_geometry": (
            len(selected) == len(expected)
            and all(item.current_interface_geometry for item in selected)
        ),
        "all_sources_are_software_model_package_eligible": (
            len(selected) == len(expected)
            and all(item.software_model_package_eligible for item in selected)
        ),
        "no_source_is_physical_installation_qualified": (
            len(selected) == len(expected)
            and not any(item.physical_installation_qualified for item in selected)
        ),
        "no_source_is_production_release_eligible": (
            len(selected) == len(expected)
            and not any(item.production_release_eligible for item in selected)
        ),
        "no_source_is_a_placeholder_or_coupon": (
            len(selected) == len(expected)
            and not any(item.placeholder_or_coupon for item in selected)
        ),
        "all_source_wall_bore_counts_are_zero": (
            len(selected) == len(expected)
            and all(item.wall_bore_count == 0 for item in selected)
        ),
        "no_source_contains_rail_or_saddle_geometry": (
            len(selected) == len(expected)
            and not any(item.rail_or_saddle_geometry for item in selected)
        ),
        "all_source_interface_blockers_are_closed": (
            len(selected) == len(expected)
            and not any(item.unresolved_interfaces for item in selected)
        ),
    }


def assert_package_mesh_sources_software_model_eligible(
    plan: PackagePlan,
    source_audits: Mapping[str, PackageMeshSourceAudit] | None,
) -> None:
    """Raise before layout/emission when an assembly-model source is unresolved."""

    checks = mesh_source_audit_checks(plan, source_audits)
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            f"{plan.package_id}: software-model mesh-source audit failed: {failed}"
        )


def arrange_on_virtual_canvas(
    instances: Iterable[PackageInstance],
    mesh_by_family: dict[str, trimesh.Trimesh],
    *,
    maximum_row_width_mm: float = 1800.0,
    gap_mm: float = 8.0,
) -> tuple[PlacedPackageInstance, ...]:
    """Place exact objects without overlap; this is not a printer plate layout."""

    source = tuple(instances)
    if not source:
        raise ValueError("A package canvas needs at least one physical instance")
    if (
        not math.isfinite(maximum_row_width_mm)
        or not math.isfinite(gap_mm)
        or maximum_row_width_mm <= 0.0
        or gap_mm < 0.0
    ):
        raise ValueError("Canvas width must be finite/positive and gap finite/nonnegative")
    names = [item.logical_name for item in source]
    if any(not name.strip() for name in names) or len(names) != len(set(names)):
        raise ValueError("Package logical names must be nonempty and unique")
    missing = sorted({item.mesh_family for item in source} - set(mesh_by_family))
    if missing:
        raise ValueError(f"Package instances reference missing mesh families: {missing}")

    placed: list[PlacedPackageInstance] = []
    cursor_x = 0.0
    cursor_y = 0.0
    row_height = 0.0
    for item in source:
        mesh = mesh_by_family[item.mesh_family]
        bounds = np.asarray(mesh.bounds, dtype=float)
        if bounds.shape != (2, 3) or not np.all(np.isfinite(bounds)):
            raise ValueError(f"{item.mesh_family}: mesh bounds must be finite 2x3 values")
        extents = bounds[1] - bounds[0]
        if np.any(extents <= 0.0):
            raise ValueError(f"{item.mesh_family}: mesh has a nonpositive extent")
        if extents[0] > maximum_row_width_mm:
            raise ValueError(f"{item.mesh_family}: mesh is wider than the virtual canvas")
        if cursor_x > 0.0 and cursor_x + extents[0] > maximum_row_width_mm + 1e-7:
            cursor_x = 0.0
            cursor_y += row_height + gap_mm
            row_height = 0.0
        translation = np.array(
            (cursor_x - bounds[0, 0], cursor_y - bounds[0, 1], -bounds[0, 2]),
            dtype=float,
        )
        translated = bounds + translation
        placed.append(
            PlacedPackageInstance(
                logical_name=item.logical_name,
                mesh_family=item.mesh_family,
                translation_mm=tuple(float(value) for value in translation),
                placed_bounds_mm=(
                    tuple(float(value) for value in translated[0]),
                    tuple(float(value) for value in translated[1]),
                ),
            )
        )
        cursor_x += float(extents[0]) + gap_mm
        row_height = max(row_height, float(extents[1]))
    return tuple(placed)


def arrange_package_plan(
    plan: PackagePlan,
    mesh_by_family: dict[str, trimesh.Trimesh],
    *,
    source_audits: Mapping[str, PackageMeshSourceAudit] | None = None,
    maximum_row_width_mm: float = 1800.0,
    gap_mm: float = 8.0,
) -> tuple[PlacedPackageInstance, ...]:
    """Place a plan after enforcing its software-model source eligibility gate."""

    assert_package_mesh_sources_software_model_eligible(plan, source_audits)
    return arrange_on_virtual_canvas(
        plan.instances,
        mesh_by_family,
        maximum_row_width_mm=maximum_row_width_mm,
        gap_mm=gap_mm,
    )


def canvas_bounds(placed: Iterable[PlacedPackageInstance]) -> tuple[float, float, float]:
    source = tuple(placed)
    if not source:
        raise ValueError("Canvas bounds need at least one placed instance")
    values = np.asarray([item.placed_bounds_mm[1] for item in source], dtype=float)
    if values.shape != (len(source), 3) or not np.all(np.isfinite(values)):
        raise ValueError("Placed package bounds must be finite 3D values")
    maximum = np.max(values, axis=0)
    return tuple(float(value) for value in maximum)


def bounds_overlap_in_xy(
    first: PlacedPackageInstance,
    second: PlacedPackageInstance,
    *,
    tolerance_mm: float = 1e-7,
) -> bool:
    """Return true only when two placed AABBs have positive XY overlap."""

    if not math.isfinite(tolerance_mm) or tolerance_mm < 0.0:
        raise ValueError("Overlap tolerance must be finite and nonnegative")
    a0, a1 = first.placed_bounds_mm
    b0, b1 = second.placed_bounds_mm
    values = (*a0, *a1, *b0, *b1)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Placed bounds must be finite")
    return (
        min(a1[0], b1[0]) - max(a0[0], b0[0]) > tolerance_mm
        and min(a1[1], b1[1]) - max(a0[1], b0[1]) > tolerance_mm
    )


__all__ = [
    "CATALOG_SOURCE_CLASSIFICATIONS",
    "EXPECTED_EMITTED_SOURCE_PART_COUNT",
    "EXPECTED_EXACT_PACKAGE_COUNTS",
    "ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS",
    "ONE_LEVEL_PHYSICAL_OBJECT_COUNT",
    "SELECTED_LEVEL_IDS",
    "ONE_LEVEL_PACKAGE_ID",
    "PACKAGE_ORDER",
    "PACKAGE_FILENAMES",
    "PRINT_FIRST_PACKAGE_ID",
    "PRINT_FIRST_REQUIRED_ROLES",
    "PackageInstance",
    "PackageMeshSourceAudit",
    "PackagePlan",
    "PlacedPackageInstance",
    "PrototypeSpec",
    "QUALIFICATION_FAMILY_COUNTS",
    "QUALIFICATION_PACKAGE_ID",
    "SAFETY_DESCRIPTION",
    "TWO_LEVEL_PACKAGE_ID",
    "UNIQUE_PARTS_PACKAGE_ID",
    "arrange_on_virtual_canvas",
    "arrange_package_plan",
    "assert_package_mesh_sources_software_model_eligible",
    "bounds_overlap_in_xy",
    "build_one_level_l_plan",
    "build_print_first_prototypes_plan",
    "build_release_package_plans",
    "build_two_level_full_project_plan",
    "build_unique_parts_catalog_plan",
    "build_worst_case_one_bay_qualification_plan",
    "canvas_bounds",
    "forbidden_package_term",
    "mesh_source_audit_checks",
    "release_mesh_family_key",
]
