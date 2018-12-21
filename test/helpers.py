"""
Common helper functions and classes for tests.
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

import numpy as np

from evo.core import lie_algebra as lie
from evo.core.trajectory import PosePath3D, PoseTrajectory3D


def random_se3_list(length):
    return [lie.random_se3() for _ in range(length)]


def fake_timestamps(length, distance, start_time=0.):
    return np.array([start_time + (distance * i) for i in range(length)])


def fake_path(length):
    return PosePath3D(poses_se3=random_se3_list(length))


def fake_trajectory(length, timestamp_distance, start_time=0.):
    return PoseTrajectory3D(
        poses_se3=random_se3_list(length), timestamps=fake_timestamps(
            length, timestamp_distance, start_time))
