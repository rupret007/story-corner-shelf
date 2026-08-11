#!/usr/bin/env python3
"""Deterministic tabletop-fixture evidence for the R9 qualification parts.

This module does not create shelf CAD, wall-drilling coordinates, a slicer
project, or production authorization.  It only reconstructs service paths for
interfaces that are explicit in :mod:`support_geometry`:

* rear-ledger male/female coupon insertion and removal;
* front-beam lower/upper-lap coupon insertion and removal; and
* a nominal 90-degree tabletop stack made from the two handed hidden-corner
  halves, the under-shelf key coupon, cosmetic-cover coupon, and angle fixture.

The compact-support/ledger/front-beam one-bay layout is deliberately blocked.
Those qualification meshes contain no authored member seats, cassette
interface, or bay-end geometry, so assigning an assembled pose would invent a
load path.  All evidence remains PETG-only, zero-rated, and dependent on field
angle measurement plus physical first-article qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import warnings
from typing import Sequence

import numpy as np
import trimesh

try:  # Support package imports and direct unittest discovery from this folder.
    from . import support_geometry as geometry
except ImportError:  # pragma: no cover - exercised by the direct test runner
    import support_geometry as geometry  # type: ignore[no-redef]


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
PRINTED_MATERIAL = "PETG"
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
FIELD_ANGLE_VERIFIED = False
WALL_BORES_EMITTED = False

DEFAULT_SERVICE_SAMPLE_COUNT = 9
COLLISION_VOLUME_TOLERANCE_MM3 = 1.0e-6

Vector3 = tuple[float, float, float]
Matrix4 = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]


@dataclass(frozen=True)
class RigidTransform:
    """One exact local-to-tabletop rigid transform in millimetres."""

    matrix: Matrix4

    def __post_init__(self) -> None:
        matrix = np.asarray(self.matrix, dtype=float)
        if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
            raise ValueError("A rigid transform must be a finite 4 x 4 matrix")
        if not np.allclose(matrix[3], (0.0, 0.0, 0.0, 1.0), atol=1.0e-12):
            raise ValueError("A rigid transform must have a homogeneous last row")
        rotation = matrix[:3, :3]
        if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1.0e-12):
            raise ValueError("A rigid transform rotation must be orthonormal")
        if not math.isclose(float(np.linalg.det(rotation)), 1.0, abs_tol=1.0e-12):
            raise ValueError("A fixture transform must be a proper rotation")

    @property
    def translation_mm(self) -> Vector3:
        return (
            float(self.matrix[0][3]),
            float(self.matrix[1][3]),
            float(self.matrix[2][3]),
        )

    def as_array(self) -> np.ndarray:
        """Return a fresh numerical matrix so callers cannot mutate evidence."""

        return np.asarray(self.matrix, dtype=float).copy()


@dataclass(frozen=True)
class PartEvidence:
    """Fail-closed topology and printer-envelope facts for one source mesh."""

    part_name: str
    mesh_fingerprint: str
    body_count: int
    watertight: bool
    winding_consistent: bool
    positive_volume: bool
    raw_part_mm: Vector3
    required_build_volume_mm: Vector3
    a1_mini_fits: bool


@dataclass(frozen=True)
class ClearanceDatum:
    """One analytic gap or intentional zero-gap contact at the target pose."""

    name: str
    value_mm: float
    interpretation: str


@dataclass(frozen=True)
class CollisionSample:
    """Volumetric collision observation at one insertion/removal pose."""

    seated_fraction: float
    service_offset_mm: float
    moving_transform: RigidTransform
    intersection_by_fixed_part_mm3: tuple[tuple[str, float], ...]
    total_intersection_volume_mm3: float


@dataclass(frozen=True)
class ServicePathEvidence:
    """Sampled straight-line insertion path and its exact reverse removal path."""

    name: str
    fixed_part_names: tuple[str, ...]
    moving_part_name: str
    target_transform: RigidTransform
    disengaged_transform: RigidTransform
    service_direction_unit_xyz: Vector3
    service_travel_mm: float
    insertion_samples: tuple[CollisionSample, ...]
    removal_samples: tuple[CollisionSample, ...]
    target_clearances: tuple[ClearanceDatum, ...]
    intended_target_contacts: tuple[str, ...]
    collision_volume_tolerance_mm3: float
    maximum_intersection_volume_mm3: float
    sampled_path_collision_free: bool


@dataclass(frozen=True)
class JointFixtureEvidence:
    """Complete non-rated evidence for one explicit two-part coupon joint."""

    name: str
    parts: tuple[PartEvidence, PartEvidence]
    service_path: ServicePathEvidence
    qualification_only: bool
    physical_qualification_complete: bool
    printed_material: str
    rated_load_kg: float
    rated_load_lb: float


@dataclass(frozen=True)
class PlacedPartEvidence:
    """One corner coupon and its exact nominal tabletop target transform."""

    part: PartEvidence
    target_transform: RigidTransform


@dataclass(frozen=True)
class PairIntersectionEvidence:
    """Target-pose penetration check for one unordered part pair."""

    part_a_name: str
    part_b_name: str
    intersection_volume_mm3: float


@dataclass(frozen=True)
class CornerDryFitEvidence:
    """Nominal-square tabletop study; never a field or structural release."""

    name: str
    nominal_fixture_angle_deg: float
    placed_parts: tuple[PlacedPartEvidence, ...]
    service_paths: tuple[ServicePathEvidence, ...]
    target_pair_intersections: tuple[PairIntersectionEvidence, ...]
    maximum_target_intersection_volume_mm3: float
    target_pose_collision_free: bool
    field_angle_verified: bool
    corner_load_path_authored: bool
    qualification_only: bool
    physical_qualification_complete: bool
    printed_material: str
    rated_load_kg: float
    rated_load_lb: float


@dataclass(frozen=True)
class BlockedFixtureEvidence:
    """Explicit record that a requested fixture pose is not yet authorable."""

    name: str
    blocked: bool
    reason: str
    missing_authored_interfaces: tuple[str, ...]
    emitted_meshes: bool
    placed_parts: tuple[PlacedPartEvidence, ...]
    qualification_only: bool
    production_ready: bool
    printed_material: str
    rated_load_kg: float
    rated_load_lb: float


def _matrix(rows: Sequence[Sequence[float]]) -> Matrix4:
    array = np.asarray(rows, dtype=float)
    if array.shape != (4, 4) or not np.isfinite(array).all():
        raise ValueError("Expected a finite 4 x 4 transform")
    return tuple(tuple(float(value) for value in row) for row in array)  # type: ignore[return-value]


def identity_transform() -> RigidTransform:
    """Return the exact tabletop identity transform."""

    return RigidTransform(
        _matrix(
            (
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            )
        )
    )


def translation_transform(translation_mm: Vector3) -> RigidTransform:
    """Return an identity rotation with one finite XYZ translation."""

    translation = np.asarray(translation_mm, dtype=float)
    if translation.shape != (3,) or not np.isfinite(translation).all():
        raise ValueError("Translation must contain three finite millimetre values")
    matrix = np.eye(4, dtype=float)
    matrix[:3, 3] = translation
    return RigidTransform(_matrix(matrix))


def offset_transform(
    transform: RigidTransform, offset_xyz_mm: Vector3
) -> RigidTransform:
    """Translate an existing local-to-world transform in world coordinates."""

    if not isinstance(transform, RigidTransform):
        raise ValueError("Expected a RigidTransform")
    offset = np.asarray(offset_xyz_mm, dtype=float)
    if offset.shape != (3,) or not np.isfinite(offset).all():
        raise ValueError("Offset must contain three finite millimetre values")
    matrix = transform.as_array()
    matrix[:3, 3] += offset
    return RigidTransform(_matrix(matrix))


def apply_transform(
    mesh: trimesh.Trimesh, transform: RigidTransform
) -> trimesh.Trimesh:
    """Return a transformed copy without mutating the qualification source."""

    if not isinstance(transform, RigidTransform):
        raise ValueError("Expected a RigidTransform")
    result = geometry.part_copy(mesh)
    result.apply_transform(transform.as_array())
    result.remove_unreferenced_vertices()
    result.fix_normals(multibody=True)
    if result.is_empty or not np.isfinite(result.vertices).all():
        raise ValueError("Fixture transform produced invalid geometry")
    return result


def _part_evidence(name: str, mesh: trimesh.Trimesh) -> PartEvidence:
    if not name:
        raise ValueError("A qualification part name is required")
    envelope = geometry.print_envelope_with_margins(mesh)
    return PartEvidence(
        part_name=name,
        mesh_fingerprint=geometry.mesh_fingerprint(mesh),
        body_count=len(mesh.split(only_watertight=False)),
        watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),
        positive_volume=bool(mesh.is_volume and float(mesh.volume) > 0.0),
        raw_part_mm=tuple(float(value) for value in envelope.raw_part_mm),  # type: ignore[arg-type]
        required_build_volume_mm=tuple(
            float(value) for value in envelope.required_build_volume_mm
        ),  # type: ignore[arg-type]
        a1_mini_fits=bool(envelope.fits),
    )


def _intersection_volume_mm3(
    first: trimesh.Trimesh, second: trimesh.Trimesh
) -> float:
    """Return positive common volume; boundary contact correctly reports zero."""

    with warnings.catch_warnings():
        # Manifold may ask Trimesh for a centroid of a zero-volume contact mesh.
        warnings.simplefilter("ignore", RuntimeWarning)
        result = trimesh.boolean.intersection(
            [geometry.part_copy(first), geometry.part_copy(second)],
            engine="manifold",
            check_volume=False,
        )
        if isinstance(result, list):
            value = sum(abs(float(mesh.volume)) for mesh in result if not mesh.is_empty)
        elif result is None or result.is_empty:
            value = 0.0
        else:
            value = abs(float(result.volume))
    if not math.isfinite(value):
        raise ValueError("Collision calculation produced a non-finite volume")
    return 0.0 if value <= COLLISION_VOLUME_TOLERANCE_MM3 else value


def _sample_count(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        raise ValueError("Service-path sample count must be an integer of at least two")
    return value


def _unit_vector(value: Vector3) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError("Service direction must contain three finite coordinates")
    length = float(np.linalg.norm(vector))
    if not math.isclose(length, 1.0, abs_tol=1.0e-12):
        raise ValueError("Service direction must be a unit vector")
    return vector


def _build_service_path(
    *,
    name: str,
    fixed_parts: Sequence[tuple[str, trimesh.Trimesh, RigidTransform]],
    moving_part_name: str,
    moving_mesh: trimesh.Trimesh,
    target_transform: RigidTransform,
    service_direction_unit_xyz: Vector3,
    service_travel_mm: float,
    target_clearances: Sequence[ClearanceDatum],
    intended_target_contacts: Sequence[str],
    sample_count: int,
) -> ServicePathEvidence:
    count = _sample_count(sample_count)
    direction = _unit_vector(service_direction_unit_xyz)
    travel = float(service_travel_mm)
    if not math.isfinite(travel) or travel <= 0.0:
        raise ValueError("Service travel must be a positive finite distance")
    if not fixed_parts:
        raise ValueError("At least one fixed qualification part is required")

    placed_fixed = tuple(
        (part_name, apply_transform(mesh, transform))
        for part_name, mesh, transform in fixed_parts
    )
    samples: list[CollisionSample] = []
    for index in range(count):
        seated_fraction = index / (count - 1)
        service_offset = travel * (1.0 - seated_fraction)
        transform = offset_transform(
            target_transform,
            tuple(float(value) for value in direction * service_offset),  # type: ignore[arg-type]
        )
        moving = apply_transform(moving_mesh, transform)
        intersections = tuple(
            (fixed_name, _intersection_volume_mm3(moving, fixed_mesh))
            for fixed_name, fixed_mesh in placed_fixed
        )
        total = float(sum(value for _, value in intersections))
        samples.append(
            CollisionSample(
                seated_fraction=float(seated_fraction),
                service_offset_mm=float(service_offset),
                moving_transform=transform,
                intersection_by_fixed_part_mm3=intersections,
                total_intersection_volume_mm3=total,
            )
        )
    maximum = max(sample.total_intersection_volume_mm3 for sample in samples)
    insertion = tuple(samples)
    return ServicePathEvidence(
        name=name,
        fixed_part_names=tuple(name for name, _, _ in fixed_parts),
        moving_part_name=moving_part_name,
        target_transform=target_transform,
        disengaged_transform=insertion[0].moving_transform,
        service_direction_unit_xyz=tuple(float(value) for value in direction),  # type: ignore[arg-type]
        service_travel_mm=travel,
        insertion_samples=insertion,
        removal_samples=tuple(reversed(insertion)),
        target_clearances=tuple(target_clearances),
        intended_target_contacts=tuple(intended_target_contacts),
        collision_volume_tolerance_mm3=COLLISION_VOLUME_TOLERANCE_MM3,
        maximum_intersection_volume_mm3=float(maximum),
        sampled_path_collision_free=maximum <= COLLISION_VOLUME_TOLERANCE_MM3,
    )


def _coupon_target_transform(pair: geometry.CouponPair) -> RigidTransform:
    return translation_transform(
        tuple(float(value) for value in pair.part_b_assembly_translation_mm)  # type: ignore[arg-type]
    )


def build_rear_ledger_insertion_removal_evidence(
    *, sample_count: int = DEFAULT_SERVICE_SAMPLE_COUNT
) -> JointFixtureEvidence:
    """Prove the explicit ledger tongue can enter and leave its coupon socket."""

    pair = geometry.build_modular_rear_ledger_joint_coupon()
    clearance = float(pair.clearance_per_face_mm)
    path = _build_service_path(
        name="r9_rear_ledger_coupon_insertion_removal",
        fixed_parts=((pair.part_a_name, pair.part_a, identity_transform()),),
        moving_part_name=pair.part_b_name,
        moving_mesh=pair.part_b,
        target_transform=_coupon_target_transform(pair),
        service_direction_unit_xyz=(1.0, 0.0, 0.0),
        service_travel_mm=geometry.REAR_LEDGER_TONGUE_LENGTH_MM + clearance,
        target_clearances=(
            ClearanceDatum(
                "socket_y_clearance_each_face",
                clearance,
                "radial running clearance on both tongue-depth faces",
            ),
            ClearanceDatum(
                "socket_z_clearance_each_face",
                clearance,
                "radial running clearance on both tongue-height faces",
            ),
            ClearanceDatum(
                "tongue_tip_clearance",
                clearance,
                "axial gap from the tongue tip to the blind socket end",
            ),
            ClearanceDatum(
                "body_shoulder_contact",
                0.0,
                "intentional coplanar end-face contact outside the tongue",
            ),
        ),
        intended_target_contacts=("male/female body shoulder plane at X = 60 mm",),
        sample_count=sample_count,
    )
    return JointFixtureEvidence(
        name=pair.name,
        parts=(
            _part_evidence(pair.part_a_name, pair.part_a),
            _part_evidence(pair.part_b_name, pair.part_b),
        ),
        service_path=path,
        qualification_only=True,
        physical_qualification_complete=False,
        printed_material=PRINTED_MATERIAL,
        rated_load_kg=0.0,
        rated_load_lb=0.0,
    )


def build_front_beam_insertion_removal_evidence(
    *, sample_count: int = DEFAULT_SERVICE_SAMPLE_COUNT
) -> JointFixtureEvidence:
    """Prove the explicit staggered upper lap can translate over the lower lap."""

    pair = geometry.build_staggered_front_beam_splice_coupon()
    clearance = float(pair.clearance_per_face_mm)
    path = _build_service_path(
        name="r9_front_beam_coupon_insertion_removal",
        fixed_parts=((pair.part_a_name, pair.part_a, identity_transform()),),
        moving_part_name=pair.part_b_name,
        moving_mesh=pair.part_b,
        target_transform=_coupon_target_transform(pair),
        service_direction_unit_xyz=(1.0, 0.0, 0.0),
        service_travel_mm=geometry.FRONT_BEAM_SPLICE_LENGTH_MM,
        target_clearances=(
            ClearanceDatum(
                "left_axial_shoulder_gap",
                clearance,
                "gap between the lower-part body and upper-lap start",
            ),
            ClearanceDatum(
                "right_axial_shoulder_gap",
                clearance,
                "gap between the lower-lap tip and upper-part body",
            ),
            ClearanceDatum(
                "opposed_lap_face_gap",
                2.0 * clearance,
                "total Z gap; 0.4 mm is reserved from each nominal half",
            ),
        ),
        intended_target_contacts=(),
        sample_count=sample_count,
    )
    return JointFixtureEvidence(
        name=pair.name,
        parts=(
            _part_evidence(pair.part_a_name, pair.part_a),
            _part_evidence(pair.part_b_name, pair.part_b),
        ),
        service_path=path,
        qualification_only=True,
        physical_qualification_complete=False,
        printed_material=PRINTED_MATERIAL,
        rated_load_kg=0.0,
        rated_load_lb=0.0,
    )


def _corner_transforms() -> dict[str, RigidTransform]:
    """Return exact target transforms in a right-handed tabletop frame.

    Global X and Z are the two perpendicular wall-normal directions and global
    Y is elevation.  The return half maps ``(q, e, run)`` to
    ``(16-run, e, q)``; this is the explicit run reversal required by the two
    complementary 45-degree miters.  Flat L coupons map authored XY into global
    ZX while their authored thickness becomes global Y.
    """

    corner = geometry.build_hidden_corner_dry_fit_set()
    flat_to_horizontal = np.asarray(
        (
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=float,
    )
    fixture = flat_to_horizontal.copy()
    fixture[1, 3] = -geometry.TABLETOP_FIXTURE_THICKNESS_MM
    key = flat_to_horizontal.copy()
    key[1, 3] = geometry.WALL_STRAP_TOTAL_DROP_MM
    cover = flat_to_horizontal.copy()
    cover[1, 3] = (
        geometry.WALL_STRAP_TOTAL_DROP_MM + geometry.SHEAR_KEY_THICKNESS_MM
    )
    return {
        corner.tabletop_fixture_name: RigidTransform(_matrix(fixture)),
        corner.through_half_name: identity_transform(),
        corner.return_half_name: RigidTransform(
            _matrix(
                (
                    (0.0, 0.0, -1.0, geometry.CONCEALED_CORNER_HALF_THICKNESS_MM),
                    (0.0, 1.0, 0.0, 0.0),
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                )
            )
        ),
        corner.shear_key_name: RigidTransform(_matrix(key)),
        corner.cosmetic_cover_name: RigidTransform(_matrix(cover)),
    }


def build_nominal_corner_target_meshes() -> dict[str, trimesh.Trimesh]:
    """Reconstruct the five separate corner parts in the nominal target pose."""

    corner = geometry.build_hidden_corner_dry_fit_set()
    sources = {
        corner.tabletop_fixture_name: corner.tabletop_fixture,
        corner.through_half_name: corner.through_half,
        corner.return_half_name: corner.return_half,
        corner.shear_key_name: corner.shear_key,
        corner.cosmetic_cover_name: corner.cosmetic_cover,
    }
    transforms = _corner_transforms()
    if tuple(sources) != tuple(transforms):
        raise AssertionError("Corner source and transform order drifted")
    return {
        name: apply_transform(mesh, transforms[name]) for name, mesh in sources.items()
    }


def _target_pair_intersections(
    placed: dict[str, trimesh.Trimesh]
) -> tuple[PairIntersectionEvidence, ...]:
    names = tuple(placed)
    evidence: list[PairIntersectionEvidence] = []
    for first_index, first_name in enumerate(names):
        for second_name in names[first_index + 1 :]:
            evidence.append(
                PairIntersectionEvidence(
                    part_a_name=first_name,
                    part_b_name=second_name,
                    intersection_volume_mm3=_intersection_volume_mm3(
                        placed[first_name], placed[second_name]
                    ),
                )
            )
    return tuple(evidence)


def build_nominal_corner_tabletop_dry_fit_evidence(
    *, sample_count: int = DEFAULT_SERVICE_SAMPLE_COUNT
) -> CornerDryFitEvidence:
    """Build exact nominal-square poses and sampled collision-free service paths.

    The fixture is placed below global Y=0.  The two support halves stand on it,
    the key seats at Y=160 mm, and the cosmetic coupon seats on the key at
    Y=164 mm.  This stacked arrangement is solely a tabletop handling/reveal
    study; it is not an authored installed corner load path.
    """

    count = _sample_count(sample_count)
    corner = geometry.build_hidden_corner_dry_fit_set()
    transforms = _corner_transforms()
    sources = {
        corner.tabletop_fixture_name: corner.tabletop_fixture,
        corner.through_half_name: corner.through_half,
        corner.return_half_name: corner.return_half,
        corner.shear_key_name: corner.shear_key,
        corner.cosmetic_cover_name: corner.cosmetic_cover,
    }

    fixture_entry = (
        corner.tabletop_fixture_name,
        corner.tabletop_fixture,
        transforms[corner.tabletop_fixture_name],
    )
    through_entry = (
        corner.through_half_name,
        corner.through_half,
        transforms[corner.through_half_name],
    )
    return_entry = (
        corner.return_half_name,
        corner.return_half,
        transforms[corner.return_half_name],
    )
    key_entry = (
        corner.shear_key_name,
        corner.shear_key,
        transforms[corner.shear_key_name],
    )

    paths = (
        _build_service_path(
            name="r9_corner_through_half_vertical_seating",
            fixed_parts=(fixture_entry,),
            moving_part_name=corner.through_half_name,
            moving_mesh=corner.through_half,
            target_transform=transforms[corner.through_half_name],
            service_direction_unit_xyz=(0.0, 1.0, 0.0),
            service_travel_mm=8.0,
            target_clearances=(
                ClearanceDatum(
                    "fixture_top_contact",
                    0.0,
                    "support bottom intentionally rests on the angle fixture",
                ),
            ),
            intended_target_contacts=("through-half bottom / fixture top",),
            sample_count=count,
        ),
        _build_service_path(
            name="r9_corner_return_half_miter_insertion",
            fixed_parts=(fixture_entry, through_entry),
            moving_part_name=corner.return_half_name,
            moving_mesh=corner.return_half,
            target_transform=transforms[corner.return_half_name],
            service_direction_unit_xyz=(0.0, 0.0, 1.0),
            service_travel_mm=(
                geometry.CONCEALED_CORNER_HALF_THICKNESS_MM
                + geometry.NOMINAL_JOINT_CLEARANCE_PER_FACE_MM
            ),
            target_clearances=(
                ClearanceDatum(
                    "complementary_miter_contact",
                    0.0,
                    "authored 45-degree faces meet at nominal 90 degrees",
                ),
                ClearanceDatum(
                    "fixture_top_contact",
                    0.0,
                    "return-half bottom slides on the tabletop fixture plane",
                ),
            ),
            intended_target_contacts=(
                "through/return complementary 45-degree miter",
                "return-half bottom / fixture top",
            ),
            sample_count=count,
        ),
        _build_service_path(
            name="r9_corner_shear_key_vertical_seating",
            fixed_parts=(through_entry, return_entry),
            moving_part_name=corner.shear_key_name,
            moving_mesh=corner.shear_key,
            target_transform=transforms[corner.shear_key_name],
            service_direction_unit_xyz=(0.0, 1.0, 0.0),
            service_travel_mm=8.0,
            target_clearances=(
                ClearanceDatum(
                    "support_top_contact",
                    0.0,
                    "flat key rests on both support top planes for handling study",
                ),
            ),
            intended_target_contacts=("key underside / both support tops",),
            sample_count=count,
        ),
        _build_service_path(
            name="r9_corner_cosmetic_cover_vertical_seating",
            fixed_parts=(key_entry,),
            moving_part_name=corner.cosmetic_cover_name,
            moving_mesh=corner.cosmetic_cover,
            target_transform=transforms[corner.cosmetic_cover_name],
            service_direction_unit_xyz=(0.0, 1.0, 0.0),
            service_travel_mm=8.0,
            target_clearances=(
                ClearanceDatum(
                    "key_top_contact",
                    0.0,
                    "cosmetic coupon rests on the key only for seam visualization",
                ),
            ),
            intended_target_contacts=("cosmetic-cover underside / key top",),
            sample_count=count,
        ),
    )
    target_meshes = {
        name: apply_transform(mesh, transforms[name]) for name, mesh in sources.items()
    }
    intersections = _target_pair_intersections(target_meshes)
    maximum = max(item.intersection_volume_mm3 for item in intersections)
    return CornerDryFitEvidence(
        name="r9_nominal_90_degree_hidden_corner_tabletop_dry_fit",
        nominal_fixture_angle_deg=float(corner.nominal_fixture_angle_deg),
        placed_parts=tuple(
            PlacedPartEvidence(
                part=_part_evidence(name, mesh),
                target_transform=transforms[name],
            )
            for name, mesh in sources.items()
        ),
        service_paths=paths,
        target_pair_intersections=intersections,
        maximum_target_intersection_volume_mm3=float(maximum),
        target_pose_collision_free=maximum <= COLLISION_VOLUME_TOLERANCE_MM3,
        field_angle_verified=False,
        corner_load_path_authored=False,
        qualification_only=True,
        physical_qualification_complete=False,
        printed_material=PRINTED_MATERIAL,
        rated_load_kg=0.0,
        rated_load_lb=0.0,
    )


def build_compact_one_bay_tabletop_evidence() -> BlockedFixtureEvidence:
    """Fail closed instead of inventing a compact-support/member assembly pose."""

    return BlockedFixtureEvidence(
        name="r9_compact_support_ledger_front_beam_one_bay_tabletop_layout",
        blocked=True,
        reason=(
            "No exact one-bay transform can be derived from the present R9 "
            "qualification meshes without inventing structural interfaces."
        ),
        missing_authored_interfaces=(
            "compact-support rear-ledger seat, notch, or attachment interface",
            "compact-support front-beam seat, notch, or attachment interface",
            "shelf-cassette/member interface and exact cassette seam geometry",
            "full bay member lengths and member-end conditions",
            "wall fastener bores, hardware envelopes, and verified framing datums",
        ),
        emitted_meshes=False,
        placed_parts=(),
        qualification_only=True,
        production_ready=False,
        printed_material=PRINTED_MATERIAL,
        rated_load_kg=0.0,
        rated_load_lb=0.0,
    )


def build_all_fixture_evidence() -> tuple[
    JointFixtureEvidence,
    JointFixtureEvidence,
    CornerDryFitEvidence,
    BlockedFixtureEvidence,
]:
    """Return the complete evidence set in stable qualification order."""

    return (
        build_rear_ledger_insertion_removal_evidence(),
        build_front_beam_insertion_removal_evidence(),
        build_nominal_corner_tabletop_dry_fit_evidence(),
        build_compact_one_bay_tabletop_evidence(),
    )

