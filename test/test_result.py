#!/usr/bin/env python
"""
unit test for lie_algebra module - mainly test mathematical correctness
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

import unittest

import numpy as np

from evo.core import result


class TestMergeResult(unittest.TestCase):
    def test_merge_strategy_average(self):
        r1 = result.Result()
        r1.add_np_array("test", np.array([1., 2., 3.]))
        r1.add_stats({"bla": 1., "blub": 2.})
        r2 = result.Result()
        r2.add_np_array("test", np.array([0., 0., 0.]))
        r2.add_stats({"bla": 0., "blub": 0.})
        merged = result.merge_results([r1, r2])
        self.assertTrue(
            np.array_equal(merged.np_arrays["test"], np.array([0.5, 1., 1.5])))
        self.assertEqual(merged.stats, {"bla": 0.5, "blub": 1.})

    def test_merge_strategy_append(self):
        r1 = result.Result()
        r1.add_np_array("test", np.array([1., 2., 3.]))
        r1.add_stats({"bla": 1., "blub": 2.})
        r2 = result.Result()
        r2.add_np_array("test", np.array([0.]))
        r2.add_stats({"bla": 0., "blub": 0.})
        merged = result.merge_results([r1, r2])
        #yapf: disable
        self.assertTrue(
            np.array_equal(merged.np_arrays["test"],
                           np.array([1., 2., 3., 0.])))
        # yapf: enable
        self.assertEqual(merged.stats, {"bla": 0.5, "blub": 1.})

    def test_non_matching_np_arrays_keys(self):
        r1 = result.Result()
        r1.add_np_array("test", np.array([]))
        r1.add_np_array("test_2", np.array([]))
        r2 = result.Result()
        r2.add_np_array("test", np.array([]))
        with self.assertRaises(result.ResultException):
            result.merge_results([r1, r2])

    def test_non_matching_stats_keys(self):
        r1 = result.Result()
        r1.add_stats({"bla": 1., "blub": 2.})
        r2 = result.Result()
        r2.add_stats({"foo": 1., "bar": 2.})
        with self.assertRaises(result.ResultException):
            result.merge_results([r1, r2])
