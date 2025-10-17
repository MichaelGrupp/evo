# -*- coding: UTF8 -*-
"""
Provides algorithms for time synchronization.
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

from evo import EvoException
from evo.core.trajectory import PoseTrajectory3D

logger = logging.getLogger(__name__)


class SyncException(EvoException):
    pass


MatchingIndices = tuple[list[int], list[int]]
TrajectoryPair = tuple[PoseTrajectory3D, PoseTrajectory3D]


def matching_time_indices(
    stamps_1: np.ndarray,
    stamps_2: np.ndarray,
    max_diff: float = 0.01,
    offset_2: float = 0.0,
) -> MatchingIndices:
    """
    Searches for the best matching timestamps of two lists of timestamps
    and returns the list indices of the best matches.
    :param stamps_1: first vector of timestamps (numpy array)
    :param stamps_2: second vector of timestamps (numpy array)
    :param max_diff: max. allowed absolute time difference
    :param offset_2: optional time offset to be applied to stamps_2
    :return: 2 lists of the matching timestamp indices (stamps_1, stamps_2)
    """
    matching_indices_1 = []
    matching_indices_2 = []
    stamps_2 = copy.deepcopy(stamps_2)
    stamps_2 += offset_2
    for index_1, stamp_1 in enumerate(stamps_1):
        diffs = np.abs(stamps_2 - stamp_1)
        index_2 = int(np.argmin(diffs))
        if diffs[index_2] <= max_diff:
            matching_indices_1.append(index_1)
            matching_indices_2.append(index_2)
    return matching_indices_1, matching_indices_2


def associate_trajectories(
    traj_1: PoseTrajectory3D,
    traj_2: PoseTrajectory3D,
    max_diff: float = 0.01,
    offset_2: float = 0.0,
    first_name: str = "first trajectory",
    snd_name: str = "second trajectory",
) -> TrajectoryPair:
    """
    Synchronizes two trajectories by matching their timestamps.
    :param traj_1: trajectory.PoseTrajectory3D object of first trajectory
    :param traj_2: trajectory.PoseTrajectory3D object of second trajectory
    :param max_diff: max. allowed absolute time difference for associating
    :param offset_2: optional time offset of second trajectory
    :param first_name: name of first trajectory for verbose logging
    :param snd_name: name of second trajectory for verbose/debug logging
    :return: traj_1, traj_2 (synchronized)
    """
    if not isinstance(traj_1, PoseTrajectory3D) or not isinstance(
        traj_2, PoseTrajectory3D
    ):
        raise SyncException("trajectories must be PoseTrajectory3D objects")

    snd_longer = len(traj_2.timestamps) > len(traj_1.timestamps)
    traj_long = copy.deepcopy(traj_2) if snd_longer else copy.deepcopy(traj_1)
    traj_short = copy.deepcopy(traj_1) if snd_longer else copy.deepcopy(traj_2)
    max_pairs = len(traj_short.timestamps)

    matching_indices_short, matching_indices_long = matching_time_indices(
        traj_short.timestamps,
        traj_long.timestamps,
        max_diff,
        offset_2 if snd_longer else -offset_2,
    )
    if len(matching_indices_short) != len(matching_indices_long):
        raise SyncException(
            "matching_time_indices returned unequal number of indices"
        )
    num_matches = len(matching_indices_long)
    traj_short.reduce_to_ids(matching_indices_short)
    traj_long.reduce_to_ids(matching_indices_long)

    traj_1 = traj_short if snd_longer else traj_long
    traj_2 = traj_long if snd_longer else traj_short

    if num_matches == 0:
        raise SyncException(
            "found no matching timestamps between {} and {} with max. time "
            "diff {} (s) and time offset {} (s)".format(
                first_name, snd_name, max_diff, offset_2
            )
        )

    logger.debug(
        "Found {} of max. {} possible matching timestamps between...\n"
        "\t{}\nand:\t{}\n..with max. time diff.: {} (s) "
        "and time offset: {} (s).".format(
            num_matches, max_pairs, first_name, snd_name, max_diff, offset_2
        )
    )

    return traj_1, traj_2
