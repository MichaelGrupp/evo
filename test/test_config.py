"""Tests for command-line configuration generation."""

import unittest

from evo.cli import config


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
