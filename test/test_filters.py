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

import context
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


class TestFilterPairsByDistance(unittest.TestCase):
    def test_poses1_all_pairs(self):
        target_path = 1.0
        tol = 0.0
        id_pairs = filters.filter_pairs_by_distance(poses_1, target_path, tol,
                                                    all_pairs=True)
        self.assertEqual(id_pairs, [(0, 3), (2, 3)])

    def test_poses1_wrong_target(self):
        target_path = 2.5
        tol = 0.0
        id_pairs = filters.filter_pairs_by_distance(poses_1, target_path, tol,
                                                    all_pairs=True)
        self.assertEqual(id_pairs, [])

    def test_poses2_all_pairs_low_tolerance(self):
        target_path = 1.0
        tol = 0.001
        id_pairs = filters.filter_pairs_by_distance(poses_2, target_path, tol,
                                                    all_pairs=True)
        self.assertEqual(id_pairs, [(0, 3)])

    def test_poses4_all_pairs(self):
        target_path = 1.0
        tol = 0.2
        id_pairs = filters.filter_pairs_by_distance(poses_4, target_path, tol,
                                                    all_pairs=True)
        self.assertEqual(id_pairs, [(0, 1), (0, 2), (0, 3)])


axis = np.array([1, 0, 0])
poses_5 = [
    lie.se3(lie.so3_exp(axis, 0.0), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis, math.pi), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis, 0.0), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis, math.pi / 3), np.array([0, 0, 0])),
    lie.se3(lie.so3_exp(axis, math.pi), np.array([0, 0, 0]))
]
stamps_5 = np.array([0, 1, 2, 3, 4])

axis = np.array([1, 0, 0])
p0 = lie.se3(lie.so3_exp(axis, 0.0), np.array([0, 0, 0]))
pd = lie.se3(lie.so3_exp(axis, math.pi / 3), np.array([1, 2, 3]))
p1 = np.dot(p0, pd)
p2 = np.dot(p1, pd)
p3 = np.dot(p2, pd)
poses_6 = [p0, p1, p2, p3, p3]
stamps_6 = np.array([0, 1, 2, 3, 4])


class TestFilterPairsByAngle(unittest.TestCase):
    def test_poses5(self):
        target_angle = math.pi
        tol = 0.001
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
        target_angle = math.pi
        tol = 0.001
        id_pairs = filters.filter_pairs_by_angle(poses_6, target_angle, tol,
                                                 all_pairs=False)
        self.assertEqual(id_pairs, [(0, 3)])

    def test_poses6_all_pairs(self):
        target_angle = math.pi
        tol = 0.001
        id_pairs = filters.filter_pairs_by_angle(poses_6, target_angle, tol,
                                                 all_pairs=True)
        self.assertEqual(id_pairs, [(0, 3), (0, 4)])


poses_7 = [
    lie.se3(np.eye(3), np.array([0, 0, 1])),
    lie.se3(np.eye(3), np.array([0, 0, 2])),
    lie.se3(np.eye(3), np.array([0, 0, 3])),
    lie.se3(np.eye(3), np.array([0, 0, 4]))
]
stamps_7 = np.array([0, 1, 2, 3])

poses_8 = [
    lie.se3(np.eye(3), np.array([0, 0, 1])),
    lie.se3(np.eye(3), np.array([0, 0, 1])),
    lie.se3(np.eye(3), np.array([0, 0, 3])),
    lie.se3(np.eye(3), np.array([0, 0, 4]))
]
stamps_8 = np.array([0, 1, 2, 3])


class TestFilterPosesBySpeed(unittest.TestCase):
    def test_poses_7_stamps_7(self):
        target_speed = 1.0  # m/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_speed(poses_7, stamps_7,
                                                 target_speed, tol)
        self.assertEqual(id_pairs, [(0, 1), (1, 2), (2, 3)])

    def test_poses_8_stamps_8(self):
        target_speed = 1.0  # m/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_speed(poses_8, stamps_8,
                                                 target_speed, tol)
        self.assertEqual(id_pairs, [(2, 3)])


class TestFilterPosesByAngularSpeed(unittest.TestCase):
    def test_poses_7_stamps_7_radians(self):
        target_speed = math.pi / 3  # rad/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_angular_speed(
            poses_7, stamps_7, target_speed, tol)
        self.assertEqual(id_pairs, [])

    def test_poses_6_stamps_6_radians(self):
        target_speed = math.pi / 3  # rad/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_angular_speed(
            poses_6, stamps_6, target_speed, tol)
        self.assertEqual(id_pairs, [(0, 1), (1, 2), (2, 3)])

    def test_poses_5_stamps_5_radians(self):
        target_speed = math.pi / 3  # rad/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_angular_speed(
            poses_5, stamps_5, target_speed, tol)
        self.assertEqual(id_pairs, [(2, 3)])

    def test_poses_7_stamps_7_degrees(self):
        target_speed = math.pi / 3 * 180 / math.pi  # deg/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_angular_speed(
            poses_7, stamps_7, target_speed, tol, degrees=True)
        self.assertEqual(id_pairs, [])

    def test_poses_6_stamps_6_degrees(self):
        target_speed = math.pi / 3.0 * 180 / math.pi  # rad/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_angular_speed(
            poses_6, stamps_6, target_speed, tol, degrees=True)
        self.assertEqual(id_pairs, [(0, 1), (1, 2), (2, 3)])

    def test_poses_5_stamps_5_degrees(self):
        target_speed = math.pi / 3 * 180 / math.pi  # rad/s
        tol = 0.01
        id_pairs = filters.filter_pairs_by_angular_speed(
            poses_5, stamps_5, target_speed, tol, degrees=True)
        self.assertEqual(id_pairs, [(2, 3)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
