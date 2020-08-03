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

import context
import helpers
from evo.core import sync


class TestMatchingTimeIndices(unittest.TestCase):
    def test_correct_positive_offset(self):
        stamps_1 = helpers.fake_timestamps(10, 0.1, start_time=0.)
        stamps_2 = helpers.fake_timestamps(10, 0.1, start_time=0.5)
        matches = sync.matching_time_indices(stamps_1, stamps_2, offset_2=-0.5)
        self.assertEqual(len(matches[0]), 10)
        self.assertEqual(len(matches[1]), 10)

    def test_correct_negative_offset(self):
        stamps_1 = helpers.fake_timestamps(10, 0.1, start_time=0.)
        stamps_2 = helpers.fake_timestamps(10, 0.1, start_time=-0.5)
        matches = sync.matching_time_indices(stamps_1, stamps_2, offset_2=0.5)
        self.assertEqual(len(matches[0]), 10)
        self.assertEqual(len(matches[1]), 10)

    def test_no_matches_due_to_offset(self):
        stamps_1 = helpers.fake_timestamps(10, 0.1, start_time=0.)
        stamps_2 = helpers.fake_timestamps(10, 0.1, start_time=2.)
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
    def test_wrong_type(self):
        path_1 = helpers.fake_path(10)
        path_2 = helpers.fake_path(10)
        with self.assertRaises(sync.SyncException):
            sync.associate_trajectories(path_1, path_2)

    def test_no_matches_due_to_offset(self):
        traj_1 = helpers.fake_trajectory(10, 0.1, start_time=0.)
        traj_2 = helpers.fake_trajectory(10, 0.1, start_time=2.)
        with self.assertRaises(sync.SyncException):
            sync.associate_trajectories(traj_1, traj_2)

    def test_association(self):
        traj_1 = helpers.fake_trajectory(10, 0.1)
        traj_2 = helpers.fake_trajectory(100, 0.01)
        traj_1_sync, traj_2_sync = sync.associate_trajectories(traj_1, traj_2)
        self.assertEqual(traj_1_sync.num_poses, traj_2_sync.num_poses)
        self.assertNotEqual(traj_2.num_poses, traj_2_sync.num_poses)
        self.assertEqual(traj_2_sync.num_poses, 10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
