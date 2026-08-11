#!/usr/bin/env python3
"""Render the frozen R7 v4 collar-hook as a deterministic SVG proof plate.

This is a read-only consumer of the v4 source and generated STLs.  It refuses
to render if any frozen source or STL digest differs from the audited values.
"""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import sys
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union


ASSET_DIR = Path(__file__).resolve().parent
R7_DIR = ASSET_DIR.parent
OUTPUT = ASSET_DIR / "cable_hook_cad_proof_v4.svg"
V4_DIR = R7_DIR / "generated" / "cable_peg_qualification_v4"

EXPECTED_SHA256 = {
    R7_DIR / "config.json": "bac5fdc0f1857ca03d786900984d946795706bc63527cae8b3aff7f8d7401f0a",
    R7_DIR / "cable_peg_geometry.py": "bf014de9c39899a204780c7f7ecf5b0ffdef42764d9c7cc8ea00e1aa3beb00e5",
    V4_DIR / "stl" / "R7_DEV_CABLE_PEG_EXACT_R6_PIER_OVERLAY_COUPON.stl": (
        "42a9ba68475d8ab2ad8c7590be76ac6ab1592d7a8e22b15cedea5281ab009755"
    ),
    V4_DIR / "stl" / "R7_DEV_CABLE_PEG_FRONT_SNAP_C_COLLAR_HOOK.stl": (
        "b8d2dada22c4273e790124310c61ee493ecd2c496256d50fb817b12967b907d1"
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


for frozen_path, expected in EXPECTED_SHA256.items():
    actual = sha256(frozen_path)
    if actual != expected:
        raise RuntimeError(
            f"Frozen v4 input changed: {frozen_path} expected {expected}, got {actual}"
        )

spec = importlib.util.spec_from_file_location(
    "r7_frozen_cable_peg_geometry", R7_DIR / "cable_peg_geometry.py"
)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot import frozen v4 cable-hook source")
geometry = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = geometry
spec.loader.exec_module(geometry)

cfg = geometry.load_config(R7_DIR / "config.json")
overlay = geometry.reference_pier_overlay_mesh()
hook = geometry.cable_hook_mesh(cfg)
cable = geometry.cable_bundle_envelope_mesh(cfg)
components = geometry._collar_components(cfg)
compressed = geometry.compressed_approach_components(cfg)
metrics = geometry.validate_geometry(cfg)

manifest = json.loads((V4_DIR / "manifest.json").read_text())
manifest_metrics = manifest["hook_metrics"]
if abs(float(hook.volume) - float(manifest_metrics["volume_mm3"])) > 1.0e-5:
    raise RuntimeError("Installed source hook no longer matches v4 manifest volume")
if abs(float(metrics.saved_plate_contact_area_mm2) - 196.28230989079876) > 1.0e-8:
    raise RuntimeError("v4 saved plate-contact metric drifted")


def fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def rgb_shade(base: tuple[int, int, int], shade: float) -> str:
    values = [max(0, min(255, round(channel * shade))) for channel in base]
    return f"rgb({values[0]},{values[1]},{values[2]})"


def geometry_to_path(
    shape: Polygon | MultiPolygon,
    mapper: Callable[[float, float], tuple[float, float]],
) -> str:
    polygons: Iterable[Polygon]
    if isinstance(shape, Polygon):
        polygons = [shape]
    elif isinstance(shape, MultiPolygon):
        polygons = shape.geoms
    else:
        polygons = [item for item in shape.geoms if isinstance(item, Polygon)]
    commands: list[str] = []
    for polygon in polygons:
        for ring in [polygon.exterior, *polygon.interiors]:
            points = [mapper(float(x), float(y)) for x, y in ring.coords]
            if len(points) < 3:
                continue
            commands.append(f"M {fmt(points[0][0])} {fmt(points[0][1])}")
            commands.extend(f"L {fmt(x)} {fmt(y)}" for x, y in points[1:])
            commands.append("Z")
    return " ".join(commands)


def projected_silhouette(
    mesh: trimesh.Trimesh,
    coordinate: Callable[[np.ndarray], tuple[float, float]],
    crop: tuple[float, float, float, float] | None = None,
):
    triangles: list[Polygon] = []
    for triangle in np.asarray(mesh.triangles, dtype=float):
        polygon = Polygon([coordinate(vertex) for vertex in triangle])
        if polygon.is_valid and polygon.area > 1.0e-9:
            triangles.append(polygon)
    output = unary_union(triangles)
    if crop is not None:
        output = output.intersection(box(*crop))
    return output


def section_path(
    mesh: trimesh.Trimesh,
    *,
    plane_origin: tuple[float, float, float],
    plane_normal: tuple[float, float, float],
    coordinate: Callable[[np.ndarray], tuple[float, float]],
    mapper: Callable[[float, float], tuple[float, float]],
) -> str:
    section = mesh.section(plane_origin=plane_origin, plane_normal=plane_normal)
    if section is None:
        return ""
    commands: list[str] = []
    for loop in section.discrete:
        points = [mapper(*coordinate(np.asarray(vertex, dtype=float))) for vertex in loop]
        if len(points) < 3:
            continue
        commands.append(f"M {fmt(points[0][0])} {fmt(points[0][1])}")
        commands.extend(f"L {fmt(x)} {fmt(y)}" for x, y in points[1:])
        commands.append("Z")
    return " ".join(commands)


def oblique_scene(
    mesh_specs: list[tuple[trimesh.Trimesh, tuple[int, int, int], str]],
    *,
    left: float,
    top: float,
    width: float,
    height: float,
):
    u = np.array([0.82, 0.0, 0.57], dtype=float)
    v = np.array([-0.10, -0.98, 0.14], dtype=float)
    u /= np.linalg.norm(u)
    v /= np.linalg.norm(v)
    view = np.cross(u, v)
    view /= np.linalg.norm(view)
    light = np.array([-0.35, -0.65, -0.68], dtype=float)
    light /= np.linalg.norm(light)

    all_vertices = np.vstack([np.asarray(item[0].vertices) for item in mesh_specs])
    raw_x = all_vertices @ u
    raw_y = all_vertices @ v
    min_x, max_x = float(raw_x.min()), float(raw_x.max())
    min_y, max_y = float(raw_y.min()), float(raw_y.max())
    scale = min(width / (max_x - min_x), height / (max_y - min_y))
    pad_x = left + (width - (max_x - min_x) * scale) / 2.0
    pad_y = top + (height - (max_y - min_y) * scale) / 2.0

    def map_world(point: np.ndarray | tuple[float, float, float]):
        point = np.asarray(point, dtype=float)
        return (
            pad_x + (float(point @ u) - min_x) * scale,
            pad_y + (float(point @ v) - min_y) * scale,
        )

    records: list[tuple[float, str]] = []
    for mesh, base, name in mesh_specs:
        for triangle, normal in zip(mesh.triangles, mesh.face_normals, strict=True):
            projected = [map_world(vertex) for vertex in triangle]
            depth = float(np.mean(np.asarray(triangle) @ view))
            illumination = 0.56 + 0.34 * max(-0.35, float(np.dot(normal, light)))
            fill = rgb_shade(base, illumination)
            opacity = "0.94" if name == "cable" else "1"
            points = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in projected)
            records.append(
                (
                    depth,
                    f'<polygon points="{points}" fill="{fill}" fill-opacity="{opacity}" '
                    f'stroke="#111" stroke-opacity="0.11" stroke-width="0.35"/>',
                )
            )
    records.sort(key=lambda item: item[0])
    markup = "".join(item[1] for item in records)

    for mesh, _, name in mesh_specs:
        projected_faces: list[Polygon] = []
        for triangle in mesh.triangles:
            poly = Polygon([map_world(vertex) for vertex in triangle])
            if poly.is_valid and poly.area > 1.0e-6:
                projected_faces.append(poly)
        silhouette = unary_union(projected_faces)
        outline = geometry_to_path(silhouette, lambda x, y: (x, y))
        stroke = {"overlay": "#1c1b19", "hook": "#075e5d", "cable": "#a6651d"}[name]
        markup += (
            f'<path d="{outline}" fill="none" stroke="{stroke}" stroke-width="1.8" '
            f'stroke-linejoin="round"/>'
        )
    return markup, map_world


hook_cfg = cfg["cable_hook"]
cable_center_y = (
    sum(float(value) for value in hook_cfg["collar_band_elevation_mm"]) / 2.0
    + float(hook_cfg["hook_stem_radius_mm"])
    + float(hook_cfg["maximum_qualified_cable_bundle_diameter_mm"]) / 2.0
)

main_markup, main_map = oblique_scene(
    [
        (overlay, (61, 59, 55), "overlay"),
        (hook, (20, 139, 132), "hook"),
        (cable, (224, 155, 53), "cable"),
    ],
    left=90,
    top=270,
    width=545,
    height=540,
)


def side_mapper(z_value: float, y_value: float) -> tuple[float, float]:
    z_min = -31.0
    y_min = 16.0
    equal_scale = 10.0
    return (
        1120.0 + (z_value - z_min) * equal_scale,
        480.0 - (y_value - y_min) * equal_scale,
    )


side_crop = (-31.0, 16.0, 11.0, 39.0)
overlay_side = projected_silhouette(overlay, lambda p: (float(p[2]), float(p[1])), side_crop)
hook_side = projected_silhouette(hook, lambda p: (float(p[2]), float(p[1])), side_crop)
cable_side = projected_silhouette(cable, lambda p: (float(p[2]), float(p[1])), side_crop)
overlay_side_path = geometry_to_path(overlay_side, side_mapper)
hook_side_path = geometry_to_path(hook_side, side_mapper)
cable_side_path = geometry_to_path(cable_side, side_mapper)


def top_mapper_factory(
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    z_min: float = -41.0,
    z_max: float = 12.0,
):
    equal_scale = min(width / 45.0, height / (z_max - z_min))
    x_padding = (width - 45.0 * equal_scale) / 2.0
    z_padding = (height - (z_max - z_min) * equal_scale) / 2.0

    def mapper(x_value: float, z_value: float):
        return (
            left + x_padding + (x_value + 5.0) * equal_scale,
            top + z_padding + (z_max - z_value) * equal_scale,
        )

    return mapper


seated_map = top_mapper_factory(1010, 633, 300, 196, z_min=-31.0)
spread_map = top_mapper_factory(1400, 633, 300, 196)
slice_y = 26.013
slice_kw = {
    "plane_origin": (0.0, slice_y, 0.0),
    "plane_normal": (0.0, 1.0, 0.0),
    "coordinate": lambda p: (float(p[0]), float(p[2])),
}
overlay_seated_path = section_path(overlay, mapper=seated_map, **slice_kw)
hook_seated_path = section_path(hook, mapper=seated_map, **slice_kw)
overlay_spread_path = section_path(overlay, mapper=spread_map, **slice_kw)
spread_paths: list[str] = []
for component in compressed:
    moved = component.copy()
    moved.apply_translation((0.0, 0.0, -10.0))
    spread_paths.append(section_path(moved, mapper=spread_map, **slice_kw))


def stop_mapper(z_value: float, y_value: float):
    z_min, z_max = 2.5, 6.7
    y_min, y_max = 16.4, 23.6
    return (
        335.0 + (z_value - z_min) / (z_max - z_min) * 285.0,
        1088.0 - (y_value - y_min) / (y_max - y_min) * 100.0,
    )


stop_x = 1.513
stop_kw = {
    "plane_origin": (stop_x, 0.0, 0.0),
    "plane_normal": (1.0, 0.0, 0.0),
    "coordinate": lambda p: (float(p[2]), float(p[1])),
}
overlay_stop_path = section_path(overlay, mapper=stop_mapper, **stop_kw)
hook_stop_path = section_path(hook, mapper=stop_mapper, **stop_kw)


def marker(number: int, world: tuple[float, float, float]) -> str:
    x, y = main_map(np.asarray(world, dtype=float))
    return (
        f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="14" fill="#fffaf0" '
        f'stroke="#c07d2a" stroke-width="3"/>'
        f'<text x="{fmt(x)}" y="{fmt(y + 5)}" text-anchor="middle" '
        f'class="marker-number">{number}</text>'
    )


svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1200" viewBox="0 0 1800 1200"
     role="img" data-drawing="r7-v4-cable-hook-cad-proof"
     data-config-sha256="{EXPECTED_SHA256[R7_DIR / 'config.json']}"
     data-source-sha256="{EXPECTED_SHA256[R7_DIR / 'cable_peg_geometry.py']}"
     data-v4-overlay-stl-sha256="{EXPECTED_SHA256[V4_DIR / 'stl' / 'R7_DEV_CABLE_PEG_EXACT_R6_PIER_OVERLAY_COUPON.stl']}"
     data-v4-hook-stl-sha256="{EXPECTED_SHA256[V4_DIR / 'stl' / 'R7_DEV_CABLE_PEG_FRONT_SNAP_C_COLLAR_HOOK.stl']}"
     data-rated-load-kg="0" data-qualification-only="true">
  <title>R7 v4 exact CAD proof — removable front-snap cable hook on R6 pier overlay</title>
  <desc>Installed oblique view, installed side profile, manual jaw-spread top sections, and vertical-stop detail derived directly from the frozen v4 source meshes. Qualification only, zero rated load.</desc>
  <defs>
    <linearGradient id="page" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbf8ef"/><stop offset="1" stop-color="#eee2cc"/></linearGradient>
    <linearGradient id="teal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2db0a8"/><stop offset="1" stop-color="#075e5d"/></linearGradient>
    <pattern id="redHatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="10" height="10" fill="#fae7e2"/><line y2="10" stroke="#bf4636" stroke-width="3" opacity=".25"/></pattern>
    <filter id="shadow" x="-15%" y="-15%" width="130%" height="140%"><feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#302a22" flood-opacity=".17"/></filter>
    <marker id="arrowTeal" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L9 4.5 L0 9 Z" fill="#0d7773"/></marker>
    <marker id="arrowRed" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L9 4.5 L0 9 Z" fill="#b64134"/></marker>
    <marker id="dimArrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0 4 L8 0 L8 8 Z" fill="#245f61"/></marker>
    <clipPath id="stopClip"><rect x="325" y="985" width="310" height="108" rx="4"/></clipPath>
    <style>
      text {{ font-family: Arial, Helvetica, sans-serif; fill: #292621; }}
      .title {{ font-family: Georgia, 'Times New Roman', serif; font-size: 36px; font-weight: 700; }}
      .subtitle {{ font-size: 17px; font-weight: 800; letter-spacing: 1px; fill: #4a443b; }}
      .panel-title {{ font-family: Georgia, 'Times New Roman', serif; font-size: 21px; font-weight: 700; }}
      .label {{ font-size: 13px; font-weight: 800; }}
      .note {{ font-size: 12px; fill: #514a40; }}
      .tiny {{ font-size: 10px; fill: #5b5348; }}
      .inverse {{ fill: #fff9f4; }}
      .teal-text {{ fill: #0b6663; }}
      .red-text {{ fill: #9f372e; }}
      .marker-number {{ font-size: 14px; font-weight: 900; fill: #9a5c18; }}
      .dimension {{ fill: none; stroke: #245f61; stroke-width: 1.7; marker-start: url(#dimArrow); marker-end: url(#dimArrow); }}
      .leader {{ fill: none; stroke: #6c604f; stroke-width: 1.4; }}
    </style>
  </defs>

  <rect width="1800" height="1200" fill="url(#page)"/>
  <rect x="20" y="20" width="1760" height="1160" rx="16" fill="none" stroke="#352f28" stroke-width="2"/>
  <path d="M52 68 H145 L170 44 H1630 L1655 68 H1748" fill="none" stroke="#b47a2b" stroke-width="3"/>
  <text x="68" y="82" class="title">R7 v4 removable cable hook · exact CAD proof</text>
  <text x="68" y="116" class="subtitle">FROZEN HOOK MESH + EXACT R6 PIER-OVERLAY COUPON · INSTALLED / SIDE / SNAP / STOP VIEWS</text>
  <rect x="68" y="132" width="1664" height="40" rx="7" fill="#97372e"/>
  <text x="900" y="158" text-anchor="middle" font-size="17" font-weight="900" letter-spacing=".8" class="inverse">ZERO RATED LOAD · QUALIFICATION ONLY · NOT AN INSTALLED RELEASE</text>

  <rect x="55" y="194" width="850" height="706" rx="14" fill="#fffaf0" stroke="#9f9077" stroke-width="1.5" filter="url(#shadow)"/>
  <text x="82" y="229" class="panel-title">Installed on the exact R6 pier overlay</text>
  <text x="82" y="251" class="note">Orthographic CAD projection · no geometry invented · black = R6 overlay · teal = v4 collar-hook · gold = Ø5 mm cable envelope</text>
  {main_markup}
  {marker(1, (17.2, 23.2, -16.0))}
  {marker(2, (1.5, 19.2, 4.8))}
  {marker(3, (17.2, cable_center_y, -18.0))}
  <g transform="translate(655 302)">
    <circle cx="0" cy="0" r="14" fill="#fffaf0" stroke="#c07d2a" stroke-width="3"/><text x="0" y="5" text-anchor="middle" class="marker-number">1</text>
    <text x="26" y="-2" class="label">Front-snap bridge</text><text x="26" y="17" class="note">open center; square rear lips</text>
    <circle cx="0" cy="78" r="14" fill="#fffaf0" stroke="#c07d2a" stroke-width="3"/><text x="0" y="83" text-anchor="middle" class="marker-number">2</text>
    <text x="26" y="76" class="label">Vertical stop feet</text><text x="26" y="95" class="note">0.2 mm free travel before support</text>
    <circle cx="0" cy="156" r="14" fill="#fffaf0" stroke="#c07d2a" stroke-width="3"/><text x="0" y="161" text-anchor="middle" class="marker-number">3</text>
    <text x="26" y="154" class="label">Cable seat</text><text x="26" y="173" class="note">18.0 mm from visible face</text>
    <line x1="0" y1="213" x2="198" y2="213" stroke="#c8b99f"/>
    <text x="0" y="240" class="label" fill="#0a6966">Actual installed bounds</text>
    <text x="0" y="261" class="note">39.56 × 14.50 × 34.50 mm</text>
    <text x="0" y="282" class="note">2.995 g estimated PETG</text>
    <text x="0" y="303" class="note">one closed positive-volume body</text>
    <rect x="0" y="336" width="202" height="74" rx="8" fill="#e5f3ee" stroke="#25847f"/>
    <text x="14" y="360" class="label" fill="#0d6562">Detachable accessory</text>
    <text x="14" y="380" class="note">Remove before facade or</text>
    <text x="14" y="398" class="note">cross-key service.</text>
  </g>
  <text x="82" y="870" class="tiny">Installed source mesh volume {fmt(float(hook.volume))} mm³ · seated overlap with exact overlay {fmt(float(metrics.maximum_seated_overlay_overlap_mm3))} mm³</text>

  <rect x="930" y="194" width="815" height="330" rx="14" fill="#fffaf0" stroke="#9f9077" stroke-width="1.5" filter="url(#shadow)"/>
  <text x="958" y="229" class="panel-title">Installed side profile · cable geometry</text>
  <text x="958" y="251" class="note">Exact orthographic silhouette cropped to the collar band; depth is normal to the visible overlay face.</text>
  <path d="{overlay_side_path}" fill="#373633" stroke="#151514" stroke-width="1.5" fill-rule="evenodd"/>
  <path d="{hook_side_path}" fill="url(#teal)" fill-opacity=".94" stroke="#075e5d" stroke-width="1.8" fill-rule="evenodd"/>
  <path d="{cable_side_path}" fill="#e5a43e" stroke="#9f611c" stroke-width="1.6" fill-rule="evenodd"/>
  <line x1="{fmt(side_mapper(0,16)[0])}" y1="266" x2="{fmt(side_mapper(0,16)[0])}" y2="486" stroke="#9b8c73" stroke-width="1.2" stroke-dasharray="5 4"/>
  <text x="{fmt(side_mapper(0,16)[0] + 6)}" y="273" class="tiny">VISIBLE FACE z = 0</text>
  <line x1="{fmt(side_mapper(-18,37)[0])}" y1="{fmt(side_mapper(-18,37)[1])}" x2="{fmt(side_mapper(0,37)[0])}" y2="{fmt(side_mapper(0,37)[1])}" class="dimension"/>
  <text x="{fmt((side_mapper(-18,37)[0]+side_mapper(0,37)[0])/2)}" y="{fmt(side_mapper(0,37)[1]-8)}" text-anchor="middle" class="label" fill="#245f61">18.0 mm cable seat</text>
  <line x1="{fmt(side_mapper(-21.5,cable_center_y-2.5)[0])}" y1="{fmt(side_mapper(-21.5,cable_center_y-2.5)[1])}" x2="{fmt(side_mapper(-21.5,cable_center_y+2.5)[0])}" y2="{fmt(side_mapper(-21.5,cable_center_y+2.5)[1])}" class="dimension"/>
  <text x="{fmt(side_mapper(-21.5,cable_center_y)[0]-8)}" y="{fmt(side_mapper(-21.5,cable_center_y)[1]+4)}" text-anchor="end" class="label" fill="#9f611c">Ø5.0</text>
  <path d="M {fmt(side_mapper(-16,23.2)[0])} {fmt(side_mapper(-16,23.2)[1])} L 1180 295" class="leader"/>
  <text x="1060" y="292" class="label">front bridge / snap root</text>
  <path d="M {fmt(side_mapper(-25.5,31)[0])} {fmt(side_mapper(-25.5,31)[1])} L 1035 445" class="leader"/>
  <text x="958" y="462" class="label">5.0 mm upturned tip</text>
  <text x="1425" y="507" class="tiny">Maximum cable envelope clears collar and tip; modeled overlap = 0 mm³</text>

  <rect x="930" y="545" width="815" height="355" rx="14" fill="#fffaf0" stroke="#9f9077" stroke-width="1.5" filter="url(#shadow)"/>
  <text x="958" y="580" class="panel-title">Manual front snap · exact y = 26.013 mm top sections</text>
  <text x="958" y="602" class="note">The square rear lips are uncamed: manually pre-spread at the jaw roots before pushing rearward. Do not lever on the hook tip.</text>
  <text x="1010" y="626" class="label">A · SEATED</text>
  <text x="1400" y="626" class="label">B · PRE-SPREAD / EXPLODED APPROACH</text>
  <rect x="1005" y="633" width="310" height="196" rx="7" fill="#f0eadf" stroke="#c0b095"/>
  <path d="{overlay_seated_path}" fill="#3d3b37" stroke="#151514" stroke-width="1.3" fill-rule="evenodd"/>
  <path d="{hook_seated_path}" fill="#1c9992" stroke="#075e5d" stroke-width="1.5" fill-rule="evenodd"/>
  <rect x="1395" y="633" width="310" height="196" rx="7" fill="#f0eadf" stroke="#c0b095"/>
  <path d="{overlay_spread_path}" fill="#3d3b37" stroke="#151514" stroke-width="1.3" fill-rule="evenodd"/>
  <path d="{spread_paths[0]}" fill="#1c9992" stroke="#075e5d" stroke-width="1.4" fill-rule="evenodd"/>
  <path d="{spread_paths[1]}" fill="#3bb7ae" stroke="#075e5d" stroke-width="1.4" fill-rule="evenodd"/>
  <path d="{spread_paths[2]}" fill="#3bb7ae" stroke="#075e5d" stroke-width="1.4" fill-rule="evenodd"/>
  <line x1="1450" y1="777" x2="1450" y2="690" stroke="#0d7773" stroke-width="3" marker-end="url(#arrowTeal)"/>
  <text x="1462" y="747" class="label" fill="#0d6b67">PUSH REARWARD</text>
  <line x1="1410" y1="838" x2="1390" y2="838" stroke="#b64134" stroke-width="2" marker-end="url(#arrowRed)"/>
  <line x1="1690" y1="838" x2="1710" y2="838" stroke="#b64134" stroke-width="2" marker-end="url(#arrowRed)"/>
  <text x="1550" y="843" text-anchor="middle" class="label red-text">1.6 mm EACH JAW · 3.2 mm TOTAL</text>
  <text x="958" y="870" class="note">Blue section = v4 clip. Gray section = exact R6 overlay. The pre-spread drawing is the frozen collision proxy, not proof of PETG fatigue life.</text>
  <text x="958" y="890" class="tiny">Conservative strain screen {metrics.flex_strain_proxy*100:.3f}% ≤ 3.000% · physical snap-cycle qualification still required.</text>

  <rect x="55" y="925" width="600" height="202" rx="14" fill="#fffaf0" stroke="#9f9077" stroke-width="1.5"/>
  <text x="80" y="958" class="panel-title">Vertical stop detail · exact x = {stop_x:.3f} mm section</text>
  <text x="80" y="979" class="note">Exact section paths; depth/elevation axes expanded independently.</text>
  <g clip-path="url(#stopClip)">
    <path d="{overlay_stop_path}" fill="#3d3b37" stroke="#151514" stroke-width="1.5" fill-rule="evenodd"/>
    <path d="{hook_stop_path}" fill="#1c9992" stroke="#075e5d" stroke-width="1.7" fill-rule="evenodd"/>
  </g>
  <line x1="{fmt(stop_mapper(4.7,18.8)[0])}" y1="{fmt(stop_mapper(4.7,18.8)[1])}" x2="{fmt(stop_mapper(4.7,19.0)[0])}" y2="{fmt(stop_mapper(4.7,19.0)[1])}" class="dimension"/>
  <path d="M {fmt(stop_mapper(4.7,18.9)[0]+8)} {fmt(stop_mapper(4.7,18.9)[1])} L 625 1032" class="leader"/>
  <text x="455" y="1024" class="label teal-text">0.2 mm free travel</text>
  <text x="80" y="1105" class="tiny">0.4 mm migration gate → positive arrest · modeled overlap {metrics.downward_stop_overlap_at_gate_mm3:.3f} mm³.</text>

  <rect x="675" y="925" width="475" height="202" rx="14" fill="url(#redHatch)" stroke="#b94335" stroke-width="1.8"/>
  <text x="700" y="958" class="panel-title red-text">Inside-corner exclusions remain</text>
  <g transform="translate(715 986)">
    <circle cx="28" cy="28" r="23" fill="#fff8f5" stroke="#b94335" stroke-width="3"/><path d="M16 16 L40 40 M40 16 L16 40" stroke="#b94335" stroke-width="6" stroke-linecap="round"/>
    <text x="66" y="25" class="label" fill="#9f372e">L1 · NO HOOK</text><text x="66" y="44" class="note">long-run start at inside corner</text>
  </g>
  <g transform="translate(715 1047)">
    <circle cx="28" cy="28" r="23" fill="#fff8f5" stroke="#b94335" stroke-width="3"/><path d="M16 16 L40 40 M40 16 L16 40" stroke="#b94335" stroke-width="6" stroke-linecap="round"/>
    <text x="66" y="25" class="label" fill="#9f372e">R1 · NO HOOK</text><text x="66" y="44" class="note">return-run start at inside corner</text>
  </g>
  <text x="1118" y="1110" text-anchor="end" class="tiny">Both levels · 4 total exclusions · service clearance governs</text>

  <rect x="1170" y="925" width="575" height="202" rx="14" fill="#e6f2ed" stroke="#297c78" stroke-width="1.5"/>
  <text x="1195" y="958" class="panel-title" fill="#155f5d">What this plate proves</text>
  <text x="1195" y="985" class="label">✓ Geometry shown comes from frozen v4 source meshes.</text>
  <text x="1195" y="1008" class="label">✓ Overlay is the exact R6 pier-overlay coupon.</text>
  <text x="1195" y="1031" class="label">✓ Seat, cable envelope, spread, and stop datums are explicit.</text>
  <text x="1195" y="1058" class="label" fill="#9b382f">✕ No printed fit, fatigue life, creep, or load capacity is proven.</text>
  <text x="1195" y="1085" class="note">Supplement to the exact 9-hooks-per-level placement schematic;</text>
  <text x="1195" y="1103" class="note">it does not replace the qualification protocol or R7 CAD.</text>

  <text x="68" y="1154" class="tiny">v4 hook STL SHA-256 {EXPECTED_SHA256[V4_DIR / 'stl' / 'R7_DEV_CABLE_PEG_FRONT_SNAP_C_COLLAR_HOOK.stl'][:16]}… · overlay STL {EXPECTED_SHA256[V4_DIR / 'stl' / 'R7_DEV_CABLE_PEG_EXACT_R6_PIER_OVERLAY_COUPON.stl'][:16]}…</text>
  <text x="1732" y="1154" text-anchor="end" class="tiny">Deterministic vector render · dimensions in mm · model geometry governs</text>
</svg>
'''

OUTPUT.write_text(svg)
print(OUTPUT)
