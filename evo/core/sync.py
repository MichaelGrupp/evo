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
from enum import Enum, unique

import numpy as np

from evo import EvoException
from evo.core.trajectory import PoseTrajectory3D

logger = logging.getLogger(__name__)


class SyncException(EvoException):
    pass


MatchingIndices = tuple[list[int], list[int]]
TrajectoryPair = tuple[PoseTrajectory3D, PoseTrajectory3D]


@unique
class SyncMethod(Enum):
    """
    Methods for synchronizing two trajectories in time.
    """

    # Associate poses with the closest matching timestamps.
    nearest_time = "nearest_time"
    # Resample the denser trajectory at the timestamps of the sparser one.
    interpolation = "interpolation"


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
    assert len(matching_indices_1) == len(matching_indices_2)  # nosec B101
    return matching_indices_1, matching_indices_2


def associate_trajectories(
    traj_1: PoseTrajectory3D,
    traj_2: PoseTrajectory3D,
    *,
    sync_method: SyncMethod = SyncMethod.nearest_time,
    max_diff: float = 0.01,
    offset_2: float = 0.0,
) -> TrajectoryPair:
    """
    Synchronizes two trajectories, so that both have the same number of poses
    at (approximately) equal timestamps.
    Doesn't modify the trajectories, synchronized copies are returned.
    :param traj_1: trajectory.PoseTrajectory3D object of first trajectory
    :param traj_2: trajectory.PoseTrajectory3D object of second trajectory
    :param sync_method: SyncMethod to use for the synchronization.
                        Both methods associate the same poses within max_diff,
                        but interpolation resamples the trajectory with more
                        poses exactly at the timestamps of the sparser one
                        instead of snapping to its closest poses.
    :param max_diff: max. allowed absolute time difference for associating
    :param offset_2: optional time offset of second trajectory
    :return: traj_1, traj_2 (synchronized)
    """
    first_name = traj_1.name if traj_1.name else "first trajectory"
    second_name = traj_2.name if traj_2.name else "second trajectory"

    # Start from the trajectory that has fewer poses, so that none of its
    # poses are lost.
    second_longer = traj_2.num_poses > traj_1.num_poses
    traj_short = traj_1 if second_longer else traj_2
    traj_long = traj_2 if second_longer else traj_1
    max_pairs = traj_short.num_poses

    matching_indices_short, matching_indices_long = matching_time_indices(
        traj_short.timestamps,
        traj_long.timestamps,
        max_diff,
        offset_2 if second_longer else -offset_2,
    )
    num_matches = len(matching_indices_short)
    if num_matches == 0:
        raise SyncException(
            f"found no matching timestamps between {first_name} and {second_name} with max. time "
            f"diff {max_diff} (s) and time offset {offset_2} (s)"
        )

    traj_short = copy.deepcopy(traj_short)
    traj_short.reduce_to_ids(matching_indices_short)

    if sync_method is SyncMethod.interpolation:
        # The time offset is only used for the association, both trajectories
        # keep their own time frame. Therefore the interpolation timestamps
        # have to be converted to the time frame of the longer trajectory.
        # interpolate() returns a new trajectory, so no copy is needed here.
        traj_long = traj_long.interpolate(
            traj_short.timestamps + (-offset_2 if second_longer else offset_2)
        )
    else:
        traj_long = copy.deepcopy(traj_long)
        traj_long.reduce_to_ids(matching_indices_long)

    logger.debug(
        f"Found {num_matches} of max. {max_pairs} possible matching timestamps between...\n"
        f"\t{first_name}\nand:\t{second_name}\n..with max. time diff.: {max_diff} (s) "
        f"and time offset: {offset_2} (s)."
    )
    if sync_method is SyncMethod.interpolation:
        logger.debug(
            f"Interpolated the poses of "
            f"{second_name if second_longer else first_name} "
            f"at the matched timestamps of "
            f"{first_name if second_longer else second_name}."
        )

    if second_longer:
        return traj_short, traj_long
    return traj_long, traj_short
