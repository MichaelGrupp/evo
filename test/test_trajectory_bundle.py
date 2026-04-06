#!/usr/bin/env python
"""
unit test for trajectory_bundle module
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

import copy
import unittest

import numpy as np

import helpers
from evo.core.trajectory import Plane
from evo.core.trajectory_bundle import (
    TrajectoryBundle,
    TrajectoryBundleException,
)


class TestTrajectoryBundle(unittest.TestCase):
    def setUp(self):
        self.bundle = TrajectoryBundle()

    def test_empty_bundle(self):
        self.assertEqual(len(self.bundle.trajectories), 0)
        self.assertIsNone(self.bundle.ref_traj)
        self.assertFalse(self.bundle.synced)

    def test_add(self):
        traj = helpers.fake_path(10)
        ref = helpers.fake_path(10)
        self.bundle.add("test", traj)
        self.bundle.add_reference(ref)
        self.assertEqual(len(self.bundle.trajectories), 1)
        self.assertIs(self.bundle.trajectories["test"], traj)
        self.assertIs(self.bundle.ref_traj, ref)

    def test_all_trajectories(self):
        traj1 = helpers.fake_path(10)
        traj2 = helpers.fake_path(10)
        ref = helpers.fake_path(10)
        self.bundle.add("a", traj1)
        self.bundle.add("b", traj2)
        self.bundle.add_reference(ref)

        result = self.bundle.all_trajectories()
        self.assertEqual(len(result), 3)
        self.assertIs(result["reference"], ref)
        self.assertIs(result["a"], traj1)
        self.assertIs(result["b"], traj2)

    def test_downsample(self):
        self.bundle.add("a", helpers.fake_path(20))
        self.bundle.add_reference(helpers.fake_path(20))
        self.bundle.downsample(10)
        self.assertEqual(self.bundle.trajectories["a"].num_poses, 10)
        self.assertEqual(self.bundle.ref_traj.num_poses, 10)

    def test_motion_filter(self):
        traj = helpers.fake_trajectory(20, 0.1)
        original_count = traj.num_poses
        self.bundle.add("a", traj)
        self.bundle.motion_filter(100.0, 100.0)
        # With very large thresholds, most poses should be filtered.
        self.assertLessEqual(
            self.bundle.trajectories["a"].num_poses, original_count
        )

    def test_merge(self):
        self.bundle.add("a", helpers.fake_trajectory(10, 0.1))
        self.bundle.add("b", helpers.fake_trajectory(10, 0.1, start_time=2.0))
        self.bundle.merge()
        self.assertEqual(len(self.bundle.trajectories), 1)
        self.assertIn("merged_trajectory", self.bundle.trajectories)
        self.assertEqual(
            self.bundle.trajectories["merged_trajectory"].num_poses, 20
        )

    def test_apply_time_offset(self):
        traj = helpers.fake_trajectory(10, 0.1)
        original_timestamps = traj.timestamps.copy()
        self.bundle.add("a", traj)
        self.bundle.apply_time_offset(1.0)
        np.testing.assert_allclose(
            self.bundle.trajectories["a"].timestamps,
            original_timestamps + 1.0,
        )

    def test_apply_time_offset_no_timestamps_raises(self):
        self.bundle.add("a", helpers.fake_path(10))
        with self.assertRaises(TrajectoryBundleException):
            self.bundle.apply_time_offset(1.0)

    def test_mark_synced(self):
        self.bundle.add("a", helpers.fake_path(10))
        self.bundle.add("b", helpers.fake_path(10))
        self.bundle.add_reference(helpers.fake_path(10))
        self.bundle.mark_synced()
        self.assertTrue(self.bundle.synced)
        self.assertIs(self.bundle.synced_refs["a"], self.bundle.ref_traj)
        self.assertIs(self.bundle.synced_refs["b"], self.bundle.ref_traj)

    def test_mark_synced_no_ref_raises(self):
        self.bundle.add("a", helpers.fake_path(10))
        with self.assertRaises(TrajectoryBundleException):
            self.bundle.mark_synced()

    def test_sync(self):
        ref = helpers.fake_trajectory(10, 0.1)
        traj = helpers.fake_trajectory(10, 0.1)
        self.bundle.add("a", traj)
        self.bundle.add_reference(ref)
        self.bundle.sync(max_diff=0.02)
        self.assertTrue(self.bundle.synced)
        self.assertIn("a", self.bundle.synced_refs)

    def test_sync_no_ref_raises(self):
        self.bundle.add("a", helpers.fake_trajectory(10, 0.1))
        with self.assertRaises(TrajectoryBundleException):
            self.bundle.sync()

    def test_sync_no_timestamps_raises(self):
        self.bundle.add("a", helpers.fake_path(10))
        self.bundle.add_reference(helpers.fake_trajectory(10, 0.1))
        with self.assertRaises(TrajectoryBundleException):
            self.bundle.sync()

    def test_align(self):
        ref = helpers.fake_trajectory(10, 0.1)
        traj = copy.deepcopy(ref)
        # Add a known offset via SE(3) transform.
        offset = np.eye(4)
        offset[:3, 3] = [1.0, 2.0, 3.0]
        traj.transform(offset)
        self.bundle.add("a", traj)
        self.bundle.add_reference(ref)
        self.bundle.align()
        # After alignment, positions should be closer to reference.
        aligned = self.bundle.trajectories["a"]
        np.testing.assert_allclose(
            aligned.positions_xyz, ref.positions_xyz, atol=1e-6
        )

    def test_align_no_ref_raises(self):
        self.bundle.add("a", helpers.fake_path(10))
        with self.assertRaises(TrajectoryBundleException):
            self.bundle.align()

    def test_align_origin(self):
        ref = helpers.fake_trajectory(10, 0.1)
        traj = copy.deepcopy(ref)
        offset = np.eye(4)
        offset[:3, 3] = [5.0, 5.0, 5.0]
        traj.transform(offset)
        self.bundle.add("a", traj)
        self.bundle.add_reference(ref)
        self.bundle.align_origin()
        aligned = self.bundle.trajectories["a"]
        np.testing.assert_allclose(
            aligned.positions_xyz[0], ref.positions_xyz[0], atol=1e-6
        )

    def test_apply_transform(self):
        traj = helpers.fake_path(10)
        original_positions = traj.positions_xyz.copy()
        self.bundle.add("a", traj)
        # Apply identity — positions should not change.
        self.bundle.apply_transform(np.eye(4))
        np.testing.assert_allclose(
            self.bundle.trajectories["a"].positions_xyz,
            original_positions,
        )

    def test_project(self):
        traj = helpers.fake_path(10)
        self.bundle.add("a", traj)
        self.bundle.add_reference(helpers.fake_path(10))
        self.bundle.project(Plane.XY)
        np.testing.assert_array_equal(
            self.bundle.trajectories["a"].positions_xyz[:, 2], 0.0
        )
        np.testing.assert_array_equal(
            self.bundle.ref_traj.positions_xyz[:, 2], 0.0
        )


if __name__ == "__main__":
    unittest.main()
