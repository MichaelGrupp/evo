#!/usr/bin/env python
"""
unit test for trajectory module
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
import copy

import numpy as np

import context
import helpers
from evo.core import trajectory
from evo.core import lie_algebra as lie


class TestPosePath3D(unittest.TestCase):
    def test_init_wrong_args(self):
        path = helpers.fake_path(10)
        # no args
        with self.assertRaises(trajectory.TrajectoryException):
            trajectory.PosePath3D()
        # only quaternion
        with self.assertRaises(trajectory.TrajectoryException):
            trajectory.PosePath3D(
                orientations_quat_wxyz=path.orientations_quat_wxyz)
        # only xyz
        with self.assertRaises(trajectory.TrajectoryException):
            trajectory.PosePath3D(positions_xyz=path.positions_xyz)

    def test_init_correct(self):
        # only poses_se3
        path = helpers.fake_path(10)
        try:
            trajectory.PosePath3D(poses_se3=path.poses_se3)
        except trajectory.TrajectoryException:
            self.fail("unexpected init failure with only poses_se3")
        # xyz + quaternion
        try:
            trajectory.PosePath3D(path.positions_xyz,
                                  path.orientations_quat_wxyz)
        except trajectory.TrajectoryException:
            self.fail("unexpected init failure with xyz + quaternion")
        # all
        try:
            trajectory.PosePath3D(path.positions_xyz,
                                  path.orientations_quat_wxyz, path.poses_se3)
        except trajectory.TrajectoryException:
            self.fail(
                "unexpected init failure with xyz + quaternion + poses_se3")

    def test_equals(self):
        path_1 = helpers.fake_path(10)
        path_1_copy = copy.deepcopy(path_1)
        path_2 = helpers.fake_path(15)
        self.assertTrue(path_1 == path_1_copy)
        self.assertFalse(path_1 == path_2)
        self.assertTrue(path_1 != path_2)
        self.assertFalse(path_1 != path_1_copy)

    def test_reduce_to_ids(self):
        path = helpers.fake_path(10)
        path_reduced = copy.deepcopy(path)
        path_reduced.reduce_to_ids([0, 2])
        self.assertEqual(path_reduced.num_poses, 2)
        # direct connection from 0 to 2 in initial should be reduced path length
        len_initial_segment = np.linalg.norm(path.positions_xyz[2] -
                                             path.positions_xyz[0])
        len_reduced = path_reduced.path_length()
        self.assertEqual(len_initial_segment, len_reduced)

    def test_transform(self):
        path = helpers.fake_path(10)
        path_transformed = copy.deepcopy(path)
        t = lie.random_se3()
        path_transformed.transform(t)
        # traj_transformed.transform(lie.se3_inverse(t))
        self.assertAlmostEqual(path_transformed.path_length(),
                               path.path_length())

    def test_scale(self):
        path = helpers.fake_path(10)
        path_scaled = copy.deepcopy(path)
        s = 5.234
        path_scaled.scale(s)
        len_initial = path.path_length()
        len_scaled = path_scaled.path_length()
        self.assertAlmostEqual(len_initial * s, len_scaled)

    def test_check(self):
        self.assertTrue(helpers.fake_path(10).check()[0])
        path_wrong = helpers.fake_path(10)
        _ = path_wrong.orientations_quat_wxyz
        path_wrong._orientations_quat_wxyz[1][1] = 666
        self.assertFalse(path_wrong.check()[0])

    def test_get_infos(self):
        helpers.fake_path(10).get_infos()

    def test_get_statistics(self):
        helpers.fake_path(10).get_statistics()

    def test_distances(self):
        path = helpers.fake_path(10)
        self.assertEqual(path.distances[0], 0.0)
        self.assertEqual(path.distances.size, path.num_poses)
        self.assertAlmostEqual(path.distances[-1], path.path_length())


class TestPoseTrajectory3D(unittest.TestCase):
    def test_equals(self):
        traj_1 = helpers.fake_trajectory(10, 1)
        traj_1_copy = copy.deepcopy(traj_1)
        traj_2 = helpers.fake_trajectory(15, 1)
        self.assertTrue(traj_1 == traj_1_copy)
        self.assertFalse(traj_1 == traj_2)
        self.assertTrue(traj_1 != traj_2)
        self.assertFalse(traj_1 != traj_1_copy)

    def test_reduce_to_ids(self):
        traj = helpers.fake_trajectory(10, 1)
        traj.reduce_to_ids([0, 2])
        self.assertEqual(traj.num_poses, 2)
        self.assertEqual(len(traj.timestamps), 2)

    def test_check(self):
        self.assertTrue(helpers.fake_trajectory(10, 1).check()[0])
        wrong_traj = helpers.fake_trajectory(10, 1)
        wrong_traj.timestamps[0] = 666
        self.assertFalse(wrong_traj.check()[0])

    def test_get_infos(self):
        helpers.fake_trajectory(10, 1).get_infos()

    def test_get_statistics(self):
        helpers.fake_trajectory(10, 1).get_statistics()


if __name__ == '__main__':
    unittest.main(verbosity=2)
