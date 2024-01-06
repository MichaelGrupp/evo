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

# TODO: clean these up and use proper fixtures.
POSES_1 = [
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 0.5])),
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 1]))
]

POSES_2 = [
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 0.5])),
    lie.se3(np.eye(3), np.array([0, 0, 0.99])),
    lie.se3(np.eye(3), np.array([0, 0, 1.0]))
]

POSES_3 = [
    lie.se3(np.eye(3), np.array([0, 0, 0.0])),
    lie.se3(np.eye(3), np.array([0, 0, 0.9])),
    lie.se3(np.eye(3), np.array([0, 0, 0.99])),
    lie.se3(np.eye(3), np.array([0, 0, 0.999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.9999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.99999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.999999])),
    lie.se3(np.eye(3), np.array([0, 0, 0.9999999]))
]

POSES_4 = [
    lie.se3(np.eye(3), np.array([0, 0, 0])),
    lie.se3(np.eye(3), np.array([0, 0, 1])),
    lie.se3(np.eye(3), np.array([0, 0, 1])),
    lie.se3(np.eye(3), np.array([0, 0, 1]))
]


class TestFilterPairsByPath(unittest.TestCase):
    def test_poses1_all_pairs(self):
        target_path = 1.0
        tol = 0.0
        id_pairs = filters.filter_pairs_by_path(POSES_1, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [(0, 2), (2, 3)])

    def test_poses1_wrong_target(self):
        target_path = 2.5
        tol = 0.0
        id_pairs = filters.filter_pairs_by_path(POSES_1, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [])

    def test_poses2_all_pairs_low_tolerance(self):
        target_path = 1.0
        tol = 0.001
        id_pairs = filters.filter_pairs_by_path(POSES_2, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [(0, 3)])

    def test_convergence_all_pairs(self):
        target_path = 1.0
        tol = 0.2
        id_pairs = filters.filter_pairs_by_path(POSES_3, target_path, tol,
                                                all_pairs=True)
        self.assertEqual(id_pairs, [(0, 7)])


axis = np.array([1, 0, 0])
POSES_5 = [
    lie.se3(lie.so3_exp(axis * 0.0), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * math.pi), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * 0.0), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * math.pi / 3), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis * math.pi), np.array([0, 0, 0]))
]
TRANSFORM = lie.random_se3()
POSES_5_TRANSFORMED = [TRANSFORM.dot(p) for p in POSES_5]

axis = np.array([1, 0, 0])
p0 = lie.se3(lie.so3_exp(axis * 0.0), np.array([0, 0, 0]))
pd = lie.se3(lie.so3_exp(axis * (math.pi / 3.)), np.array([1, 2, 3]))
p1 = np.dot(p0, pd)
p2 = np.dot(p1, pd)
p3 = np.dot(p2, pd)
POSES_6 = [p0, p1, p2, p3, p3]
POSES_6_TRANSFORMED = [TRANSFORM.dot(p) for p in POSES_6]


class TestFilterPairsByAngle(unittest.TestCase):
    def test_poses5(self):
        tol = 0.001
        expected_result = [(0, 1), (1, 2), (2, 4)]
        # Result should be unaffected by global transformation.
        for poses in (POSES_5, POSES_5_TRANSFORMED):
            target_angle = math.pi - tol
            id_pairs = filters.filter_pairs_by_angle(poses, target_angle, tol,
                                                     all_pairs=False)
            self.assertEqual(id_pairs, expected_result)
            # Check for same result when using degrees:
            target_angle = np.rad2deg(target_angle)
            id_pairs = filters.filter_pairs_by_angle(poses, target_angle, tol,
                                                     all_pairs=False,
                                                     degrees=True)
            self.assertEqual(id_pairs, expected_result)

    def test_poses5_all_pairs(self):
        tol = 0.01
        expected_result = [(0, 1), (0, 4), (1, 2), (2, 4)]
        # Result should be unaffected by global transformation.
        for poses in (POSES_5, POSES_5_TRANSFORMED):
            target_angle = math.pi
            id_pairs = filters.filter_pairs_by_angle(poses, target_angle, tol,
                                                     all_pairs=True)
            self.assertEqual(id_pairs, expected_result)
            # Check for same result when using degrees:
            target_angle = np.rad2deg(target_angle)
            id_pairs = filters.filter_pairs_by_angle(poses, target_angle, tol,
                                                     all_pairs=True,
                                                     degrees=True)
            self.assertEqual(id_pairs, expected_result)

    def test_poses6(self):
        tol = 0.001
        target_angle = math.pi - tol
        expected_result = [(0, 3)]
        # Result should be unaffected by global transformation.
        for poses in (POSES_6, POSES_6_TRANSFORMED):
            id_pairs = filters.filter_pairs_by_angle(poses, target_angle, tol,
                                                     all_pairs=False)
            self.assertEqual(id_pairs, expected_result)

    def test_poses6_all_pairs(self):
        target_angle = math.pi
        tol = 0.001
        expected_result = [(0, 3), (0, 4)]
        # Result should be unaffected by global transformation.
        for poses in (POSES_6, POSES_6_TRANSFORMED):
            id_pairs = filters.filter_pairs_by_angle(poses, target_angle, tol,
                                                     all_pairs=True)
            self.assertEqual(id_pairs, expected_result)


class TestFilterByMotion(unittest.TestCase):
    def test_angle_threshold_only(self):
        poses = POSES_5
        angle_threshold = math.pi
        expected_result = [0, 1, 2, 4]
        filtered_ids = filters.filter_by_motion(poses, 999, angle_threshold)
        self.assertEqual(filtered_ids, expected_result)

    def test_distance_threshold_only(self):
        poses = POSES_2
        distance_threshold = 0.5
        expected_result = [0, 1, 3]
        filtered_ids = filters.filter_by_motion(poses, distance_threshold, 99)
        self.assertEqual(filtered_ids, expected_result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
