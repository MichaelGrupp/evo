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
        ids = np.arange(len(poses))
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
            current_path += float(
                np.linalg.norm(current_pose[:3, 3] - previous_pose[:3, 3]))
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
    filters pairs in a list of SE(3) poses by their relative angle
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
    # Angle-axis angles are within [0, pi] / [0, 180] (Euler theorem).
    bounds = [0., 180.] if degrees else [0, np.pi]
    if delta < bounds[0] or delta > bounds[1]:
        raise FilterException(f"delta angle must be within {bounds}")
    delta = np.deg2rad(delta) if degrees else delta
    tol = np.deg2rad(tol) if degrees else tol
    if all_pairs:
        upper_bound = delta + tol
        lower_bound = delta - tol
        id_pairs = []
        ids = list(range(len(poses)))
        # All pairs search is O(n^2) here. Use vectorized operations with
        # scipy.spatial.transform.Rotation for quicker processing.
        logger.info("Searching all pairs with matching rotation delta,"
                    " this can take a while.")
        start_indices = ids[:-1]
        for i in start_indices:
            if not i % 100:
                print(int(i / len(start_indices) * 100), "%", end="\r")
            offset = i + 1
            end_indices = ids[offset:]
            rotations_i = lie.sst_rotation_from_matrix(
                np.array([poses[i][:3, :3]] * len(end_indices)))
            rotations_j = lie.sst_rotation_from_matrix(
                np.array([poses[j][:3, :3] for j in end_indices]))
            delta_angles = np.linalg.norm(
                (rotations_i.inv() * rotations_j).as_rotvec(), axis=1)
            matches = np.argwhere((lower_bound <= delta_angles)
                                  & (delta_angles <= upper_bound)) + offset
            id_pairs.extend([(i, j) for j in matches.flatten().tolist()])
    else:
        delta_angles = [
            lie.so3_log_angle(lie.relative_so3(p1[:3, :3], p2[:3, :3]))
            for p1, p2 in zip(poses, poses[1:])
        ]
        accumulated_delta = 0.0
        current_start_index = 0
        id_pairs = []
        for i, current_delta in enumerate(delta_angles):
            end_index = i + 1
            accumulated_delta += current_delta
            if accumulated_delta >= delta:
                id_pairs.append((current_start_index, end_index))
                accumulated_delta = 0.0
                current_start_index = end_index
    return id_pairs


def filter_by_motion(poses: typing.Sequence[np.ndarray],
                     distance_threshold: float, angle_threshold: float,
                     degrees: bool = False):
    """
    Filters a list of SE(3) poses by their motion if either the
    distance or rotation angle is exceeded.
    :param poses: list of SE(3) poses
    :param distance_threshold: the distance threshold in meters
    :param angle_threshold: the angle threshold in radians
                            (or degrees if degrees=True)
    :param degrees: set to True if angle_threshold is in degrees
    :return: list of indices of the filtered poses
    """
    if len(poses) < 2:
        raise FilterException("poses must contain at least two poses")
    if distance_threshold < 0.0:
        raise FilterException("distance threshold must be >= 0.0")
    if angle_threshold < 0.0:
        raise FilterException("angle threshold must be >= 0.0")
    if degrees:
        angle_threshold = np.deg2rad(angle_threshold)

    positions = np.array([pose[:3, 3] for pose in poses])
    distances = geometry.accumulated_distances(positions)
    previous_angle_id = 0
    previous_distance = 0.

    filtered_ids = [0]
    for i in range(1, len(poses)):
        if distances[i] - previous_distance >= distance_threshold:
            filtered_ids.append(i)
            previous_angle_id = i
            previous_distance = distances[i]
            continue
        current_angle = lie.so3_log_angle(
            lie.relative_so3(poses[previous_angle_id][:3, :3],
                             poses[i][:3, :3]))
        if current_angle >= angle_threshold:
            filtered_ids.append(i)
            previous_angle_id = i
            previous_distance = distances[i]
            continue

    return filtered_ids
