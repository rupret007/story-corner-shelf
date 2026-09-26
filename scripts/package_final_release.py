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

READY NOW: print `models/MODEL_ONLY_PETG_TopTile_Center_6inPitch.3mf`.
It is an actual installed part, not a coupon. The measured long wall uses 14
of these universal center tiles. Inspect the first one before repeating it.
""",
    )
    write(
        DESTINATION / "START_PRINTING_NOW.md",
        """
# Start printing an actual project part now

Open `models/MODEL_ONLY_PETG_TopTile_Center_6inPitch.3mf` in Bambu Studio.
This is a 151.8 x 101.3 x 2.4 mm installed top-finish tile. It is not a test
coupon, and the long wall requires 14 identical copies.

Use the A1 Mini 0.4 nozzle, Textured PEI Plate, SUNLU clear PETG, the supplied
R12 strength profile, saved orientation, and 100% scale. Confirm six walls,
five top/bottom shells, 60% gyroid, supports off, 3 mm outer brim, 240 C nozzle,
70 C bed, 20 mm/s first layer, and calibrated flow.

Watch the first layer before leaving. Continue only if its lines are continuous
and fully bonded with no dragged strand or lifted corner. Let the tile cool on
the plate before removal. A passing tile counts toward the final installation;
after it passes, print the remaining 13 long-wall center tiles as separate jobs
or conservative batches.

Do not print fitted fascia, parametric ends, or corner pieces yet. Those remain
on hold until installed shelf-back offsets and the full-size corner geometry are
verified. Do not cut or mount the shelf until end blocking is installed.
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
# R12 production-first print order

1. Print one `MODEL_ONLY_PETG_TopTile_Center_6inPitch.3mf`; it is an installed part.
2. After it passes first-layer and cooled-flatness inspection, print the remaining 13 long-wall center tiles.
3. Universal rear-curb centers may follow; the long wall uses eight.
4. Before any fitted fascia or corner piece, print the adhesion-corner, fascia-fit, Palatine-detail, and corner-gauge qualifications.
5. Regenerate fitted pieces after both installed shelf-back offsets and full-size corner geometry are verified.
6. Return-arm production parts remain on hold until its measurements are entered.

A production tile passes only with continuous bonded first-layer lines, no
dragged strand, no lifted corner, no delamination, and no more than 0.5 mm
cooled corner lift on a flat reference surface.
""",
    )
    print(f"Packaged {len(models)} R12 model files in {DESTINATION}")


if __name__ == "__main__":
    main()
