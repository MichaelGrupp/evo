"""
Unit test for pandas_bridge module.
Author: Michael Grupp

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

import helpers
from evo.core import trajectory
from evo.tools import pandas_bridge


class TrajectoryDataframeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = helpers.fake_path(100)
        self.trajectory = helpers.fake_trajectory(100, 0.1)

    def test_back_and_forth(self):
        for input_traj in (self.path, self.trajectory):
            df = pandas_bridge.trajectory_to_df(input_traj)
            output_traj = pandas_bridge.df_to_trajectory(df)
            self.assertIsInstance(output_traj, type(input_traj))
            self.assertEqual(input_traj, output_traj)

    def test_explicit_type(self):
        df = pandas_bridge.trajectory_to_df(self.trajectory)
        output = pandas_bridge.df_to_trajectory(df,
                                                as_type=trajectory.PosePath3D)
        self.assertIsInstance(output, trajectory.PosePath3D)
