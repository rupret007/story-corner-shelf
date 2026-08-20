#!/usr/bin/env python3
"""Build the human-facing R12 print folder from validated model-only 3MFs."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "generated" / "model_only_3mf"
DESTINATION = ROOT / "generated" / "final_release_r12"
PROFILES = ROOT / "profiles"


def write(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def main() -> None:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    profile = config["print_profile"]
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    (DESTINATION / "models").mkdir(parents=True)
    (DESTINATION / "profiles").mkdir()

    models = sorted(SOURCE.glob("*.3mf"))
    if not models:
        raise SystemExit("No generated model-only 3MF files were found")
    for source in models:
        shutil.copy2(source, DESTINATION / "models" / source.name)
    for source in sorted(PROFILES.glob("*.json")):
        shutil.copy2(source, DESTINATION / "profiles" / source.name)

    write(
        DESTINATION / "README_FIRST.md",
        f"""
# Story Corner R12 final durable print package

This folder is the only current R12 print handoff. Files contain model geometry
and project presets but no embedded G-code. PETG is nonstructural finish; shelf
weight must remain on plywood, continuous steel angle, brackets, standards,
verified studs, and the two required blocking locations.

Printer: Bambu Lab A1 mini, 0.4 mm nozzle, Textured PEI Plate.
Filament: SUNLU clear PETG.
Process: {profile['name']}.

The 61.5 in long wall uses planned support stations 6.0, 17.0, 32.5, 48.5,
and 60.5 in from the inside corner. Stations 17.0, 32.5, and 48.5 are measured
studs. Stations 6.0 and 60.5 require purpose-installed structural blocking
before mounting or loading.

The 36 in return arm remains nominal. Do not cut, mount, or bulk-print its
production parts until that wall and its framing have been measured.
""",
    )
    write(
        DESTINATION / "SETTINGS_LOCK.md",
        f"""
# R12 A1 Mini / SUNLU clear PETG settings lock

- Layer height: {profile['layer_height_mm']:.2f} mm
- Wall loops: {profile['wall_loops']}
- Top/bottom shells: {profile['top_shell_layers']}/{profile['bottom_shell_layers']}
- Infill: {profile['sparse_infill_density_percent']}% {profile['sparse_infill_pattern']}
- Supports: off
- Outer brim: {profile['outer_brim_width_mm']:.1f} mm, {profile['brim_object_gap_mm']:.1f} mm gap
- Nozzle/bed: {profile['nozzle_temperature_c']} C / {profile['textured_plate_temperature_c']} C
- First/outer/inner speed: {profile['first_layer_speed_mm_s']}/{profile['outer_wall_speed_mm_s']}/{profile['inner_wall_speed_mm_s']} mm/s
- Maximum volumetric speed: {profile['max_volumetric_speed_mm3_s']} mm3/s
- Fan: off for first {profile['fan_first_layers']} layers, then {profile['fan_percent_after_first_layers'][0]}-{profile['fan_percent_after_first_layers'][1]}%
- Z-hop: {profile['z_hop_mm']:.1f} mm; avoid crossing walls
- Preserve saved orientation and 100% scale
- Run bed leveling and filament flow-dynamics/flow-rate calibration
- Wash the plate with plain dish detergent, keep it fingerprint-free, clean the nozzle, and dry PETG before printing

Never use the superseded 8 mm brim, 90-100 C bed guidance, or forced 105% first-layer flow.
""",
    )
    write(
        DESTINATION / "PRINT_ORDER.md",
        """
# R12 print order

1. `MODEL_ONLY_PRINT_FIRST_R12_AdhesionCornerCoupon.3mf`
2. `MODEL_ONLY_PRINT_FIRST_FasciaFitCoupon.3mf`
3. `MODEL_ONLY_PRINT_FIRST_PalatineDetailCoupon.3mf`
4. `MODEL_ONLY_PRINT_FIRST_CornerFitGauge.3mf`
5. `MODEL_ONLY_PETG_Palatine_ArcadeFascia_Half_left_long_wall_5ft.3mf`
6. Remaining long-wall production parts after the first fascia passes
7. Return-arm production parts only after return-wall measurements and regeneration

Coupon acceptance: continuous first-layer lines, no dragged strand, no lifted
corner, no delamination, and no more than 0.5 mm cooled corner lift on a flat
reference surface. Stop the queue on any failure.
""",
    )
    print(f"Packaged {len(models)} R12 model files in {DESTINATION}")


if __name__ == "__main__":
    main()
