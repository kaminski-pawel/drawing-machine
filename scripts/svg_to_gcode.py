#!/usr/bin/env python3
"""
Convert an SVG drawing into a GCode-like command stream for a two-motor hanging plotter.

This script is standalone and uses only Python's standard library.

Coordinate model
----------------
- Machine origin is at the LEFT motor pulley.
- RIGHT motor pulley is at (machine_width_mm, 0).
- Pen position is represented as two cable lengths:
  - L = distance from pen to left motor
  - R = distance from pen to right motor

Output command format
---------------------
The script emits plain-text commands inspired by GCode:
- `G0 L... R... F...` : rapid/travel move with pen up
- `G1 L... R... F...` : drawing move with pen down
- `M300 S....`        : servo pulse width in microseconds (pen up/down)

The generated file is intentionally simple so firmware can parse it with a tiny parser.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


# Matches SVG path command letters and numbers, including scientific notation.
PATH_TOKEN_RE = re.compile(r"[MmLlHhVvCcQqZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
NUMBER_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


@dataclass(frozen=True)
class Point:
    """2D point in Cartesian coordinates."""

    x: float
    y: float


@dataclass
class PlotterConfig:
    """Machine and conversion settings used for SVG->command translation."""

    machine_width_mm: float
    machine_height_mm: float
    margin_mm: float
    travel_feed_mm_min: float
    draw_feed_mm_min: float
    pen_up_us: int
    pen_down_us: int
    curve_segments: int
    max_segment_mm: float


DISTANCE_BETWEEN_STEPPERS_IN_MM = 230.0 # mm


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command line options for the converter."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_svg", type=Path, help="Path to input SVG file")
    parser.add_argument("output_gcode", type=Path, help="Path to output text file")

    parser.add_argument("--machine-width-mm", type=float, default=DISTANCE_BETWEEN_STEPPERS_IN_MM)
    parser.add_argument("--machine-height-mm", type=float, default=DISTANCE_BETWEEN_STEPPERS_IN_MM)
    parser.add_argument("--margin-mm", type=float, default=0.0)
    parser.add_argument("--travel-feed", type=float, default=2500.0, help="Travel feed in mm/min")
    parser.add_argument("--draw-feed", type=float, default=1200.0, help="Draw feed in mm/min")
    parser.add_argument("--pen-up-us", type=int, default=1100, help="Servo pulse for pen-up")
    parser.add_argument("--pen-down-us", type=int, default=1700, help="Servo pulse for pen-down")
    parser.add_argument("--curve-segments", type=int, default=20, help="Segments per bezier curve")
    parser.add_argument(
        "--max-segment-mm",
        type=float,
        default=2.0,
        help="Resample long lines so each output segment is <= this length",
    )

    return parser.parse_args(argv)


def strip_unit(value: str) -> float:
    """Extract a numeric float from an SVG attribute that may include units."""

    match = NUMBER_RE.search(value.strip())
    if not match:
        raise ValueError(f"Cannot parse numeric SVG value: {value!r}")
    return float(match.group(0))


def parse_viewbox(root: ET.Element) -> Tuple[float, float, float, float] | None:
    """Return SVG viewBox as (min_x, min_y, width, height), or None if missing."""

    vb = root.get("viewBox")
    if not vb:
        return None
    parts = [p for p in re.split(r"[\s,]+", vb.strip()) if p]
    if len(parts) != 4:
        raise ValueError(f"Invalid viewBox format: {vb!r}")
    min_x, min_y, width, height = map(float, parts)
    return min_x, min_y, width, height


def tokenize_path(d: str) -> List[str]:
    """Tokenize SVG path `d` data into command and numeric tokens."""

    return PATH_TOKEN_RE.findall(d)


def cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    """Evaluate a cubic bezier at parameter t in [0, 1]."""

    u = 1.0 - t
    x = (u ** 3) * p0.x + 3 * (u ** 2) * t * p1.x + 3 * u * (t ** 2) * p2.x + (t ** 3) * p3.x
    y = (u ** 3) * p0.y + 3 * (u ** 2) * t * p1.y + 3 * u * (t ** 2) * p2.y + (t ** 3) * p3.y
    return Point(x, y)


def quadratic_point(p0: Point, p1: Point, p2: Point, t: float) -> Point:
    """Evaluate a quadratic bezier at parameter t in [0, 1]."""

    u = 1.0 - t
    x = (u ** 2) * p0.x + 2 * u * t * p1.x + (t ** 2) * p2.x
    y = (u ** 2) * p0.y + 2 * u * t * p1.y + (t ** 2) * p2.y
    return Point(x, y)


def parse_path_to_polyline(d: str, curve_segments: int) -> List[List[Point]]:
    """
    Parse path data and return a list of polyline subpaths.

    Supported commands: M, L, H, V, C, Q, Z (and lowercase relatives).
    Arcs and shorthand bezier commands are intentionally omitted for clarity.
    """

    tokens = tokenize_path(d)
    i = 0
    cmd = ""

    polylines: List[List[Point]] = []
    current_polyline: List[Point] = []

    current = Point(0.0, 0.0)
    subpath_start = Point(0.0, 0.0)

    def read_float() -> float:
        nonlocal i
        if i >= len(tokens):
            raise ValueError("Unexpected end of path tokens")
        value = float(tokens[i])
        i += 1
        return value

    def ensure_subpath() -> None:
        nonlocal current_polyline
        if not current_polyline:
            current_polyline = [current]
            polylines.append(current_polyline)

    while i < len(tokens):
        token = tokens[i]
        if re.fullmatch(r"[A-Za-z]", token):
            cmd = token
            i += 1
        elif not cmd:
            raise ValueError("Path data starts with coordinates but no command")

        absolute = cmd.isupper()
        op = cmd.upper()

        if op == "M":
            x = read_float()
            y = read_float()
            if not absolute:
                x += current.x
                y += current.y
            current = Point(x, y)
            subpath_start = current
            current_polyline = [current]
            polylines.append(current_polyline)

            # SVG allows extra coordinate pairs after M/m, treated as implicit L/l.
            while i < len(tokens) and not re.fullmatch(r"[A-Za-z]", tokens[i]):
                x = read_float()
                y = read_float()
                if not absolute:
                    x += current.x
                    y += current.y
                current = Point(x, y)
                current_polyline.append(current)

        elif op == "L":
            ensure_subpath()
            while i < len(tokens) and not re.fullmatch(r"[A-Za-z]", tokens[i]):
                x = read_float()
                y = read_float()
                if not absolute:
                    x += current.x
                    y += current.y
                current = Point(x, y)
                current_polyline.append(current)

        elif op == "H":
            ensure_subpath()
            while i < len(tokens) and not re.fullmatch(r"[A-Za-z]", tokens[i]):
                x = read_float()
                if not absolute:
                    x += current.x
                current = Point(x, current.y)
                current_polyline.append(current)

        elif op == "V":
            ensure_subpath()
            while i < len(tokens) and not re.fullmatch(r"[A-Za-z]", tokens[i]):
                y = read_float()
                if not absolute:
                    y += current.y
                current = Point(current.x, y)
                current_polyline.append(current)

        elif op == "C":
            ensure_subpath()
            while i < len(tokens) and not re.fullmatch(r"[A-Za-z]", tokens[i]):
                x1 = read_float()
                y1 = read_float()
                x2 = read_float()
                y2 = read_float()
                x = read_float()
                y = read_float()
                if not absolute:
                    x1 += current.x
                    y1 += current.y
                    x2 += current.x
                    y2 += current.y
                    x += current.x
                    y += current.y

                p1 = Point(x1, y1)
                p2 = Point(x2, y2)
                p3 = Point(x, y)
                for s in range(1, curve_segments + 1):
                    t = s / curve_segments
                    current_polyline.append(cubic_point(current, p1, p2, p3, t))
                current = p3

        elif op == "Q":
            ensure_subpath()
            while i < len(tokens) and not re.fullmatch(r"[A-Za-z]", tokens[i]):
                x1 = read_float()
                y1 = read_float()
                x = read_float()
                y = read_float()
                if not absolute:
                    x1 += current.x
                    y1 += current.y
                    x += current.x
                    y += current.y

                p1 = Point(x1, y1)
                p2 = Point(x, y)
                for s in range(1, curve_segments + 1):
                    t = s / curve_segments
                    current_polyline.append(quadratic_point(current, p1, p2, t))
                current = p2

        elif op == "Z":
            ensure_subpath()
            current_polyline.append(subpath_start)
            current = subpath_start

        else:
            raise ValueError(
                f"Unsupported SVG path command: {cmd!r}. "
                "Supported: M, L, H, V, C, Q, Z (and lowercase variants)."
            )

    # Drop degenerate polylines that have fewer than 2 points.
    return [line for line in polylines if len(line) > 1]


def parse_points_attr(value: str) -> List[Point]:
    """Parse SVG points attribute used by polyline/polygon elements."""

    numbers = [float(n) for n in NUMBER_RE.findall(value)]
    if len(numbers) % 2 != 0:
        raise ValueError(f"Invalid points attribute: {value!r}")
    return [Point(numbers[i], numbers[i + 1]) for i in range(0, len(numbers), 2)]


def svg_to_polylines(svg_path: Path, curve_segments: int) -> List[List[Point]]:
    """
    Extract drawable SVG geometry into polylines.

    Supports: path, polyline, polygon, line, rect, circle, ellipse.
    Ignores transforms/styles for simplicity.
    """

    tree = ET.parse(svg_path)
    root = tree.getroot()

    polylines: List[List[Point]] = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1]  # Strip optional XML namespace.

        if tag == "path":
            d = elem.get("d")
            if d:
                polylines.extend(parse_path_to_polyline(d, curve_segments))

        elif tag == "polyline":
            points = elem.get("points", "")
            line = parse_points_attr(points)
            if len(line) > 1:
                polylines.append(line)

        elif tag == "polygon":
            points = elem.get("points", "")
            line = parse_points_attr(points)
            if len(line) > 2:
                line = line + [line[0]]
            if len(line) > 1:
                polylines.append(line)

        elif tag == "line":
            x1 = strip_unit(elem.get("x1", "0"))
            y1 = strip_unit(elem.get("y1", "0"))
            x2 = strip_unit(elem.get("x2", "0"))
            y2 = strip_unit(elem.get("y2", "0"))
            polylines.append([Point(x1, y1), Point(x2, y2)])

        elif tag == "rect":
            x = strip_unit(elem.get("x", "0"))
            y = strip_unit(elem.get("y", "0"))
            w = strip_unit(elem.get("width", "0"))
            h = strip_unit(elem.get("height", "0"))
            if w > 0 and h > 0:
                polylines.append([
                    Point(x, y),
                    Point(x + w, y),
                    Point(x + w, y + h),
                    Point(x, y + h),
                    Point(x, y),
                ])

        elif tag == "circle":
            cx = strip_unit(elem.get("cx", "0"))
            cy = strip_unit(elem.get("cy", "0"))
            r = strip_unit(elem.get("r", "0"))
            if r > 0:
                segments = max(16, curve_segments * 2)
                line = []
                for i in range(segments + 1):
                    t = 2.0 * math.pi * i / segments
                    line.append(Point(cx + r * math.cos(t), cy + r * math.sin(t)))
                polylines.append(line)

        elif tag == "ellipse":
            cx = strip_unit(elem.get("cx", "0"))
            cy = strip_unit(elem.get("cy", "0"))
            rx = strip_unit(elem.get("rx", "0"))
            ry = strip_unit(elem.get("ry", "0"))
            if rx > 0 and ry > 0:
                segments = max(16, curve_segments * 2)
                line = []
                for i in range(segments + 1):
                    t = 2.0 * math.pi * i / segments
                    line.append(Point(cx + rx * math.cos(t), cy + ry * math.sin(t)))
                polylines.append(line)

    if not polylines:
        raise ValueError("No supported drawable geometry found in SVG")

    return polylines


def bounds(polylines: Sequence[Sequence[Point]]) -> Tuple[float, float, float, float]:
    """Compute axis-aligned bounds as (min_x, min_y, max_x, max_y)."""

    xs = [p.x for line in polylines for p in line]
    ys = [p.y for line in polylines for p in line]
    return min(xs), min(ys), max(xs), max(ys)


def fit_to_machine(polylines: Sequence[Sequence[Point]], cfg: PlotterConfig) -> List[List[Point]]:
    """
    Fit SVG geometry uniformly into the configured machine drawing rectangle.

    The drawing rectangle is machine size reduced by margins on all sides.
    """

    min_x, min_y, max_x, max_y = bounds(polylines)
    art_w = max(1e-9, max_x - min_x)
    art_h = max(1e-9, max_y - min_y)

    target_w = cfg.machine_width_mm - 2.0 * cfg.margin_mm
    target_h = cfg.machine_height_mm - 2.0 * cfg.margin_mm
    if target_w <= 0.0 or target_h <= 0.0:
        raise ValueError("Margins are too large for machine dimensions")

    scale = min(target_w / art_w, target_h / art_h)

    # Center in the usable area after scaling.
    draw_w = art_w * scale
    draw_h = art_h * scale
    offset_x = cfg.margin_mm + 0.5 * (target_w - draw_w)
    offset_y = cfg.margin_mm + 0.5 * (target_h - draw_h)

    fitted: List[List[Point]] = []
    for line in polylines:
        mapped = [Point((p.x - min_x) * scale + offset_x, (p.y - min_y) * scale + offset_y) for p in line]
        fitted.append(mapped)
    return fitted


def segment_length(a: Point, b: Point) -> float:
    """Return Euclidean distance between points a and b."""

    return math.hypot(b.x - a.x, b.y - a.y)


def resample_line(line: Sequence[Point], max_segment_mm: float) -> List[Point]:
    """
    Split long line segments into shorter pieces for smoother motion control.

    This reduces large jumps and helps low-resource firmware keep timing stable.
    """

    if len(line) < 2:
        return list(line)

    sampled: List[Point] = [line[0]]
    for i in range(1, len(line)):
        a = line[i - 1]
        b = line[i]
        dist = segment_length(a, b)
        if dist <= max_segment_mm:
            sampled.append(b)
            continue

        steps = max(1, int(math.ceil(dist / max_segment_mm)))
        for s in range(1, steps + 1):
            t = s / steps
            sampled.append(Point(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t))

    return sampled


def xy_to_lengths(x: float, y: float, machine_width_mm: float) -> Tuple[float, float]:
    """Convert Cartesian pen coordinate to left/right cable lengths in mm."""

    left = math.hypot(x, y)
    right = math.hypot(machine_width_mm - x, y)
    return left, right


def emit_commands(polylines_mm: Sequence[Sequence[Point]], cfg: PlotterConfig) -> List[str]:
    """Generate the final GCode-like command lines."""

    out: List[str] = []
    out.append("; SVG -> dual-stepper cable-length commands")
    out.append(f"; Machine width={cfg.machine_width_mm:.3f}mm height={cfg.machine_height_mm:.3f}mm")
    out.append(f"M300 S{cfg.pen_up_us} ; pen up")

    for line in polylines_mm:
        if len(line) < 2:
            continue

        start = line[0]
        left, right = xy_to_lengths(start.x, start.y, cfg.machine_width_mm)
        out.append(
            f"G0 L{left:.3f} R{right:.3f} F{cfg.travel_feed_mm_min:.1f} ; X{start.x:.3f} Y{start.y:.3f}"
        )
        out.append(f"M300 S{cfg.pen_down_us} ; pen down")

        for p in line[1:]:
            left, right = xy_to_lengths(p.x, p.y, cfg.machine_width_mm)
            out.append(
                f"G1 L{left:.3f} R{right:.3f} F{cfg.draw_feed_mm_min:.1f} ; X{p.x:.3f} Y{p.y:.3f}"
            )

        out.append(f"M300 S{cfg.pen_up_us} ; pen up")

    return out


def main(argv: Sequence[str]) -> int:
    """
    End-to-end conversion pipeline.

    Steps:
    1) Parse SVG into polylines (curves are approximated with line segments).
    2) Uniformly fit art into machine drawing bounds with margins.
    3) Resample long segments for smoother execution.
    4) Convert XY points into left/right cable lengths.
    5) Emit simple GCode-like lines and write output file.
    """

    args = parse_args(argv)

    cfg = PlotterConfig(
        machine_width_mm=args.machine_width_mm,
        machine_height_mm=args.machine_height_mm,
        margin_mm=args.margin_mm,
        travel_feed_mm_min=args.travel_feed,
        draw_feed_mm_min=args.draw_feed,
        pen_up_us=args.pen_up_us,
        pen_down_us=args.pen_down_us,
        curve_segments=max(3, args.curve_segments),
        max_segment_mm=max(0.1, args.max_segment_mm),
    )

    try:
        raw_lines = svg_to_polylines(args.input_svg, curve_segments=cfg.curve_segments)
        fitted = fit_to_machine(raw_lines, cfg)
        resampled = [resample_line(line, cfg.max_segment_mm) for line in fitted]
        commands = emit_commands(resampled, cfg)

        args.output_gcode.parent.mkdir(parents=True, exist_ok=True)
        args.output_gcode.write_text("\n".join(commands) + "\n", encoding="utf-8")

    except Exception as exc:  # pylint: disable=broad-except
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(commands)} commands to {args.output_gcode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
