"""Stream a GCode-like text file to an Arduino over serial, line by line."""

from __future__ import annotations
import argparse
import pathlib
import serial
import sys
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream GCode to Arduino over a serial port."
    )
    parser.add_argument("file_path", type=pathlib.Path, help="Path to GCode text file")
    parser.add_argument(
        "--port",
        default="COM3",
        help="Serial port (for example COM3, /dev/ttyACM0, /dev/ttyUSB0)",
    )
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument(
        "--startup-delay-ms",
        type=int,
        default=2000,
        help="Delay after opening serial port to allow Arduino reset",
    )
    parser.add_argument(
        "--read-timeout-ms",
        type=int,
        default=3000,
        help="Read and write timeout in milliseconds",
    )
    parser.add_argument(
        "--continue-on-arduino-error",
        action="store_true",
        help="Warn and continue when Arduino responds with ERR",
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
    port: str,
    baud: int,
    startup_delay_ms: int,
    read_timeout_ms: int,
    continue_on_arduino_error: bool,
) -> int:
    if not file_path.exists():
        raise FileNotFoundError(f"GCode file not found: {file_path}")

    resolved_path = file_path.resolve()
    timeout_seconds = read_timeout_ms / 1000.0
    sent_count = 0
    line_number = 0

    try:
        with serial.Serial(
            port=port,
            baudrate=baud,
            timeout=timeout_seconds,
            write_timeout=timeout_seconds,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        ) as ser:
            time.sleep(startup_delay_ms / 1000.0)
            ser.reset_input_buffer()

            print(f"Streaming '{resolved_path}' to {port} at {baud} baud...")

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
                        if continue_on_arduino_error:
                            print(f"WARNING: {message}", file=sys.stderr)
                            continue
                        raise RuntimeError(message)

            print(f"Done. Sent {sent_count} commands from {line_number} input lines.")
            return 0
    except serial.SerialException as exc:
        raise RuntimeError(f"Serial communication error on {port}: {exc}") from exc


def main() -> int:
    args = parse_args()

    try:
        return stream_gcode(
            file_path=args.file_path,
            port=args.port,
            baud=args.baud,
            startup_delay_ms=args.startup_delay_ms,
            read_timeout_ms=args.read_timeout_ms,
            continue_on_arduino_error=args.continue_on_arduino_error,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
