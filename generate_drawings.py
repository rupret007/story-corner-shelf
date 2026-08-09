#!/usr/bin/env python3
"""Generate deterministic Story Corner r6 engineering-reference SVG sheets.

The drawings in this module are communication artifacts, not fabrication
drawings and not structural analysis.  They resolve their dimensions through
``design_math.py`` and a duplicate-key-rejecting read of ``config.json`` so
that the labels cannot silently drift from the r6 geometry contract.

Every sheet deliberately states that the design is experimental, unrated,
nominal/unverified, model-only, and has no generated wall-fastener bores.
Curved and ornamental SVG paths are display geometry; the printed labels and
the parametric model remain authoritative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.sax.saxutils import escape


R6_DIR = Path(__file__).resolve().parent
CONFIG_PATH = R6_DIR / "config.json"
DRAWINGS_OUT = R6_DIR / "generated" / "drawings"

from design_math import calculate_plan, grand_arc, x_corbel_geometry  # noqa: E402


DRAWING_FILENAMES = (
    "plan_layout.svg",
    "palatine_3_6_elevation.svg",
    "two_level_vertical_layout.svg",
    "exploded_joinery.svg",
    "crown_assembly_sequence.svg",
    "x_corbel_load_path.svg",
    "corner_ownership_clearance.svg",
)

STATUS_LINE = (
    "EXPERIMENTAL / UNRATED · NOMINAL / UNVERIFIED · MODEL-ONLY · "
    "NO WALL BORES"
)
DISPLAY_NOTICE = (
    "SCHEMATIC DISPLAY PATHS ONLY — dimensions and parametric data labels govern; "
    "no load rating is claimed."
)


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON object keys instead of accepting the last value."""

    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_config(path: Path = CONFIG_PATH) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    cfg = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )
    if not isinstance(cfg, dict):
        raise ValueError("r6 config root must be a JSON object")
    return cfg, payload


def n(value: float, places: int = 6) -> str:
    """Return a stable, compact decimal representation for SVG coordinates."""

    rendered = f"{float(value):.{places}f}".rstrip("0").rstrip(".")
    return "0" if rendered in ("-0", "") else rendered


def exact(value: float, places: int = 6) -> str:
    """Return a stable dimension label with intentional decimal precision."""

    return f"{float(value):.{places}f}".rstrip("0").rstrip(".")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def points(values: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{n(x)},{n(y)}" for x, y in values)


class Sheet:
    """Small deterministic SVG writer with a shared r6 safety/title frame."""

    def __init__(
        self,
        *,
        drawing_id: str,
        title: str,
        subtitle: str,
        config_hash: str,
        width: int = 1600,
        height: int = 1000,
        data: dict[str, str] | None = None,
    ) -> None:
        self.drawing_id = drawing_id
        self.title = title
        self.subtitle = subtitle
        self.config_hash = config_hash
        self.width = width
        self.height = height
        self.data = data or {}
        self.body: list[str] = []

    def raw(self, payload: str) -> None:
        self.body.append(payload)

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        cls: str = "line",
        **attrs: str,
    ) -> None:
        extra = "".join(f' {key.replace("_", "-")}="{escape(str(value))}"' for key, value in attrs.items())
        self.raw(
            f'<line x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" '
            f'y2="{n(y2)}" class="{escape(cls)}"{extra}/>'
        )

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        cls: str = "outline",
        *,
        rx: float = 0.0,
        **attrs: str,
    ) -> None:
        extra = "".join(f' {key.replace("_", "-")}="{escape(str(value))}"' for key, value in attrs.items())
        self.raw(
            f'<rect x="{n(x)}" y="{n(y)}" width="{n(width)}" height="{n(height)}" '
            f'rx="{n(rx)}" class="{escape(cls)}"{extra}/>'
        )

    def circle(self, cx: float, cy: float, radius: float, cls: str = "node", **attrs: str) -> None:
        extra = "".join(f' {key.replace("_", "-")}="{escape(str(value))}"' for key, value in attrs.items())
        self.raw(
            f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(radius)}" '
            f'class="{escape(cls)}"{extra}/>'
        )

    def polyline(self, values: Sequence[tuple[float, float]], cls: str = "line", **attrs: str) -> None:
        extra = "".join(f' {key.replace("_", "-")}="{escape(str(value))}"' for key, value in attrs.items())
        self.raw(f'<polyline points="{points(values)}" class="{escape(cls)}"{extra}/>' )

    def polygon(self, values: Sequence[tuple[float, float]], cls: str = "outline", **attrs: str) -> None:
        extra = "".join(f' {key.replace("_", "-")}="{escape(str(value))}"' for key, value in attrs.items())
        self.raw(f'<polygon points="{points(values)}" class="{escape(cls)}"{extra}/>' )

    def path(self, d: str, cls: str = "line", **attrs: str) -> None:
        extra = "".join(f' {key.replace("_", "-")}="{escape(str(value))}"' for key, value in attrs.items())
        self.raw(f'<path d="{escape(d)}" class="{escape(cls)}"{extra}/>' )

    def text(
        self,
        x: float,
        y: float,
        value: object,
        cls: str = "label",
        *,
        anchor: str | None = None,
        rotate: float | None = None,
        **attrs: str,
    ) -> None:
        if cls == "inverse" and "fill" not in attrs:
            attrs["fill"] = "#f7f0de"
        extra = ""
        if anchor:
            extra += f' text-anchor="{escape(anchor)}"'
        if rotate is not None:
            extra += f' transform="rotate({n(rotate)} {n(x)} {n(y)})"'
        extra += "".join(
            f' {key.replace("_", "-")}="{escape(str(item))}"'
            for key, item in attrs.items()
        )
        self.raw(
            f'<text x="{n(x)}" y="{n(y)}" class="{escape(cls)}"{extra}>'
            f"{escape(str(value))}</text>"
        )

    def multiline(
        self,
        x: float,
        y: float,
        lines: Sequence[str],
        cls: str = "note",
        *,
        line_height: float = 22.0,
    ) -> None:
        for index, value in enumerate(lines):
            self.text(x, y + index * line_height, value, cls)

    def dim(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        label: str,
        *,
        label_dx: float = 0.0,
        label_dy: float = -8.0,
        label_cls: str = "dimension-text",
        rotate_vertical_label: bool = True,
    ) -> None:
        self.line(x1, y1, x2, y2, "dimension", marker_start="url(#dim-arrow)", marker_end="url(#dim-arrow)")
        vertical = abs(x2 - x1) < 1.0e-7 and abs(y2 - y1) > 1.0e-7
        self.text(
            (x1 + x2) / 2.0 + label_dx,
            (y1 + y2) / 2.0 + label_dy,
            label,
            label_cls,
            anchor="middle",
            rotate=-90.0 if vertical and rotate_vertical_label else None,
        )

    def render(self) -> str:
        data_attrs = {
            "data-drawing": self.drawing_id,
            "data-revision": "r6",
            "data-config-sha256": self.config_hash,
            "data-status": "experimental-unrated-nominal-unverified-model-only-no-wall-bores",
            **self.data,
        }
        attrs = "".join(
            f' {escape(str(key))}="{escape(str(value))}"'
            for key, value in sorted(data_attrs.items())
        )
        style = """
        :root { color-scheme: light; }
        text { font-family: Inter, Avenir, Helvetica, Arial, sans-serif; fill: #181716; }
        .sheet-bg { fill: #f7f0de; }
        .border { fill: none; stroke: #181716; stroke-width: 2; }
        .deco { fill: none; stroke: #a46b2a; stroke-width: 3; }
        .hairline { fill: none; stroke: #756b5a; stroke-width: 1.2; }
        .line { fill: none; stroke: #181716; stroke-width: 2.2; }
        .heavy { fill: none; stroke: #111; stroke-width: 10; stroke-linecap: round; stroke-linejoin: round; }
        .arch { fill: none; stroke: #111; stroke-width: 11; stroke-linecap: round; stroke-linejoin: round; }
        .arch-highlight { fill: none; stroke: #c78a2f; stroke-width: 2; }
        .deck { fill: #151515; stroke: #c78a2f; stroke-width: 2; }
        .petg { fill: #1a1a1a; stroke: #b77a28; stroke-width: 2; }
        .petg-soft { fill: #32302c; stroke: #c78a2f; stroke-width: 1.5; }
        .wall { fill: #d8d0bd; stroke: #756b5a; stroke-width: 1.5; }
        .clearance { fill: #dce9e9; stroke: #2f6e73; stroke-width: 1.5; }
        .warning-fill { fill: #f1d8c9; stroke: #a53c2d; stroke-width: 2; }
        .candidate { fill: none; stroke: #b33c2e; stroke-width: 12; stroke-linecap: round; }
        .candidate-2 { fill: none; stroke: #176c73; stroke-width: 12; stroke-linecap: round; }
        .union { fill: none; stroke: #c78a2f; stroke-width: 18; stroke-linecap: round; opacity: .86; }
        .seam-fixed { fill: none; stroke: #b33c2e; stroke-width: 2.2; }
        .seam-floating { fill: none; stroke: #176c73; stroke-width: 2.2; stroke-dasharray: 7 5; }
        .construction { fill: none; stroke: #8d8372; stroke-width: 1.2; stroke-dasharray: 5 5; }
        .dimension { fill: none; stroke: #2d5960; stroke-width: 1.5; }
        .motion { fill: none; stroke: #b33c2e; stroke-width: 3; marker-end: url(#motion-arrow); }
        .motion-blue { fill: none; stroke: #176c73; stroke-width: 3; marker-end: url(#motion-blue-arrow); }
        .node { fill: #f7f0de; stroke: #181716; stroke-width: 2; }
        .support-node { fill: #b33c2e; stroke: #f7f0de; stroke-width: 1.5; }
        .crown-node { fill: #c78a2f; stroke: #181716; stroke-width: 1.2; }
        .title { font-family: Georgia, 'Times New Roman', serif; font-size: 34px; font-weight: 700; letter-spacing: 1.2px; }
        .subtitle { font-size: 16px; letter-spacing: 1.5px; fill: #4a4439; }
        .header-subtitle { font-size: 14px; letter-spacing: .25px; fill: #4a4439; }
        .status { font-size: 14px; font-weight: 800; fill: #892f24; letter-spacing: .25px; }
        .section { font-family: Georgia, 'Times New Roman', serif; font-size: 22px; font-weight: 700; }
        .label { font-size: 15px; font-weight: 650; }
        .small { font-size: 12px; }
        .tiny { font-size: 10px; }
        .note { font-size: 14px; }
        .dimension-text { font-size: 13px; font-weight: 700; fill: #244f55; }
        .callout { font-size: 15px; font-weight: 750; fill: #892f24; }
        .inverse { fill: #f7f0de; font-size: 13px; font-weight: 700; }
        .inverse-label { fill: #f7f0de; font-size: 15px; font-weight: 650; }
        .inverse-callout { fill: #f7f0de; font-size: 15px; font-weight: 750; }
        .panel { fill: #fbf6e8; stroke: #756b5a; stroke-width: 1.5; }
        .panel-title { font-family: Georgia, 'Times New Roman', serif; font-size: 18px; font-weight: 700; }
        """
        header = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}"
     viewBox="0 0 {self.width} {self.height}" role="img"{attrs}>
  <title>{escape(self.title)}</title>
  <desc>{escape(self.subtitle)} {escape(STATUS_LINE)}. {escape(DISPLAY_NOTICE)}</desc>
  <defs>
    <style>{style}</style>
    <marker id="motion-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 z" fill="#b33c2e"/>
    </marker>
    <marker id="motion-blue-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 z" fill="#176c73"/>
    </marker>
    <marker id="dim-arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse" markerUnits="strokeWidth">
      <path d="M0,4 L8,0 L8,8 z" fill="#2d5960"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="{self.width}" height="{self.height}" class="sheet-bg"/>
  <rect x="18" y="18" width="{self.width - 36}" height="{self.height - 36}" class="border"/>
  <path d="M42 72 H126 L146 52 H{self.width - 146} L{self.width - 126} 72 H{self.width - 42}" class="deco"/>
  <path d="M42 {self.height - 72} H126 L146 {self.height - 52} H{self.width - 146} L{self.width - 126} {self.height - 72} H{self.width - 42}" class="deco"/>
  <text x="52" y="44" class="subtitle">STORY CORNER · TRIADIC PALATINE ORDER · r6</text>
  <text x="52" y="96" class="title">{escape(self.title)}</text>
  <text x="52" y="122" class="header-subtitle">{escape(self.subtitle)}</text>
  <rect x="50" y="136" width="{self.width - 100}" height="34" rx="5" class="warning-fill"/>
  <text x="{self.width / 2}" y="159" class="status" text-anchor="middle">{escape(STATUS_LINE)}</text>
"""
        footer_y = self.height - 33
        footer = f"""
  <text x="52" y="{footer_y}" class="small">{escape(DISPLAY_NOTICE)}</text>
  <text x="{self.width - 52}" y="{footer_y}" class="small" text-anchor="end">CONFIG SHA-256 {self.config_hash[:16]}… · deterministic SVG</text>
</svg>
"""
        return header + "\n".join(self.body) + footer


def arc_display_points(
    *,
    x_start: float,
    span: float,
    spring_y: float,
    crown_y: float,
    radius: float,
    sx: Any,
    sy: Any,
    samples: int = 40,
) -> list[tuple[float, float]]:
    """Sample the exact circular extrados solely for an SVG display path."""

    center_x = x_start + span / 2.0
    center_y = crown_y - radius
    values: list[tuple[float, float]] = []
    for index in range(samples + 1):
        x = x_start + span * index / samples
        local_x = x - center_x
        y = center_y + math.sqrt(max(0.0, radius * radius - local_x * local_x))
        values.append((sx(x), sy(y)))
    # The parametric endpoints are governed by the configured spring datum.
    values[0] = (sx(x_start), sy(spring_y))
    values[-1] = (sx(x_start + span), sy(spring_y))
    return values


def add_plan_layout(cfg: dict[str, Any], config_hash: str) -> Sheet:
    plan = calculate_plan(cfg)
    sheet = Sheet(
        drawing_id="plan-layout",
        title="Nominal L-Plan · 3 / 6 / 9 Rhythm",
        subtitle="One independently supported shelf level; repeat as a complete independent level only",
        config_hash=config_hash,
        data={
            "data-through-length-mm": exact(plan.through.length_mm),
            "data-return-length-mm": exact(plan.return_run.length_mm),
            "data-depth-mm": exact(plan.depth_mm),
            "data-support-count": "11",
            "data-half-cassette-count": "18",
        },
    )
    ox, oy, scale = 125.0, 205.0, 0.70
    sx = lambda value: ox + value * scale
    sy = lambda value: oy + value * scale

    sheet.rect(sx(-8), sy(-8), 1540 * scale, 14 * scale, "wall")
    sheet.rect(sx(-8), sy(-8), 14 * scale, 930 * scale, "wall")

    through = plan.through
    ret = plan.return_run
    sheet.rect(
        sx(through.start_from_corner_mm),
        sy(plan.through_back_clearance_mm),
        through.length_mm * scale,
        plan.depth_mm * scale,
        "deck",
        rx=2,
    )
    sheet.rect(
        sx(plan.return_back_clearance_mm),
        sy(ret.start_from_corner_mm),
        plan.depth_mm * scale,
        ret.length_mm * scale,
        "deck",
        rx=2,
    )

    for index, local in enumerate(through.cassette_boundary_stations_local_mm[1:-1], 1):
        absolute = through.start_from_corner_mm + local
        cls = "seam-fixed" if index % 2 else "seam-floating"
        sheet.line(sx(absolute), sy(plan.through_back_clearance_mm), sx(absolute), sy(plan.through_back_clearance_mm + plan.depth_mm), cls)
    for index, local in enumerate(ret.cassette_boundary_stations_local_mm[1:-1], 1):
        absolute = ret.start_from_corner_mm + local
        cls = "seam-fixed" if index % 2 else "seam-floating"
        sheet.line(sx(plan.return_back_clearance_mm), sy(absolute), sx(plan.return_back_clearance_mm + plan.depth_mm), sy(absolute), cls)

    for index, station in enumerate(through.support_centers_absolute_mm, 1):
        sheet.circle(sx(station), sy(plan.through_back_clearance_mm + plan.depth_mm - 13), 6, "support-node")
        sheet.text(sx(station), sy(plan.through_back_clearance_mm + plan.depth_mm - 30), f"L{index}", "tiny", anchor="middle")
    for index, station in enumerate(ret.support_centers_absolute_mm, 1):
        sheet.circle(sx(plan.return_back_clearance_mm + plan.depth_mm - 13), sy(station), 6, "support-node")
        sheet.text(sx(plan.return_back_clearance_mm + plan.depth_mm - 30), sy(station) + 4, f"R{index}", "tiny", anchor="middle")

    for index, crown in enumerate(through.crown_seam_stations_local_mm, 1):
        absolute = through.start_from_corner_mm + crown
        sheet.circle(sx(absolute), sy(plan.through_back_clearance_mm + 20), 4.5, "crown-node")
        sheet.text(sx(absolute), sy(plan.through_back_clearance_mm + 42), str(index), "tiny", anchor="middle")
    for index, crown in enumerate(ret.crown_seam_stations_local_mm, 1):
        absolute = ret.start_from_corner_mm + crown
        sheet.circle(sx(plan.return_back_clearance_mm + 20), sy(absolute), 4.5, "crown-node")
        sheet.text(sx(plan.return_back_clearance_mm + 42), sy(absolute) + 4, str(index), "tiny", anchor="middle")

    # Keep the top dimension label visibly below the mandatory warning band.
    dim_y = 194.0
    sheet.line(sx(through.start_from_corner_mm), dim_y - 10.0, sx(through.start_from_corner_mm), sy(plan.through_back_clearance_mm), "construction")
    sheet.line(sx(through.start_from_corner_mm + through.length_mm), dim_y - 10.0, sx(through.start_from_corner_mm + through.length_mm), sy(plan.through_back_clearance_mm), "construction")
    sheet.dim(
        sx(through.start_from_corner_mm),
        dim_y,
        sx(through.start_from_corner_mm + through.length_mm),
        dim_y,
        f"THROUGH ARM {exact(through.length_mm, 3)} mm · nominal 5 ft wall",
    )
    sheet.dim(
        sx(through.start_from_corner_mm + 100),
        sy(plan.through_back_clearance_mm),
        sx(through.start_from_corner_mm + 100),
        sy(plan.through_back_clearance_mm + plan.depth_mm),
        f"DEPTH {exact(plan.depth_mm, 1)} mm / 6 in",
        label_dx=72,
        label_dy=4,
        label_cls="inverse",
        rotate_vertical_label=False,
    )

    dim_x = sx(-42)
    sheet.line(sx(-28), sy(ret.start_from_corner_mm), sx(plan.return_back_clearance_mm), sy(ret.start_from_corner_mm), "construction")
    sheet.line(sx(-28), sy(ret.start_from_corner_mm + ret.length_mm), sx(plan.return_back_clearance_mm), sy(ret.start_from_corner_mm + ret.length_mm), "construction")
    sheet.dim(
        dim_x,
        sy(ret.start_from_corner_mm),
        dim_x,
        sy(ret.start_from_corner_mm + ret.length_mm),
        f"RETURN ARM {exact(ret.length_mm, 3)} mm · nominal 3 ft wall",
        label_dx=-16,
        label_dy=4,
    )
    panel_x = 1235
    sheet.rect(panel_x, 205, 305, 655, "panel", rx=8)
    sheet.text(panel_x + 20, 238, "Exact nominal contract", "section")
    sheet.multiline(
        panel_x + 20,
        270,
        [
            "6 bays through + 3 bays return = 9",
            "7 + 4 independent pier/X-corbels = 11",
            "12 + 6 half-bay cassettes = 18",
            "16 seams: 9 fixed crowns + 7 floating piers",
            "48 diaphragm keys: 3 per seam",
            "",
            f"Through bay span  {exact(through.bay_span_mm, 3)} mm",
            f"Return bay span   {exact(ret.bay_span_mm, 3)} mm",
            f"Pier insets through  {exact(through.start_pier_inset_mm,4)} / {exact(through.end_pier_inset_mm,4)} mm",
            f"Pier insets return   {exact(ret.start_pier_inset_mm,4)} / {exact(ret.end_pier_inset_mm,4)} mm",
            f"Back clearances   {exact(plan.through_back_clearance_mm, 2)} / {exact(plan.return_back_clearance_mm, 2)} mm",
            f"Outer clearances  3.175 mm each",
            f"Visible joint gap {exact(plan.corner_gap_mm, 1)} mm",
            f"Full removable-facade projection  {exact(plan.full_removable_facade_projection_beyond_cassette_mm,1)} mm",
            f"Integral parent-boss projection    {exact(plan.integral_boss_projection_beyond_cassette_mm,1)} mm",
            "",
            "RED DOT = independent structural station",
            "GOLD DOT = fixed crown seam",
            "BLUE DASH = floating supported pier seam",
            "",
            "Through arm owns the 152.4 × 152.4 mm",
            "inside-corner deck square. Return begins beyond",
            "the full facade plus its service-stroke envelope",
            f"at {exact(ret.start_from_corner_mm, 2)} mm from corner datum.",
            "",
            "METAL STRUCTURAL SCREWS + WASHERS",
            "INTO VERIFIED STUDS/BLOCKING REQUIRED.",
        ],
        line_height=18,
    )
    sheet.text(300, 762, "SUPPORT CENTERS — THROUGH (absolute from corner datum, mm)", "label")
    sheet.text(300, 784, ", ".join(exact(value, 4) for value in through.support_centers_absolute_mm), "small")
    sheet.text(300, 812, "SUPPORT CENTERS — RETURN (absolute from corner datum, mm)", "label")
    sheet.text(300, 834, ", ".join(exact(value, 4) for value in ret.support_centers_absolute_mm), "small")
    return sheet


def add_arcade_run(
    sheet: Sheet,
    *,
    x0: float,
    base_y: float,
    span: float,
    bays: int,
    scale: float,
    rise: float,
    spring: float,
    crown: float,
    total_height: float,
    cassette_bottom: float,
    pier_width: float,
    radius: float,
    run_prefix: str,
) -> None:
    sx = lambda value: x0 + value * scale
    sy = lambda value: base_y - value * scale
    total_span = span * bays
    sheet.rect(sx(0), sy(total_height), total_span * scale, (total_height - cassette_bottom) * scale, "deck")
    for pier in range(bays + 1):
        center = pier * span
        sheet.rect(sx(center - pier_width / 2.0), sy(cassette_bottom), pier_width * scale, cassette_bottom * scale, "petg", rx=2)
        for flute in (-6, 0, 6):
            if pier_width * scale > 14:
                sheet.line(sx(center + flute), sy(17), sx(center + flute), sy(53), "arch-highlight")
        sheet.circle(sx(center), sy(0), 4.5, "support-node")
        sheet.text(sx(center), base_y + 20, f"{run_prefix}{pier + 1}", "tiny", anchor="middle")
    for bay in range(bays):
        start = bay * span
        curve = arc_display_points(
            x_start=start,
            span=span,
            spring_y=spring,
            crown_y=crown,
            radius=radius,
            sx=sx,
            sy=sy,
        )
        sheet.polyline(curve, "arch")
        sheet.polyline(curve, "arch-highlight")
        sheet.circle(sx(start + span / 2.0), sy(crown), 4, "crown-node")
        sheet.text(sx(start + span / 2.0), sy(crown) - 12, str(bay + 1), "tiny", anchor="middle")


def add_palatine_elevation(cfg: dict[str, Any], config_hash: str) -> Sheet:
    plan = calculate_plan(cfg)
    tied = cfg["tied_arcade"]
    # The elevation shows the removable palace facade. The qualified-candidate
    # structural rib is shorter, begins at the inner capital face, and is
    # reported separately so the drawing cannot imply that carved columns or
    # the full visual archivolt receive capacity credit.
    rise = float(tied["visual_facade_arch_rise_mm"])
    spring = float(tied["visual_facade_spring_extrados_y_mm"])
    crown = float(tied["visual_facade_crown_extrados_y_mm"])
    structural_spring = float(tied["arch_spring_extrados_y_mm"])
    structural_crown = float(tied["arch_crown_extrados_y_mm"])
    spring_joint = tied["spring_final_x_vertical_joint"]
    long_structural_radius = float(spring_joint["through_regenerated_arc_radius_mm"])
    return_structural_radius = float(spring_joint["return_regenerated_arc_radius_mm"])
    total = float(tied["total_height_mm"])
    cassette_bottom = float(tied["cassette_entablature_bottom_y_mm"])
    pier_width = float(tied["pier_width_mm"])
    long_arc = grand_arc(plan.through.bay_span_mm, rise)
    short_arc = grand_arc(plan.return_run.bay_span_mm, rise)
    sheet = Sheet(
        drawing_id="palatine-3-6-elevation",
        title="Triadic Palatine Elevation · Six + Three",
        subtitle="Exact bay rhythm and visual facade; hidden compact-capital structural datums are reported separately",
        config_hash=config_hash,
        data={
            "data-long-bays": "6",
            "data-return-bays": "3",
            "data-total-bays": "9",
            "data-long-radius-mm": exact(long_arc.radius_mm),
            "data-return-radius-mm": exact(short_arc.radius_mm),
            "data-structural-long-radius-mm": exact(long_structural_radius),
            "data-structural-return-radius-mm": exact(return_structural_radius),
        },
    )
    add_arcade_run(
        sheet,
        x0=125,
        base_y=420,
        span=plan.through.bay_span_mm,
        bays=6,
        scale=0.78,
        rise=rise,
        spring=spring,
        crown=crown,
        total_height=total,
        cassette_bottom=cassette_bottom,
        pier_width=pier_width,
        radius=long_arc.radius_mm,
        run_prefix="L",
    )
    sheet.text(125, 220, "5 FT THROUGH ARM · 6 VISIBLE BAYS · 7 SUPPORT CAPITALS", "section")
    sheet.text(125, 248, f"center-to-center span {exact(plan.through.bay_span_mm, 3)} mm · visual R {exact(long_arc.radius_mm, 6)} mm · structural R {exact(long_structural_radius, 6)} mm", "label")
    # Keep the dimension chain below the L1…L7 support labels.  The former
    # 448 px baseline crossed L4 at the center of the through run.
    sheet.dim(125, 475, 125 + 6 * plan.through.bay_span_mm * 0.78, 475, f"6 × {exact(plan.through.bay_span_mm, 3)} = {exact(6 * plan.through.bay_span_mm, 3)} mm pier-center rhythm")

    add_arcade_run(
        sheet,
        x0=125,
        base_y=790,
        span=plan.return_run.bay_span_mm,
        bays=3,
        scale=1.08,
        rise=rise,
        spring=spring,
        crown=crown,
        total_height=total,
        cassette_bottom=cassette_bottom,
        pier_width=pier_width,
        radius=short_arc.radius_mm,
        run_prefix="R",
    )
    sheet.text(125, 548, "3 FT RETURN ARM · 3 VISIBLE BAYS · 4 SUPPORT CAPITALS", "section")
    sheet.text(125, 576, f"center-to-center span {exact(plan.return_run.bay_span_mm, 3)} mm · visual R {exact(short_arc.radius_mm, 6)} mm · structural R {exact(return_structural_radius, 6)} mm", "label")
    sheet.dim(125, 840, 125 + 3 * plan.return_run.bay_span_mm * 1.08, 840, f"3 × {exact(plan.return_run.bay_span_mm, 3)} = {exact(3 * plan.return_run.bay_span_mm, 3)} mm pier-center rhythm")

    panel_x = 970
    sheet.rect(panel_x, 525, 560, 365, "panel", rx=8)
    sheet.text(panel_x + 20, 558, "Visual order and hidden candidate chassis", "section")
    sheet.multiline(
        panel_x + 20,
        590,
        [
            f"Overall frame / cassette height: {exact(total, 1)} mm",
            f"Cassette-entablature zone: y = {exact(cassette_bottom, 1)}…{exact(total, 1)} mm",
            f"Visual facade spring / crown: e = {exact(spring, 1)} / {exact(crown, 1)} mm",
            f"Hidden structural spring / crown: e = {exact(structural_spring, 1)} / {exact(structural_crown, 1)} mm",
            f"Structural rib: {exact(tied['arch_radial_rib_mm'], 1)} mm · inner-capital root u = {exact(spring_joint['structural_arc_root_from_support_toward_crown_mm'][0], 1)} mm",
            f"Visual pier width: {exact(pier_width, 1)} mm · minimum structural root web: {exact(spring_joint['minimum_root_transition_web_mm'], 1)} mm",
            "",
            "BLACK = printed PETG; drawing silhouette is the removable facade.",
            "GOLD = Greek/Roman/Art-Deco display accent.",
            "Flutes, full visual columns, archivolts and ornament receive zero credit.",
            "",
            "This is a mixed compression / bending / tension / shear",
            "hidden load-sharing chassis. It is not a pure masonry arch.",
            "Only comparative full-bay physical tests may establish benefit.",
        ],
        line_height=22,
    )
    sheet.text(970, 470, "3 + 6 = 9 visible bays · (3 + 1) + (6 + 1) = 11 independent supports per level", "callout")
    return sheet


def add_two_level_layout(cfg: dict[str, Any], config_hash: str) -> Sheet:
    closet = cfg["closet"]
    vertical = closet["vertical_layout"]
    zone_in = float(closet["measured_vertical_zone_from_outlet_top_to_ceiling_in"])
    zone = zone_in * 25.4
    lower_in = float(vertical["reference_lower_shelf_top_above_outlet_top_in"])
    upper_in = float(vertical["reference_upper_shelf_top_above_outlet_top_in"])
    lower = lower_in * 25.4
    upper = upper_in * 25.4
    drop = float(cfg["tied_arcade"]["total_height_mm"])
    clear = upper - drop - lower
    above = zone - upper
    lower_bottom = lower - drop
    sheet = Sheet(
        drawing_id="two-level-vertical-layout",
        title="Two Independent Levels · Provisional Vertical Layout",
        subtitle="Outlet-top datum to ceiling; upper level installs first and neither level carries the other",
        config_hash=config_hash,
        data={
            "data-zone-in": exact(zone_in),
            "data-lower-offset-in": exact(lower_in),
            "data-upper-offset-in": exact(upper_in),
            "data-top-spacing-in": exact(upper_in - lower_in),
            "data-clear-opening-in": exact(clear / 25.4),
        },
    )
    x_wall = 430.0
    bottom = 840.0
    scale = 0.57
    sy = lambda value: bottom - value * scale
    sheet.rect(x_wall - 22, sy(zone), 26, zone * scale, "wall")
    sheet.line(x_wall - 70, sy(zone), 925, sy(zone), "heavy")
    sheet.text(440, sy(zone) - 15, f"CEILING · +{exact(zone_in, 1)} in / {exact(zone, 1)} mm", "label")
    sheet.line(x_wall - 70, bottom, 925, bottom, "line")
    sheet.text(440, bottom + 25, "DATUM 0 · TOP OF ELECTRICAL OUTLET (user-reported datum; remeasure level)", "label")
    sheet.rect(x_wall - 72, bottom - 72, 48, 72, "wall", rx=5)
    sheet.text(x_wall - 48, bottom - 82, "OUTLET", "tiny", anchor="middle")

    for number, top, offset_in in ((1, lower, lower_in), (2, upper, upper_in)):
        top_y = sy(top)
        frame_bottom_y = sy(top - drop)
        sheet.rect(x_wall, top_y - 7, 500, 14, "deck", rx=2)
        sheet.rect(x_wall + 20, top_y, 460, frame_bottom_y - top_y, "clearance", rx=4)
        # Three stylized arches indicate rhythm without implying a vertical tie.
        arch_width = 140
        for bay in range(3):
            left = x_wall + 38 + bay * 148
            sheet.path(
                f"M {n(left)} {n(frame_bottom_y - 5)} Q {n(left + arch_width / 2)} {n(top_y + 26)} {n(left + arch_width)} {n(frame_bottom_y - 5)}",
                "arch",
            )
        sheet.text(1015, top_y - 30, f"LEVEL {number} TOP · +{exact(offset_in, 1)} in / {exact(top, 1)} mm", "section", anchor="end")
        sheet.text(1015, top_y + 31, f"independent 11-support L assembly · frame drop {exact(drop, 1)} mm", "label", anchor="end")

    # Explicitly reject a structural column between levels.
    mid_x = 700
    sheet.line(mid_x - 15, sy(lower) - 18, mid_x + 15, sy(upper) + 18, "candidate")
    sheet.line(mid_x + 15, sy(lower) - 18, mid_x - 15, sy(upper) + 18, "candidate")
    sheet.text(mid_x + 34, (sy(lower) + sy(upper)) / 2, "NO VERTICAL STRUCTURAL TIE", "callout")

    sheet.dim(315, bottom, 315, sy(zone), f"{exact(zone_in, 1)} in ZONE", label_dx=-8, label_dy=4)
    sheet.dim(365, sy(lower), 365, sy(upper), f"{exact((upper-lower)/25.4, 1)} in TOP-TO-TOP", label_dx=-12, label_dy=4)
    sheet.dim(1025, sy(upper - drop), 1025, sy(lower), f"{exact(clear/25.4, 6)} in CLEAR", label_dx=3, label_dy=4)
    sheet.dim(1025, sy(zone), 1025, sy(upper), f"{exact(above/25.4, 1)} in ABOVE", label_dx=3, label_dy=4)
    sheet.dim(385, bottom, 385, sy(lower - drop), f"{exact(lower_bottom/25.4, 6)} in", label_dx=-12, label_dy=4)

    panel_x = 1040
    sheet.rect(panel_x, 510, 490, 348, "panel", rx=8)
    sheet.text(panel_x + 20, 544, "Placement gates before freezing elevation", "section")
    sheet.multiline(
        panel_x + 20,
        577,
        [
            "• Measure loaded bin/item width, depth, height and weight.",
            "• Verify outlet, plug and cord service envelope.",
            "• Verify ceiling bow and both shelf-top offsets from one level datum.",
            "• Preserve ≥ 75 mm straight visible-front/open-underside",
            "  cross-key and pin service access with stored items removed.",
            "• Install and service-check the upper level first.",
            "• Each level gets its own 7 + 4 verified support stations.",
            "",
            f"Nominal opening between levels: {exact(clear, 6)} mm / {exact(clear/25.4, 6)} in",
            f"Nominal upper ceiling clearance: {exact(above, 1)} mm / {exact(above/25.4, 1)} in",
            f"Nominal lower frame bottom: +{exact(lower_bottom, 6)} mm / {exact(lower_bottom/25.4, 6)} in",
        ],
        line_height=22,
    )
    return sheet


def add_exploded_joinery(cfg: dict[str, Any], config_hash: str) -> Sheet:
    tied = cfg["tied_arcade"]
    top_joint = tied["cassette_final_x_vertical_tenon_joint"]
    spring_joint = tied["spring_final_x_vertical_joint"]
    bridge = tied["rear_crown_bridge"]
    long_centers = top_joint["run_centers_mm"]["long_wall_5ft"]["final_u_centers_mm"]
    short_centers = top_joint["run_centers_mm"]["short_wall_3ft"]["final_u_centers_mm"]
    sheet = Sheet(
        drawing_id="exploded-joinery",
        title="Exploded Final-Coordinate Joinery",
        subtitle="Lincoln-Logs-style serviceable assembly: broad bearing first, accessible cross-keys and pins retain only",
        config_hash=config_hash,
        data={
            "data-cassette-tenons-per-half": str(len(long_centers)),
            "data-spring-tenons-per-half": "1",
            "data-long-tenon-centers-mm": ",".join(exact(v, 6) for v in long_centers),
            "data-short-tenon-centers-mm": ",".join(exact(v, 6) for v in short_centers),
        },
    )
    # Wall / corbel candidate at installed final coordinate.
    sheet.rect(95, 360, 28, 465, "wall")
    sheet.line(123, 455, 560, 790, "candidate")
    sheet.line(123, 790, 560, 455, "candidate-2")
    sheet.line(123, 790, 560, 790, "heavy")
    sheet.text(150, 814, "A · independently wall-fastened pier / X-corbel", "label")
    sheet.text(150, 837, "wall plate remains SOLID: provisional station targets only; NO BORES", "callout")

    # Half frame with a spring tenon and two top tenons.
    sheet.rect(295, 490, 420, 95, "petg", rx=6)
    sheet.path("M 315 575 Q 500 660 690 575", "arch")
    sheet.rect(300, 574, 30, 188, "petg", rx=3)
    sheet.rect(680, 574, 30, 188, "petg", rx=3)
    sheet.rect(300, 447, 34, 43, "petg-soft", rx=2)
    sheet.text(317, 440, "spring tenon", "tiny", anchor="middle")
    top_xs = [455, 565]
    for index, x in enumerate(top_xs, 1):
        sheet.rect(x - 16, 447, 32, 43, "petg-soft", rx=2)
        sheet.text(x, 440, f"T{index}", "tiny", anchor="middle")
    sheet.text(350, 522, "B · one arcade half at FINAL run coordinate", "inverse")
    sheet.text(350, 546, "2 cassette tenons + 1 spring tenon; lift straight upward", "inverse")

    # Cassette above, with open-bottom receivers.
    sheet.rect(260, 280, 490, 82, "deck", rx=6)
    for x in top_xs:
        sheet.rect(x - 19, 340, 38, 24, "clearance", rx=2)
    sheet.rect(295, 340, 44, 24, "clearance", rx=2)
    sheet.text(280, 305, "C · coffered cassette / entablature", "inverse")
    sheet.text(280, 328, "open-bottom receivers + broad compression-pad hard stops", "inverse")
    for x in (317, *top_xs):
        sheet.line(x, 430, x, 369, "motion")
    sheet.text(756, 393, "STRAIGHT +y INSERTION", "callout")
    sheet.text(756, 416, "0.0 mm whole-half run travel", "label")

    # Positive quarter-turn cross-keys enter from the visible front; q is displayed obliquely.
    wedge_y = 470
    for index, x in enumerate((317, *top_xs), 1):
        sheet.polygon([(x - 18, wedge_y - 5), (x + 6, wedge_y - 5), (x + 12, wedge_y + 5), (x - 18, wedge_y + 5)], "warning-fill")
        sheet.line(x - 62, wedge_y, x - 21, wedge_y, "motion-blue")
        sheet.text(x, wedge_y + 19, f"K{index}", "inverse", anchor="middle")
    sheet.text(980, 462, "3 indexed quarter-turn cross-keys per half", "label", anchor="end")
    sheet.text(980, 484, "visible front → rear (+q), rotate 90°; withdrawal retention only", "small", anchor="end")

    # Crown bridge is exploded below the crown seam to show its independent motion.
    sheet.rect(790, 630, 190, 120, "petg-soft", rx=5)
    sheet.rect(812, 615, 18, 35, "petg")
    sheet.rect(900, 615, 18, 35, "petg")
    sheet.line(865, 610, 865, 548, "motion")
    sheet.text(810, 674, "D · rear crown bridge", "inverse")
    sheet.text(810, 697, f"{exact(bridge['width_mm'],1)} × {exact(bridge['height_mm'],1)} × {exact(bridge['thickness_mm'],1)} mm", "inverse")
    sheet.text(810, 720, "upward from below", "inverse")
    sheet.text(810, 741, "to positive hard stop", "inverse")
    sheet.circle(910, 657, 6, "crown-node")
    sheet.line(978, 657, 921, 657, "motion-blue")
    sheet.text(975, 575, f"one {exact(bridge['retention_pin_diameter_mm'],1)} mm pin", "label", anchor="end")
    sheet.text(975, 597, "right fixed half · anti-drop only", "small", anchor="end")

    panel_x = 1010
    sheet.rect(panel_x, 205, 520, 610, "panel", rx=8)
    sheet.text(panel_x + 20, 239, "Final-X interface contract", "section")
    sheet.multiline(
        panel_x + 20,
        273,
        [
            "CASSETTE JOINT — each half",
            f"{len(long_centers)} × {exact(top_joint['tenon_run_width_mm'],1)} × {exact(top_joint['tenon_depth_mm'],1)} × {exact(top_joint['tenon_engagement_height_mm'],1)} mm top tenons",
            f"receiver {exact(top_joint['receiver_run_width_mm'],1)} × {exact(top_joint['receiver_depth_mm'],1)} mm",
            f"clearance {exact(top_joint['receiver_clearance_per_side_mm'],1)} mm per side",
            f"long centers: {', '.join(exact(v, 5) for v in long_centers)} mm",
            f"return centers: {', '.join(exact(v, 4) for v in short_centers)} mm",
            f"cross-key bore center y = {exact(top_joint['retention_wedge_center_y_mm'],1)} mm",
            "",
            "SPRING JOINT — each half",
            f"{exact(spring_joint['tenon_run_width_mm'],1)} × {exact(spring_joint['tenon_depth_mm'],1)} × {exact(spring_joint['tenon_engagement_height_mm'],1)} mm tenon",
            f"receiver {exact(spring_joint['receiver_run_width_mm'],1)} × {exact(spring_joint['receiver_depth_mm'],1)} mm",
            f"cross-key bore center y = {exact(spring_joint['retention_wedge_center_y_mm'],1)} mm",
            "",
            "CROWN",
            "bridge enters upward only; one accessible double-shear pin",
            f"pin center (u,y) = ({exact(bridge['retention_pin_center_u_y_mm'][0],1)}, {exact(bridge['retention_pin_center_u_y_mm'][1],1)}) mm",
            f"dovetail rail centers u = ±{exact(abs(bridge['dovetail_rails']['u_centers_from_crown_mm'][0]),1)} mm",
            "",
            "NO whole-half run-axis slide · NO top-down bridge",
            "NO wall-side-only access · NO friction-only keeper",
            "Cross-keys and pin receive ZERO vertical load capacity credit.",
            "Broad shoulders / pads are the candidate bearing path.",
        ],
        line_height=22,
    )
    return sheet


def add_crown_sequence(cfg: dict[str, Any], config_hash: str) -> Sheet:
    bridge = cfg["tied_arcade"]["rear_crown_bridge"]
    sheet = Sheet(
        drawing_id="crown-assembly-sequence",
        title="Rear Crown Bridge · Assembly / Service Sequence",
        subtitle="One upward-inserted hard-stop bridge and one accessible fixed-side anti-drop pin per visible bay",
        config_hash=config_hash,
        data={
            "data-bridge-width-mm": exact(bridge["width_mm"]),
            "data-bridge-height-mm": exact(bridge["height_mm"]),
            "data-bridge-thickness-mm": exact(bridge["thickness_mm"]),
            "data-pin-diameter-mm": exact(bridge["retention_pin_diameter_mm"]),
            "data-pin-hole-mm": exact(bridge["retention_pin_hole_diameter_mm"]),
        },
    )
    panel_width = 275
    panel_gap = 22
    x_positions = [50 + index * (panel_width + panel_gap) for index in range(5)]
    titles = (
        "1 · Seat both halves",
        "2 · Retain each half",
        "3 · Lift bridge",
        "4 · Meet hard stop",
        "5 · Install one pin",
    )
    for x, title in zip(x_positions, titles):
        sheet.rect(x, 205, panel_width, 500, "panel", rx=8)
        sheet.text(x + 15, 236, title, "panel-title")

    # Panel 1
    x = x_positions[0]
    sheet.rect(x + 30, 365, 92, 42, "petg")
    sheet.rect(x + 153, 365, 92, 42, "petg")
    sheet.line(x + 137.5, 570, x + 137.5, 428, "construction")
    sheet.line(x + 76, 530, x + 76, 415, "motion")
    sheet.line(x + 199, 530, x + 199, 415, "motion")
    sheet.text(x + 18, 600, "Lift each half straight upward", "label")
    sheet.text(x + 18, 623, "at its final run coordinate.", "label")
    sheet.text(x + 18, 654, "Two cassette + one spring", "small")
    sheet.text(x + 18, 674, "tenon seat per half.", "small")

    # Panel 2
    x = x_positions[1]
    sheet.rect(x + 30, 365, 92, 42, "petg")
    sheet.rect(x + 153, 365, 92, 42, "petg")
    for yy in (378, 394):
        sheet.line(x + 8, yy, x + 40, yy, "motion-blue")
        sheet.line(x + 145, yy, x + 177, yy, "motion-blue")
    sheet.text(x + 18, 520, "Insert 3 accessible cross-keys", "label")
    sheet.text(x + 18, 543, "per half; index each 90°.", "label")
    sheet.text(x + 18, 580, "Cross-keys prevent withdrawal only;", "small")
    sheet.text(x + 18, 600, "they carry no shelf load.", "small")

    # Panel 3
    x = x_positions[2]
    sheet.rect(x + 32, 300, 90, 42, "petg")
    sheet.rect(x + 153, 300, 90, 42, "petg")
    sheet.rect(x + 79, 515, 117, 90, "petg-soft", rx=4)
    sheet.rect(x + 95, 490, 18, 32, "petg")
    sheet.rect(x + 162, 490, 18, 32, "petg")
    sheet.line(x + 137, 485, x + 137, 365, "motion")
    sheet.text(x + 18, 630, f"Bridge {exact(bridge['width_mm'],1)} × {exact(bridge['height_mm'],1)} × {exact(bridge['thickness_mm'],1)} mm", "label")
    sheet.text(x + 18, 653, "enters only upward from below.", "label")
    sheet.text(x + 18, 680, "No cassette removal required.", "small")

    # Panel 4
    x = x_positions[3]
    sheet.rect(x + 32, 300, 90, 42, "petg")
    sheet.rect(x + 153, 300, 90, 42, "petg")
    sheet.rect(x + 79, 342, 117, 90, "petg-soft", rx=4)
    sheet.line(x + 68, 342, x + 208, 342, "candidate")
    sheet.text(x + 18, 475, "Integral shoulders meet a", "label")
    sheet.text(x + 18, 498, "positive hard stop.", "label")
    sheet.text(x + 18, 540, f"Dovetail centers: u = ±{exact(abs(bridge['dovetail_rails']['u_centers_from_crown_mm'][0]),1)} mm", "small")
    sheet.text(
        x + 18,
        562,
        f"Bridge e envelope: {exact(bridge['final_y_envelope_mm'][0],1)}…{exact(bridge['final_y_envelope_mm'][1],1)} mm",
        "small",
    )
    sheet.text(
        x + 18,
        584,
        f"Swept depth envelope: {exact(bridge['assembled_swept_depth_envelope_mm'],1)} mm",
        "small",
    )

    # Panel 5
    x = x_positions[4]
    sheet.rect(x + 32, 300, 90, 42, "petg")
    sheet.rect(x + 153, 300, 90, 42, "petg")
    sheet.rect(x + 79, 342, 117, 90, "petg-soft", rx=4)
    sheet.circle(x + 170, 372, 8, "crown-node")
    sheet.line(x + 250, 372, x + 181, 372, "motion-blue")
    sheet.text(x + 18, 475, f"Insert one {exact(bridge['retention_pin_diameter_mm'],1)} mm PETG pin", "label")
    sheet.text(x + 18, 498, "through 5.4 mm double-shear hole", "label")
    sheet.text(x + 18, 532, "on RIGHT / fixed half only.", "callout")
    sheet.text(x + 18, 562, "Pin is anti-drop / reverse-slide", "small")
    sheet.text(x + 18, 582, "retention only; split tail captures positively.", "small")

    sheet.rect(50, 738, 1460, 165, "panel", rx=8)
    sheet.text(72, 772, "Service / removal sequence", "section")
    sheet.multiline(
        72,
        804,
        [
            "FULLY UNLOAD → remove ornament → squeeze/pull crown pin → lower bridge along −y → release/turn/withdraw all three cross-keys per half → lower each half vertically at final u.",
            f"Reserve ≥ {exact(bridge['minimum_straight_service_access_mm'],1)} mm straight visible-front or open-underside access. Pin center (u,y) = ({exact(bridge['retention_pin_center_u_y_mm'][0],1)}, {exact(bridge['retention_pin_center_u_y_mm'][1],1)}) mm; minimum boss = 19.4 × 19.4 mm; clear ligament = 7.0 mm.",
            "PROHIBITED: top-down bridge insertion · second fixed pin · friction-only keeper · hidden wall-side service · assigning shelf-load capacity to the pin.",
        ],
        line_height=27,
    )
    return sheet


def add_x_corbel(cfg: dict[str, Any], config_hash: str) -> Sheet:
    corbel_cfg = cfg["corbel"]
    tied = cfg["tied_arcade"]
    xgeo = x_corbel_geometry(cfg)
    sheet = Sheet(
        drawing_id="x-corbel-load-path",
        title="Exact 3 : 4 : 5 X-Corbel · Candidate Load Path",
        subtitle="Side elevation in wall projection x / frame elevation y; bearing and union continuity are test candidates",
        config_hash=config_hash,
        data={
            "data-horizontal-leg-mm": exact(xgeo.projection_mm),
            "data-vertical-leg-mm": exact(xgeo.vertical_leg_mm),
            "data-diagonal-mm": exact(xgeo.diagonal_mm),
            "data-crossing-mm": f"{exact(xgeo.brace_crossing[0])},{exact(xgeo.brace_crossing[1])}",
        },
    )
    ox, bottom, scale = 190.0, 800.0, 3.25
    sx = lambda value: ox + value * scale
    sy = lambda value: bottom - value * scale
    cradle = corbel_cfg["upper_diagonal_cassette_union_segment_mm"]
    cradle_from = tuple(float(value) for value in cradle["from"])
    cradle_to = tuple(float(value) for value in cradle["to"])
    screw_stations = [
        float(value) for value in corbel_cfg["provisional_wall_screw_station_y_mm"]
    ]
    screw_station_label = " / ".join(exact(value, 1) for value in screw_stations)
    sheet.rect(sx(-7), sy(174), 14 * scale, 180 * scale, "wall")
    sheet.rect(sx(0), sy(168), 144 * scale, 30 * scale, "deck")
    sheet.line(sx(xgeo.wall_upper_node[0]), sy(xgeo.wall_upper_node[1]), sx(xgeo.front_spring_node[0]), sy(xgeo.front_spring_node[1]), "candidate")
    sheet.line(sx(xgeo.wall_lower_node[0]), sy(xgeo.wall_lower_node[1]), sx(xgeo.front_saddle_node[0]), sy(xgeo.front_saddle_node[1]), "candidate-2")
    sheet.line(sx(cradle_from[0]), sy(cradle_from[1]), sx(cradle_to[0]), sy(cradle_to[1]), "union")
    for label, node in (
        (f"Wᵤ ({exact(xgeo.wall_upper_node[0])},{exact(xgeo.wall_upper_node[1])})", xgeo.wall_upper_node),
        (f"Fₛ ({exact(xgeo.front_spring_node[0])},{exact(xgeo.front_spring_node[1])})", xgeo.front_spring_node),
        (f"Wₗ ({exact(xgeo.wall_lower_node[0])},{exact(xgeo.wall_lower_node[1])})", xgeo.wall_lower_node),
        (f"Fᵦ ({exact(xgeo.front_saddle_node[0])},{exact(xgeo.front_saddle_node[1])})", xgeo.front_saddle_node),
        (f"X ({exact(xgeo.brace_crossing[0])},{exact(xgeo.brace_crossing[1])})", xgeo.brace_crossing),
    ):
        sheet.circle(sx(node[0]), sy(node[1]), 7 if label.startswith("X") else 5.5, "node")
        dx = 12 if node[0] < 100 else -12
        anchor = "start" if dx > 0 else "end"
        label_y = sy(node[1]) + (25 if label.startswith("Fᵦ") else -10)
        sheet.text(
            sx(node[0]) + dx,
            label_y,
            label,
            "inverse-label" if node == xgeo.wall_upper_node else "label",
            anchor=anchor,
            **({"fill": "#f7f0de"} if node == xgeo.wall_upper_node else {}),
        )

    for station in screw_stations:
        x = sx(0)
        y = sy(station)
        sheet.line(x - 8, y - 8, x + 8, y + 8, "candidate")
        sheet.line(x + 8, y - 8, x - 8, y + 8, "candidate")
        sheet.text(x - 20, y + 4, f"y {exact(station,1)}", "tiny", anchor="end")

    sheet.dim(sx(0), sy(15), sx(144), sy(15), "144 mm · 4 units", label_dy=20)
    sheet.dim(sx(156), sy(xgeo.wall_upper_node[1]), sx(156), sy(xgeo.front_spring_node[1]), "108 mm · 3 units", label_dx=48, label_dy=4)
    panel_x = 825
    sheet.rect(panel_x, 205, 700, 655, "panel", rx=8)
    sheet.text(panel_x + 20, 238, "Exact path geometry", "section")
    sheet.multiline(
        panel_x + 20,
        270,
        [
            f"RED: upper wall node ({exact(xgeo.wall_upper_node[0])},{exact(xgeo.wall_upper_node[1])}) → front spring ({exact(xgeo.front_spring_node[0])},{exact(xgeo.front_spring_node[1])})",
            f"BLUE: lower wall node ({exact(xgeo.wall_lower_node[0])},{exact(xgeo.wall_lower_node[1])}) → integral cap at cassette underside ({exact(xgeo.front_saddle_node[0])},{exact(xgeo.front_saddle_node[1])})",
            "Each diagonal: √(144² + 108²) = 180 mm · exact 3:4:5",
            f"GOLD CRADLE: ({exact(cradle_from[0])},{exact(cradle_from[1])}) → ({exact(cradle_to[0])},{exact(cradle_to[1])}) in rear cassette",
            f"Both 12 mm paths union through ≥ 24 mm boss at x={exact(xgeo.brace_crossing[0])}, y={exact(xgeo.brace_crossing[1])}",
        ],
        line_height=22,
    )
    sheet.text(panel_x + 20, 390, "What is — and is not — being claimed", "section")
    sheet.multiline(
        panel_x + 20,
        424,
        [
            "CANDIDATE CONTINUITY",
            "• front spring shoulder → upper wall node",
            "• cassette underside / integral bearing cap → lower wall node",
            "• crossing boss joins both diagonal paths as one body",
            "• upper diagonal is unioned into the cassette-zone rear rib",
            "",
            "NO CAPACITY CLAIM",
            "The PETG corbel is anisotropic and creep-sensitive. These paths may",
            "share compression, bending, tension and shear only after exact-orientation",
            "coupon, full-corbel, full-bay, destructive and sustained-load testing.",
            "",
            "WALL BOUNDARY IS FAIL-CLOSED",
            f"Three red X marks at y = {screw_station_label} mm are provisional targets only.",
            "Clearance bores, head/washer pockets, bosses and driver tunnels remain",
            "BLOCKED until the exact metal screw, head/washer, embedment, wall finish,",
            "driver envelope, verified stud/blocking and utility-clearance method exist.",
            "",
            "Metal structural screws with suitable heads/washers into verified",
            "wood studs or purpose-installed blocking remain the only nonprinted boundary.",
        ],
        line_height=22,
    )
    return sheet


def add_corner_clearance(cfg: dict[str, Any], config_hash: str) -> Sheet:
    plan = calculate_plan(cfg)
    corner = cfg["closet"]["inside_corner"]
    visible_base_gap = float(corner["return_corner_visible_base_relief_gap_mm"])
    visible_base_leading = plan.corner_visible_front_plane_absolute_mm + visible_base_gap
    projection = float(cfg["corbel"]["shelf_arm_length_mm"])
    cap_profile = cfg["corbel"]["integrated_bearing_cap"]["run_e_profile_polygon_mm"]
    cap_half_run = max(abs(float(point[0])) for point in cap_profile)
    through_nose = plan.through_back_clearance_mm + projection
    visible_front = plan.corner_visible_front_plane_absolute_mm
    return_near_edge = plan.return_run.support_centers_absolute_mm[0] - cap_half_run
    sheet = Sheet(
        drawing_id="corner-ownership-clearance",
        title="Inside Corner Ownership · Fit / Clearance Gate",
        subtitle="Through arm owns the corner square; return structure clears the full removable-facade service stroke",
        config_hash=config_hash,
        data={
            "data-corner-gap-mm": exact(plan.corner_gap_mm),
            "data-corner-front-plane-mm": exact(plan.corner_front_plane_absolute_mm),
            "data-corner-visible-front-plane-mm": exact(visible_front),
            "data-integral-boss-projection-mm": exact(plan.integral_boss_projection_beyond_cassette_mm),
            "data-full-removable-facade-projection-mm": exact(plan.full_removable_facade_projection_beyond_cassette_mm),
            "data-ornament-axial-service-stroke-mm": exact(plan.ornament_axial_service_stroke_mm),
            "data-service-swept-front-plane-mm": exact(plan.corner_service_swept_front_plane_absolute_mm),
            "data-return-cosmetic-leading-plane-mm": exact(plan.return_corner_cosmetic_leading_plane_absolute_mm),
            "data-return-visible-base-leading-plane-mm": exact(visible_base_leading),
            "data-locked-all-solid-gap-mm": exact(plan.corner_gap_mm),
            "data-visible-base-relief-gap-mm": exact(visible_base_gap),
            "data-structural-arm-clearance-mm": exact(plan.structural_arm_clearance_mm),
            "data-first-through-crown-mm": exact(plan.through.start_from_corner_mm + plan.through.crown_seam_stations_local_mm[0]),
            "data-perpendicular-corbel-clearance-mm": exact(plan.minimum_perpendicular_corbel_clearance_mm),
            "data-visible-front-corbel-plan-reserve-mm": exact(plan.minimum_visible_front_to_perpendicular_corbel_plan_reserve_mm),
            "data-service-swept-front-corbel-plan-reserve-mm": exact(plan.minimum_service_swept_front_to_perpendicular_corbel_plan_reserve_mm),
        },
    )
    ox, oy, scale = 150.0, 230.0, 2.45
    sx = lambda value: ox + value * scale
    sy = lambda value: oy + value * scale
    sheet.rect(sx(-10), sy(-10), 340 * scale, 16 * scale, "wall")
    sheet.rect(sx(-10), sy(-10), 16 * scale, 285 * scale, "wall")
    sheet.rect(sx(plan.through.start_from_corner_mm), sy(plan.through_back_clearance_mm), 320 * scale, plan.depth_mm * scale, "deck", rx=3)
    sheet.rect(sx(plan.return_back_clearance_mm), sy(plan.return_run.start_from_corner_mm), plan.depth_mm * scale, 105 * scale, "deck", rx=3)
    sheet.rect(sx(plan.through.start_from_corner_mm), sy(plan.through_back_clearance_mm), plan.depth_mm * scale, plan.depth_mm * scale, "petg-soft", rx=3)
    sheet.text(sx(20), sy(62), "THROUGH ARM OWNS", "inverse", fill="#f7f0de")
    sheet.text(sx(20), sy(73), "152.4 × 152.4 mm", "inverse", fill="#f7f0de")
    sheet.text(sx(20), sy(84), "CORNER SQUARE", "inverse", fill="#f7f0de")

    front = plan.corner_front_plane_absolute_mm
    first_crown = plan.through.start_from_corner_mm + plan.through.crown_seam_stations_local_mm[0]
    sheet.line(sx(first_crown), sy(plan.through_back_clearance_mm), sx(first_crown), sy(front), "seam-fixed")
    sheet.circle(sx(first_crown), sy(plan.through_back_clearance_mm + 25), 6, "crown-node")
    sheet.text(sx(first_crown) + 12, sy(36), "first through crown = 158.75 mm", "inverse", fill="#f7f0de")
    sheet.text(sx(first_crown) + 12, sy(44), "exactly aligns corner front plane", "inverse", fill="#f7f0de")

    sheet.rect(
        sx(10),
        sy(front),
        305 * scale,
        plan.full_removable_facade_projection_beyond_cassette_mm * scale,
        "petg-soft",
    )
    sheet.rect(
        sx(10),
        sy(visible_front),
        305 * scale,
        plan.corner_gap_mm * scale,
        "clearance",
    )
    sheet.rect(
        sx(245),
        sy(plan.return_corner_cosmetic_leading_plane_absolute_mm),
        65 * scale,
        plan.return_corner_cosmetic_overhang_back_mm * scale,
        "petg-soft",
    )
    sheet.dim(
        sx(290),
        sy(visible_front),
        sx(290),
        sy(plan.return_corner_cosmetic_leading_plane_absolute_mm),
        f"{exact(plan.corner_gap_mm,1)} mm LOCKED ALL-SOLID GAP",
        label_dx=78,
        label_dy=4,
    )
    sheet.line(sx(0), sy(front), sx(330), sy(front), "construction")
    sheet.text(sx(200), sy(front) - 8, f"structural front {exact(front,2)} mm", "inverse")
    sheet.line(sx(0), sy(visible_front), sx(330), sy(visible_front), "construction")
    sheet.text(sx(15), sy(visible_front) - 8, f"full locked facade front {exact(visible_front,2)} mm", "inverse")
    sheet.line(sx(238), sy(visible_base_leading), sx(330), sy(visible_base_leading), "construction")
    sheet.text(sx(160), sy(visible_base_leading) + 15, f"relieved visible base starts {exact(visible_base_leading,2)} mm", "tiny")
    sheet.line(sx(0), sy(plan.corner_service_swept_front_plane_absolute_mm), sx(330), sy(plan.corner_service_swept_front_plane_absolute_mm), "motion-blue")
    sheet.text(sx(160), sy(plan.corner_service_swept_front_plane_absolute_mm) - 8, f"max 4.4 mm service face {exact(plan.corner_service_swept_front_plane_absolute_mm,2)} mm", "inverse")
    sheet.line(sx(0), sy(plan.return_run.start_from_corner_mm), sx(330), sy(plan.return_run.start_from_corner_mm), "construction")
    sheet.text(sx(15), sy(plan.return_run.start_from_corner_mm) + 20, f"return structure starts {exact(plan.return_run.start_from_corner_mm,2)} mm", "inverse")

    # Perpendicular corbel-clearance chain.
    sheet.line(sx(55), sy(through_nose), sx(130), sy(through_nose), "candidate")
    sheet.line(sx(55), sy(return_near_edge), sx(130), sy(return_near_edge), "candidate-2")
    sheet.line(
        sx(95),
        sy(through_nose),
        sx(95),
        sy(return_near_edge),
        "dimension",
        marker_start="url(#dim-arrow)",
        marker_end="url(#dim-arrow)",
    )
    sheet.line(sx(145), sy(visible_front), sx(185), sy(visible_front), "petg-soft")
    sheet.line(
        sx(165),
        sy(visible_front),
        sx(165),
        sy(return_near_edge),
        "dimension",
        marker_start="url(#dim-arrow)",
        marker_end="url(#dim-arrow)",
    )
    sheet.rect(650, 735, 320, 76, "panel", rx=6)
    sheet.text(670, 763, "INTEGRAL-CAP / CORBEL GAP", "small")
    sheet.text(670, 790, f"{exact(plan.minimum_perpendicular_corbel_clearance_mm,4)} mm", "dimension-text")
    sheet.line(650, 755, sx(95) + 8, (sy(through_nose) + sy(return_near_edge)) / 2, "hairline")
    sheet.rect(650, 825, 320, 76, "panel", rx=6)
    sheet.text(670, 853, "LOCKED FACADE / CAP RESERVE", "small")
    sheet.text(670, 880, f"{exact(plan.minimum_visible_front_to_perpendicular_corbel_plan_reserve_mm,4)} mm", "dimension-text")
    sheet.line(650, 845, sx(165) + 8, (sy(visible_front) + sy(return_near_edge)) / 2, "hairline")

    first_return_support = plan.return_run.support_centers_absolute_mm[0]
    sheet.circle(sx(plan.return_back_clearance_mm + plan.depth_mm - 20), sy(first_return_support), 7, "support-node")
    sheet.text(sx(plan.return_back_clearance_mm + plan.depth_mm + 8), sy(first_return_support) + 5, f"R1 center {exact(first_return_support,4)} mm", "label")

    panel_x = 1010
    sheet.rect(panel_x, 205, 520, 655, "panel", rx=8)
    sheet.text(panel_x + 20, 240, "Corner fit rules", "section")
    sheet.multiline(
        panel_x + 20,
        275,
        [
            f"Wall-plane datum: finished-wall intersection (0,0)",
            f"Back clearances: {exact(plan.through_back_clearance_mm,2)} mm on both walls",
            f"Through arm start: {exact(plan.through.start_from_corner_mm,2)} mm",
            f"Structural cassette front plane: {exact(front,2)} mm",
            f"Integral boss / full facade projection: {exact(plan.integral_boss_projection_beyond_cassette_mm,1)} / {exact(plan.full_removable_facade_projection_beyond_cassette_mm,1)} mm",
            f"Full locked facade front plane: {exact(visible_front,2)} mm",
            f"Axial ornament service stroke: {exact(plan.ornament_axial_service_stroke_mm,1)} mm",
            f"Return cosmetic leading solid: {exact(plan.return_corner_cosmetic_leading_plane_absolute_mm,2)} mm",
            f"Return relieved visible base: {exact(visible_base_leading,2)} mm",
            f"Return structural arm start: {exact(plan.return_run.start_from_corner_mm,2)} mm",
            f"Structural arm clearance: {exact(plan.structural_arm_clearance_mm,1)} mm",
            f"Locked all-solid / visible-base gaps: {exact(plan.corner_gap_mm,1)} / {exact(visible_base_gap,1)} mm",
            f"Minimum residual solid gap: {exact(corner['minimum_residual_visible_joint_clearance_mm'],2)} mm",
            f"Maximum nominal square deviation: ±{exact(corner['maximum_square_corner_deviation_deg'],1)}°",
            "",
            f"First through crown error: {exact(plan.exact_crown_alignment_error_mm,1)} mm",
            f"Nominal perpendicular corbel clearance: {exact(plan.minimum_perpendicular_corbel_clearance_mm,4)} mm",
            f"Locked facade to perpendicular-cap reserve: {exact(plan.minimum_visible_front_to_perpendicular_corbel_plan_reserve_mm,4)} mm",
            f"Service-swept-front to perpendicular-cap reserve: {exact(plan.minimum_service_swept_front_to_perpendicular_corbel_plan_reserve_mm,4)} mm",
            "",
            "FIELD GATE",
            "Measure both clear wall widths, both installed back clearances, wall bow,",
            "inside angle at shelf elevation, trim/door interference and every verified",
            "support center. Regenerate if any value differs from this nominal snapshot.",
            "",
            "MOVEMENT RULE",
            "Remove the floating return-corner finish first; only then may the fixed",
            "through rosette use its full axial stroke. Each arm remains independently corbel-",
            "supported; the cosmetic corner closure receives zero structural credit.",
            "",
            "NO printed wall anchors · NO hollow-wall primary anchors · NO adhesive.",
            "Metal screws/washers into verified studs or blocking are still required.",
        ],
        line_height=18,
    )
    sheet.path("M 760 300 L 800 300 L 800 340", "deco")
    sheet.path("M 760 300 A 40 40 0 0 1 800 340", "deco")
    sheet.text(650, 365, f"NOMINAL 90° · verify within ±{exact(corner['maximum_square_corner_deviation_deg'],1)}°", "inverse-callout", fill="#f7f0de")
    return sheet


def build_sheets(cfg: dict[str, Any], config_hash: str) -> dict[str, Sheet]:
    """Return all drawing sheets without touching the filesystem."""

    sheets = {
        "plan_layout.svg": add_plan_layout(cfg, config_hash),
        "palatine_3_6_elevation.svg": add_palatine_elevation(cfg, config_hash),
        "two_level_vertical_layout.svg": add_two_level_layout(cfg, config_hash),
        "exploded_joinery.svg": add_exploded_joinery(cfg, config_hash),
        "crown_assembly_sequence.svg": add_crown_sequence(cfg, config_hash),
        "x_corbel_load_path.svg": add_x_corbel(cfg, config_hash),
        "corner_ownership_clearance.svg": add_corner_clearance(cfg, config_hash),
    }
    if tuple(sheets) != DRAWING_FILENAMES:
        raise AssertionError("Drawing set drifted from the declared deterministic order")
    return sheets


def generate_drawings(
    *,
    config_path: Path = CONFIG_PATH,
    out_dir: Path = DRAWINGS_OUT,
) -> tuple[Path, ...]:
    """Generate all seven SVGs and return paths in canonical order."""

    cfg, payload = load_config(config_path)
    config_hash = sha256(payload)
    sheets = build_sheets(cfg, config_hash)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename in DRAWING_FILENAMES:
        path = out_dir / filename
        path.write_text(sheets[filename].render(), encoding="utf-8", newline="\n")
        paths.append(path)
    return tuple(paths)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--out", type=Path, default=DRAWINGS_OUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    paths = generate_drawings(config_path=args.config, out_dir=args.out)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
