#!/usr/bin/env python3
"""Build the numbered comparison sheet for the 20 all-PETG concepts."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
RENDER_DIR = ROOT / "artist_renderings"
OUTPUT = ROOT / "all_petg_artist_concepts_01_20.png"

CONCEPTS = (
    ("01", "Black minimal ribbed", "01_black_minimal_ribbed_petg.png"),
    ("02", "Black Art Deco", "02_black_art_deco_petg.png"),
    ("03", "Restrained Gothic", "03_black_restrained_gothic_petg.png"),
    ("04", "Ivory mid-century", "04_ivory_midcentury_petg.png"),
    ("05", "Graphite hex-rib", "05_graphite_hex_rib_petg.png"),
    ("06", "Bone-white organic", "06_bone_white_organic_petg.png"),
    ("07", "Charcoal minimal", "07_charcoal_japanese_minimal_petg.png"),
    ("08", "Black + ivory grid", "08_black_ivory_modular_grid_petg.png"),
    ("09", "Black retro-futurist", "09_black_retro_futurist_petg.png"),
    ("10", "Forest-green parametric", "10_forest_green_parametric_petg.png"),
    ("11", "Black classical", "11_black_classical_arcade_petg.png"),
    ("12", "Cream scalloped", "12_cream_contemporary_scalloped_petg.png"),
    ("13", "Graphite brutalist", "13_graphite_brutalist_petg.png"),
    ("14", "White aerofoil truss", "14_white_aerofoil_truss_petg.png"),
    ("15", "Black practical snap-trim", "15_black_practical_snap_trim_petg.png"),
    ("16", "Black radiused corbels", "16_black_radiused_corbels_petg.png"),
    ("17", "Smoke honeycomb", "17_smoke_honeycomb_petg.png"),
    ("18", "Greige soft-modern", "18_greige_soft_modern_petg.png"),
    ("19", "Black + white modular", "19_black_white_modular_petg.png"),
    ("20", "Black balanced arch", "20_black_balanced_arch_petg.png"),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def main() -> None:
    missing = [name for _, _, name in CONCEPTS if not (RENDER_DIR / name).is_file()]
    if missing:
        raise SystemExit(f"Missing concept renderings: {missing}")

    columns = 4
    rows = 5
    cell_w, cell_h = 500, 390
    margin = 36
    header_h = 120
    canvas = Image.new(
        "RGB",
        (margin * 2 + columns * cell_w, header_h + margin + rows * cell_h),
        "#f4f1eb",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 24), "20 ALL-PETG SHELF DIRECTIONS", fill="#171717", font=font(35, True))
    draw.text(
        (margin, 72),
        "Artist concepts only — choose the forms worth developing into load-validated CAD",
        fill="#53504b",
        font=font(21),
    )

    for index, (number, title, filename) in enumerate(CONCEPTS):
        row, column = divmod(index, columns)
        x = margin + column * cell_w
        y = header_h + row * cell_h
        card = (x + 7, y + 7, x + cell_w - 7, y + cell_h - 7)
        draw.rounded_rectangle(card, radius=18, fill="#ffffff", outline="#d2cec7", width=2)

        with Image.open(RENDER_DIR / filename) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            image_box = (x + 18, y + 18, x + cell_w - 18, y + 316)
            target_w = image_box[2] - image_box[0]
            target_h = image_box[3] - image_box[1]
            thumb = ImageOps.contain(source, (target_w, target_h), Image.Resampling.LANCZOS)
            backdrop = Image.new("RGB", (target_w, target_h), "#e9e6e0")
            backdrop.paste(thumb, ((target_w - thumb.width) // 2, (target_h - thumb.height) // 2))
            canvas.paste(backdrop, image_box[:2])

        draw.rounded_rectangle((x + 18, y + 326, x + 76, y + 372), radius=11, fill="#111111")
        number_bbox = draw.textbbox((0, 0), number, font=font(24, True))
        number_w = number_bbox[2] - number_bbox[0]
        draw.text((x + 47 - number_w / 2, y + 334), number, fill="#ffffff", font=font(24, True))
        draw.text((x + 91, y + 335), title, fill="#202020", font=font(21, True))

    canvas.save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
