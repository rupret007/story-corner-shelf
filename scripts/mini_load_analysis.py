#!/usr/bin/env python3
"""Conservative, analysis-only load study for the Story Corner Mini (all-PETG).

Derives section properties from config.mini.json / structural_mini parameters and
generated/mini/validation.json deck layout. Does not create a safe-working load;
physical proof per docs/LOAD_TEST.md is required before changing SAFETY.md.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MINI_CONFIG_PATH = ROOT / "config.mini.json"
MINI_VALIDATION_PATH = ROOT / "generated" / "mini" / "validation.json"

# ---------------------------------------------------------------------------
# Published PETG / FDM allowables (see docs/LOAD_ANALYSIS.md for citations)
# ---------------------------------------------------------------------------

# ASTM D638-class molded PETG tensile strength (typical datasheet range).
PETG_MOLDED_TENSILE_STRENGTH_MPA = 50.0

# Reported FDM interlayer (Z) tensile strength for PETG, ~25–40% of in-plane bulk
# in peer-reviewed print studies; use a low literature-side value before safety factor.
PETG_FDM_INTERLAYER_TENSILE_STRENGTH_MPA = 15.0

# Large factor on layer adhesion: FDM Z strength varies with temperature, speed,
# moisture, and operator; delamination at re-entrant bracket roots is not modeled
# in FE here — treat interlayer allowables with an explicit factor (documented in docs).
LAYER_ADHESION_SAFETY_FACTOR = 4.0

# General material uncertainty on bulk in-plane bending (print porosity, notch at bore).
BULK_MATERIAL_SAFETY_FACTOR = 3.0

PETG_FDM_YOUNGS_MODULUS_MPA = 1800.0

# Connection / wood literature-side conservative anchors (not GRK ESR values on PETG).
SCREW_WITHDRAWAL_SAFETY_FACTOR = 2.5
PETG_BEARING_SAFETY_FACTOR = 3.0

# GRK RSS 1/4 in candidate from config (geometric only in repo).
SCREW_DIAMETER_IN = 0.25
SCREW_LENGTH_IN = 3.5
WASHER_OD_MM = 20.0

# NDS-style withdrawal coefficient for lag-type screw in softwood (lb/in^2), conservative.
# AWC NDS Supplement Table 12D; use low-end for SP/DF mix when exact species unknown.
NDS_WITHDRAWAL_COEF_LB_PER_IN2 = 138.0


@dataclass(frozen=True)
class FailureModeResult:
    name: str
    limit_total_load_lb: float
    limit_basis: str
    detail: dict[str, Any]


@dataclass(frozen=True)
class LoadAnalysisReport:
    qualification_only: bool
    official_rated_load_lb: float
    provisional_contents_load_lb: float
    governing_failure_mode: str
    layer_adhesion_safety_factor: float
    modes: tuple[FailureModeResult, ...]
    inputs: dict[str, Any]
    material_sources: tuple[str, ...]
    notes: tuple[str, ...]


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_structural_inputs() -> dict[str, Any]:
    mini = json.loads(
        MINI_CONFIG_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )
    sm = mini["structural_mini"]
    closet = mini["closet"]
    validation: dict[str, Any] = {}
    if MINI_VALIDATION_PATH.is_file():
        validation = json.loads(
            MINI_VALIDATION_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    deck_layout = validation.get("deck_layout", {})
    packaged_kg = validation.get("estimated_packaged_petg_mass_kg")
    return {
        "structural_mini": sm,
        "closet": closet,
        "deck_layout": deck_layout,
        "packaged_kg": packaged_kg,
    }


def inches_to_mm(value_in: float) -> float:
    return float(value_in) * 25.4


def lb_to_n(value_lb: float) -> float:
    return float(value_lb) * 4.4482216153


def n_to_lb(value_n: float) -> float:
    return float(value_n) / 4.4482216153


def rectangular_section_modulus_mm3(width_mm: float, height_mm: float) -> float:
    return width_mm * height_mm * height_mm / 6.0


def rectangular_moment_of_inertia_mm4(width_mm: float, height_mm: float) -> float:
    return width_mm * height_mm**3 / 12.0


def allowable_interlayer_mpa() -> float:
    return PETG_FDM_INTERLAYER_TENSILE_STRENGTH_MPA / LAYER_ADHESION_SAFETY_FACTOR


def allowable_bulk_flex_mpa() -> float:
    return PETG_MOLDED_TENSILE_STRENGTH_MPA / BULK_MATERIAL_SAFETY_FACTOR


def bracket_arm_cantilever_limit_lb(
    *,
    arm_length_mm: float,
    arm_width_mm: float,
    arm_height_mm: float,
    allowable_mpa: float,
    use_half_bracket_reaction: bool,
) -> tuple[float, dict[str, Any]]:
    """Uniform line load on arm; fixed end at wall strap; arm length = shelf depth."""
    section_modulus = rectangular_section_modulus_mm3(arm_width_mm, arm_height_mm)
    # M_max = w L^2 / 2, total on arm = w L = P_bracket => w = P/L, M = P L / 2
    # sigma = M / S => P = 2 sigma S / L
    p_bracket_n = 2.0 * allowable_mpa * section_modulus / arm_length_mm
    if use_half_bracket_reaction:
        total_n = 2.0 * p_bracket_n
    else:
        total_n = p_bracket_n
    return n_to_lb(total_n), {
        "arm_length_mm": arm_length_mm,
        "section_modulus_mm3": section_modulus,
        "allowable_stress_mpa": allowable_mpa,
        "reaction_model": "each_bracket_carries_half_total_contents_load",
    }


def bracket_root_interlayer_limit_lb(
    *,
    arm_length_mm: float,
    strap_width_mm: float,
    arm_width_mm: float,
    arm_height_mm: float,
    arm_layers_along_depth: bool,
) -> tuple[float, dict[str, Any]]:
    """Root stress: interlayer peel (legacy orientation) or bulk bending with stress concentration."""
    if arm_layers_along_depth:
        allowable = allowable_bulk_flex_mpa() / 1.5
        basis = "bulk_bending_with_root_stress_concentration_factor_1p5"
    else:
        allowable = allowable_interlayer_mpa()
        basis = "fdm_z_tension_with_layer_adhesion_factor"
    limit_lb, detail = bracket_arm_cantilever_limit_lb(
        arm_length_mm=arm_length_mm,
        arm_width_mm=arm_width_mm,
        arm_height_mm=arm_height_mm,
        allowable_mpa=allowable,
        use_half_bracket_reaction=True,
    )
    bonded_area_mm2 = strap_width_mm * arm_width_mm
    detail = {
        **detail,
        "allowable_root_mpa": allowable,
        "limit_basis": basis,
        "arm_layers_along_shelf_depth": arm_layers_along_depth,
        "estimated_bonded_plan_area_mm2": bonded_area_mm2,
    }
    return limit_lb, detail


def deck_span_limit_lb(
    *,
    span_mm: float,
    deck_depth_mm: float,
    thickness_mm: float,
    interlayer_governed: bool,
) -> tuple[float, dict[str, Any]]:
    allowable = allowable_interlayer_mpa() if interlayer_governed else allowable_bulk_flex_mpa()
    width_mm = deck_depth_mm
    height_mm = thickness_mm
    inertia = rectangular_moment_of_inertia_mm4(width_mm, height_mm)
    c_mm = height_mm / 2.0
    # Simply supported uniform load: M_max = w L^2 / 8, W = w L
    # sigma = M c / I = (w L^2 / 8) * c / I => W = 8 sigma I / (L c)
    total_n = 8.0 * allowable * inertia / (span_mm * c_mm)
    detail = {
        "span_mm": span_mm,
        "section_width_mm": width_mm,
        "section_thickness_mm": height_mm,
        "moment_of_inertia_mm4": inertia,
        "allowable_stress_mpa": allowable,
        "stress_direction": "bottom_fiber_tension_across_print_layers" if interlayer_governed else "bulk_flex",
        "model": "simply_supported_uniform_load_between_two_bracket_arms",
    }
    return n_to_lb(total_n), detail


def screw_withdrawal_limit_lb(*, screws_per_bracket: int, bracket_count: int) -> tuple[float, dict[str, Any]]:
    """NDS lag-screw withdrawal estimate in side grain; conservative length in stud."""
    d_in = SCREW_DIAMETER_IN
    # Effective thread length into stud beyond PETG strap (~16 mm) and washer stack.
    penetration_in = max(SCREW_LENGTH_IN - 0.75 - (16.0 / 25.4), 1.0)
    per_screw_lb = NDS_WITHDRAWAL_COEF_LB_PER_IN2 * (d_in**2) * penetration_in
    per_screw_allow = per_screw_lb / SCREW_WITHDRAWAL_SAFETY_FACTOR
    per_bracket_lb = per_screw_allow * screws_per_bracket
    total_lb = per_bracket_lb * 2.0  # two brackets; each resists half of total shelf load
    detail = {
        "nds_withdrawal_coef_lb_per_in2": NDS_WITHDRAWAL_COEF_LB_PER_IN2,
        "screw_diameter_in": d_in,
        "effective_penetration_in": penetration_in,
        "per_screw_ultimate_withdrawal_lb": per_screw_lb,
        "per_screw_allowable_lb": per_screw_allow,
        "screws_per_bracket": screws_per_bracket,
        "bracket_count": bracket_count,
        "caveat": "Stud species, edge distance, and GRK RSS thread form not certified here.",
    }
    return total_lb, detail


def petg_washer_bearing_limit_lb(
    *,
    strap_thickness_mm: float,
    screws_per_bracket: int,
    bracket_count: int,
) -> tuple[float, dict[str, Any]]:
    washer_area_mm2 = math.pi * (WASHER_OD_MM / 2.0) ** 2
    allowable_mpa = allowable_bulk_flex_mpa() / PETG_BEARING_SAFETY_FACTOR
    per_screw_n = allowable_mpa * washer_area_mm2
    per_bracket_n = per_screw_n * screws_per_bracket
    total_n = per_bracket_n * 2.0
    detail = {
        "washer_od_mm": WASHER_OD_MM,
        "bearing_area_mm2": washer_area_mm2,
        "allowable_bearing_mpa": allowable_mpa,
        "strap_thickness_mm": strap_thickness_mm,
    }
    return n_to_lb(total_n), detail


def build_report(inputs: dict[str, Any] | None = None) -> LoadAnalysisReport:
    inputs = inputs or load_structural_inputs()
    sm = inputs["structural_mini"]
    closet = inputs["closet"]
    deck_layout = inputs["deck_layout"]

    arm_len = float(sm["bracket_shelf_arm_length_mm"])
    arm_t = float(sm["bracket_shelf_arm_thickness_mm"])
    strap_w = float(sm["bracket_wall_strap_width_mm"])
    strap_t = float(sm["bracket_wall_strap_thickness_mm"])
    deck_t = float(sm["deck_tile_thickness_mm"])
    screws = int(sm["mounting_bore_count_per_bracket"])
    span_mm = inches_to_mm(float(closet["deck_clear_span_in"]))
    deck_depth_mm = float(deck_layout.get("deck_depth_mm", inches_to_mm(float(closet["shelf_depth_in"]))))

    modes: list[FailureModeResult] = []

    bulk_arm_lb, bulk_arm_detail = bracket_arm_cantilever_limit_lb(
        arm_length_mm=arm_len,
        arm_width_mm=arm_t,
        arm_height_mm=arm_t,
        allowable_mpa=allowable_bulk_flex_mpa(),
        use_half_bracket_reaction=True,
    )
    modes.append(
        FailureModeResult(
            "bracket_arm_bulk_bending",
            bulk_arm_lb,
            "in_plane_fiber_bending_allowable",
            bulk_arm_detail,
        )
    )

    root_lb, root_detail = bracket_root_interlayer_limit_lb(
        arm_length_mm=arm_len,
        strap_width_mm=strap_w,
        arm_width_mm=arm_t,
        arm_height_mm=arm_t,
        arm_layers_along_depth=bool(sm.get("bracket_print_arm_layers_along_depth", False)),
    )
    modes.append(
        FailureModeResult(
            "bracket_root_interlayer_tension",
            root_lb,
            "fdm_z_tension_with_layer_adhesion_factor",
            root_detail,
        )
    )

    deck_lb, deck_detail = deck_span_limit_lb(
        span_mm=span_mm,
        deck_depth_mm=deck_depth_mm,
        thickness_mm=deck_t,
        interlayer_governed=True,
    )
    modes.append(
        FailureModeResult(
            "deck_tile_span_interlayer",
            deck_lb,
            "fdm_z_tension_bottom_fiber",
            deck_detail,
        )
    )

    screw_lb, screw_detail = screw_withdrawal_limit_lb(screws_per_bracket=screws, bracket_count=2)
    modes.append(
        FailureModeResult(
            "wood_screw_withdrawal_stud",
            screw_lb,
            "nds_conservative_withdrawal",
            screw_detail,
        )
    )

    bearing_lb, bearing_detail = petg_washer_bearing_limit_lb(
        strap_thickness_mm=strap_t,
        screws_per_bracket=screws,
        bracket_count=2,
    )
    modes.append(
        FailureModeResult(
            "petg_washer_bearing",
            bearing_lb,
            "compressive_bearing_on_strap_face",
            bearing_detail,
        )
    )

    governing = min(modes, key=lambda m: m.limit_total_load_lb)
    provisional = round(governing.limit_total_load_lb, 1)

    material_sources = (
        "ASTM D638 / ISO 527 typical PETG tensile (~50 MPa molded) — see docs/LOAD_ANALYSIS.md",
        "FDM interlayer strength literature (~15 MPa PETG Z before project safety factor)",
        "AWC NDS lag-screw withdrawal coefficient (Table 12D, conservative)",
    )

    notes = (
        "ANALYSIS-ONLY / PROVISIONAL — not a safe-working load.",
        "Official rated load remains 0 lb in SAFETY.md until docs/LOAD_TEST.md proof passes.",
        f"Printed self-weight (~{inputs.get('packaged_kg', 'unknown')} kg) is in addition to any contents rating.",
    )

    report_inputs = {
        "deck_clear_span_mm": span_mm,
        "shelf_depth_mm": deck_depth_mm,
        "deck_tile_thickness_mm": deck_t,
        "bracket_arm_mm": [arm_len, arm_t, arm_t],
        "bracket_strap_mm": [strap_w, strap_t, float(sm["bracket_vertical_drop_mm"])],
        "bracket_print_arm_layers_along_depth": bool(sm.get("bracket_print_arm_layers_along_depth", False)),
        "layer_adhesion_safety_factor": LAYER_ADHESION_SAFETY_FACTOR,
        "bulk_material_safety_factor": BULK_MATERIAL_SAFETY_FACTOR,
    }

    return LoadAnalysisReport(
        qualification_only=True,
        official_rated_load_lb=0.0,
        provisional_contents_load_lb=provisional,
        governing_failure_mode=governing.name,
        layer_adhesion_safety_factor=LAYER_ADHESION_SAFETY_FACTOR,
        modes=tuple(modes),
        inputs=report_inputs,
        material_sources=material_sources,
        notes=notes,
    )


def report_to_dict(report: LoadAnalysisReport) -> dict[str, Any]:
    return {
        "qualification_only": report.qualification_only,
        "official_rated_load_lb": report.official_rated_load_lb,
        "provisional_contents_load_lb_analysis_only": report.provisional_contents_load_lb,
        "governing_failure_mode": report.governing_failure_mode,
        "layer_adhesion_safety_factor": report.layer_adhesion_safety_factor,
        "inputs": report.inputs,
        "material_sources": list(report.material_sources),
        "notes": list(report.notes),
        "failure_modes": [
            {
                "name": mode.name,
                "limit_total_load_lb": round(mode.limit_total_load_lb, 2),
                "limit_basis": mode.limit_basis,
                "detail": mode.detail,
            }
            for mode in report.modes
        ],
    }


def main() -> None:
    report = build_report()
    print(json.dumps(report_to_dict(report), indent=2))


if __name__ == "__main__":
    main()
