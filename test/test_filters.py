#!/usr/bin/env python
"""
unit test for filters module
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

from evo.core import filters
from evo.core import lie_algebra as lie

poses_1 = [
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 0.5])),
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 1]))
]

poses_2 = [
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 0.5])),
    lie.se3(np.eye(3), np.array([0, 0, 0.99])),
    lie.se3(np.eye(3), np.array([0, 0, 1.0]))
]

poses_3 = [
    lie.se3(np.eye(3), np.array([0, 0, 0.0])),
    lie.se3(np.eye(3), np.array([0, 0, 0.9])),
    lie.se3(np.eye(3), np.array([0, 0, 0.99])),
    lie.se3(np.eye(3), np.array([0, 0, 0.999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.9999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.99999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.999999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.9999999]))
]

poses_4 = [
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 1])),
    lie.se3(np.eye(3), np.array([0, 0, 1])),
    lie.se3(np.eye(3), np.array([0, 0, 1]))
]


class TestFilterPairsByPath(unittest.TestCase):
    def test_poses1_all_pairs(self):
        target_path = 1.0
        tol = 0.0
        id_pairs = filters.filter_pairs_by_path(poses_1, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [(0, 2), (2, 3)])

    def test_poses1_wrong_target(self):
        target_path = 2.5
        tol = 0.0
        id_pairs = filters.filter_pairs_by_path(poses_1, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [])

    def test_poses2_all_pairs_low_tolerance(self):
        target_path = 1.0
        tol = 0.001
        id_pairs = filters.filter_pairs_by_path(poses_2, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [(0, 3)])

    def test_convergence_all_pairs(self):
        target_path = 1.0
        tol = 0.2
        id_pairs = filters.filter_pairs_by_path(poses_3, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [(0, 7)])


axis = np.array([1, 0, 0])
poses_5 = [
    lie.se3(lie.so3_exp(axis * 0.0), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * math.pi), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * 0.0), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * math.pi / 3), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * math.pi), np.array([0, 0, 0]))
]
stamps_5 = np.array([0, 1, 2, 3, 4])

axis = np.array([1, 0, 0])
p0 = lie.se3(lie.so3_exp(axis * 0.0), np.array([0, 0, 0]))
pd = lie.se3(lie.so3_exp(axis * (math.pi / 3.)), np.array([1, 2, 3]))
p1 = np.dot(p0, pd)
p2 = np.dot(p1, pd)
p3 = np.dot(p2, pd)
poses_6 = [p0, p1, p2, p3, p3]
stamps_6 = np.array([0, 1, 2, 3, 4])


class TestFilterPairsByAngle(unittest.TestCase):
    def test_poses5(self):
        tol = 0.001
        target_angle = math.pi - tol
        id_pairs = filters.filter_pairs_by_angle(poses_5, target_angle, tol,
                                                 all_pairs=False)
        self.assertEqual(id_pairs, [(0, 1), (1, 2), (2, 4)])

    def test_poses5_all_pairs(self):
        target_angle = math.pi
        tol = 0.01
        id_pairs = filters.filter_pairs_by_angle(poses_5, target_angle, tol,
                                                 all_pairs=True)
        self.assertEqual(id_pairs, [(0, 1), (0, 4), (1, 2), (2, 4)])

    def test_poses6(self):
        tol = 0.001
        target_angle = math.pi - tol
        id_pairs = filters.filter_pairs_by_angle(poses_6, target_angle, tol,
                                                 all_pairs=False)
        self.assertEqual(id_pairs, [(0, 3)])

    def test_poses6_all_pairs(self):
        target_angle = math.pi
        tol = 0.001
        id_pairs = filters.filter_pairs_by_angle(poses_6, target_angle, tol,
                                                 all_pairs=True)
        self.assertEqual(id_pairs, [(0, 3), (0, 4)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
