#!/usr/bin/env python3
"""Measured, evenly spaced support layout for the eventual R9 shelf set.

This module converts the accepted 61.25 in and 36.75 in wall measurements into
the minimum number of equally spaced support stations that does not exceed the
qualification scaffold's maximum pitch.  It is intentionally separate from
the immutable qualification bundles: the centers are exact design candidates,
but they are not drilling coordinates until trim, wall bow, framing, substrate,
and one exact metal-fastener system have been recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

try:
    from . import design_math
except ImportError:  # pragma: no cover - direct unittest discovery
    import design_math  # type: ignore[no-redef]


INCH_MM = 25.4
TERMINAL_CENTER_INSET_MM = 16.0
LEVEL_TOP_ELEVATIONS_IN = (68.0, 84.0)
MOUNTING_BORES_PER_SUPPORT = 3
PRIMARY_HOLLOW_WALL_ANCHOR_AUTHORIZED = False
DRILLING_COORDINATES_RELEASED = False


@dataclass(frozen=True)
class FieldSupportStation:
    run_id: str
    index: int
    center_from_run_datum_mm: float
    center_from_run_datum_in: float
    role: str
    visible: bool
    mounting_bores: int


@dataclass(frozen=True)
class EvenRunLayout:
    run_id: str
    datum: str
    direction: str
    clear_length_mm: float
    end_inset_mm: float
    maximum_pitch_mm: float
    actual_pitch_mm: float
    actual_pitch_in: float
    stations: tuple[FieldSupportStation, ...]


@dataclass(frozen=True)
class EvenFieldLayout:
    runs: tuple[EvenRunLayout, ...]
    level_top_elevations_in: tuple[float, ...]
    supports_per_level: int
    visible_supports_per_level: int
    hidden_corner_halves_per_level: int
    mounting_bores_per_support: int
    drilling_coordinates_released: bool
    primary_hollow_wall_anchor_authorized: bool


def _run_roles(run_id: str, count: int) -> tuple[str, ...]:
    if run_id == "through":
        return ("outer_bookend", *("compact" for _ in range(count - 2)), "hidden_corner")
    if run_id == "return":
        return ("hidden_corner", *("compact" for _ in range(count - 2)), "outer_bookend")
    raise ValueError(f"Unknown measured run: {run_id}")


def _build_run(
    *,
    run_id: str,
    clear_length_mm: float,
    maximum_pitch_mm: float,
) -> EvenRunLayout:
    usable = clear_length_mm - 2.0 * TERMINAL_CENTER_INSET_MM
    if not math.isfinite(usable) or usable <= 0.0:
        raise ValueError(f"{run_id} measured wall is too short for terminal supports")
    intervals = max(1, math.ceil(usable / maximum_pitch_mm - 1.0e-12))
    count = intervals + 1
    pitch = usable / intervals
    if pitch > maximum_pitch_mm + 1.0e-9:
        raise ValueError(f"{run_id} evenly spaced support pitch exceeds its ceiling")
    roles = _run_roles(run_id, count)
    stations = tuple(
        FieldSupportStation(
            run_id=run_id,
            index=index,
            center_from_run_datum_mm=round(
                TERMINAL_CENTER_INSET_MM + index * pitch, 6
            ),
            center_from_run_datum_in=round(
                (TERMINAL_CENTER_INSET_MM + index * pitch) / INCH_MM, 6
            ),
            role=roles[index],
            visible=roles[index] != "hidden_corner",
            mounting_bores=MOUNTING_BORES_PER_SUPPORT,
        )
        for index in range(count)
    )
    datum, direction = {
        "through": ("far-left wall end", "toward the inside corner"),
        "return": ("inside corner", "toward the far-right wall end"),
    }[run_id]
    return EvenRunLayout(
        run_id=run_id,
        datum=datum,
        direction=direction,
        clear_length_mm=round(clear_length_mm, 6),
        end_inset_mm=TERMINAL_CENTER_INSET_MM,
        maximum_pitch_mm=maximum_pitch_mm,
        actual_pitch_mm=round(pitch, 6),
        actual_pitch_in=round(pitch / INCH_MM, 6),
        stations=stations,
    )


def build_even_field_layout(config: dict[str, Any] | None = None) -> EvenFieldLayout:
    """Return the exact equal-pitch candidate for both measured wall runs."""

    cfg = design_math.load_config() if config is None else config
    design_math.validate_config(cfg)
    field = cfg["field_reference"]
    bridging = cfg["span_bridging_system"]
    through = _build_run(
        run_id="through",
        clear_length_mm=round(
            float(field["through_wall_clear_length_in"]) * INCH_MM, 6
        ),
        maximum_pitch_mm=float(
            bridging["maximum_nominal_through_support_pitch_mm"]
        ),
    )
    return_run = _build_run(
        run_id="return",
        clear_length_mm=round(
            float(field["return_wall_clear_length_in"]) * INCH_MM, 6
        ),
        maximum_pitch_mm=float(
            bridging["maximum_nominal_return_support_pitch_mm"]
        ),
    )
    runs = (through, return_run)
    all_stations = tuple(station for run in runs for station in run.stations)
    return EvenFieldLayout(
        runs=runs,
        level_top_elevations_in=LEVEL_TOP_ELEVATIONS_IN,
        supports_per_level=len(all_stations),
        visible_supports_per_level=sum(item.visible for item in all_stations),
        hidden_corner_halves_per_level=sum(
            item.role == "hidden_corner" for item in all_stations
        ),
        mounting_bores_per_support=MOUNTING_BORES_PER_SUPPORT,
        drilling_coordinates_released=DRILLING_COORDINATES_RELEASED,
        primary_hollow_wall_anchor_authorized=(
            PRIMARY_HOLLOW_WALL_ANCHOR_AUTHORIZED
        ),
    )


if __name__ == "__main__":
    layout = build_even_field_layout()
    for run in layout.runs:
        centers = ", ".join(
            f"{station.center_from_run_datum_in:.3f} in" for station in run.stations
        )
        print(f"{run.run_id}: {len(run.stations)} supports at {centers}")
