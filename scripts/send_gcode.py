"""Stream a GCode-like text file to an Arduino over serial, line by line."""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import serial
import sys
import time
import tomllib
import typing as t


@dataclasses.dataclass(frozen=True)
class Config:
    port: str
    baud: int
    startup_delay_ms: int
    read_timeout_ms: int
    continue_on_arduino_error: bool


def load_config(config_path: pathlib.Path) -> Config:
    with config_path.open("rb") as file_obj:
        raw_config: dict[str, t.Any] = tomllib.load(file_obj)

    port_raw: t.Any = raw_config.get("port")
    baud_raw: t.Any = raw_config.get("baud")
    startup_delay_raw: t.Any = raw_config.get("startup_delay_ms")
    read_timeout_raw: t.Any = raw_config.get("read_timeout_ms")
    continue_on_error_raw: t.Any = raw_config.get("continue_on_arduino_error")

    if not isinstance(port_raw, str) or not port_raw.strip():
        raise ValueError("Config key 'port' must be a non-empty string.")
    if not isinstance(baud_raw, int) or baud_raw <= 0:
        raise ValueError("Config key 'baud' must be a positive integer.")
    if not isinstance(startup_delay_raw, int) or startup_delay_raw < 0:
        raise ValueError("Config key 'startup_delay_ms' must be an integer >= 0.")
    if not isinstance(read_timeout_raw, int) or read_timeout_raw <= 0:
        raise ValueError("Config key 'read_timeout_ms' must be a positive integer.")
    if not isinstance(continue_on_error_raw, bool):
        raise ValueError("Config key 'continue_on_arduino_error' must be a boolean.")

    return Config(
        port=port_raw,
        baud=baud_raw,
        startup_delay_ms=startup_delay_raw,
        read_timeout_ms=read_timeout_raw,
        continue_on_arduino_error=continue_on_error_raw,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream GCode to Arduino over a serial port."
    )
    parser.add_argument("file_path", type=pathlib.Path, help="Path to GCode text file")
    parser.add_argument(
        "-c",
        "--config",
        type=pathlib.Path,
        default=pathlib.Path("scripts_cfg.toml"),
        help="Path to config TOML file",
    )
    return parser.parse_args()


def normalized_command(raw_line: str) -> str:
    line = raw_line.strip()
    if not line:
        return ""
    if line.startswith(";") or line.startswith("#"):
        return ""
    return line


def stream_gcode(
    file_path: pathlib.Path,
    config: Config,
) -> int:
    if not file_path.exists():
        raise FileNotFoundError(f"GCode file not found: {file_path}")

    resolved_path = file_path.resolve()
    timeout_seconds = config.read_timeout_ms / 1000.0
    sent_count = 0
    line_number = 0

    try:
        with serial.Serial(
            port=config.port,
            baudrate=config.baud,
            timeout=timeout_seconds,
            write_timeout=timeout_seconds,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        ) as ser:
            time.sleep(config.startup_delay_ms / 1000.0)
            ser.reset_input_buffer()

            print(f"Streaming '{resolved_path}' to {config.port} at {config.baud} baud...")

            with resolved_path.open("r", encoding="utf-8") as gcode_file:
                for raw_line in gcode_file:
                    line_number += 1
                    line = normalized_command(raw_line)
                    if not line:
                        continue

                    ser.write((line + "\n").encode("utf-8"))
                    sent_count += 1

                    response_raw = ser.readline()
                    if not response_raw:
                        raise TimeoutError(
                            "Timeout waiting for Arduino response after "
                            f"line {line_number}: {line}"
                        )

                    response = response_raw.decode("utf-8", errors="replace").strip()
                    if response.lower().startswith("err"):
                        message = (
                            f"Arduino error at line {line_number}: {line}\n"
                            f"Response: {response}"
                        )
                        if config.continue_on_arduino_error:
                            print(f"WARNING: {message}", file=sys.stderr)
                            continue
                        raise RuntimeError(message)

            print(f"Done. Sent {sent_count} commands from {line_number} input lines.")
            return 0
    except serial.SerialException as exc:
        raise RuntimeError(f"Serial communication error on {config.port}: {exc}") from exc


def main() -> int:
    args = parse_args()
    config_path: pathlib.Path = args.config
    config = load_config(config_path)

    try:
        return stream_gcode(
            file_path=args.file_path,
            config=config,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
