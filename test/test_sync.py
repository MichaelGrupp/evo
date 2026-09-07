#!/usr/bin/env python
"""
Unit test for evo.core.sync module
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

import helpers
from evo.core import sync


class TestMatchingTimeIndices(unittest.TestCase):
    def test_correct_positive_offset(self):
        stamps_1 = helpers.fake_timestamps(10, 0.1, start_time=0.0)
        stamps_2 = helpers.fake_timestamps(10, 0.1, start_time=0.5)
        matches = sync.matching_time_indices(stamps_1, stamps_2, offset_2=-0.5)
        self.assertEqual(len(matches[0]), 10)
        self.assertEqual(len(matches[1]), 10)

    def test_correct_negative_offset(self):
        stamps_1 = helpers.fake_timestamps(10, 0.1, start_time=0.0)
        stamps_2 = helpers.fake_timestamps(10, 0.1, start_time=-0.5)
        matches = sync.matching_time_indices(stamps_1, stamps_2, offset_2=0.5)
        self.assertEqual(len(matches[0]), 10)
        self.assertEqual(len(matches[1]), 10)

    def test_no_matches_due_to_offset(self):
        stamps_1 = helpers.fake_timestamps(10, 0.1, start_time=0.0)
        stamps_2 = helpers.fake_timestamps(10, 0.1, start_time=2.0)
        matches = sync.matching_time_indices(stamps_1, stamps_2)
        self.assertEqual(len(matches[0]), 0)
        self.assertEqual(len(matches[1]), 0)

    def test_max_diff(self):
        stamps_1 = helpers.fake_timestamps(10, 0.1, start_time=0.01)
        stamps_2 = helpers.fake_timestamps(500, 2e-3)
        # default max_diff: 0.01
        matches = sync.matching_time_indices(stamps_1, stamps_2)
        self.assertEqual(len(matches[0]), 10)
        self.assertEqual(len(matches[1]), 10)
        matches = sync.matching_time_indices(stamps_2, stamps_1, max_diff=1e-3)
        self.assertEqual(len(matches[0]), 10)
        self.assertEqual(len(matches[1]), 10)


class TestAssociateTrajectories(unittest.TestCase):
    def test_no_matches_due_to_offset(self):
        traj_1 = helpers.fake_trajectory(10, 0.1, start_time=0.0)
        traj_2 = helpers.fake_trajectory(10, 0.1, start_time=2.0)
        with self.assertRaises(sync.SyncException):
            sync.associate_trajectories(traj_1, traj_2)

    def test_association(self):
        traj_1 = helpers.fake_trajectory(10, 0.1)
        traj_2 = helpers.fake_trajectory(100, 0.01)
        traj_1_sync, traj_2_sync = sync.associate_trajectories(traj_1, traj_2)
        self.assertEqual(traj_1_sync.num_poses, traj_2_sync.num_poses)
        self.assertNotEqual(traj_2.num_poses, traj_2_sync.num_poses)
        self.assertEqual(traj_2_sync.num_poses, 10)

    def test_options_are_keyword_only(self):
        """
        Checks that the options can't be passed positionally, so that client
        code can't miss the sync method option.
        """
        traj_1 = helpers.fake_trajectory(10, 0.1)
        traj_2 = helpers.fake_trajectory(100, 0.01)
        with self.assertRaises(TypeError):
            sync.associate_trajectories(traj_1, traj_2, 0.01)  # type: ignore


class TestInterpolationSyncMethod(unittest.TestCase):
    @staticmethod
    def interpolate(traj_1, traj_2, **kwargs):
        return sync.associate_trajectories(
            traj_1,
            traj_2,
            sync_method=sync.SyncMethod.interpolation,
            **kwargs,
        )

    def test_interpolation(self):
        """
        Checks that the trajectory with more poses is resampled at the
        timestamps of the sparser one.
        """
        traj_1 = helpers.fake_trajectory(10, 0.1)
        traj_2 = helpers.fake_trajectory(100, 0.01)
        traj_1_sync, traj_2_sync = self.interpolate(traj_1, traj_2)
        self.assertEqual(traj_1_sync.num_poses, 10)
        self.assertEqual(traj_2_sync.num_poses, 10)
        # No snapping to the closest poses - the timestamps are exactly equal.
        self.assertTrue(
            np.allclose(traj_1_sync.timestamps, traj_2_sync.timestamps)
        )
        self.assertTrue(np.allclose(traj_1_sync.timestamps, traj_1.timestamps))

    def test_same_association_as_nearest_time(self):
        """
        Checks that both sync methods associate the same pose pairs.
        """
        traj_1 = helpers.fake_trajectory(10, 0.1)
        traj_2 = helpers.fake_trajectory(100, 0.01)
        nearest = sync.associate_trajectories(traj_1, traj_2)
        interpolated = self.interpolate(traj_1, traj_2)
        self.assertEqual(nearest[0].num_poses, interpolated[0].num_poses)
        self.assertEqual(nearest[1].num_poses, interpolated[1].num_poses)
        # The kept timestamps of the sparser trajectory are the same.
        self.assertTrue(
            np.allclose(nearest[0].timestamps, interpolated[0].timestamps)
        )

    def test_names_are_preserved(self):
        """
        Checks that the synchronized trajectories keep their names.
        """
        traj_1 = helpers.fake_trajectory(10, 0.1)
        traj_2 = helpers.fake_trajectory(100, 0.01)
        traj_1.name, traj_2.name = "sparse", "dense"
        traj_1_sync, traj_2_sync = self.interpolate(traj_1, traj_2)
        self.assertEqual(traj_1_sync.name, "sparse")
        self.assertEqual(traj_2_sync.name, "dense")

    def test_no_matches_due_to_offset(self):
        """
        Checks that non-overlapping trajectories are rejected.
        """
        traj_1 = helpers.fake_trajectory(10, 0.1, start_time=0.0)
        traj_2 = helpers.fake_trajectory(10, 0.1, start_time=2.0)
        with self.assertRaises(sync.SyncException):
            self.interpolate(traj_1, traj_2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
