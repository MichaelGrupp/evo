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

from __future__ import print_function  # Python 2.7 backwards compatibility

import unittest
import copy

import numpy as np

from evo.algorithms import trajectory, geometry
from evo.algorithms import lie_algebra as lie
from evo.tools import file_interface


ex_tum_traj = file_interface.read_tum_trajectory_file("data/fr2_desk_ORB.txt")
ex_kitti_traj = file_interface.read_kitti_poses_file("data/KITTI_00_gt.txt")
ex_kitti_traj_wrong = copy.deepcopy(ex_kitti_traj)
ex_kitti_traj_wrong._poses_se3 = [np.zeros((4, 4)) for i in range(ex_kitti_traj.num_poses)]

ex_tum_traj_wrong_quat = copy.deepcopy(ex_tum_traj)
ex_tum_traj_wrong_quat._orientations_quat_wxyz[3] = [5000, 0, 0, 0]

ex_tum_traj_wrong_stamps = copy.deepcopy(ex_tum_traj)
ex_tum_traj_wrong_stamps.timestamps = [1, 2, 3]


class TestPosePath3D(unittest.TestCase):
    def test_init_wrong_args(self):
        # no args
        with self.assertRaises(trajectory.TrajectoryException):
            trajectory.PosePath3D()
        # only quaternion
        with self.assertRaises(trajectory.TrajectoryException):
            trajectory.PosePath3D(orientations_quat_wxyz=ex_tum_traj.orientations_quat_wxyz)
        # only xyz
        with self.assertRaises(trajectory.TrajectoryException):
            trajectory.PosePath3D(positions_xyz=ex_tum_traj.positions_xyz)

    def test_init_correct(self):
        # only poses_se3
        try:
            trajectory.PosePath3D(poses_se3=ex_tum_traj.poses_se3)
        except trajectory.TrajectoryException:
            self.fail("unexpected init failure with only poses_se3")
        # xyz + quaternion
        try:
            trajectory.PosePath3D(ex_tum_traj.positions_xyz, ex_tum_traj.orientations_quat_wxyz)
        except trajectory.TrajectoryException:
            self.fail("unexpected init failure with xyz + quaternion")
        # all
        try:
            trajectory.PosePath3D(ex_tum_traj.positions_xyz, ex_tum_traj.orientations_quat_wxyz,
                                  ex_tum_traj.poses_se3)
        except trajectory.TrajectoryException:
            self.fail("unexpected init failure with xyz + quaternion + poses_se3")

    def test_equals(self):
        ex_kitti_traj_copy = copy.deepcopy(ex_kitti_traj)
        self.assertTrue(ex_kitti_traj == ex_kitti_traj_copy)
        self.assertFalse(ex_kitti_traj == ex_kitti_traj_wrong)
        self.assertTrue(ex_kitti_traj != ex_kitti_traj_wrong)
        self.assertFalse(ex_kitti_traj != ex_kitti_traj_copy)

    def test_reduce_to_ids(self):
        traj_reduced = copy.deepcopy(ex_kitti_traj)
        traj_reduced.reduce_to_ids([0, 2])
        self.assertEqual(traj_reduced.num_poses, 2)
        # direct connection from 0 to 2 in initial should be reduced path length
        len_initial_segment = np.linalg.norm(ex_kitti_traj.positions_xyz[2]
                                             - ex_kitti_traj.positions_xyz[0])
        len_reduced = traj_reduced.path_length()
        self.assertEqual(len_initial_segment, len_reduced)

    def test_transform(self):
        traj_transformed = copy.deepcopy(ex_kitti_traj)
        t = lie.random_se3()
        traj_transformed.transform(t)
        # traj_transformed.transform(lie.se3_inverse(t))
        self.assertAlmostEqual(traj_transformed.path_length(), ex_kitti_traj.path_length())

    def test_scale(self):
        traj_scaled = copy.deepcopy(ex_kitti_traj)
        s = 5.234
        traj_scaled.scale(s)
        len_initial = ex_kitti_traj.path_length()
        len_scaled = traj_scaled.path_length()
        self.assertAlmostEqual(len_initial * s, len_scaled)

    def test_check(self):
        self.assertTrue(ex_kitti_traj.check()[0])
        self.assertFalse(ex_kitti_traj_wrong.check()[0])

    def test_get_infos(self):
        ex_kitti_traj.get_infos()

    def test_get_statistics(self):
        ex_kitti_traj.get_statistics()


class TestPoseTrajectory3D(unittest.TestCase):
    def test_equals(self):
        ex_tum_traj_copy = copy.deepcopy(ex_tum_traj)
        self.assertTrue(ex_tum_traj == ex_tum_traj_copy)
        self.assertFalse(ex_tum_traj == ex_tum_traj_wrong_stamps)
        self.assertFalse(ex_tum_traj == ex_tum_traj_wrong_quat)
        self.assertTrue(ex_tum_traj != ex_tum_traj_wrong_stamps)
        self.assertTrue(ex_tum_traj != ex_tum_traj_wrong_quat)
        self.assertFalse(ex_tum_traj != ex_tum_traj_copy)

    def test_reduce_to_ids(self):
        traj_reduced = copy.deepcopy(ex_tum_traj)
        traj_reduced.reduce_to_ids([0, 2])
        self.assertEqual(traj_reduced.num_poses, 2)
        self.assertEqual(len(traj_reduced.timestamps), 2)

    def test_check(self):
        self.assertTrue(ex_tum_traj.check()[0])
        self.assertFalse(ex_tum_traj_wrong_quat.check()[0])
        self.assertFalse(ex_tum_traj_wrong_stamps.check()[0])

    def test_get_infos(self):
        ex_tum_traj.get_infos()

    def test_get_statistics(self):
        ex_tum_traj.get_statistics()


if __name__ == '__main__':
    unittest.main(verbosity=2)
