#!/usr/bin/env python3
"""Render the deterministic R8 / 16B exact-design proof.

The proof is code-native: the SVG and PNG are drawn from the live R8 JSON and
Python geometry sources.  No generative imagery, production authorization, or
load-rating inference is involved.  The script deliberately fails closed when
the live topology no longer matches the proof's stated two-level 9 + 5 support
layout.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import html
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from typing import Any, Iterable
import xml.etree.ElementTree as ET


R8_DIR = Path(__file__).resolve().parent
REPO_DIR = R8_DIR.parent.parent
ASSET_DIR = R8_DIR / "assets"
SVG_PATH = ASSET_DIR / "r8_16b_exact_proof.svg"
PNG_PATH = ASSET_DIR / "r8_16b_exact_proof.png"
MANIFEST_PATH = ASSET_DIR / "r8_16b_exact_proof.manifest.json"

WIDTH = 1800
HEIGHT = 1200
ASSET_ID = "r8_16b_exact_proof"

SOURCE_PATHS = (
    REPO_DIR / "requirements.txt",
    R8_DIR / "config.json",
    R8_DIR / "design_math.py",
    R8_DIR / "shelf_geometry.py",
    R8_DIR / "accessory_geometry.py",
    R8_DIR / "interface_geometry.py",
    R8_DIR / "assembly_geometry.py",
    R8_DIR / "production_plan.py",
    R8_DIR / "render_proof.py",
)

# Black / warm cream / restrained copper.  The same tokens are used in
# both vector and raster outputs because Matplotlib owns both render passes.
CREAM = "#f1eadf"
PAPER = "#fffaf2"
BLACK = "#151515"
BLACK_2 = "#292826"
INK = "#1d1b18"
MUTED = "#6e685f"
LINE = "#cfc4b4"
SOFT = "#e8ded0"
ACCENT = "#bc7737"
ACCENT_LIGHT = "#e9b77d"
WHITE = "#fffdf8"

CAD_PACKAGE_NAMES = (
    "numpy",
    "shapely",
    "trimesh",
    "manifold3d",
    "mapbox-earcut",
    "scipy",
    "networkx",
)


@dataclass(frozen=True)
class ProofPaths:
    """One coherent proof-output set in a single target directory."""

    directory: Path
    svg: Path
    png: Path
    manifest: Path


def proof_paths(directory: Path) -> ProofPaths:
    directory = Path(directory).resolve()
    return ProofPaths(
        directory=directory,
        svg=directory / SVG_PATH.name,
        png=directory / PNG_PATH.name,
        manifest=directory / MANIFEST_PATH.name,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant: {value}")


def _assert_finite_json_numbers(value: Any, path: str = "$") -> None:
    """Reject overflow-to-infinity numbers that ``parse_constant`` cannot see."""

    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Non-finite JSON number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite_json_numbers(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_finite_json_numbers(item, f"{path}.{key}")
        return
    raise ValueError(f"Unsupported JSON value at {path}: {type(value).__name__}")


def strict_json_loads(source: str, *, source_name: str = "JSON") -> Any:
    """Decode JSON while rejecting duplicate keys and every non-finite number."""

    try:
        value = json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
        _assert_finite_json_numbers(value)
        return value
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid strict {source_name}: {exc}") from exc


def strict_json_file(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"), source_name=str(path))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes() -> dict[str, str]:
    return {
        path.relative_to(REPO_DIR).as_posix(): sha256_file(path)
        for path in SOURCE_PATHS
    }


def load_config() -> dict[str, Any]:
    cfg = strict_json_file(R8_DIR / "config.json")
    if not isinstance(cfg, dict):
        raise ValueError("R8 config root must be a JSON object")
    return cfg


def validate_project_scope(cfg: dict[str, Any]) -> None:
    """Invoke the planner's public fail-closed project-scope gate."""

    inserted = False
    if str(R8_DIR) not in sys.path:
        sys.path.insert(0, str(R8_DIR))
        inserted = True
    try:
        production_plan = importlib.import_module("production_plan")
        production_plan.validate_project_scope(cfg)
    finally:
        if inserted:
            sys.path.remove(str(R8_DIR))


def extract_live_d_frame() -> tuple[dict[str, Any], dict[str, Any]]:
    """Ask the exact CAD runtime for geometry, service limits, and provenance."""

    interpreter = REPO_DIR / ".venv" / "bin" / "python"
    if not interpreter.is_file():
        raise RuntimeError("The project .venv Python is required for exact CAD extraction")
    program = r"""
import json
import importlib.metadata
import platform
import sys
from pathlib import Path
import numpy as np

r8_dir = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(r8_dir))
import assembly_geometry as assembly
import shelf_geometry as shelf

inner = np.asarray(shelf._curved_corbel_cutout_profile(), dtype=float)
outer_start = np.asarray((shelf.CORBEL_WALL_CHORD_MM, 0.0), dtype=float)
outer_end = np.asarray(
    (
        shelf.CORBEL_PROJECTION_MM,
        shelf.CORBEL_INSTALLED_HEIGHT_MM - shelf.CORBEL_FRONT_NOSE_MM,
    ),
    dtype=float,
)
direction = outer_end - outer_start
t = ((inner - outer_start) @ direction) / float(direction @ direction)
feet = outer_start + t[:, None] * direction
distances = np.linalg.norm(inner - feet, axis=1)
index = int(np.argmin(distances))
print(json.dumps({
    "outer_profile_mm": shelf._outer_corbel_profile(),
    "inner_profile_mm": shelf._curved_corbel_cutout_profile(),
    "minimum_web_mm": shelf.minimum_curved_web_thickness_mm(),
    "minimum_web_inner_point_mm": inner[index].tolist(),
    "minimum_web_outer_foot_mm": feet[index].tolist(),
    "minimum_web_vertex_index": index,
    "assembly_contract": {
        "rail_service_requires_module_removal": assembly.RAIL_SERVICE_REQUIRES_MODULE_REMOVAL,
    },
    "renderer_provenance": {
        "invoked_interpreter": str(Path(sys.argv[2])),
        "resolved_interpreter": str(Path(sys.executable).resolve()),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in %s
        },
    },
}, sort_keys=True, separators=(",", ":")))
""" % (CAD_PACKAGE_NAMES,)
    result = subprocess.run(
        [str(interpreter), "-c", program, str(R8_DIR), str(interpreter)],
        check=True,
        capture_output=True,
        text=True,
    )
    decoded = strict_json_loads(result.stdout, source_name="CAD extraction")
    if not isinstance(decoded, dict):
        raise ValueError("CAD extraction root must be a JSON object")
    provenance = decoded.pop("renderer_provenance", None)
    if not isinstance(provenance, dict):
        raise ValueError("CAD extraction omitted renderer provenance")
    return decoded, provenance


def validate_contract(cfg: dict[str, Any], d_frame: dict[str, Any]) -> dict[str, Any]:
    runs = {item["id"]: item for item in cfg["runs"]}
    accessory = cfg["accessory_system"]
    frame = cfg["d_frame"]
    shelf = cfg["shelf"]
    assembly_contract = d_frame["assembly_contract"]
    exact = {
        "levels": int(shelf["selected_level_count"]),
        "through_supports_per_level": int(runs["through"]["corbel_count"]),
        "return_supports_per_level": int(runs["return"]["corbel_count"]),
        "through_length_mm": float(runs["through"]["nominal_length_mm"]),
        "return_length_mm": float(runs["return"]["nominal_length_mm"]),
        "shelf_depth_mm": float(shelf["depth_mm"]),
        "terminal_support_center_inset_mm": float(
            shelf["terminal_corbel_center_inset_mm"]
        ),
        "cassette_internal_web_count": int(
            shelf["selected_cassette_geometry_mm"]["internal_web_count"]
        ),
        "d_frame_downleg_mm": float(frame["installed_height_mm"]),
        "d_frame_cap_mm": float(frame["shelf_bearing_cap_width_across_run_mm"]),
        "d_frame_measured_minimum_web_mm": float(d_frame["minimum_web_mm"]),
        "rail_envelope_mm": [float(value) for value in accessory["rail_envelope_mm"]],
        "rail_socket_count": int(accessory["sockets_per_eligible_corbel"]),
        "rail_socket_centers_mm": [
            float(value) for value in accessory["socket_centers_from_rail_bottom_mm"]
        ],
        "through_default_rail_indices": [
            int(value)
            for value in accessory["default_equipped_station_indices"]["through"]
        ],
        "return_default_rail_indices": [
            int(value)
            for value in accessory["default_equipped_station_indices"]["return"]
        ],
        "module_count": len(accessory["available_modules"]),
        "module_service_lift_mm": float(accessory["module_service_lift_mm"]),
        "rail_service_lift_mm": float(accessory["rail_service_lift_mm"]),
        "rail_service_requires_module_removal": bool(
            assembly_contract["rail_service_requires_module_removal"]
        ),
        "layout_representation": "frozen_nominal_two_run_topology_schematic_not_to_scale",
        "return_and_corner_field_verified": False,
        "exact_full_l_placement": False,
    }
    frozen_expectations = {
        "levels": 2,
        "through_supports_per_level": 9,
        "return_supports_per_level": 5,
        "shelf_depth_mm": 152.4,
        "terminal_support_center_inset_mm": 16.0,
        "cassette_internal_web_count": 3,
        "d_frame_downleg_mm": 160.0,
        "d_frame_cap_mm": 32.0,
        "rail_envelope_mm": [36.0, 88.0, 8.8],
        "rail_socket_count": 3,
        "through_default_rail_indices": [1, 3, 5, 7],
        "return_default_rail_indices": [1, 3],
        "module_count": 4,
        "module_service_lift_mm": 8.0,
        "rail_service_lift_mm": 4.0,
        "rail_service_requires_module_removal": True,
        "layout_representation": "frozen_nominal_two_run_topology_schematic_not_to_scale",
        "return_and_corner_field_verified": False,
        "exact_full_l_placement": False,
    }
    disagreements = {
        key: (exact[key], expected)
        for key, expected in frozen_expectations.items()
        if exact[key] != expected
    }
    if disagreements:
        raise RuntimeError(f"Live R8 contract no longer matches proof: {disagreements}")
    if exact["d_frame_measured_minimum_web_mm"] < float(
        frame["minimum_authored_web_normal_thickness_mm"]
    ):
        raise RuntimeError("Measured D-frame web fell below the authored minimum")
    return exact


def import_drawing_runtime() -> tuple[Any, ...]:
    """Load Matplotlib or re-exec with the macOS system Python that provides it."""

    # Keep Matplotlib's cache inside the writable project, not in the user home.
    cache_dir = Path(tempfile.gettempdir()) / "r8-16b-render-proof-mpl-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
        from matplotlib.patches import Circle, FancyBboxPatch, PathPatch, Polygon, Rectangle
        from matplotlib.path import Path as MplPath
    except ModuleNotFoundError as exc:
        system_python = Path("/usr/bin/python3")
        if system_python.is_file() and Path(sys.executable).resolve() != system_python.resolve():
            completed = subprocess.run(
                [str(system_python), str(Path(__file__).resolve()), *sys.argv[1:]]
            )
            raise SystemExit(completed.returncode)
        raise RuntimeError("Matplotlib is required to render the exact proof") from exc
    matplotlib.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 14,
            "svg.fonttype": "none",
            "svg.hashsalt": "r8-16b-exact-proof-v1",
            "axes.linewidth": 0.0,
        }
    )
    return plt, Line2D, Circle, FancyBboxPatch, PathPatch, Polygon, Rectangle, MplPath


def drawing_renderer_provenance() -> dict[str, Any]:
    """Record the exact raster/vector runtime and resolved drawing font."""

    import matplotlib
    from matplotlib import font_manager

    font: dict[str, Any] = {"requested_family": "Arial"}
    try:
        resolved = Path(
            font_manager.findfont(
                font_manager.FontProperties(family="Arial"),
                fallback_to_default=False,
            )
        ).resolve()
        font.update(
            {
                "resolved_family": font_manager.FontProperties(
                    fname=str(resolved)
                ).get_name(),
                "resolved_path": str(resolved),
                "sha256": sha256_file(resolved),
                "bytes": resolved.stat().st_size,
            }
        )
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        font["resolution_error"] = f"{type(exc).__name__}: {exc}"

    drawing_packages: dict[str, str] = {"matplotlib": matplotlib.__version__}
    for package_name in ("numpy",):
        try:
            drawing_packages[package_name] = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            drawing_packages[package_name] = "not-installed-as-distribution"
    return {
        "invoked_interpreter": sys.executable,
        "resolved_interpreter": str(Path(sys.executable).resolve()),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "matplotlib_backend": str(matplotlib.get_backend()),
        "packages": drawing_packages,
        "font": font,
    }


def rounded_card(ax: Any, patch_cls: Any, x: float, y: float, w: float, h: float, gid: str) -> None:
    shadow = patch_cls(
        (x + 5, y + 8),
        w,
        h,
        boxstyle="round,pad=0,rounding_size=22",
        facecolor="#c7bbab",
        edgecolor="none",
        alpha=0.24,
        zorder=0,
    )
    ax.add_patch(shadow)
    card = patch_cls(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0,rounding_size=22",
        facecolor=PAPER,
        edgecolor=LINE,
        linewidth=1.2,
        zorder=1,
    )
    card.set_gid(gid)
    ax.add_patch(card)


def label(
    ax: Any,
    x: float,
    y: float,
    text: str,
    *,
    size: float = 14,
    color: str = INK,
    weight: str = "normal",
    align: str = "left",
    rotation: float = 0.0,
    gid: str | None = None,
    zorder: int = 20,
) -> Any:
    artist = ax.text(
        x,
        y,
        text,
        fontsize=size,
        color=color,
        fontweight=weight,
        ha=align,
        va="center",
        rotation=rotation,
        zorder=zorder,
    )
    if gid:
        artist.set_gid(gid)
    return artist


def panel_heading(ax: Any, number: str, title: str, x: float, y: float) -> None:
    label(
        ax,
        x,
        y,
        number,
        size=13,
        color=ACCENT,
        weight="bold",
        gid=f"heading-{number}-number",
    )
    label(
        ax,
        x + 35,
        y,
        title,
        size=17,
        color=INK,
        weight="bold",
        gid=f"heading-{number}-title",
    )


def line(
    ax: Any,
    line_cls: Any,
    points: Iterable[tuple[float, float]],
    *,
    color: str = INK,
    width: float = 1.5,
    dash: tuple[float, ...] | None = None,
    gid: str | None = None,
    zorder: int = 10,
) -> Any:
    pairs = tuple(points)
    properties: dict[str, Any] = {
        "color": color,
        "linewidth": width,
        "solid_capstyle": "round",
        "solid_joinstyle": "round",
        "zorder": zorder,
    }
    if dash is not None:
        properties["dashes"] = dash
    artist = line_cls(
        [point[0] for point in pairs],
        [point[1] for point in pairs],
        **properties,
    )
    if gid:
        artist.set_gid(gid)
    ax.add_line(artist)
    return artist


def double_arrow(
    ax: Any,
    polygon_cls: Any,
    line_cls: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = ACCENT,
    width: float = 1.6,
    head: float = 7.0,
    gid: str | None = None,
) -> None:
    line(ax, line_cls, (start, end), color=color, width=width, gid=gid, zorder=24)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    for point, direction in ((start, 1.0), (end, -1.0)):
        tip = point
        base = (point[0] + direction * head * ux, point[1] + direction * head * uy)
        triangle = polygon_cls(
            [
                tip,
                (base[0] + 0.55 * head * px, base[1] + 0.55 * head * py),
                (base[0] - 0.55 * head * px, base[1] - 0.55 * head * py),
            ],
            closed=True,
            facecolor=color,
            edgecolor="none",
            zorder=25,
        )
        ax.add_patch(triangle)


def draw_d_frame(
    ax: Any,
    runtime: tuple[Any, ...],
    cfg: dict[str, Any],
    exact: dict[str, Any],
    d_frame: dict[str, Any],
) -> None:
    _, line_cls, circle_cls, _, path_patch_cls, polygon_cls, rectangle_cls, mpl_path = runtime
    panel_heading(ax, "01", "STRUCTURAL D-FRAME", 82, 188)
    label(
        ax,
        82,
        219,
        "Exact live side profile · curved comparison candidate",
        size=13,
        color=MUTED,
        gid="heading-01-subtitle",
    )

    origin_x = 115.0
    baseline_y = 681.0
    scale = 2.28

    def map_point(point: Iterable[float]) -> tuple[float, float]:
        q, e = point
        return origin_x + float(q) * scale, baseline_y - float(e) * scale

    outer = [map_point(point) for point in d_frame["outer_profile_mm"]]
    inner = [map_point(point) for point in d_frame["inner_profile_mm"]]
    shadow = [(x + 7, y + 8) for x, y in outer]
    shadow_patch = polygon_cls(shadow, closed=True, facecolor="#9e9487", edgecolor="none", alpha=0.35, zorder=3)
    ax.add_patch(shadow_patch)
    outer_patch = polygon_cls(outer, closed=True, facecolor=BLACK, edgecolor="#050505", linewidth=1.2, zorder=5)
    outer_patch.set_gid("exact-d-frame-outer-profile")
    ax.add_patch(outer_patch)
    inner_patch = polygon_cls(inner, closed=True, facecolor=PAPER, edgecolor=BLACK_2, linewidth=1.0, zorder=6)
    inner_patch.set_gid("exact-d-frame-inner-profile")
    ax.add_patch(inner_patch)

    # Warm edge glints make the black part legible without implying another material.
    line(ax, line_cls, outer[3:5], color="#46423d", width=2.0, zorder=7)
    line(ax, line_cls, inner[8:50], color="#504a43", width=1.1, zorder=7)

    top_y = baseline_y - exact["d_frame_downleg_mm"] * scale
    right_x = origin_x + exact["shelf_depth_mm"] * scale
    double_arrow(ax, polygon_cls, line_cls, (origin_x, top_y - 29), (right_x, top_y - 29))
    label(
        ax,
        (origin_x + right_x) / 2,
        top_y - 48,
        f'{exact["shelf_depth_mm"]:.1f} mm SHELF DEPTH',
        size=13,
        color=ACCENT,
        weight="bold",
        align="center",
    )
    line(ax, line_cls, ((origin_x, top_y - 35), (origin_x, top_y - 5)), color=LINE, width=1.0)
    line(ax, line_cls, ((right_x, top_y - 35), (right_x, top_y + 4)), color=LINE, width=1.0)

    double_arrow(ax, polygon_cls, line_cls, (origin_x - 29, top_y), (origin_x - 29, baseline_y))
    label(
        ax,
        origin_x - 52,
        (top_y + baseline_y) / 2,
        f'{exact["d_frame_downleg_mm"]:.0f} mm DOWNLEG',
        size=13,
        color=ACCENT,
        weight="bold",
        align="center",
        rotation=90,
    )

    inner_point = map_point(d_frame["minimum_web_inner_point_mm"])
    outer_foot = map_point(d_frame["minimum_web_outer_foot_mm"])
    double_arrow(ax, polygon_cls, line_cls, outer_foot, inner_point, color=ACCENT_LIGHT, width=2.1, head=5.0, gid="measured-minimum-web")
    ax.add_patch(circle_cls(inner_point, radius=3.5, facecolor=ACCENT, edgecolor=WHITE, linewidth=1.0, zorder=27))
    callout_x, callout_y = 423, 561
    line(ax, line_cls, (inner_point, (callout_x - 13, callout_y)), color=ACCENT, width=1.2, dash=(3, 3), zorder=22)
    label(ax, callout_x, callout_y - 8, "MEASURED CAD MIN WEB", size=12, color=MUTED, weight="bold")
    label(
        ax,
        callout_x,
        callout_y + 16,
        f'{exact["d_frame_measured_minimum_web_mm"]:.3f} mm NORMAL',
        size=18,
        color=INK,
        weight="bold",
    )
    label(ax, callout_x, callout_y + 39, "authored floor ≥ 16.0 mm", size=12, color=MUTED)

    # Small isometric cap-width cue.  The 32 mm cap is across the run and is
    # therefore intentionally not faked as a side-profile dimension.
    cap_x, cap_y = 508, 317
    cap = rectangle_cls((cap_x, cap_y), 95, 26, facecolor=BLACK, edgecolor="none", zorder=8)
    cap.set_gid("d-frame-32mm-bearing-cap")
    ax.add_patch(cap)
    ax.add_patch(polygon_cls([(cap_x + 95, cap_y), (cap_x + 112, cap_y - 10), (cap_x + 112, cap_y + 16), (cap_x + 95, cap_y + 26)], facecolor=BLACK_2, edgecolor="none", zorder=8))
    ax.add_patch(polygon_cls([(cap_x, cap_y), (cap_x + 17, cap_y - 10), (cap_x + 112, cap_y - 10), (cap_x + 95, cap_y)], facecolor="#34312e", edgecolor="none", zorder=8))
    label(ax, cap_x + 55, cap_y + 51, f'{exact["d_frame_cap_mm"]:.0f} mm CAP', size=13, color=INK, weight="bold", align="center")
    label(ax, cap_x + 55, cap_y + 70, "across run", size=12, color=MUTED, align="center")

    badge = rectangle_cls((82, 704), 570, 25, facecolor=SOFT, edgecolor="none", zorder=8)
    ax.add_patch(badge)
    label(ax, 94, 717, "CURVE = CONTROLLED GEOMETRY COMPARISON · NOT CAPACITY CREDIT", size=12, color=MUTED, weight="bold")


def socket_shape(ax: Any, runtime: tuple[Any, ...], cx: float, cy: float, gid: str) -> None:
    _, _, _, _, _, polygon_cls, _, _ = runtime
    shape = [
        (cx - 12, cy - 15),
        (cx + 8, cy - 15),
        (cx + 8, cy - 7),
        (cx + 5, cy - 7),
        (cx + 5, cy + 15),
        (cx - 5, cy + 15),
        (cx - 5, cy - 7),
        (cx - 12, cy - 7),
    ]
    patch = polygon_cls(shape, closed=True, facecolor=PAPER, edgecolor=ACCENT_LIGHT, linewidth=1.4, zorder=12)
    patch.set_gid(gid)
    ax.add_patch(patch)


def module_icon(
    ax: Any,
    runtime: tuple[Any, ...],
    x: float,
    y: float,
    kind: str,
    display: str,
    index: int,
) -> None:
    _, line_cls, circle_cls, rounded_cls, _, polygon_cls, rectangle_cls, _ = runtime
    card = rounded_cls((x, y), 102, 118, boxstyle="round,pad=0,rounding_size=12", facecolor="#f5ede2", edgecolor=LINE, linewidth=1.0, zorder=5)
    card.set_gid(f"module-{index}-{kind}")
    ax.add_patch(card)
    # Common base + keyed lug.
    ax.add_patch(rectangle_cls((x + 39, y + 63), 24, 14, facecolor=BLACK, edgecolor="none", zorder=12))
    ax.add_patch(rectangle_cls((x + 46, y + 54), 10, 10, facecolor=BLACK_2, edgecolor="none", zorder=12))
    ax.add_patch(rectangle_cls((x + 43, y + 48), 16, 7, facecolor=BLACK_2, edgecolor="none", zorder=12))
    # The copper detent is intentionally visible on every removable module.
    latch = polygon_cls([(x + 62, y + 63), (x + 69, y + 57), (x + 69, y + 68), (x + 62, y + 72)], facecolor=ACCENT, edgecolor="none", zorder=14)
    latch.set_gid(f"positive-latch-{index}")
    ax.add_patch(latch)
    if kind == "blank":
        ax.add_patch(rounded_cls((x + 34, y + 28), 34, 25, boxstyle="round,pad=0,rounding_size=7", facecolor=BLACK, edgecolor="none", zorder=10))
    elif kind == "peg":
        line(ax, line_cls, ((x + 51, y + 51), (x + 51, y + 22)), color=BLACK, width=7, zorder=11)
        line(ax, line_cls, ((x + 51, y + 22), (x + 59, y + 16)), color=BLACK, width=6, zorder=11)
    elif kind == "comb":
        line(ax, line_cls, ((x + 28, y + 41), (x + 74, y + 41)), color=BLACK, width=7, zorder=11)
        for offset in (-18, 0, 18):
            line(ax, line_cls, ((x + 51 + offset, y + 41), (x + 51 + offset, y + 18)), color=BLACK, width=5, zorder=11)
            ax.add_patch(circle_cls((x + 51 + offset, y + 17), radius=3, facecolor=BLACK, edgecolor="none", zorder=11))
    else:
        line(ax, line_cls, ((x + 51, y + 52), (x + 51, y + 22), (x + 67, y + 16), (x + 72, y + 28)), color=BLACK, width=8, zorder=11)
    label(ax, x + 51, y + 96, display, size=12, color=INK, weight="bold", align="center")


def draw_rail(ax: Any, runtime: tuple[Any, ...], exact: dict[str, Any]) -> None:
    _, line_cls, circle_cls, rounded_cls, _, polygon_cls, rectangle_cls, _ = runtime
    panel_heading(ax, "02", "EXTERNAL CABLE RAIL", 752, 188)
    label(
        ax,
        752,
        219,
        "Boss-mounted · structural D-frame remains uncut",
        size=13,
        color=MUTED,
        gid="heading-02-subtitle",
    )

    # Structural downleg in context.
    ax.add_patch(rounded_cls((774, 280), 42, 268, boxstyle="round,pad=0,rounding_size=9", facecolor=BLACK, edgecolor="none", zorder=6))
    label(ax, 795, 570, "D-FRAME", size=12, color=MUTED, weight="bold", align="center")
    boss_centers = [(808, 321), (808, 489), (823, 321), (823, 489)]
    for index, (cx, cy) in enumerate(boss_centers):
        boss = circle_cls((cx, cy), radius=7 if index < 2 else 5, facecolor=ACCENT_LIGHT if index < 2 else ACCENT, edgecolor=BLACK, linewidth=0.7, zorder=10)
        boss.set_gid(f"external-boss-{index}")
        ax.add_patch(boss)
    for cy in (321, 489):
        line(ax, line_cls, ((829, cy), (877, cy)), color=ACCENT, width=1.3, dash=(4, 4), zorder=9)
        double_arrow(ax, polygon_cls, line_cls, (846, cy), (874, cy), color=ACCENT, width=1.0, head=4.0)

    # Exploded 36 x 88 face rail, drawn at its exact 36:88 front aspect ratio.
    rail_x, rail_y = 884, 276
    rail_w, rail_h = 112, 274
    ax.add_patch(polygon_cls([(rail_x + rail_w, rail_y), (rail_x + rail_w + 18, rail_y - 10), (rail_x + rail_w + 18, rail_y + rail_h - 10), (rail_x + rail_w, rail_y + rail_h)], facecolor=BLACK_2, edgecolor="none", zorder=7))
    rail = rounded_cls((rail_x, rail_y), rail_w, rail_h, boxstyle="round,pad=0,rounding_size=12", facecolor=BLACK, edgecolor="#050505", linewidth=1.0, zorder=8)
    rail.set_gid("boss-mounted-three-socket-rail")
    ax.add_patch(rail)
    socket_ys = [rail_y + rail_h - center / 88.0 * rail_h for center in exact["rail_socket_centers_mm"]]
    for index, cy in enumerate(socket_ys):
        socket_shape(ax, runtime, rail_x + rail_w / 2, cy, f"rail-socket-{index}")
    label(ax, rail_x + rail_w / 2, 258, "36 × 88 × 8.8 mm", size=13, color=INK, weight="bold", align="center")
    label(ax, 1030, 315, "3 GRAVITY\nSOCKETS", size=14, color=INK, weight="bold")
    line(ax, line_cls, ((1020, 342), (986, socket_ys[0])), color=LINE, width=1.2, zorder=10)
    label(ax, 1030, 389, "4 EXTERNAL\nBOSSES", size=14, color=INK, weight="bold")
    line(ax, line_cls, ((1020, 409), (824, 489)), color=LINE, width=1.2, zorder=10)
    label(ax, 1030, 472, "NO RECEIVER CUT\nIN STRUCTURAL SPINE", size=12, color=MUTED, weight="bold")

    # Four exact module families; the orange element is the positive release detent.
    modules = (
        ("blank", "BLANK"),
        ("peg", "SINGLE PEG"),
        ("comb", "3-WAY COMB"),
        ("coil", "COIL J"),
    )
    for index, (kind, display) in enumerate(modules):
        module_icon(ax, runtime, 746 + index * 117, 603, kind, display, index)
    label(ax, 752, 586, "FOUR REMOVABLE PETG MODULES", size=12, color=MUTED, weight="bold")
    label(ax, 1212, 572, "POSITIVE\nRELEASE LATCH", size=12, color=ACCENT, weight="bold", align="right")
    line(ax, line_cls, ((1194, 589), (1167, 657)), color=ACCENT, width=1.3, dash=(3, 3), zorder=20)
    label(
        ax,
        752,
        735,
        "SERVICE LIMIT: REMOVE ALL MODULES BEFORE RAIL SERVICE",
        size=12,
        color=ACCENT,
        weight="bold",
    )


def draw_sections(ax: Any, runtime: tuple[Any, ...], cfg: dict[str, Any]) -> None:
    _, line_cls, _, rounded_cls, _, _, rectangle_cls, _ = runtime
    panel_heading(ax, "03", "CASSETTE DECISION", 1282, 188)
    label(
        ax,
        1282,
        219,
        "Selected section versus matched heavy control",
        size=13,
        color=MUTED,
        gid="heading-03-subtitle",
    )
    geometry = cfg["shelf"]["selected_cassette_geometry_mm"]

    selected = rounded_cls((1282, 260), 126, 28, boxstyle="round,pad=0,rounding_size=14", facecolor=ACCENT, edgecolor="none", zorder=8)
    ax.add_patch(selected)
    label(ax, 1345, 274, "SELECTED U-BOX", size=12, color=WHITE, weight="bold", align="center")

    # Section through shelf depth: top + bottom + visible front, open at rear.
    x0, x1, y0, y1 = 1315, 1680, 324, 496
    top_h = 18
    bottom_h = 14
    front_w = 22
    section_parts = (
        rectangle_cls((x0, y0), x1 - x0, top_h, facecolor=BLACK, edgecolor="none", zorder=8),
        rectangle_cls((x0, y1 - bottom_h), x1 - x0, bottom_h, facecolor=BLACK, edgecolor="none", zorder=8),
        rectangle_cls((x1 - front_w, y0), front_w, y1 - y0, facecolor=BLACK, edgecolor="none", zorder=8),
    )
    for index, part in enumerate(section_parts):
        part.set_gid(f"selected-u-box-section-{index}")
        ax.add_patch(part)
    # Repeated hidden full-depth webs are called out because they are not seen
    # in this through-depth U section.
    line(ax, line_cls, ((x0, y0 - 10), (x0, y1 + 10)), color=ACCENT, width=2.0, dash=(4, 4), zorder=12)
    label(ax, x0 + 8, y0 + 50, "REAR OPEN", size=12, color=ACCENT, weight="bold")
    label(ax, x0 + 8, y0 + 70, "hidden at wall", size=12, color=MUTED)
    label(ax, (x0 + x1) / 2, y0 - 19, f'TOP {geometry["top_skin"]:.1f} mm', size=12, color=INK, weight="bold", align="center")
    label(ax, (x0 + x1) / 2, y1 + 21, f'BOTTOM {geometry["bottom_skin"]:.1f} mm', size=12, color=INK, weight="bold", align="center")
    label(ax, x1 + 4, (y0 + y1) / 2, f'FRONT {geometry["visible_front_wall"]:.1f}', size=12, color=INK, weight="bold", rotation=90, align="center")
    label(
        ax,
        1494,
        420,
        "CONNECTED FRONT-FIRST\nPRINT SECTION",
        size=14,
        color=MUTED,
        weight="bold",
        align="center",
    )
    label(
        ax,
        1492,
        466,
        f'{geometry["internal_web_count"]} FULL-DEPTH INTERNAL WEBS · {geometry["internal_web"]:.1f} mm',
        size=12,
        color=INK,
        weight="bold",
        align="center",
    )

    # Heavy coffer control: a dense underside grid, intentionally subordinate.
    label(ax, 1282, 556, "MATCHED HEAVY COFFER CONTROL", size=12, color=MUTED, weight="bold")
    control = rectangle_cls((1282, 580), 420, 112, facecolor=BLACK_2, edgecolor="none", zorder=6)
    control.set_gid("heavy-coffer-control")
    ax.add_patch(control)
    for row in range(3):
        for column in range(10):
            cavity = rounded_cls(
                (1291 + column * 41, 589 + row * 34),
                30,
                22,
                boxstyle="round,pad=0,rounding_size=3",
                facecolor=PAPER,
                edgecolor="#5b5751",
                linewidth=0.7,
                zorder=7,
            )
            cavity.set_gid(f"coffer-control-cell-{row}-{column}")
            ax.add_patch(cavity)
    label(ax, 1492, 718, "CONTROL ONLY · DENSE RIB NETWORK · NOT SELECTED", size=12, color=MUTED, weight="bold", align="center")


def draw_level_plan(
    ax: Any,
    runtime: tuple[Any, ...],
    exact: dict[str, Any],
    level: int,
    x: float,
    y: float,
) -> None:
    _, line_cls, circle_cls, rounded_cls, _, polygon_cls, rectangle_cls, _ = runtime
    card = rounded_cls((x, y), 760, 247, boxstyle="round,pad=0,rounding_size=16", facecolor="#f7efe5", edgecolor=LINE, linewidth=1.0, zorder=4)
    card.set_gid(f"level-plan-{level}")
    ax.add_patch(card)
    label(ax, x + 24, y + 25, f"LEVEL {level}", size=15, color=INK, weight="bold")
    label(
        ax,
        x + 122,
        y + 25,
        "14 DISTINCT SUPPORTS · 6 DEFAULT RAILS",
        size=12,
        color=MUTED,
        weight="bold",
    )
    label(
        ax,
        x + 736,
        y + 25,
        "SCHEMATIC · NOT TO SCALE",
        size=12,
        color=ACCENT,
        weight="bold",
        align="right",
    )

    run_start = x + 45
    through_end = x + 690
    through_y = y + 78
    return_end = run_start + (through_end - run_start) * exact[
        "return_length_mm"
    ] / exact["through_length_mm"]
    return_y = y + 157
    terminal_inset = exact["terminal_support_center_inset_mm"]

    line(
        ax,
        line_cls,
        ((run_start, through_y), (through_end, through_y)),
        color=BLACK,
        width=21,
        zorder=7,
    )
    line(
        ax,
        line_cls,
        ((run_start, return_y), (return_end, return_y)),
        color=BLACK,
        width=21,
        zorder=7,
    )
    label(
        ax,
        run_start,
        y + 50,
        "THROUGH · 9 SUPPORTS · DEFAULT RAILS 1 / 3 / 5 / 7",
        size=12,
        color=MUTED,
        weight="bold",
    )
    label(
        ax,
        run_start,
        y + 129,
        "RETURN · 5 SUPPORTS · DEFAULT RAILS 1 / 3",
        size=12,
        color=MUTED,
        weight="bold",
    )

    defaults = {
        "through": set(exact["through_default_rail_indices"]),
        "return": set(exact["return_default_rail_indices"]),
    }
    run_specs = (
        (
            "through",
            through_y,
            through_end,
            exact["through_length_mm"],
            exact["through_supports_per_level"],
        ),
        (
            "return",
            return_y,
            return_end,
            exact["return_length_mm"],
            exact["return_supports_per_level"],
        ),
    )
    for run_id, shelf_y, run_end, length_mm, support_count in run_specs:
        pitch_mm = (length_mm - 2.0 * terminal_inset) / (support_count - 1)
        for index in range(support_count):
            center_mm = terminal_inset + index * pitch_mm
            px = run_start + (run_end - run_start) * center_mm / length_mm
            support = circle_cls(
                (px, shelf_y),
                radius=7.2,
                facecolor=PAPER,
                edgecolor=BLACK,
                linewidth=1.8,
                zorder=12,
            )
            support.set_gid(f"{run_id}-support-L{level}-{index}")
            ax.add_patch(support)
            label(
                ax,
                px,
                shelf_y + 24,
                str(index),
                size=12,
                color=MUTED,
                align="center",
            )
            if index in (0, support_count - 1):
                terminal = rectangle_cls(
                    (px - 3.2, shelf_y - 3.2),
                    6.4,
                    6.4,
                    facecolor=ACCENT_LIGHT,
                    edgecolor="none",
                    zorder=14,
                )
                terminal.set_gid(
                    f"terminal-marker-{run_id}-L{level}-{index}"
                )
                ax.add_patch(terminal)
            if index in defaults[run_id]:
                tab = rounded_cls(
                    (px - 5.5, shelf_y - 26),
                    11,
                    14,
                    boxstyle="round,pad=0,rounding_size=4",
                    facecolor=ACCENT,
                    edgecolor=WHITE,
                    linewidth=0.8,
                    zorder=13,
                )
                tab.set_gid(f"default-rail-L{level}-{run_id}-{index}")
                ax.add_patch(tab)

    label(
        ax,
        x + 24,
        y + 224,
        "□ 16 mm inset clean terminal",
        size=12,
        color=MUTED,
    )
    ax.add_patch(
        rounded_cls(
            (x + 215, y + 216),
            11,
            14,
            boxstyle="round,pad=0,rounding_size=4",
            facecolor=ACCENT,
            edgecolor="none",
            zorder=11,
        )
    )
    label(ax, x + 236, y + 224, "default external rail", size=12, color=MUTED)
    label(
        ax,
        x + 736,
        y + 224,
        "CORNER TRANSITION UNAUTHORED",
        size=12,
        color=INK,
        weight="bold",
        align="right",
    )


def draw_layout(ax: Any, runtime: tuple[Any, ...], exact: dict[str, Any]) -> None:
    panel_heading(ax, "04", "FROZEN NOMINAL TWO-RUN TOPOLOGY", 82, 807)
    label(
        ax,
        82,
        833,
        "Same nominal topology per level · return / corner field-unverified · not an exact full-L",
        size=13,
        color=MUTED,
        gid="heading-04-subtitle",
    )
    draw_level_plan(ax, runtime, exact, 1, 82, 850)
    draw_level_plan(ax, runtime, exact, 2, 878, 850)


def add_footer(ax: Any, runtime: tuple[Any, ...]) -> None:
    _, _, _, rounded_cls, _, _, _, _ = runtime
    footer_items = (
        (50, 540, ACCENT, "ALL PRINTED PARTS PETG"),
        (610, 690, BLACK, "METAL STRUCTURAL SCREWS INTO VERIFIED FRAMING REQUIRED"),
        (1320, 430, ACCENT, "QUALIFICATION ONLY / ZERO RATED LOAD"),
    )
    for index, (x, width, color, text) in enumerate(footer_items):
        patch = rounded_cls((x, 1137), width, 42, boxstyle="round,pad=0,rounding_size=21", facecolor=color, edgecolor="none", zorder=6)
        patch.set_gid(f"footer-warning-{index}")
        ax.add_patch(patch)
        label(ax, x + width / 2, 1158, text, size=13, color=WHITE, weight="bold", align="center", gid=f"footer-warning-text-{index}")


def render_figure(
    cfg: dict[str, Any], exact: dict[str, Any], d_frame: dict[str, Any]
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    runtime = import_drawing_runtime()
    plt, _, _, rounded_cls, _, _, _, _ = runtime
    fig = plt.figure(figsize=(25, 50 / 3), dpi=72, facecolor=CREAM)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(HEIGHT, 0)
    ax.set_axis_off()
    ax.set_facecolor(CREAM)

    label(ax, 50, 32, "STORY CORNER · R8 / 16B", size=13, color=ACCENT, weight="bold")
    label(ax, 50, 78, "A shelf that works hard—and stays visually quiet.", size=38, color=INK, weight="bold")
    label(
        ax,
        1750,
        79,
        "EXACT DESIGN PROOF · LIVE SOURCE",
        size=13,
        color=MUTED,
        weight="bold",
        align="right",
    )
    label(
        ax,
        50,
        116,
        "Black PETG structure · modular lightweight cable utility · fail-closed qualification state",
        size=15,
        color=MUTED,
    )

    rounded_card(ax, rounded_cls, 50, 150, 650, 600, "panel-structural-frame")
    rounded_card(ax, rounded_cls, 720, 150, 510, 600, "panel-accessory-rail")
    rounded_card(ax, rounded_cls, 1250, 150, 500, 600, "panel-cassette-section")
    rounded_card(ax, rounded_cls, 50, 775, 1700, 340, "panel-two-level-layout")

    draw_d_frame(ax, runtime, cfg, exact, d_frame)
    draw_rail(ax, runtime, exact)
    draw_sections(ax, runtime, cfg)
    draw_layout(ax, runtime, exact)
    add_footer(ax, runtime)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text_artists = list(ax.texts)
    bounds = [artist.get_window_extent(renderer=renderer) for artist in text_artists]
    tolerance = 1.0
    all_text_contained = all(
        box.x0 >= -tolerance
        and box.y0 >= -tolerance
        and box.x1 <= WIDTH + tolerance
        and box.y1 <= HEIGHT + tolerance
        for box in bounds
    )
    if not all_text_contained:
        escaped = [
            (artist.get_text(), tuple(round(value, 3) for value in box.bounds))
            for artist, box in zip(text_artists, bounds)
            if box.x0 < -tolerance
            or box.y0 < -tolerance
            or box.x1 > WIDTH + tolerance
            or box.y1 > HEIGHT + tolerance
        ]
        raise RuntimeError(f"Text escaped the 1800 x 1200 canvas: {escaped}")

    heading_indices = [
        index
        for index, artist in enumerate(text_artists)
        if str(artist.get_gid() or "").startswith("heading-")
    ]
    heading_overlaps: list[dict[str, str]] = []
    for heading_index in heading_indices:
        heading_artist = text_artists[heading_index]
        heading_box = bounds[heading_index]
        for other_index, (other_artist, other_box) in enumerate(
            zip(text_artists, bounds)
        ):
            if other_index == heading_index:
                continue
            # Each pair involving two heading artists is checked only once.
            if other_index in heading_indices and other_index < heading_index:
                continue
            horizontal_overlap = min(heading_box.x1, other_box.x1) - max(
                heading_box.x0, other_box.x0
            )
            vertical_overlap = min(heading_box.y1, other_box.y1) - max(
                heading_box.y0, other_box.y0
            )
            if horizontal_overlap > 0.5 and vertical_overlap > 0.5:
                heading_overlaps.append(
                    {
                        "heading": str(heading_artist.get_gid()),
                        "other": str(
                            other_artist.get_gid() or other_artist.get_text()
                        ),
                    }
                )
    if heading_overlaps:
        raise RuntimeError(f"Heading text overlap detected: {heading_overlaps}")
    layout = {
        "all_text_contained": True,
        "all_heading_text_clear": True,
        "heading_text_overlap_pairs": [],
        "minimum_font_size_px": min(float(artist.get_fontsize()) for artist in text_artists),
        "panel_bounds_px": {
            "structural_frame": [50, 150, 650, 600],
            "accessory_rail": [720, 150, 510, 600],
            "cassette_section": [1250, 150, 500, 600],
            "two_level_layout": [50, 775, 1700, 340],
        },
        "footer_bounds_px": [50, 1137, 1700, 42],
    }
    return (fig, plt), layout, drawing_renderer_provenance()


def metadata_payload(
    cfg: dict[str, Any],
    exact: dict[str, Any],
    hashes: dict[str, str],
    layout: dict[str, Any],
    renderer_provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "asset_id": ASSET_ID,
        "canvas_px": [WIDTH, HEIGHT],
        "config_revision": cfg["project"]["revision"],
        "qualification_only": bool(cfg["project"]["qualification_only"]),
        "rated_load_kg": float(cfg["project"]["rated_load_kg"]),
        "rated_load_lb": float(cfg["project"]["rated_load_lb"]),
        "source_hashes": hashes,
        "renderer_provenance": renderer_provenance,
        "exact": exact,
        "counts": {
            "panels": 4,
            "through_support_markers": exact["levels"] * exact["through_supports_per_level"],
            "return_support_markers": exact["levels"] * exact["return_supports_per_level"],
            "distinct_support_markers": exact["levels"]
            * (
                exact["through_supports_per_level"]
                + exact["return_supports_per_level"]
            ),
            "clean_terminal_markers": exact["levels"] * 4,
            "default_rail_markers": exact["levels"]
            * (
                len(exact["through_default_rail_indices"])
                + len(exact["return_default_rail_indices"])
            ),
            "exploded_rail_sockets": exact["rail_socket_count"],
            "accessory_modules": exact["module_count"],
        },
        "required_statements": [
            "all printed parts PETG",
            "metal structural screws into verified framing required",
            "qualification only / zero rated load",
            "remove all modules before rail service",
            "return / corner field-unverified",
            "not an exact full-L",
        ],
        "layout_validation": layout,
    }


def inject_svg_metadata(path: Path, payload: dict[str, Any]) -> None:
    source = path.read_text(encoding="utf-8")
    source = re.sub(r'width="[^"]+"', f'width="{WIDTH}"', source, count=1)
    source = re.sub(r'height="[^"]+"', f'height="{HEIGHT}"', source, count=1)
    source = re.sub(
        r"<svg ",
        (
            f'<svg data-asset-id="{ASSET_ID}" '
            f'data-config-sha256="{payload["source_hashes"]["development/r8/config.json"]}" '
            f'data-min-font-size-px="{payload["layout_validation"]["minimum_font_size_px"]:.1f}" '
        ),
        source,
        count=1,
    )
    root_end = source.index(">", source.index("<svg")) + 1
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    metadata = f'\n <metadata id="r8-proof-metadata">{html.escape(serialized)}</metadata>'
    source = source[:root_end] + metadata + source[root_end:]
    path.write_text(source, encoding="utf-8")


def build_manifest(
    cfg: dict[str, Any],
    exact: dict[str, Any],
    hashes: dict[str, str],
    layout: dict[str, Any],
    renderer_provenance: dict[str, Any],
    paths: ProofPaths,
) -> dict[str, Any]:
    payload = metadata_payload(
        cfg, exact, hashes, layout, renderer_provenance
    )
    return {
        "schema_version": 2,
        **payload,
        "render": {
            "kind": "deterministic code-native matplotlib SVG + PNG",
            "script": "development/r8/render_proof.py",
            "generative_ai_used": False,
            "publication": {
                "staged_and_validated_before_replacement": True,
                "individual_replacement_primitive": "os.replace",
                "commit_marker": "manifest replaced last",
                "source_hashes_checked_pre_render_pre_publish_and_post_publish": True,
            },
        },
        "outputs": {
            "svg": {
                "path": "development/r8/assets/r8_16b_exact_proof.svg",
                "sha256": sha256_file(paths.svg),
                "bytes": paths.svg.stat().st_size,
            },
            "png": {
                "path": "development/r8/assets/r8_16b_exact_proof.png",
                "sha256": sha256_file(paths.png),
                "bytes": paths.png.stat().st_size,
                "dimensions_px": [WIDTH, HEIGHT],
            },
        },
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Not a PNG file: {path}")
        length = struct.unpack(">I", stream.read(4))[0]
        if stream.read(4) != b"IHDR" or length < 8:
            raise ValueError(f"PNG omitted a valid IHDR chunk: {path}")
        data = stream.read(length)
    return struct.unpack(">II", data[:8])


def _svg_metadata(path: Path) -> tuple[ET.Element, dict[str, Any]]:
    root = ET.parse(path).getroot()
    matches = [
        element
        for element in root.iter()
        if _local_name(element.tag) == "metadata"
        and element.attrib.get("id") == "r8-proof-metadata"
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one r8-proof-metadata element, found {len(matches)}"
        )
    payload = strict_json_loads(
        matches[0].text or "", source_name=f"{path} metadata"
    )
    if not isinstance(payload, dict):
        raise ValueError("SVG proof metadata must be a JSON object")
    return root, payload


def validate_output_set(
    paths: ProofPaths, expected_payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate a complete candidate set before it can become authoritative."""

    for path in (paths.svg, paths.png, paths.manifest):
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"Missing or empty proof output: {path}")
    manifest = strict_json_file(paths.manifest)
    if not isinstance(manifest, dict):
        raise ValueError("Proof manifest must be a JSON object")
    root, svg_payload = _svg_metadata(paths.svg)
    if expected_payload is not None:
        for key, expected in expected_payload.items():
            if manifest.get(key) != expected:
                raise ValueError(f"Manifest payload mismatch at {key}")
        if svg_payload != expected_payload:
            raise ValueError("SVG metadata does not equal the staged proof payload")
    if root.attrib.get("width") != str(WIDTH):
        raise ValueError("SVG width does not match the proof contract")
    if root.attrib.get("height") != str(HEIGHT):
        raise ValueError("SVG height does not match the proof contract")
    if root.attrib.get("viewBox") != f"0 0 {WIDTH} {HEIGHT}":
        raise ValueError("SVG viewBox does not match the proof contract")
    if _png_dimensions(paths.png) != (WIDTH, HEIGHT):
        raise ValueError("PNG dimensions do not match the proof contract")
    for kind, path in (("svg", paths.svg), ("png", paths.png)):
        entry = manifest.get("outputs", {}).get(kind, {})
        if entry.get("sha256") != sha256_file(path):
            raise ValueError(f"{kind.upper()} hash does not match the manifest")
        if entry.get("bytes") != path.stat().st_size:
            raise ValueError(f"{kind.upper()} byte count does not match the manifest")
    if manifest.get("outputs", {}).get("png", {}).get("dimensions_px") != [
        WIDTH,
        HEIGHT,
    ]:
        raise ValueError("Manifest PNG dimensions do not match the proof contract")
    return manifest


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_output_set(
    staged: ProofPaths,
    target: ProofPaths,
    expected_source_hashes: dict[str, str],
) -> None:
    """Publish three validated files, with the manifest as final commit marker.

    Each replacement is atomic on the target filesystem.  Existing files are
    held in a transaction backup and restored if publication or the final
    source-snapshot check fails.
    """

    target.directory.mkdir(parents=True, exist_ok=True)
    ordered = (
        (staged.svg, target.svg),
        (staged.png, target.png),
        (staged.manifest, target.manifest),
    )
    with tempfile.TemporaryDirectory(
        prefix=".r8-proof-backup-", dir=target.directory
    ) as backup_name:
        backup_dir = Path(backup_name)
        backups: dict[Path, Path | None] = {}
        for _, destination in ordered:
            if destination.is_file():
                backup = backup_dir / destination.name
                shutil.copy2(destination, backup)
                backups[destination] = backup
            else:
                backups[destination] = None
        try:
            for candidate, destination in ordered:
                os.replace(candidate, destination)
            _fsync_directory(target.directory)
            if source_hashes() != expected_source_hashes:
                raise RuntimeError(
                    "R8 sources changed during proof publication; restored prior set"
                )
        except BaseException:
            for _, destination in reversed(ordered):
                backup = backups[destination]
                if backup is not None and backup.exists():
                    os.replace(backup, destination)
                elif destination.exists():
                    destination.unlink()
            _fsync_directory(target.directory)
            raise


def render_proof(output_directory: Path = ASSET_DIR) -> dict[str, Any]:
    """Render, validate, and transactionally publish one proof-output set."""

    target = proof_paths(output_directory)
    target.directory.mkdir(parents=True, exist_ok=True)
    pre_render_hashes = source_hashes()
    cfg = load_config()
    validate_project_scope(cfg)
    d_frame, cad_provenance = extract_live_d_frame()
    exact = validate_contract(cfg, d_frame)
    (fig, plt), layout, drawing_provenance = render_figure(cfg, exact, d_frame)
    renderer_provenance = {
        "cad": cad_provenance,
        "drawing": drawing_provenance,
    }
    fixed_metadata = {
        "Title": "R8 / 16B exact PETG shelf design proof",
        "Creator": "development/r8/render_proof.py",
        "Date": "2026-08-10T00:00:00-05:00",
        "Description": "Qualification-only exact design proof; zero rated load.",
    }
    with tempfile.TemporaryDirectory(
        prefix=".r8-proof-stage-", dir=target.directory
    ) as stage_name:
        staged = proof_paths(Path(stage_name))
        try:
            fig.savefig(
                staged.svg,
                format="svg",
                dpi=72,
                facecolor=CREAM,
                edgecolor="none",
                metadata=fixed_metadata,
            )
            fig.savefig(
                staged.png,
                format="png",
                dpi=72,
                facecolor=CREAM,
                edgecolor="none",
                metadata={"Software": "development/r8/render_proof.py"},
            )
        finally:
            plt.close(fig)
        payload = metadata_payload(
            cfg,
            exact,
            pre_render_hashes,
            layout,
            renderer_provenance,
        )
        inject_svg_metadata(staged.svg, payload)
        manifest = build_manifest(
            cfg,
            exact,
            pre_render_hashes,
            layout,
            renderer_provenance,
            staged,
        )
        staged.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        if source_hashes() != pre_render_hashes:
            raise RuntimeError(
                "R8 sources changed during proof rendering; no outputs published"
            )
        validate_output_set(staged, expected_payload=payload)
        if source_hashes() != pre_render_hashes:
            raise RuntimeError(
                "R8 sources changed after proof validation; no outputs published"
            )
        publish_output_set(staged, target, pre_render_hashes)
    return validate_output_set(target, expected_payload=payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ASSET_DIR,
        help="Target directory for the coherent proof output set",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = render_proof(args.output_dir)
    exact = manifest["exact"]
    print(
        json.dumps(
            {
                "svg_sha256": manifest["outputs"]["svg"]["sha256"],
                "png_sha256": manifest["outputs"]["png"]["sha256"],
                "minimum_web_mm": exact["d_frame_measured_minimum_web_mm"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
