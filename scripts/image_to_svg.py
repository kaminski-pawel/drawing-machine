from __future__ import annotations

import argparse
import cv2
import dataclasses
import pathlib
import numpy as np
import typing as t
import tomllib


@dataclasses.dataclass(frozen=True)
class Config:
    threshold: int
    stroke_width: float


def load_config(config_path: pathlib.Path) -> Config:
    with config_path.open("rb") as file_obj:
        raw_config: dict[str, t.Any] = tomllib.load(file_obj)

    threshold_raw: t.Any = raw_config.get("threshold")
    stroke_width_raw: t.Any = raw_config.get("stroke_width")

    if not isinstance(threshold_raw, int) or not (0 <= threshold_raw <= 255):
        raise ValueError("Config key 'threshold' must be an integer between 0 and 255.")

    if not isinstance(stroke_width_raw, (int, float)) or float(stroke_width_raw) <= 0:
        raise ValueError("Config key 'stroke_width' must be a positive number.")

    return Config(threshold=threshold_raw, stroke_width=float(stroke_width_raw))


def image_to_binary(
    image_path: pathlib.Path, threshold: int
) -> tuple[np.typing.NDArray[np.uint8], int, int]:
    image: np.typing.NDArray[np.uint8] | None = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    height, width = image.shape

    _, binary = cv2.threshold(
        image,
        threshold,
        255,
        cv2.THRESH_BINARY_INV,
    )

    return binary, width, height


def contour_to_path_data(contour: np.typing.NDArray[np.int32]) -> str:
    points: np.typing.NDArray[np.int32] = contour.reshape(-1, 2)
    if points.shape[0] == 0:
        return ""

    commands: list[str] = [f"M {int(points[0, 0])} {int(points[0, 1])}"]
    for point in points[1:]:
        x: int = int(point[0])
        y: int = int(point[1])
        commands.append(f"L {x} {y}")

    commands.append("Z")
    return " ".join(commands)


def contours_to_svg(
    contours: tuple[np.typing.NDArray[np.int32], ...],
    width: int,
    height: int,
    stroke_width: float,
) -> str:
    path_lines: list[str] = []

    for contour in contours:
        path_data = contour_to_path_data(contour)
        if path_data:
            path_lines.append(
                f'  <path d="{path_data}" fill="none" stroke="black" stroke-width="{stroke_width}"/>'
            )

    svg_content: str = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
            *path_lines,
            "</svg>",
        ]
    )
    return svg_content


def convert_image_to_svg(input_path: pathlib.Path, output_path: pathlib.Path, config: Config) -> None:
    binary, width, height = image_to_binary(input_path, config.threshold)

    contours_raw, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours: tuple[np.typing.NDArray[np.int32], ...] = tuple(contours_raw)

    svg_data: str = contours_to_svg(contours, width, height, config.stroke_width)
    output_path.write_text(svg_data, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PNG/JPEG/JPG images to SVG outlines using contour tracing."
    )
    parser.add_argument("input", type=pathlib.Path, help="Input image path (.png, .jpeg, .jpg)")
    parser.add_argument(
        "-o", "--output", type=pathlib.Path, default=None, help="Output SVG path"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=pathlib.Path,
        default=pathlib.Path("scripts_cfg.toml"),
        help="Path to config TOML file",
    )
    return parser.parse_args()


def validate_input_extension(path: pathlib.Path) -> None:
    allowed_suffixes: set[str] = {".png", ".jpeg", ".jpg"}
    suffix = path.suffix.lower()
    if suffix not in allowed_suffixes:
        raise ValueError(
            f"Unsupported input format '{suffix}'. Expected one of: {', '.join(sorted(allowed_suffixes))}."
        )


def main() -> None:
    args = parse_args()
    input_path: pathlib.Path = args.input
    output_path: pathlib.Path = (
        args.output if args.output is not None else input_path.with_suffix(".svg")
    )
    config_path: pathlib.Path = args.config

    validate_input_extension(input_path)
    config = load_config(config_path)
    convert_image_to_svg(input_path, output_path, config)


if __name__ == "__main__":
    main()
