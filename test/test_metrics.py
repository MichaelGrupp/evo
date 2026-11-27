#!/usr/bin/env python
"""
unit test for metrics module
author: Michael Grupp

This file is part of evo (github.com/MichaelGrupp/evo).

evo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

evo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with evo.  If not, see <http://www.gnu.org/licenses/>.
"""

import math

import unittest

import numpy as np

import helpers
from evo.core import metrics
from evo.core.units import Unit


class TestRPEDelta(unittest.TestCase):
    def test_non_positive_delta_is_rejected(self):
        for delta_unit in (Unit.frames, Unit.meters, Unit.degrees):
            for delta in (0, 0.0, -1):
                with self.subTest(delta=delta, delta_unit=delta_unit):
                    with self.assertRaises(metrics.MetricsException):
                        metrics.RPE(delta=delta, delta_unit=delta_unit)

    def test_positive_delta_is_accepted(self):
        path = helpers.fake_path(10)
        rpe = metrics.RPE(delta=1, delta_unit=Unit.frames)
        rpe.process_data((path, path))
        self.assertTrue(np.allclose(rpe.error, 0.0))
        self.assertEqual(len(rpe.error), 9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
