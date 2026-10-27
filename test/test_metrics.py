"""
Unit tests for pose error metrics.

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

import unittest

import numpy as np

from evo.core import metrics
from evo.core.trajectory import PosePath3D
from evo.core.units import Unit


class TestChangeUnit(unittest.TestCase):
    def test_length_conversion_preserves_existing_results(self):
        """A result's errors must keep the unit of its label and statistics."""
        orientations = np.tile([1.0, 0.0, 0.0, 0.0], (3, 1))
        reference = PosePath3D(
            np.array([[0.0, 0, 0], [1.0, 0, 0], [2.0, 0, 0]]), orientations
        )
        estimate = PosePath3D(
            np.array([[1.0, 0, 0], [3.0, 0, 0], [5.0, 0, 0]]), orientations
        )
        for metric_type in (metrics.APE, metrics.RPE):
            with self.subTest(metric=metric_type.__name__):
                metric = metric_type()
                metric.process_data((reference, estimate))
                errors_m = metric.error.copy()
                result_m = metric.get_result()

                metric.change_unit(Unit.centimeters)

                np.testing.assert_allclose(metric.error, errors_m * 100)
                np.testing.assert_array_equal(
                    result_m.np_arrays["error_array"], errors_m
                )
                self.assertEqual(
                    result_m.info["label"], f"{metric_type.__name__} (m)"
                )
                self.assertAlmostEqual(
                    result_m.stats["rmse"], np.sqrt(np.mean(errors_m**2))
                )

                result_cm = metric.get_result()
                metric.change_unit(Unit.millimeters)

                np.testing.assert_allclose(metric.error, errors_m * 1000)
                np.testing.assert_allclose(
                    result_cm.np_arrays["error_array"], errors_m * 100
                )
                np.testing.assert_array_equal(
                    result_m.np_arrays["error_array"], errors_m
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
