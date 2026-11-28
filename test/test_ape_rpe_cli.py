"""Regression tests for the APE and RPE command-line interfaces."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evo.cli import entry_points
from evo.tools.file_interface import load_res_file


class TestTimeBounds(unittest.TestCase):
    def test_single_zero_time_bound(self):
        cases = (
            (entry_points.ape, "--t_start", [0.0, 1.0]),
            (entry_points.ape, "--t_end", [-1.0, 0.0]),
            (entry_points.rpe, "--t_start", [1.0]),
            (entry_points.rpe, "--t_end", [0.0]),
        )
        with TemporaryDirectory() as temp_dir:
            trajectory = Path(temp_dir) / "trajectory.tum"
            trajectory.write_text(
                "-1 0 0 0 0 0 0 1\n0 1 0 0 0 0 0 1\n1 2 0 0 0 0 0 1\n",
                encoding="utf-8",
            )
            for entry_point, bound, expected_timestamps in cases:
                command = f"evo_{entry_point.__name__}"
                with self.subTest(command=command, bound=bound):
                    result_file = Path(temp_dir) / f"{command}{bound}.zip"
                    arguments = [
                        command,
                        "tum",
                        str(trajectory),
                        str(trajectory),
                        bound,
                        "0",
                        "--save_results",
                        str(result_file),
                    ]
                    with (
                        patch.object(sys, "argv", arguments),
                        patch("evo.tools.log.configure_logging"),
                    ):
                        entry_point()
                    result = load_res_file(result_file)
                    self.assertEqual(
                        result.np_arrays["timestamps"].tolist(),
                        expected_timestamps,
                    )
                    self.assertEqual(
                        len(result.np_arrays["error_array"]),
                        len(expected_timestamps),
                    )
