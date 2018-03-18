# -*- coding: UTF8 -*-
"""
algorithms for time synchronization
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
import logging

import numpy as np

from evo.core.trajectory import PoseTrajectory3D

logger = logging.getLogger(__name__)


class SyncException(Exception):
    pass


def matching_time_indices(stamps_1, stamps_2, max_diff=0.01, offset_2=0.0):
    """
    searches for the best matching timestamps of 2 lists and returns their list indices
    :param stamps_1: first vector of timestamps
    :param stamps_2: second vector of timestamps
    :param max_diff: max. allowed absolute time difference
    :param offset_2: optional offset of second vector
    :return: the indices of the matching stamps in stamps_1
    """
    matching_indices = []
    stamps_2 += offset_2
    for stamp in stamps_1:
        diffs = np.abs(stamps_2 - stamp)
        argmin = np.argmin(diffs)
        if diffs[argmin] <= max_diff:
            matching_indices.append(argmin)
    return matching_indices


def associate_trajectories(traj_1, traj_2, max_diff=0.01, offset_2=0.0, invert=False,
                           first_name="first trajectory", snd_name="estimated trajectory"):
    """
    synchronize two trajectories via matching timestamps (e.g. for TUM RGB-D dataset, ROS bags, ...)
    :param traj_1: trajectory.PoseTrajectory3D object of first trajectory
    :param traj_2: trajectory.PoseTrajectory3D object of second trajectory
    :param max_diff: max. allowed absolute time difference for associating
    :param offset_2: optional time offset of second timestamp vector
    :param invert: set to True to match from longer list to short (default: short to longer list)
    :param first_name: optional name of reference trajectory for verbose/debug logging
    :param snd_name: optional name of estimated trajectory for verbose/debug logging
    :return: synchronized traj_1 and traj_2 of same length
    """
    if not isinstance(traj_1, PoseTrajectory3D) or not isinstance(traj_2, PoseTrajectory3D):
        raise SyncException("trajectories must be PoseTrajectory3D objects")
    if invert:
        logger.debug("using inverse matching logic")
    traj_1 = copy.deepcopy(traj_1)
    traj_2 = copy.deepcopy(traj_2)
    snd_longer = len(traj_2.timestamps) > len(traj_1.timestamps)
    max_pairs = len(traj_2.timestamps) if not snd_longer and not invert else len(traj_1.timestamps)
    if invert:
        snd_longer = not snd_longer
    traj_long = traj_2 if snd_longer else traj_1
    traj_short = traj_1 if snd_longer else traj_2

    # associate the timestamps of the shorter trajectory to the longer one
    # select matching data from longer one
    matching_indices = matching_time_indices(traj_short.timestamps, traj_long.timestamps,
                                             max_diff, offset_2 if snd_longer else -offset_2)
    traj_long.reduce_to_ids(matching_indices)

    # reversely select matching data from shorter one
    # (if longer one is now smaller than shorter one)
    matching_indices = matching_time_indices(traj_long.timestamps, traj_short.timestamps,
                                             max_diff, -offset_2 if snd_longer else offset_2)
    traj_short.reduce_to_ids(matching_indices)

    traj_1 = traj_short if snd_longer else traj_long
    traj_2 = traj_long if snd_longer else traj_short
    if len(matching_indices) == 0:
        raise SyncException("found no matching timestamps between "
                            + first_name + " and " + snd_name + " with "
                            + "max. time diff.: " + str(max_diff)
                            + " (s) and time offset: " + str(offset_2) + " (s)")
    logger.debug("found " + str(len(matching_indices)) + " of max. " + str(max_pairs)
                  + " possible matching timestamps between..."
                  + "\n\t" + first_name
                  + "\nand: \t" + snd_name
                  + "\n...with max. time diff.: " + str(max_diff)
                  + " (s) and time offset: " + str(offset_2) + " (s)")

    return traj_1, traj_2
