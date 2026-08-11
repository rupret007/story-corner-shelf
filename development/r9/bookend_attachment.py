#!/usr/bin/env python3
"""Additive outer-bookend / two-socket-rail qualification candidate.

The separate R9 cable fit rail is mapped onto the shortened outer bookend's
full 160 mm wall strap and Manifold-unioned with 0.4 mm of positive material
overlap.  The source support is copied, never cut.  Rail socket cavities begin
2.0 mm beyond the source strap's outer face, so they cannot subtract from the
structural core.

Coordinates before print orientation are the support convention:

* X: wall-to-front projection ``q``;
* Y: installed elevation ``e``; and
* Z: across the shelf run.

The saved orientation maps the broad wall-facing strap onto the XY plate.  All
parts remain PETG-only, zero-rated, and qualification-only.  Wall attachment,
door/trim clearance, cable-loop clearance, endpoint service access, snagging,
and load capacity are expressly unqualified.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal
import warnings

import numpy as np
import trimesh

try:  # Package imports and direct unittest discovery are both supported.
    from . import cable_geometry, support_geometry
except ImportError:  # pragma: no cover - direct unittest discovery path
    import cable_geometry  # type: ignore[no-redef]
    import support_geometry  # type: ignore[no-redef]


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
PRINTED_MATERIAL = "PETG"
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
STRUCTURAL_OR_SHELF_LOAD_CREDIT = False
SUPPORT_CORE_SUBTRACTION_ALLOWED = False
WALL_BORES_EMITTED = False
ENDPOINT_INSTALLED_CLEARANCE_QUALIFIED = False
DOOR_AND_CABLE_LOOP_CLEARANCE_QUALIFIED = False

RAIL_TO_STRAP_OVERLAP_MM = 0.4
RAIL_ACROSS_RUN_REVEAL_EACH_SIDE_MM = (
    cable_geometry.RAIL_WIDTH_MM - support_geometry.SUPPORT_RUN_THICKNESS_MM
) / 2.0
# A 64..126 mm middle-upper band keeps the complete rail inside the authored
# D-window immediately beyond q=16.  That prevents accidental overlap with the
# shortened diagonal web while leaving both sockets comfortably below the top.
RAIL_VERTICAL_BOTTOM_MM = 64.0
RAIL_VERTICAL_TOP_MM = RAIL_VERTICAL_BOTTOM_MM + cable_geometry.RAIL_HEIGHT_MM
RAIL_BACK_Q_MM = (
    support_geometry.WALL_STRAP_PROJECTION_MM - RAIL_TO_STRAP_OVERLAP_MM
)
RAIL_FRONT_Q_MM = RAIL_BACK_Q_MM + cable_geometry.RAIL_THICKNESS_MM
SOCKET_CAVITY_NEAREST_CORE_Q_MM = (
    RAIL_BACK_Q_MM + cable_geometry.UNINTERRUPTED_BACK_WEB_MM
)
SOURCE_CORE_OUTER_Q_MM = support_geometry.WALL_STRAP_PROJECTION_MM
PRINT_FOOT_SIDE_EXTENSION_MM = RAIL_ACROSS_RUN_REVEAL_EACH_SIDE_MM
PRINT_FOOT_CORE_OVERLAP_MM = 0.4

Endpoint = Literal["through_outer", "return_outer"]
THROUGH_PART_NAME = "r9_through_outer_bookend_additive_two_socket_candidate"
RETURN_PART_NAME = "r9_return_outer_bookend_additive_two_socket_candidate"
SAME_CANDIDATE_SKU_BOTH_ENDPOINTS = False
GEOMETRY_EPSILON = 1.0e-7


@dataclass(frozen=True)
class AttachmentCandidate:
    endpoint: Endpoint
    part_name: str
    source_core: trimesh.Trimesh
    mapped_rail: trimesh.Trimesh
    additive_print_foot: trimesh.Trimesh
    body: trimesh.Trimesh
    rail_to_support: np.ndarray
    mirrored_from_through: bool


@dataclass(frozen=True)
class CoreContainmentEvidence:
    endpoint: Endpoint
    source_core_digest_before: str
    source_core_digest_after: str
    source_core_volume_mm3: float
    mapped_rail_volume_mm3: float
    additive_print_foot_volume_mm3: float
    positive_overlap_volume_mm3: float
    expected_overlap_volume_mm3: float
    union_volume_mm3: float
    volume_balance_error_mm3: float
    missing_source_core_volume_mm3: float
    source_core_preserved: bool
    additive_only: bool


@dataclass(frozen=True)
class EndpointSemanticsEvidence:
    through_part_name: str
    return_part_name: str
    same_candidate_sku_both_endpoints: bool
    through_is_self_mirror_symmetric: bool
    mirrored_through_matches_return: bool
    return_mirrored_back_matches_through: bool
    reason: str


@dataclass(frozen=True)
class SavedAttachmentPrintEvidence:
    endpoint: Endpoint
    part_name: str
    orientation_id: str
    support_required: bool
    support_classification: str
    layer_connected: bool
    sampled_layer_count: int
    disconnected_layer_indices: tuple[int, ...]
    first_layer_contact_area_mm2: float
    maximum_new_side_reveal_mm: float
    body_count: int
    watertight: bool
    winding_consistent: bool
    envelope: support_geometry.PrintEnvelope


@dataclass(frozen=True)
class MappedServicePath:
    endpoint: Endpoint
    station_index: int
    insertion_approach: tuple[trimesh.Trimesh, ...]
    gravity_drop: tuple[trimesh.Trimesh, ...]
    removal_lift: tuple[trimesh.Trimesh, ...]
    removal_outward: tuple[trimesh.Trimesh, ...]
    increment_mm: float


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("Geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Geometry operation produced non-finite vertices")
    return mesh


def _endpoint(value: str) -> Endpoint:
    if value not in ("through_outer", "return_outer"):
        raise ValueError("endpoint must be through_outer or return_outer")
    return value  # type: ignore[return-value]


def rail_to_support_transform() -> np.ndarray:
    """Map rail (across, outward, vertical) into support (q, e, run)."""

    matrix = np.zeros((4, 4), dtype=float)
    matrix[0, 1] = 1.0  # rail outward Y -> support projection Q
    matrix[1, 2] = 1.0  # rail vertical Z -> support elevation E
    matrix[2, 0] = 1.0  # rail across X -> support run Z
    matrix[0, 3] = RAIL_BACK_Q_MM
    matrix[1, 3] = RAIL_VERTICAL_BOTTOM_MM
    matrix[2, 3] = -RAIL_ACROSS_RUN_REVEAL_EACH_SIDE_MM
    matrix[3, 3] = 1.0
    return matrix


def transformed(mesh: trimesh.Trimesh, matrix: np.ndarray) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    transform = np.asarray(matrix, dtype=float)
    if transform.shape != (4, 4) or not np.isfinite(transform).all():
        raise ValueError("A finite 4 x 4 transform is required")
    result = mesh.copy()
    result.apply_transform(transform)
    return _clean(result)


def mirror_across_support_run_center(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Reflect an installed candidate about the source core's Z=16 centre."""

    matrix = np.eye(4, dtype=float)
    matrix[2, 2] = -1.0
    matrix[2, 3] = support_geometry.SUPPORT_RUN_THICKNESS_MM
    return transformed(mesh, matrix)


def map_rail_to_support(rail: trimesh.Trimesh) -> trimesh.Trimesh:
    return transformed(rail, rail_to_support_transform())


def _positive_intersection_volume(
    first: trimesh.Trimesh, second: trimesh.Trimesh
) -> float:
    return cable_geometry.positive_intersection_volume(first, second)


def _missing_volume(body: trimesh.Trimesh, container: trimesh.Trimesh) -> float:
    """Return positive volume in body that is absent from container."""

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, module=r"trimesh\.triangles"
        )
        result = trimesh.boolean.difference(
            [body, container], engine="manifold", check_volume=True
        )
        if result is None or (isinstance(result, list) and not result):
            return 0.0
        if isinstance(result, list):
            result = trimesh.util.concatenate(result)
        if result.is_empty:
            return 0.0
        volume = abs(float(result.volume))
        return 0.0 if volume <= 1.0e-10 else volume


def _union(*meshes: trimesh.Trimesh) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("At least one mesh is required for union")
    result = trimesh.boolean.union(
        [mesh.copy() for mesh in meshes], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _build_additive_print_foot(source_core: trimesh.Trimesh) -> trimesh.Trimesh:
    """Extend one complete run-side profile so the broad face prints first.

    The centered rail is 2 mm wider than the 32 mm source support on each side.
    Without this additive foot, a run-side print would begin on the narrow rail
    reveal and introduce the much larger core profile at z=0.  A 2.4 mm copy of
    the source profile spans z=-2..0.4 instead, overlapping the unmodified core
    by 0.4 mm.  Later layers only retain or remove already-supported material.
    """

    foot = source_core.copy()
    source_min = float(foot.bounds[0, 2])
    source_thickness = float(foot.extents[2])
    target_thickness = PRINT_FOOT_SIDE_EXTENSION_MM + PRINT_FOOT_CORE_OVERLAP_MM
    foot.vertices[:, 2] = (
        (foot.vertices[:, 2] - source_min) * target_thickness / source_thickness
        - PRINT_FOOT_SIDE_EXTENSION_MM
    )
    return _clean(foot)


def _build_through_candidate() -> AttachmentCandidate:
    source = support_geometry.build_outer_feature_support_candidate()
    source_digest = support_geometry.mesh_fingerprint(source)
    rail = cable_geometry.build_two_socket_outer_bookend_rail_fit_coupon()
    mapped_rail = map_rail_to_support(rail)
    print_foot = _build_additive_print_foot(source)
    body = _union(source, mapped_rail, print_foot)
    if support_geometry.mesh_fingerprint(source) != source_digest:
        raise AssertionError("Attachment union mutated the caller's source support")
    return AttachmentCandidate(
        endpoint="through_outer",
        part_name=THROUGH_PART_NAME,
        source_core=source,
        mapped_rail=mapped_rail,
        additive_print_foot=print_foot,
        body=body,
        rail_to_support=rail_to_support_transform(),
        mirrored_from_through=False,
    )


def build_outer_bookend_attachment(
    endpoint: Endpoint = "through_outer",
) -> AttachmentCandidate:
    """Build one explicitly labelled additive endpoint candidate."""

    selected = _endpoint(endpoint)
    through = _build_through_candidate()
    if selected == "through_outer":
        return through
    return AttachmentCandidate(
        endpoint="return_outer",
        part_name=RETURN_PART_NAME,
        source_core=mirror_across_support_run_center(through.source_core),
        mapped_rail=mirror_across_support_run_center(through.mapped_rail),
        additive_print_foot=mirror_across_support_run_center(
            through.additive_print_foot
        ),
        body=mirror_across_support_run_center(through.body),
        rail_to_support=through.rail_to_support.copy(),
        mirrored_from_through=True,
    )


def build_through_outer_bookend_attachment_candidate() -> trimesh.Trimesh:
    return build_outer_bookend_attachment("through_outer").body


def build_return_outer_bookend_attachment_candidate() -> trimesh.Trimesh:
    return build_outer_bookend_attachment("return_outer").body


def build_all_attachment_candidates() -> dict[str, trimesh.Trimesh]:
    through = build_outer_bookend_attachment("through_outer")
    return_candidate = build_outer_bookend_attachment("return_outer")
    return {
        through.part_name: through.body,
        return_candidate.part_name: return_candidate.body,
    }


def core_containment_evidence(
    endpoint: Endpoint = "through_outer",
) -> CoreContainmentEvidence:
    candidate = build_outer_bookend_attachment(_endpoint(endpoint))
    before = support_geometry.mesh_fingerprint(candidate.source_core)
    source_volume = float(candidate.source_core.volume)
    rail_volume = float(candidate.mapped_rail.volume)
    foot_volume = float(candidate.additive_print_foot.volume)
    overlap = _positive_intersection_volume(
        candidate.source_core, candidate.mapped_rail
    )
    expected_overlap = (
        RAIL_TO_STRAP_OVERLAP_MM
        * cable_geometry.RAIL_HEIGHT_MM
        * support_geometry.SUPPORT_RUN_THICKNESS_MM
    )
    core_foot_union = _union(candidate.source_core, candidate.additive_print_foot)
    rail_overlap_with_base = _positive_intersection_volume(
        core_foot_union, candidate.mapped_rail
    )
    union_volume = float(candidate.body.volume)
    balance_error = abs(
        union_volume
        - (float(core_foot_union.volume) + rail_volume - rail_overlap_with_base)
    )
    missing = _missing_volume(candidate.source_core, candidate.body)
    after = support_geometry.mesh_fingerprint(candidate.source_core)
    preserved = bool(
        before == after
        and missing <= 1.0e-7
        and math.isclose(overlap, expected_overlap, abs_tol=0.01)
        and balance_error <= 0.01
    )
    return CoreContainmentEvidence(
        endpoint=candidate.endpoint,
        source_core_digest_before=before,
        source_core_digest_after=after,
        source_core_volume_mm3=source_volume,
        mapped_rail_volume_mm3=rail_volume,
        additive_print_foot_volume_mm3=foot_volume,
        positive_overlap_volume_mm3=overlap,
        expected_overlap_volume_mm3=expected_overlap,
        union_volume_mm3=union_volume,
        volume_balance_error_mm3=balance_error,
        missing_source_core_volume_mm3=missing,
        source_core_preserved=preserved,
        additive_only=preserved,
    )


def endpoint_semantics_evidence() -> EndpointSemanticsEvidence:
    through = build_outer_bookend_attachment("through_outer").body
    return_candidate = build_outer_bookend_attachment("return_outer").body
    mirrored_through = mirror_across_support_run_center(through)
    mirrored_return = mirror_across_support_run_center(return_candidate)
    digest = support_geometry.mesh_fingerprint
    self_symmetric = digest(through) == digest(mirrored_through)
    mirrored_match = digest(mirrored_through) == digest(return_candidate)
    reverse_match = digest(mirrored_return) == digest(through)
    return EndpointSemanticsEvidence(
        through_part_name=THROUGH_PART_NAME,
        return_part_name=RETURN_PART_NAME,
        same_candidate_sku_both_endpoints=(
            self_symmetric and SAME_CANDIDATE_SKU_BOTH_ENDPOINTS
        ),
        through_is_self_mirror_symmetric=self_symmetric,
        mirrored_through_matches_return=mirrored_match,
        return_mirrored_back_matches_through=reverse_match,
        reason=(
            "The inherited keyed socket extension is asymmetric across the run; "
            "publish deterministic through/return mirrors, not one same-SKU claim."
        ),
    )


def orient_additive_print_foot_on_plate(
    mesh: trimesh.Trimesh, *, endpoint: Endpoint
) -> trimesh.Trimesh:
    """Place the authored broad run-side print foot at saved Z zero.

    Return uses a proper 180-degree rotation about support Q (E and run both
    reverse), never a reflection that would silently change the handed SKU.
    """

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty attachment mesh is required")
    selected = _endpoint(endpoint)
    if selected == "through_outer":
        result = mesh.copy()
    else:
        rotation = np.eye(4, dtype=float)
        rotation[1, 1] = -1.0
        rotation[1, 3] = support_geometry.WALL_STRAP_TOTAL_DROP_MM
        rotation[2, 2] = -1.0
        rotation[2, 3] = support_geometry.SUPPORT_RUN_THICKNESS_MM
        if not math.isclose(np.linalg.det(rotation[:3, :3]), 1.0, abs_tol=1.0e-12):
            raise AssertionError("Return print transform must remain a proper rotation")
        result = transformed(mesh, rotation)
    result.apply_translation(-result.bounds[0])
    return _clean(result)


def build_saved_attachment_candidates() -> dict[str, trimesh.Trimesh]:
    installed = build_all_attachment_candidates()
    return {
        THROUGH_PART_NAME: orient_additive_print_foot_on_plate(
            installed[THROUGH_PART_NAME], endpoint="through_outer"
        ),
        RETURN_PART_NAME: orient_additive_print_foot_on_plate(
            installed[RETURN_PART_NAME], endpoint="return_outer"
        ),
    }


def _saved_layer_connectivity(
    mesh: trimesh.Trimesh, *, layer_height_mm: float = 0.2
) -> tuple[int, tuple[int, ...]]:
    """Require exactly one filled material component at every saved layer."""

    layer = float(layer_height_mm)
    if not math.isfinite(layer) or layer <= 0.0:
        raise ValueError("Layer height must be positive and finite")
    height = float(mesh.extents[2])
    ratio = height / layer
    nearest = round(ratio)
    count = (
        int(nearest)
        if math.isclose(ratio, nearest, rel_tol=0.0, abs_tol=1.0e-5)
        else int(math.ceil(ratio))
    )
    failed: list[int] = []
    minimum = float(mesh.bounds[0, 2])
    for index in range(count):
        bottom = index * layer
        deposited = min(layer, height - bottom)
        region = cable_geometry._section_material_region(
            mesh, minimum + bottom + 0.5 * deposited
        )
        if len(cable_geometry._filled_components(region)) != 1:
            failed.append(index)
    return count, tuple(failed)


def saved_attachment_print_evidence() -> tuple[SavedAttachmentPrintEvidence, ...]:
    saved = build_saved_attachment_candidates()
    endpoints: tuple[tuple[Endpoint, str], ...] = (
        ("through_outer", THROUGH_PART_NAME),
        ("return_outer", RETURN_PART_NAME),
    )
    evidence: list[SavedAttachmentPrintEvidence] = []
    for endpoint, name in endpoints:
        mesh = saved[name]
        islands = cable_geometry.saved_layer_island_report(mesh)
        count, disconnected = _saved_layer_connectivity(mesh)
        evidence.append(
            SavedAttachmentPrintEvidence(
                endpoint=endpoint,
                part_name=name,
                orientation_id="broad_run_side_additive_print_foot_on_plate",
                support_required=islands.support_required,
                support_classification=islands.support_classification,
                layer_connected=not disconnected,
                sampled_layer_count=count,
                disconnected_layer_indices=disconnected,
                first_layer_contact_area_mm2=islands.first_layer_contact_area_mm2,
                maximum_new_side_reveal_mm=RAIL_ACROSS_RUN_REVEAL_EACH_SIDE_MM,
                body_count=len(mesh.split(only_watertight=False)),
                watertight=bool(mesh.is_watertight),
                winding_consistent=bool(mesh.is_winding_consistent),
                envelope=support_geometry.print_envelope_with_margins(mesh),
            )
        )
    return tuple(evidence)


def _map_local_pose_to_endpoint(
    mesh: trimesh.Trimesh, local_pose: np.ndarray, endpoint: Endpoint
) -> trimesh.Trimesh:
    mapped = transformed(transformed(mesh, local_pose), rail_to_support_transform())
    return (
        mapped
        if endpoint == "through_outer"
        else mirror_across_support_run_center(mapped)
    )


def mapped_module_service_path(
    module: trimesh.Trimesh,
    *,
    endpoint: Endpoint,
    station_index: int,
    increment_mm: float = 1.0,
) -> MappedServicePath:
    """Map the exact rail-local install/removal path into one endpoint body."""

    selected = _endpoint(endpoint)
    path = cable_geometry.service_path_transforms(
        station_index, increment_mm=increment_mm
    )

    def map_all(transforms: tuple[np.ndarray, ...]) -> tuple[trimesh.Trimesh, ...]:
        return tuple(
            _map_local_pose_to_endpoint(module, matrix, selected)
            for matrix in transforms
        )

    return MappedServicePath(
        endpoint=selected,
        station_index=station_index,
        insertion_approach=map_all(path.insertion_approach),
        gravity_drop=map_all(path.gravity_drop),
        removal_lift=map_all(path.removal_lift),
        removal_outward=map_all(path.removal_outward),
        increment_mm=path.increment_mm,
    )


def attachment_collision_volume(
    attachment: trimesh.Trimesh, module_pose: trimesh.Trimesh
) -> float:
    return cable_geometry.positive_intersection_volume(attachment, module_pose)
