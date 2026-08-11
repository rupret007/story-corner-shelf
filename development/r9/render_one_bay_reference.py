#!/usr/bin/env python3
"""Deterministic SVG view of the exact R9 tabletop one-bay target pose."""

from __future__ import annotations

import base64
import html
import struct
import zlib

import numpy as np

try:
    from . import one_bay_geometry as one_bay
except ImportError:  # pragma: no cover
    import one_bay_geometry as one_bay  # type: ignore[no-redef]


WIDTH = 1200
HEIGHT = 1200
VIEW_CENTER = np.asarray((80.0, 76.2, 96.0), dtype=float)
CAMERA = np.asarray((300.0, 360.0, 280.0), dtype=float)

COLORS = {
    "r9_one_bay_left_compact_support": (30, 32, 36),
    "r9_one_bay_right_compact_support": (30, 32, 36),
    "r9_one_bay_rear_ledger": (48, 51, 56),
    "r9_one_bay_front_beam": (48, 51, 56),
    "r9_one_bay_shelf_cassette": (64, 67, 73),
}


def _view_basis() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    forward = VIEW_CENTER - CAMERA
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, np.asarray((0.0, 0.0, 1.0)))
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    up /= np.linalg.norm(up)
    return right, up, forward


def _project(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    right, up, forward = _view_basis()
    relative = points - VIEW_CENTER
    planar = np.column_stack((relative @ right, -(relative @ up)))
    depth = (points - CAMERA) @ forward
    return planar, depth


def _shade(color: tuple[int, int, int], normal: np.ndarray) -> str:
    light = np.asarray((-0.4, -0.55, 0.8), dtype=float)
    light /= np.linalg.norm(light)
    normal = np.asarray(normal, dtype=float)
    magnitude = np.linalg.norm(normal)
    incidence = 0.0 if magnitude <= 1.0e-12 else max(0.0, float(normal @ light / magnitude))
    factor = 0.68 + 0.32 * incidence
    values = tuple(max(0, min(255, round(channel * factor))) for channel in color)
    return "#" + "".join(f"{value:02x}" for value in values)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def _png_bytes(pixels: np.ndarray) -> bytes:
    image = np.asarray(pixels, dtype=np.uint8)
    height, width, channels = image.shape
    if channels != 4:
        raise ValueError("Reference raster must be RGBA")
    rows = b"".join(b"\x00" + image[row].tobytes() for row in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(rows, level=9))
        + _png_chunk(b"IEND", b"")
    )


def _geometry_raster(width: int = 1040, height: int = 650) -> bytes:
    parts = one_bay.build_installed_one_bay_parts()
    triangles: list[tuple[np.ndarray, np.ndarray, tuple[int, int, int]]] = []
    all_projected: list[np.ndarray] = []
    for name, mesh in parts.items():
        projected, depth = _project(np.asarray(mesh.vertices, dtype=float))
        all_projected.append(projected)
        for face, normal in zip(mesh.faces, mesh.face_normals):
            indices = np.asarray(face, dtype=int)
            shade = _shade(COLORS[name], normal)
            color = tuple(int(shade[index : index + 2], 16) for index in (1, 3, 5))
            triangles.append((projected[indices], depth[indices], color))
    aggregate = np.vstack(all_projected)
    minimum = aggregate.min(axis=0)
    maximum = aggregate.max(axis=0)
    available = np.asarray((width - 32.0, height - 32.0))
    scale = float(min(available / (maximum - minimum)))
    offset = np.asarray((width / 2.0, height / 2.0)) - scale * (minimum + maximum) / 2.0
    pixels = np.zeros((height, width, 4), dtype=np.uint8)
    z_buffer = np.full((height, width), np.inf, dtype=float)
    for polygon, depths, color in triangles:
        screen = polygon * scale + offset
        x0, y0 = screen[0]
        x1, y1 = screen[1]
        x2, y2 = screen[2]
        denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(float(denominator)) <= 1.0e-12:
            continue
        minimum_x = max(0, int(np.floor(screen[:, 0].min())))
        maximum_x = min(width - 1, int(np.ceil(screen[:, 0].max())))
        minimum_y = max(0, int(np.floor(screen[:, 1].min())))
        maximum_y = min(height - 1, int(np.ceil(screen[:, 1].max())))
        if minimum_x > maximum_x or minimum_y > maximum_y:
            continue
        grid_y, grid_x = np.mgrid[minimum_y : maximum_y + 1, minimum_x : maximum_x + 1]
        sample_x = grid_x + 0.5
        sample_y = grid_y + 0.5
        weight0 = (
            (y1 - y2) * (sample_x - x2) + (x2 - x1) * (sample_y - y2)
        ) / denominator
        weight1 = (
            (y2 - y0) * (sample_x - x2) + (x0 - x2) * (sample_y - y2)
        ) / denominator
        weight2 = 1.0 - weight0 - weight1
        inside = (weight0 >= -1.0e-8) & (weight1 >= -1.0e-8) & (weight2 >= -1.0e-8)
        interpolated = weight0 * depths[0] + weight1 * depths[1] + weight2 * depths[2]
        current = z_buffer[minimum_y : maximum_y + 1, minimum_x : maximum_x + 1]
        update = inside & (interpolated < current)
        current[update] = interpolated[update]
        region = pixels[minimum_y : maximum_y + 1, minimum_x : maximum_x + 1]
        region[update, 0] = color[0]
        region[update, 1] = color[1]
        region[update, 2] = color[2]
        region[update, 3] = 255
    return _png_bytes(pixels)


def svg_bytes() -> bytes:
    encoded = base64.b64encode(_geometry_raster()).decode("ascii")

    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
        ),
        '<rect width="100%" height="100%" fill="#f4f1ea"/>',
        (
            '<text x="60" y="64" font-family="Arial, sans-serif" '
            'font-size="34" font-weight="700" fill="#17191d">'
            'R9 Palatine Moderne one-bay shelf prototype</text>'
        ),
        (
            '<text x="60" y="98" font-family="Arial, sans-serif" '
            'font-size="18" fill="#4a4e55">Exact CAD target pose · '
            '160 × 152.4 × 190 mm overall · five printed parts</text>'
        ),
        f'<image x="80" y="130" width="1040" height="650" href="data:image/png;base64,{encoded}"/>',
    ]
    labels = (
        "Two handed compact supports",
        "Rear ledger + front beam lower into top-open sockets",
        "Full-depth three-web cassette lowers onto four locator bosses",
        "Roman stepped keystones + Art-Deco front-beam center relief",
        "Each support: three 7.0 mm bores at 16 / 80 / 144 mm drops",
    )
    for index, label in enumerate(labels):
        y = 860 + index * 34
        lines.append(f'<circle cx="65" cy="{y - 5}" r="4" fill="#202329"/>')
        lines.append(
            f'<text x="80" y="{y}" font-family="Arial, sans-serif" '
            f'font-size="18" fill="#30343a">{html.escape(label)}</text>'
        )
    lines.append(
        '<rect x="60" y="1030" width="1080" height="92" rx="12" '
        'fill="#f6dfda" stroke="#b34838" stroke-width="2"/>'
    )
    lines.append(
        '<text x="600" y="1070" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="19" font-weight="700" '
        'fill="#8b2626">TABLETOP FIT PROTOTYPE · 0 KG / 0 LB</text>'
    )
    lines.append(
        '<text x="600" y="1100" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="16" fill="#6e2b23">'
        'Printed bores are present; drilling and wall installation remain '
        'blocked until hardware and framing are verified.</text>'
    )
    lines.append("</svg>")
    return ("\n".join(lines) + "\n").encode("utf-8")


if __name__ == "__main__":
    import sys

    sys.stdout.buffer.write(svg_bytes())
