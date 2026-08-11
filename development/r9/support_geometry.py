#!/usr/bin/env python3
"""Deterministic, qualification-only geometry for the minimized R9 supports.

This module is intentionally narrower than a production shelf generator.  It
authors five physical studies:

* a shortened outer-feature/bookend support;
* a smooth compact support;
* one concealed inside-corner half;
* a two-piece modular rear-ledger joint coupon; and
* a two-piece staggered front-beam splice coupon.

It also provides a minimal hidden-corner dry-fit set.  The set has explicitly
handed complementary-miter halves, a non-rated under-shelf shear-key coupon, a
cosmetic-cover coupon, and a flat 90-degree tabletop reference.  That fixture
can reveal basic interference at a nominal square corner; it cannot represent
the still-unmeasured field angle, wall bow, framing, or fastener access.

The support mesh axes retain the R8 convention: ``q`` (mesh X) projects from
the wall, ``e`` (mesh Y) is installed elevation, and mesh Z is across the run.
The saved orientation therefore places a broad run-side face on the build
plate.  Coupon axes are conventional X along the member, Y through its depth,
and Z through its height.

No builder emits a wall-fastener bore, printed anchor, load rating, slicer
profile, or production authorization.  Every printed study is PETG-only and
must remain a qualification article until physical tests are completed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Iterable, Sequence

import numpy as np
from shapely.geometry import Polygon
import trimesh

try:  # Support both package imports and the repository's direct test runner.
    from . import design_math
except ImportError:  # pragma: no cover - exercised by direct unittest discovery
    import design_math  # type: ignore[no-redef]


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
PRINTED_MATERIAL = "PETG"
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
WALL_BORES_EMITTED = False

A1_MINI_BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
GEOMETRY_EPSILON = 1.0e-7

# R9 inherits the R8 shelf projection, installed strap drop, and 32 mm
# qualification-corbel thickness.  The visible bodies are the deliberately
# shortened R9 dimensions read from the current fail-closed configuration.
_CONFIG = design_math.load_config()
design_math.validate_config(_CONFIG)
_TOPOLOGY = _CONFIG["support_topology"]

SHELF_PROJECTION_MM = float(_TOPOLOGY["shelf_projection_mm"])
SUPPORT_RUN_THICKNESS_MM = float(
    _TOPOLOGY["support_body_thickness_across_run_mm"]
)
WALL_STRAP_TOTAL_DROP_MM = float(
    _TOPOLOGY["wall_hugging_strap_total_drop_mm"]
)
WALL_STRAP_PROJECTION_MM = float(
    _TOPOLOGY["wall_hugging_strap_projection_mm"]
)
OUTER_FEATURE_VISIBLE_DROP_MM = float(
    _TOPOLOGY["outer_feature_visible_drop_mm"]
)
COMPACT_VISIBLE_DROP_MM = float(_TOPOLOGY["compact_arch_visible_drop_mm"])

# The R8 top chord and front nose are retained as geometric reference datums,
# not as evidence that a shortened support has equivalent capacity.
TOP_CHORD_MM = 16.0
FRONT_NOSE_MM = 32.0
ARCH_WEB_MM = 16.0

# A corner half is deliberately narrower and shorter than an ordinary visible
# support.  Two independently qualified halves are intended at the two walls;
# this single candidate does not author the final corner load path.
CONCEALED_CORNER_VISIBLE_DROP_MM = 50.8
CONCEALED_CORNER_HALF_THICKNESS_MM = SUPPORT_RUN_THICKNESS_MM / 2.0

NOMINAL_JOINT_CLEARANCE_PER_FACE_MM = 0.4

REAR_LEDGER_BODY_LENGTH_MM = 60.0
REAR_LEDGER_PROJECTION_MM = WALL_STRAP_PROJECTION_MM
REAR_LEDGER_HEIGHT_MM = 30.0
REAR_LEDGER_TONGUE_LENGTH_MM = 12.0
REAR_LEDGER_TONGUE_DEPTH_MM = 8.0
REAR_LEDGER_TONGUE_HEIGHT_MM = 18.0

FRONT_BEAM_BODY_LENGTH_MM = 60.0
FRONT_BEAM_SPLICE_LENGTH_MM = 16.0
FRONT_BEAM_DEPTH_MM = 16.0
FRONT_BEAM_HEIGHT_MM = 30.0

CORNER_MITER_ANGLE_DEG = 45.0
SHEAR_KEY_OUTER_LEG_MM = 48.0
SHEAR_KEY_ARM_WIDTH_MM = 12.0
SHEAR_KEY_THICKNESS_MM = 4.0
COSMETIC_COVER_OUTER_LEG_MM = 64.0
COSMETIC_COVER_ARM_WIDTH_MM = 12.0
COSMETIC_COVER_THICKNESS_MM = 1.6
TABLETOP_FIXTURE_OUTER_LEG_MM = 160.0
TABLETOP_FIXTURE_ARM_WIDTH_MM = 20.0
TABLETOP_FIXTURE_THICKNESS_MM = 4.0


def _require_exact_reference(value: float, expected: float, name: str) -> None:
    if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError(f"R9 {name} drifted from its exact reference: {value}")


_require_exact_reference(SHELF_PROJECTION_MM, 152.4, "shelf projection")
_require_exact_reference(SUPPORT_RUN_THICKNESS_MM, 32.0, "support thickness")
_require_exact_reference(WALL_STRAP_TOTAL_DROP_MM, 160.0, "wall strap drop")
_require_exact_reference(WALL_STRAP_PROJECTION_MM, 16.0, "wall strap projection")
_require_exact_reference(OUTER_FEATURE_VISIBLE_DROP_MM, 120.65, "bookend drop")
_require_exact_reference(COMPACT_VISIBLE_DROP_MM, 76.2, "compact drop")


@dataclass(frozen=True)
class PrintEnvelope:
    """A saved-orientation part envelope including process margins."""

    raw_part_mm: tuple[float, float, float]
    required_build_volume_mm: tuple[float, float, float]
    available_build_volume_mm: tuple[float, float, float]
    brim_mm: float
    brim_object_gap_mm: float
    reserve_per_bed_edge_mm: float
    fits: bool


@dataclass(frozen=True)
class CouponPair:
    """Two separate printable parts and their deterministic fit-study pose."""

    name: str
    part_a_name: str
    part_b_name: str
    part_a: trimesh.Trimesh
    part_b: trimesh.Trimesh
    part_b_assembly_translation_mm: tuple[float, float, float]
    clearance_per_face_mm: float

    def assembled_parts(self) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
        """Return fresh copies in the nominal non-fused qualification pose."""

        first = part_copy(self.part_a)
        second = part_copy(self.part_b)
        second.apply_translation(self.part_b_assembly_translation_mm)
        return _clean(first), _clean(second)


@dataclass(frozen=True)
class HiddenCornerDryFitSet:
    """Separate nominal-90-degree corner studies; never an installed release."""

    through_half_name: str
    return_half_name: str
    shear_key_name: str
    cosmetic_cover_name: str
    tabletop_fixture_name: str
    through_half: trimesh.Trimesh
    return_half: trimesh.Trimesh
    shear_key: trimesh.Trimesh
    cosmetic_cover: trimesh.Trimesh
    tabletop_fixture: trimesh.Trimesh
    nominal_fixture_angle_deg: float
    field_angle_verified: bool
    corner_load_path_authored: bool


@dataclass(frozen=True)
class SavedPrintOrientationEvidence:
    """Analytic support rationale for one deterministic saved mesh."""

    part_name: str
    orientation_id: str
    support_required: bool
    analytic_layer_rule: str
    body_count: int
    watertight: bool
    winding_consistent: bool
    envelope: PrintEnvelope


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return result


def _nonnegative(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite nonnegative number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return result


def _joint_clearance(value: float) -> float:
    clearance = _positive(value, "joint clearance per face")
    if clearance > 1.0:
        raise ValueError("Qualification clearance must not exceed 1.0 mm per face")
    return clearance


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("Geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Geometry operation produced non-finite coordinates")
    return mesh


def part_copy(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Return a cleaned copy without mutating the caller's qualification part."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    return _clean(mesh.copy())


def _box(
    size: tuple[float, float, float],
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> trimesh.Trimesh:
    extents = np.asarray(
        [_positive(value, "box dimension") for value in size], dtype=float
    )
    start = np.asarray(origin, dtype=float)
    if start.shape != (3,) or not np.isfinite(start).all():
        raise ValueError("Box origin must contain three finite coordinates")
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(start + extents / 2.0)
    return _clean(mesh)


def _union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("At least one mesh is required for a union")
    result = trimesh.boolean.union(
        [part_copy(mesh) for mesh in meshes], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _difference(body: trimesh.Trimesh, cutters: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not cutters:
        return part_copy(body)
    result = trimesh.boolean.difference(
        [part_copy(body), *[part_copy(cutter) for cutter in cutters]],
        engine="manifold",
        check_volume=True,
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _support_profile(visible_drop_mm: float) -> Polygon:
    """Return one shortened D-window profile with an uninterrupted wall strap."""

    visible_drop = _positive(visible_drop_mm, "visible support drop")
    if visible_drop >= WALL_STRAP_TOTAL_DROP_MM - ARCH_WEB_MM:
        raise ValueError("Visible support drop leaves no lower arch root")
    body_bottom = WALL_STRAP_TOTAL_DROP_MM - visible_drop
    front_underside = WALL_STRAP_TOTAL_DROP_MM - FRONT_NOSE_MM
    top_inner = WALL_STRAP_TOTAL_DROP_MM - TOP_CHORD_MM
    if body_bottom >= front_underside:
        raise ValueError("Visible support body is too short for the R9 arch study")

    # The outer shell retains the exact R8 projection and front nose.  Its
    # lower wall root is lifted to the requested R9 visible drop while the
    # separate 16 mm wall-hugging strap still runs the full 160 mm.
    shell: tuple[tuple[float, float], ...] = (
        (0.0, 0.0),
        (WALL_STRAP_PROJECTION_MM, 0.0),
        (WALL_STRAP_PROJECTION_MM, body_bottom),
        (2.0 * WALL_STRAP_PROJECTION_MM, body_bottom),
        (SHELF_PROJECTION_MM, front_underside),
        (SHELF_PROJECTION_MM, WALL_STRAP_TOTAL_DROP_MM),
        (0.0, WALL_STRAP_TOTAL_DROP_MM),
    )
    # One deliberate D-window leaves exact 16 mm wall/top/diagonal reference
    # webs.  It never reaches q < 16 mm, so it cannot become a wall bore.
    window: tuple[tuple[float, float], ...] = (
        (WALL_STRAP_PROJECTION_MM, top_inner),
        (WALL_STRAP_PROJECTION_MM, body_bottom + ARCH_WEB_MM),
        (SHELF_PROJECTION_MM - WALL_STRAP_PROJECTION_MM, top_inner),
    )
    profile = Polygon(shell=shell, holes=(window,))
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("R9 support profile is invalid")
    return profile


def _support_mesh(visible_drop_mm: float, run_thickness_mm: float) -> trimesh.Trimesh:
    mesh = trimesh.creation.extrude_polygon(
        _support_profile(visible_drop_mm),
        height=_positive(run_thickness_mm, "support run thickness"),
        engine="earcut",
    )
    return _clean(mesh)


def _qz_prism(
    points_qz: Sequence[tuple[float, float]],
    *,
    elevation_start_mm: float,
    elevation_height_mm: float,
) -> trimesh.Trimesh:
    """Extrude a q/z polygon through elevation and relabel it q/e/z."""

    profile = Polygon(points_qz)
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("Q/Z cutter profile is invalid")
    source = trimesh.creation.extrude_polygon(
        profile,
        height=_positive(elevation_height_mm, "elevation prism height"),
        engine="earcut",
    )
    # extrude_polygon emits (q, z, extrusion); the support convention is
    # (q, elevation, across-run z).  fix_normals handles the odd axis swap.
    source.vertices = np.asarray(source.vertices, dtype=float)[:, (0, 2, 1)]
    source.vertices[:, 1] += float(elevation_start_mm)
    return _clean(source)


def _mitered_corner_half(*, hand: str) -> trimesh.Trimesh:
    """Trim one support half so two labelled parts meet without corner overlap."""

    if hand not in ("through", "return"):
        raise ValueError("Corner hand must be 'through' or 'return'")
    core = build_concealed_corner_half_candidate()
    width = CONCEALED_CORNER_HALF_THICKNESS_MM
    # In the tabletop pose, through retains q >= z.  Return retains the
    # complementary q >= width-z and is installed with its run coordinate
    # reversed.  The pair therefore meets on one 45-degree plane instead of
    # occupying the same 16 x 16 mm corner prism.
    if hand == "through":
        removed_qz = ((0.0, 0.0), (0.0, width), (width, width))
    else:
        removed_qz = ((0.0, 0.0), (width, 0.0), (0.0, width))
    cutter = _qz_prism(
        removed_qz,
        elevation_start_mm=-1.0,
        elevation_height_mm=WALL_STRAP_TOTAL_DROP_MM + 2.0,
    )
    return _difference(core, (cutter,))


def build_outer_feature_support_candidate() -> trimesh.Trimesh:
    """Build the 120.65 mm visible-drop outer/bookend qualification core.

    This smooth structural study deliberately omits cable-rail features.  A
    later additive wrapper may be qualified separately; no receiver cavity is
    allowed to subtract from this support or its wall strap.
    """

    return _support_mesh(OUTER_FEATURE_VISIBLE_DROP_MM, SUPPORT_RUN_THICKNESS_MM)


def build_shortened_outer_bookend_support() -> trimesh.Trimesh:
    """Descriptive alias for :func:`build_outer_feature_support_candidate`."""

    return build_outer_feature_support_candidate()


def build_compact_support_candidate() -> trimesh.Trimesh:
    """Build the smooth 76.2 mm visible-drop compact qualification support."""

    return _support_mesh(COMPACT_VISIBLE_DROP_MM, SUPPORT_RUN_THICKNESS_MM)


def build_concealed_corner_half_candidate() -> trimesh.Trimesh:
    """Build one 16 mm-wide, 50.8 mm visible-drop concealed corner half."""

    return _support_mesh(
        CONCEALED_CORNER_VISIBLE_DROP_MM,
        CONCEALED_CORNER_HALF_THICKNESS_MM,
    )


def build_through_hidden_corner_half_candidate() -> trimesh.Trimesh:
    """Build the labelled through-wall half with its authored 45-degree miter."""

    return _mitered_corner_half(hand="through")


def build_return_hidden_corner_half_candidate() -> trimesh.Trimesh:
    """Build the labelled return-wall half; no user-side mirroring is required."""

    return _mitered_corner_half(hand="return")


def _flat_l_coupon(outer_leg_mm: float, arm_width_mm: float, thickness_mm: float) -> trimesh.Trimesh:
    outer = _positive(outer_leg_mm, "L-coupon outer leg")
    arm = _positive(arm_width_mm, "L-coupon arm width")
    thickness = _positive(thickness_mm, "L-coupon thickness")
    if arm >= outer:
        raise ValueError("L-coupon arm must be narrower than its outer leg")
    profile = Polygon(
        (
            (0.0, 0.0),
            (outer, 0.0),
            (outer, arm),
            (arm, arm),
            (arm, outer),
            (0.0, outer),
        )
    )
    if not profile.is_valid or profile.area <= 0.0:
        raise ValueError("L-coupon profile is invalid")
    return _clean(
        trimesh.creation.extrude_polygon(profile, height=thickness, engine="earcut")
    )


def build_under_shelf_shear_key_coupon() -> trimesh.Trimesh:
    """Build a flat L-key coupon for nominal corner registration only.

    The coupon has no fastener bores and receives no structural credit.  Its
    purpose is limited to checking whether one simple under-shelf bridge can be
    handled around the explicitly handed half geometry.
    """

    return _flat_l_coupon(
        SHEAR_KEY_OUTER_LEG_MM,
        SHEAR_KEY_ARM_WIDTH_MM,
        SHEAR_KEY_THICKNESS_MM,
    )


def build_cosmetic_corner_cover_coupon() -> trimesh.Trimesh:
    """Build a thin flat L-cover coupon for seam/reveal visualization."""

    return _flat_l_coupon(
        COSMETIC_COVER_OUTER_LEG_MM,
        COSMETIC_COVER_ARM_WIDTH_MM,
        COSMETIC_COVER_THICKNESS_MM,
    )


def build_90_degree_tabletop_angle_fixture() -> trimesh.Trimesh:
    """Build a flat 160 mm square-reference L that fits the A1 mini.

    The fixture's CAD angle is exactly 90 degrees.  It is a tabletop reference,
    not a measurement of the closet and not a drilling or installation jig.
    """

    return _flat_l_coupon(
        TABLETOP_FIXTURE_OUTER_LEG_MM,
        TABLETOP_FIXTURE_ARM_WIDTH_MM,
        TABLETOP_FIXTURE_THICKNESS_MM,
    )


def build_hidden_corner_dry_fit_set() -> HiddenCornerDryFitSet:
    """Return the complete, explicitly non-structural nominal corner study."""

    return HiddenCornerDryFitSet(
        through_half_name="r9_through_hidden_corner_half",
        return_half_name="r9_return_hidden_corner_half",
        shear_key_name="r9_under_shelf_shear_key_coupon",
        cosmetic_cover_name="r9_cosmetic_corner_cover_coupon",
        tabletop_fixture_name="r9_90_degree_tabletop_angle_fixture",
        through_half=build_through_hidden_corner_half_candidate(),
        return_half=build_return_hidden_corner_half_candidate(),
        shear_key=build_under_shelf_shear_key_coupon(),
        cosmetic_cover=build_cosmetic_corner_cover_coupon(),
        tabletop_fixture=build_90_degree_tabletop_angle_fixture(),
        nominal_fixture_angle_deg=90.0,
        field_angle_verified=False,
        corner_load_path_authored=False,
    )


def _rear_ledger_male() -> trimesh.Trimesh:
    tongue_y = (REAR_LEDGER_PROJECTION_MM - REAR_LEDGER_TONGUE_DEPTH_MM) / 2.0
    tongue_z = (REAR_LEDGER_HEIGHT_MM - REAR_LEDGER_TONGUE_HEIGHT_MM) / 2.0
    return _union(
        (
            _box(
                (
                    REAR_LEDGER_BODY_LENGTH_MM,
                    REAR_LEDGER_PROJECTION_MM,
                    REAR_LEDGER_HEIGHT_MM,
                )
            ),
            _box(
                (
                    REAR_LEDGER_TONGUE_LENGTH_MM,
                    REAR_LEDGER_TONGUE_DEPTH_MM,
                    REAR_LEDGER_TONGUE_HEIGHT_MM,
                ),
                (REAR_LEDGER_BODY_LENGTH_MM, tongue_y, tongue_z),
            ),
        )
    )


def _rear_ledger_female(clearance_per_face_mm: float) -> trimesh.Trimesh:
    clearance = _joint_clearance(clearance_per_face_mm)
    tongue_y = (REAR_LEDGER_PROJECTION_MM - REAR_LEDGER_TONGUE_DEPTH_MM) / 2.0
    tongue_z = (REAR_LEDGER_HEIGHT_MM - REAR_LEDGER_TONGUE_HEIGHT_MM) / 2.0
    body = _box(
        (
            REAR_LEDGER_BODY_LENGTH_MM,
            REAR_LEDGER_PROJECTION_MM,
            REAR_LEDGER_HEIGHT_MM,
        )
    )
    # The cutter opens through only the module end.  It is an intentional
    # joint socket, not a wall-fastener bore.
    cutter = _box(
        (
            REAR_LEDGER_TONGUE_LENGTH_MM + clearance + 1.0,
            REAR_LEDGER_TONGUE_DEPTH_MM + 2.0 * clearance,
            REAR_LEDGER_TONGUE_HEIGHT_MM + 2.0 * clearance,
        ),
        (
            -1.0,
            tongue_y - clearance,
            tongue_z - clearance,
        ),
    )
    return _difference(body, (cutter,))


def build_modular_rear_ledger_joint_coupon(
    *, clearance_per_face_mm: float = NOMINAL_JOINT_CLEARANCE_PER_FACE_MM,
) -> CouponPair:
    """Build a male/female rear-ledger fit coupon with a blind-end socket."""

    clearance = _joint_clearance(clearance_per_face_mm)
    return CouponPair(
        name="r9_modular_rear_ledger_joint_coupon",
        part_a_name="r9_rear_ledger_male_coupon",
        part_b_name="r9_rear_ledger_female_coupon",
        part_a=_rear_ledger_male(),
        part_b=_rear_ledger_female(clearance),
        part_b_assembly_translation_mm=(REAR_LEDGER_BODY_LENGTH_MM, 0.0, 0.0),
        clearance_per_face_mm=clearance,
    )


def build_rear_ledger_joint_coupon(
    *, clearance_per_face_mm: float = NOMINAL_JOINT_CLEARANCE_PER_FACE_MM,
) -> CouponPair:
    """Short alias for :func:`build_modular_rear_ledger_joint_coupon`."""

    return build_modular_rear_ledger_joint_coupon(
        clearance_per_face_mm=clearance_per_face_mm
    )


def build_staggered_front_beam_splice_coupon(
    *, clearance_per_face_mm: float = NOMINAL_JOINT_CLEARANCE_PER_FACE_MM,
) -> CouponPair:
    """Build complementary lower/upper lap coupons for the front beam.

    The two steps are staggered by 16 mm along the member.  In the nominal
    assembly pose, the configured clearance exists both between the horizontal
    lap faces and at each axial shoulder.  The pair remains two separate parts.
    """

    clearance = _joint_clearance(clearance_per_face_mm)
    middle = FRONT_BEAM_HEIGHT_MM / 2.0
    lower_tongue_height = middle - clearance
    upper_tongue_start = middle + clearance
    upper_tongue_height = FRONT_BEAM_HEIGHT_MM - upper_tongue_start

    part_a = _union(
        (
            _box(
                (
                    FRONT_BEAM_BODY_LENGTH_MM,
                    FRONT_BEAM_DEPTH_MM,
                    FRONT_BEAM_HEIGHT_MM,
                )
            ),
            _box(
                (
                    FRONT_BEAM_SPLICE_LENGTH_MM,
                    FRONT_BEAM_DEPTH_MM,
                    lower_tongue_height,
                ),
                (FRONT_BEAM_BODY_LENGTH_MM, 0.0, 0.0),
            ),
        )
    )
    part_b = _union(
        (
            _box(
                (
                    FRONT_BEAM_BODY_LENGTH_MM,
                    FRONT_BEAM_DEPTH_MM,
                    FRONT_BEAM_HEIGHT_MM,
                ),
                (FRONT_BEAM_SPLICE_LENGTH_MM, 0.0, 0.0),
            ),
            _box(
                (
                    FRONT_BEAM_SPLICE_LENGTH_MM,
                    FRONT_BEAM_DEPTH_MM,
                    upper_tongue_height,
                ),
                (0.0, 0.0, upper_tongue_start),
            ),
        )
    )
    return CouponPair(
        name="r9_staggered_front_beam_splice_coupon",
        part_a_name="r9_front_beam_lower_lap_coupon",
        part_b_name="r9_front_beam_upper_lap_coupon",
        part_a=part_a,
        part_b=part_b,
        part_b_assembly_translation_mm=(
            FRONT_BEAM_BODY_LENGTH_MM + clearance,
            0.0,
            0.0,
        ),
        clearance_per_face_mm=clearance,
    )


def build_front_beam_splice_coupon(
    *, clearance_per_face_mm: float = NOMINAL_JOINT_CLEARANCE_PER_FACE_MM,
) -> CouponPair:
    """Short alias for :func:`build_staggered_front_beam_splice_coupon`."""

    return build_staggered_front_beam_splice_coupon(
        clearance_per_face_mm=clearance_per_face_mm
    )


def build_all_qualification_parts() -> dict[str, trimesh.Trimesh]:
    """Return every individual R9 mesh in stable, generator-friendly order."""

    ledger = build_modular_rear_ledger_joint_coupon()
    beam = build_staggered_front_beam_splice_coupon()
    corner = build_hidden_corner_dry_fit_set()
    return {
        "r9_shortened_outer_bookend_support": build_outer_feature_support_candidate(),
        "r9_compact_support": build_compact_support_candidate(),
        # Preserve the untrimmed seed as a control; the two following meshes
        # are the only explicitly handed dry-fit parts.
        "r9_concealed_corner_half_control": build_concealed_corner_half_candidate(),
        corner.through_half_name: corner.through_half,
        corner.return_half_name: corner.return_half,
        corner.shear_key_name: corner.shear_key,
        corner.cosmetic_cover_name: corner.cosmetic_cover,
        corner.tabletop_fixture_name: corner.tabletop_fixture,
        ledger.part_a_name: ledger.part_a,
        ledger.part_b_name: ledger.part_b,
        beam.part_a_name: beam.part_a,
        beam.part_b_name: beam.part_b,
    }


def print_envelope_with_margins(
    mesh: trimesh.Trimesh,
    *,
    brim_mm: float = 5.0,
    brim_object_gap_mm: float = 0.1,
    reserve_per_bed_edge_mm: float = 2.0,
    available_build_volume_mm: tuple[float, float, float] = A1_MINI_BUILD_VOLUME_MM,
) -> PrintEnvelope:
    """Measure one saved-orientation part against the 180 mm A1 mini volume."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    brim = _nonnegative(brim_mm, "brim")
    gap = _nonnegative(brim_object_gap_mm, "brim-object gap")
    reserve = _nonnegative(reserve_per_bed_edge_mm, "bed-edge reserve")
    available = tuple(
        _positive(value, "available build-volume dimension")
        for value in available_build_volume_mm
    )
    if len(available) != 3:
        raise ValueError("Available build volume must have three dimensions")
    raw = tuple(float(value) for value in mesh.extents)
    bed_margin = 2.0 * (brim + gap + reserve)
    required = (raw[0] + bed_margin, raw[1] + bed_margin, raw[2])
    return PrintEnvelope(
        raw_part_mm=raw,
        required_build_volume_mm=required,
        available_build_volume_mm=available,  # type: ignore[arg-type]
        brim_mm=brim,
        brim_object_gap_mm=gap,
        reserve_per_bed_edge_mm=reserve,
        fits=all(
            needed <= allowed + GEOMETRY_EPSILON
            for needed, allowed in zip(required, available)
        ),
    )


def _normalize_positive(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    result = part_copy(mesh)
    result.apply_translation(-result.bounds[0])
    return _clean(result)


def orient_broad_face_on_plate(
    mesh: trimesh.Trimesh, *, face: str = "minimum_z"
) -> trimesh.Trimesh:
    """Place a support's selected broad run-side face at build Z zero."""

    if face not in ("minimum_z", "maximum_z"):
        raise ValueError("Broad-face selector must be minimum_z or maximum_z")
    result = part_copy(mesh)
    if face == "maximum_z":
        maximum = float(result.bounds[1, 2])
        result.vertices[:, 2] = maximum - result.vertices[:, 2]
    return _normalize_positive(result)


def orient_member_end_on_plate(
    mesh: trimesh.Trimesh, *, end: str = "minimum_x"
) -> trimesh.Trimesh:
    """Map a member's selected X end to the plate and X length to build Z."""

    if end not in ("minimum_x", "maximum_x"):
        raise ValueError("Member-end selector must be minimum_x or maximum_x")
    result = part_copy(mesh)
    old = np.asarray(result.vertices, dtype=float).copy()
    if end == "maximum_x":
        old[:, 0] = float(result.bounds[1, 0]) - old[:, 0]
    # saved X/Y/Z = installed Y/Z/X.  This is a proper cyclic permutation.
    result.vertices = old[:, (1, 2, 0)]
    return _normalize_positive(result)


def build_saved_qualification_parts() -> dict[str, trimesh.Trimesh]:
    """Return every part in its deterministic, analytically support-free pose."""

    installed = build_all_qualification_parts()
    broad_min = {
        "r9_shortened_outer_bookend_support",
        "r9_compact_support",
        "r9_concealed_corner_half_control",
        "r9_through_hidden_corner_half",
    }
    broad_max = {"r9_return_hidden_corner_half"}
    end_min = {
        "r9_rear_ledger_male_coupon",
        "r9_front_beam_lower_lap_coupon",
    }
    end_max = {
        "r9_rear_ledger_female_coupon",
        "r9_front_beam_upper_lap_coupon",
    }
    saved: dict[str, trimesh.Trimesh] = {}
    for name, mesh in installed.items():
        if name in broad_min:
            saved[name] = orient_broad_face_on_plate(mesh, face="minimum_z")
        elif name in broad_max:
            saved[name] = orient_broad_face_on_plate(mesh, face="maximum_z")
        elif name in end_min:
            saved[name] = orient_member_end_on_plate(mesh, end="minimum_x")
        elif name in end_max:
            saved[name] = orient_member_end_on_plate(mesh, end="maximum_x")
        else:
            # Flat L coupons and the tabletop reference are authored plate-down.
            saved[name] = _normalize_positive(mesh)
    if set(saved) != set(installed):
        raise AssertionError("Saved-orientation routing dropped an R9 part")
    return saved


def saved_print_orientation_evidence() -> tuple[SavedPrintOrientationEvidence, ...]:
    """Publish generator-facing support rationale for every saved mesh.

    The statements are analytic consequences of the authored monotone build
    directions.  They are software evidence, not a substitute for first-article
    PETG prints or slicer preview review.
    """

    saved = build_saved_qualification_parts()
    orientation_ids = {
        "r9_shortened_outer_bookend_support": "broad_min_z_constant_profile",
        "r9_compact_support": "broad_min_z_constant_profile",
        "r9_concealed_corner_half_control": "broad_min_z_constant_profile",
        "r9_through_hidden_corner_half": "broad_min_z_miter_only_subtracts",
        "r9_return_hidden_corner_half": "broad_max_z_miter_only_subtracts",
        "r9_rear_ledger_male_coupon": "minimum_member_end_on_plate",
        "r9_rear_ledger_female_coupon": "closed_maximum_member_end_on_plate",
        "r9_front_beam_lower_lap_coupon": "minimum_member_end_on_plate",
        "r9_front_beam_upper_lap_coupon": "maximum_member_end_on_plate",
        "r9_under_shelf_shear_key_coupon": "flat_authored_face_on_plate",
        "r9_cosmetic_corner_cover_coupon": "flat_authored_face_on_plate",
        "r9_90_degree_tabletop_angle_fixture": "flat_authored_face_on_plate",
    }
    rules = {
        "broad_min_z_constant_profile": "every layer repeats one connected D-window profile",
        "broad_min_z_miter_only_subtracts": "later layers only remove the 45-degree miter field",
        "broad_max_z_miter_only_subtracts": "reversed broad-face build makes later layers only remove the miter field",
        "minimum_member_end_on_plate": "full member end precedes the smaller tongue or lap section",
        "closed_maximum_member_end_on_plate": "closed socket end precedes the cavity opening",
        "maximum_member_end_on_plate": "full member end precedes the smaller upper-lap section",
        "flat_authored_face_on_plate": "constant connected L profile repeats through thickness",
    }
    if set(orientation_ids) != set(saved):
        raise AssertionError("Saved orientation evidence is incomplete")
    evidence: list[SavedPrintOrientationEvidence] = []
    for name, mesh in saved.items():
        orientation_id = orientation_ids[name]
        evidence.append(
            SavedPrintOrientationEvidence(
                part_name=name,
                orientation_id=orientation_id,
                support_required=False,
                analytic_layer_rule=rules[orientation_id],
                body_count=len(mesh.split(only_watertight=False)),
                watertight=bool(mesh.is_watertight),
                winding_consistent=bool(mesh.is_winding_consistent),
                envelope=print_envelope_with_margins(mesh),
            )
        )
    return tuple(evidence)


def wall_strap_is_uninterrupted(mesh: trimesh.Trimesh) -> bool:
    """Prove the full-drop strap section is one solid rectangle.

    The probe plane lies halfway through the 16 mm wall projection.  A screw
    bore, cable receiver, or other subtraction through the wall strap would
    introduce another loop or shorten the exact 160 mm by run-thickness span.
    """

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        return False
    section = mesh.section(
        plane_origin=(WALL_STRAP_PROJECTION_MM / 2.0, 0.0, 0.0),
        plane_normal=(1.0, 0.0, 0.0),
    )
    if section is None or len(section.discrete) != 1:
        return False
    points = np.asarray(section.discrete[0], dtype=float)
    if len(points) < 4 or np.linalg.norm(points[0] - points[-1]) > 1.0e-6:
        return False
    spans = np.ptp(points, axis=0)
    expected_thickness = float(mesh.extents[2])
    return bool(
        math.isclose(float(spans[0]), 0.0, abs_tol=1.0e-6)
        and math.isclose(
            float(spans[1]), WALL_STRAP_TOTAL_DROP_MM, abs_tol=1.0e-6
        )
        and math.isclose(float(spans[2]), expected_thickness, abs_tol=1.0e-6)
    )


def mesh_fingerprint(mesh: trimesh.Trimesh) -> str:
    """Hash canonical rounded triangle coordinates for determinism tests."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    triangles = np.round(np.asarray(mesh.triangles, dtype=np.float64), 9)
    rows: list[tuple[float, ...]] = []
    for triangle in triangles:
        points = sorted(tuple(float(value) for value in point) for point in triangle)
        rows.append(tuple(value for point in points for value in point))
    rows.sort()
    payload = np.asarray(rows, dtype="<f8").tobytes(order="C")
    header = f"r9-qualification-triangles-v1\0{len(rows)}\0".encode("ascii")
    return hashlib.sha256(header + payload).hexdigest()


def projecting_body_bottom_mm(mesh: trimesh.Trimesh) -> float:
    """Return the lowest elevation that projects beyond the thin wall strap."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    vertices = np.asarray(mesh.vertices, dtype=float)
    projected = vertices[vertices[:, 0] > WALL_STRAP_PROJECTION_MM + 1.0e-6]
    if len(projected) == 0:
        raise ValueError("Mesh contains no body beyond the wall strap")
    return float(np.min(projected[:, 1]))


def individual_meshes(coupons: Iterable[CouponPair]) -> tuple[trimesh.Trimesh, ...]:
    """Flatten coupon pairs without joining their intentionally separate parts."""

    result: list[trimesh.Trimesh] = []
    for coupon in coupons:
        if not isinstance(coupon, CouponPair):
            raise ValueError("Expected a CouponPair")
        result.extend((coupon.part_a, coupon.part_b))
    return tuple(result)
