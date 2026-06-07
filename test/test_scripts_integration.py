from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


class TestDrawingPipelineIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = pathlib.Path(__file__).resolve().parents[1]
        self.image_path = self.repo_root / "data" / "plus.jpeg"
        self.config_path = self.repo_root / "scripts_cfg.toml"
        self.image_to_svg_script = self.repo_root / "scripts" / "image_to_svg.py"
        self.svg_to_gcode_script = self.repo_root / "scripts" / "svg_to_gcode.py"

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_generates_svg_from_plus_jpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_svg = pathlib.Path(temp_dir) / "plus.generated.svg"
            result = self._run(
                str(self.image_to_svg_script),
                str(self.image_path),
                "-o",
                str(output_svg),
                "-c",
                str(self.config_path),
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"image_to_svg.py failed. stderr:\n{result.stderr}\nstdout:\n{result.stdout}",
            )
            self.assertTrue(output_svg.exists(), "SVG output file was not created.")

            svg_text = output_svg.read_text(encoding="utf-8")
            self.assertIn("<svg", svg_text)
            self.assertIn("viewBox=", svg_text)
            self.assertIn("<path", svg_text)

            root = ET.fromstring(svg_text)
            self.assertTrue(root.tag.endswith("svg"))

            path_count = sum(1 for elem in root.iter() if elem.tag.endswith("path"))
            self.assertGreater(path_count, 0, "Generated SVG has no path elements.")

    def test_generates_gcode_from_generated_svg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_svg = pathlib.Path(temp_dir) / "plus.generated.svg"
            output_gcode = pathlib.Path(temp_dir) / "plus.generated.gcode"

            image_to_svg = self._run(
                str(self.image_to_svg_script),
                str(self.image_path),
                "-o",
                str(output_svg),
                "-c",
                str(self.config_path),
            )
            self.assertEqual(
                image_to_svg.returncode,
                0,
                msg=f"image_to_svg.py failed. stderr:\n{image_to_svg.stderr}\nstdout:\n{image_to_svg.stdout}",
            )

            svg_to_gcode = self._run(
                str(self.svg_to_gcode_script),
                str(output_svg),
                str(output_gcode),
                "-c",
                str(self.config_path),
            )
            self.assertEqual(
                svg_to_gcode.returncode,
                0,
                msg=f"svg_to_gcode.py failed. stderr:\n{svg_to_gcode.stderr}\nstdout:\n{svg_to_gcode.stdout}",
            )
            self.assertTrue(output_gcode.exists(), "GCode output file was not created.")

            lines = output_gcode.read_text(encoding="utf-8").splitlines()
            self.assertGreater(len(lines), 5, "Generated GCode-like file is unexpectedly short.")
            self.assertTrue(lines[0].startswith("; SVG ->"))

            g0_lines = [line for line in lines if line.startswith("G0 ")]
            g1_lines = [line for line in lines if line.startswith("G1 ")]
            pen_up_lines = [line for line in lines if line.startswith("M300 S1100")]
            pen_down_lines = [line for line in lines if line.startswith("M300 S1700")]

            self.assertGreater(len(g0_lines), 0, "Expected at least one travel move (G0).")
            self.assertGreater(len(g1_lines), 0, "Expected at least one drawing move (G1).")
            self.assertGreater(len(pen_up_lines), 0, "Expected pen-up command(s).")
            self.assertGreater(len(pen_down_lines), 0, "Expected pen-down command(s).")


if __name__ == "__main__":
    unittest.main()
