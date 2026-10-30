"""Tests for command-line configuration generation."""

import io
import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evo.cli import ape_parser, config, entry_points
from evo.tools.file_interface import load_res_file


class TestGenerate(unittest.TestCase):
    """Check numeric arguments and compatibility of generated CLI configs."""

    def test_negative_numbers(self):
        """Keep signed numeric tokens as values rather than option names."""
        for token in ("-1", "-0.1", "-.5", "-1e-3", "-2E+2", "-0"):
            with self.subTest(token=token):
                self.assertEqual(
                    config.generate(["--t_offset", token, "--align"]),
                    {"t_offset": float(token), "align": True},
                )

    def test_mixed_numeric_list(self):
        """Preserve numeric lists until a real option begins."""
        self.assertEqual(
            config.generate(["--values", "1", "-2", "3e-4", "-5e-6", "-v"]),
            {"values": [1.0, -2.0, 3e-4, -5e-6], "v": True},
        )

    def test_flags_and_strings(self):
        """Keep ordinary short flags, long flags and string values unchanged."""
        self.assertEqual(
            config.generate(["--align", "-v", "--plot_mode", "xz", "--plot"]),
            {"align": True, "v": True, "plot_mode": "xz", "plot": True},
        )

    def test_invalid_number_remains_an_option(self):
        """Retain the existing treatment of nonnumeric hyphenated tokens."""
        self.assertEqual(
            config.generate(["--align", "-1e", "value", "--plot"]),
            {"align": True, "1e": "value", "plot": True},
        )

    def test_cli_config_preserves_time_offset(self):
        """Generate a config through the CLI and use it to synchronize APE."""
        logger = logging.getLogger("evo")
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(sys, "stdout", io.StringIO()),
            patch.object(sys, "stderr", io.StringIO()),
            patch.object(logger, "handlers", list(logger.handlers)),
            patch.object(logger, "level", logger.level),
            patch.object(logger, "propagate", logger.propagate),
            patch.object(config.colorama, "init"),
        ):
            output = Path(tmp) / "ape.json"
            with patch.object(
                sys,
                "argv",
                [
                    "evo_config",
                    "generate",
                    "--no_color",
                    "-o",
                    str(output),
                    "--t_offset",
                    "-0.1",
                    "--align",
                ],
            ):
                config.main()
            self.assertEqual(
                json.loads(output.read_text()),
                {"t_offset": -0.1, "align": True},
            )
            args = ape_parser.parser().parse_args(
                ["tum", "ref.tum", "est.tum", "--config", str(output)]
            )
            merged = entry_points.merge_config(args)
            self.assertEqual(merged.t_offset, -0.1)
            self.assertIs(merged.align, True)
            reference = Path(tmp) / "ref.tum"
            estimate = Path(tmp) / "est.tum"
            result = Path(tmp) / "result.zip"
            positions = ("0 0 0", "1 0 0", "1 1 0")
            reference.write_text(
                "".join(
                    f"{i} {xyz} 0 0 0 1\n" for i, xyz in enumerate(positions)
                )
            )
            estimate.write_text(
                "".join(
                    f"{i + 0.1} {xyz} 0 0 0 1\n"
                    for i, xyz in enumerate(positions)
                )
            )
            with patch.object(
                sys,
                "argv",
                [
                    "evo_ape",
                    "tum",
                    str(reference),
                    str(estimate),
                    "--config",
                    str(output),
                    "--save_results",
                    str(result),
                ],
            ):
                entry_points.ape()
            self.assertAlmostEqual(load_res_file(result).stats["rmse"], 0.0)
