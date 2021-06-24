"""
filter algorithms
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

import logging
import typing

import numpy as np

from evo import EvoException
from evo.core import geometry
from evo.core import lie_algebra as lie

logger = logging.getLogger(__name__)


class FilterException(EvoException):
    pass


IdPairs = typing.List[typing.Tuple[int, int]]


def filter_pairs_by_index(poses: typing.Sequence[np.ndarray], delta: int,
                          all_pairs: bool = False) -> IdPairs:
    """
    filters pairs in a list of SE(3) poses by their index distance
    :param poses: list of SE(3) poses
    :param delta: the index distance used for filtering
    :param all_pairs: use all pairs instead of consecutive pairs
    :return: list of index tuples of the filtered pairs
    """
    if all_pairs:
        ids = range(len(poses))
        id_pairs = [(i, i + delta) for i in ids if i + delta < len(poses)]
    else:
        ids = np.arange(0, len(poses), delta)
        id_pairs = [(i, j) for i, j in zip(ids, ids[1:])]
    return id_pairs


def filter_pairs_by_path(poses: typing.Sequence[np.ndarray], delta: float,
                         tol: float = 0.0, all_pairs: bool = False) -> IdPairs:
    """
    filters pairs in a list of SE(3) poses by their path distance in meters
     - the accumulated, traveled path distance between the two pair points
       is considered
    :param poses: list of SE(3) poses
    :param delta: the path distance in meters used for filtering
    :param tol: absolute path tolerance to accept or reject pairs
                in all_pairs mode
    :param all_pairs: use all pairs instead of consecutive pairs
    :return: list of index tuples of the filtered pairs
    """
    id_pairs = []
    if all_pairs:
        positions = np.array([pose[:3, 3] for pose in poses])
        distances = geometry.accumulated_distances(positions)
        for i in range(distances.size - 1):
            offset = i + 1
            distances_from_here = distances[offset:] - distances[i]
            candidate_index = int(
                np.argmin(np.abs(distances_from_here - delta)))
            if (np.abs(distances_from_here[candidate_index] - delta) > tol):
                continue
            id_pairs.append((i, candidate_index + offset))
    else:
        ids = []
        previous_pose = poses[0]
        current_path = 0.0
        for i, current_pose in enumerate(poses):
            current_path += np.linalg.norm(current_pose[:3, 3] -
                                           previous_pose[:3, 3])
            previous_pose = current_pose
            if current_path >= delta:
                ids.append(i)
                current_path = 0.0
        id_pairs = [(i, j) for i, j in zip(ids, ids[1:])]
    return id_pairs


def filter_pairs_by_angle(poses: typing.Sequence[np.ndarray], delta: float,
                          tol: float = 0.0, degrees: bool = False,
                          all_pairs: bool = False) -> IdPairs:
    """
    filters pairs in a list of SE(3) poses by their absolute relative angle
     - by default, the angle accumulated on the path between the two pair poses
       is considered
     - if <all_pairs> is set to True, the direct angle between the two pair
       poses is considered
    :param poses: list of SE(3) poses
    :param delta: the angle in radians used for filtering
    :param tol: absolute angle tolerance to accept or reject pairs
                in all_pairs mode
    :param degrees: set to True if <delta> is in degrees instead of radians
    :param all_pairs: use all pairs instead of consecutive pairs
    :return: list of index tuples of the filtered pairs
    """
    if all_pairs:
        upper_bound = delta + tol
        lower_bound = delta - tol
        id_pairs = []
        ids = list(range(len(poses)))
        angles = [lie.so3_log_angle(p[:3, :3], degrees) for p in poses]
        for i in ids:
            for j in ids[i + 1:]:
                current_angle = abs(angles[i] - angles[j])
                if lower_bound <= current_angle <= upper_bound:
                    id_pairs.append((i, j))
    else:
        ids = []
        angles = [lie.so3_log_angle(p[:3, :3], degrees) for p in poses]
        previous_angle = angles[0]
        current_delta = 0.0
        ids.append(0)
        for i, current_angle in enumerate(angles):
            current_delta += abs(current_angle - previous_angle)
            previous_angle = current_angle
            if current_delta >= delta:
                ids.append(i)
                current_delta = 0.0
        id_pairs = [(i, j) for i, j in zip(ids, ids[1:])]
    return id_pairs
