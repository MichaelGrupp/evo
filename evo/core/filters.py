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

from __future__ import print_function

import sys
import logging

import numpy as np

from evo.core import geometry, trajectory
from evo.core import lie_algebra as lie

logger = logging.getLogger(__name__)


def bounded_binary_search(generator, length, target, lower_bound, upper_bound):
    """
    efficient binary search for a <target> value within bounds [<lower_bound>, <upper_bound>]
    - converges to a locally optimal result within the bounds
    - instead of indexing an iterable, lazy evaluate a functor for performance
    :param generator: a generator or functor that yields a value of the search area given an index
    :param length: full length of the search area
    :param target: the value to search
    :param lower_bound: the lower bound up to which results are accepted
    :param upper_bound: the upper bound up to which results are accepted
    :return: success: (True, the index of the target) - fail: (False, -1)
    """
    start, mid = 0, -1
    end = length - 1
    residual = 0.0
    found = False
    num_iter = 0
    while start <= end and not found:
        num_iter += 1
        mid = (start + end) // 2
        val = generator(mid)
        if lower_bound <= val <= upper_bound:
            residual = abs(val - target)
            if abs(generator(mid - 1) - target) <= residual:
                end = mid - 1
                continue  # refinement possible in left direction
            elif abs(generator(mid + 1) - target) < residual:
                start = mid + 1
                continue  # refinement possible in right direction
            else:
                found = True  # converged
        if not found:
            if target < val:
                end = mid - 1
            else:
                start = mid + 1
    return found, mid, residual, num_iter


def filter_pairs_by_index(poses, delta, all_pairs=False):
    """
    filters pairs in a list of SE(3) poses by their index distance
    :param poses: list of SE(3) poses
    :param delta: the index distance used for filtering
    :param all_pairs: use all possible pairs instead of consecutive pairs
    :return: list of index tuples of the filtered pairs
    """
    if all_pairs:
        ids = range(len(poses))
        id_pairs = [(i, i + delta) for i in ids if i + delta < len(poses)]
    else:
        ids = np.arange(0, len(poses), delta)
        id_pairs = [(i, j) for i, j in zip(ids, ids[1:])]
    return id_pairs


def filter_pairs_by_distance(poses, delta, tol=0.0, all_pairs=False):
    """
    filters pairs in a list of SE(3) poses by their direct distance in meters
     - only the direct distance between the two pair points is considered
    :param poses: list of SE(3) poses
    :param delta: the distance in meters used for filtering
    :param tol: absolute distance tolerance to accept or reject pairs in all_pairs mode
    :param all_pairs: use all possible pairs instead of consecutive pairs
    :return: list of index tuples of the filtered pairs
    """
    if all_pairs:
        upper_bound = delta + tol
        lower_bound = delta - tol
        id_pairs = []
        ids = range(len(poses))
        positions = [pose[:3, 3] for pose in poses]
        for i in ids:
            for j in ids[i + 1:]:
                current_dist = abs(np.linalg.norm(positions[i] - positions[j]))
                if lower_bound <= current_dist <= upper_bound:
                    id_pairs.append((i, j))
    else:
        ids = []
        i = 0
        while i < len(poses):
            current_pose = poses[i]
            for j, next_pose in enumerate(poses[i:]):
                j += i
                current_dist = np.linalg.norm(current_pose[:3, 3] - next_pose[:3, 3])
                if current_dist >= delta:
                    ids.append(i)
                    i = j
                    break
            i += 1
        id_pairs = [(i, j) for i, j in zip(ids, ids[1:])]
    return id_pairs


def filter_pairs_by_path(poses, delta, tol=0.0, all_pairs=False):
    """
    filters pairs in a list of SE(3) poses by their path distance in meters
     - the accumulated, traveled path distance between the two pair points is considered
    :param poses: list of SE(3) poses
    :param delta: the path distance in meters used for filtering
    :param tol: absolute path tolerance to accept or reject pairs in all_pairs mode
    :param all_pairs: use all possible pairs instead of consecutive pairs
    :return: list of index tuples of the filtered pairs
    """
    if all_pairs:
        upper_bound = delta + tol
        lower_bound = delta - tol
        id_pairs = []
        ids = range(len(poses))
        positions = np.array([pose[:3, 3] for pose in poses])
        res_avg = 0.0
        n_iter_avg = 0.0
        print_progress = logger.isEnabledFor(logging.DEBUG)
        num_pairs = 0
        for i in ids:
            found, j, res, n = bounded_binary_search(lambda x: geometry.arc_len(positions[i:x+1]),
                                                     len(positions), delta, 
                                                     lower_bound, upper_bound)
            n_iter_avg += n
            if found:
                num_pairs += 1
                res_avg += res
                id_pairs.append((i, j))
            if print_progress:
                print("\rsearching", delta, "m path sub-sequences - found", num_pairs, end="\r")
                sys.stdout.flush()
        if print_progress:
            print("")
        if num_pairs != 0:
            logger.debug("avg. target residual: " + "{0:.6f}".format(res_avg / num_pairs) + "m"
                        + " | avg. num. iterations: " + "{0:.6f}".format(n_iter_avg / num_pairs))
        else:
            logger.debug("found no pairs for delta " + str(delta) + "m")
    else:
        ids = []
        previous_pose = poses[0]
        current_path = 0.0
        for i, current_pose in enumerate(poses):
            current_path += np.linalg.norm(current_pose[:3, 3] - previous_pose[:3, 3])
            previous_pose = current_pose
            if current_path >= delta:
                ids.append(i)
                current_path = 0.0
        id_pairs = [(i, j) for i, j in zip(ids, ids[1:])]
    return id_pairs


def filter_pairs_by_angle(poses, delta, tol=0.0, degrees=False, all_pairs=False):
    """
    filters pairs in a list of SE(3) poses by their absolute relative angle
     - by default, the angle accumulated on the path between the two pair poses is considered
     - if <all_pairs> is set to True, the direct angle between the two pair poses is considered
    :param poses: list of SE(3) poses
    :param delta: the angle in radians used for filtering
    :param tol: absolute angle tolerance to accept or reject pairs in all_pairs mode
    :param degrees: set to True if <delta> is in degrees instead of radians
    :param all_pairs: use all possible pairs instead of consecutive pairs
    :return: list of index tuples of the filtered pairs
    """
    if all_pairs:
        upper_bound = delta + tol
        lower_bound = delta - tol
        id_pairs = []
        ids = range(len(poses))
        if degrees:
            angles = [lie.so3_log(p[:3, :3]) * 180 / np.pi for p in poses]
        else:
            angles = [lie.so3_log(p[:3, :3]) for p in poses]
        for i in ids:
            for j in ids[i + 1:]:
                current_angle = abs(angles[i] - angles[j])
                if lower_bound <= current_angle <= upper_bound:
                    id_pairs.append((i, j))
    else:
        ids = []
        if degrees:
            angles = [lie.so3_log(p[:3, :3]) * 180 / np.pi for p in poses]
        else:
            angles = [lie.so3_log(p[:3, :3]) for p in poses]
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


def filter_pairs_by_speed(poses, timestamps, speed, tol):
    """
    filters pairs in a list of SE(3) poses by the linear speed of the motion in between them
    :param poses: list of SE(3) poses
    :param timestamps: list of timestamps corresponding to the poses
    :param speed: in m/s
    :param tol: tolerance to accept or reject velocities, in m/s
    :return: list of index tuples of the filtered pairs
    """
    positions = [pose[:3, 3] for pose in poses]
    speeds = [trajectory.calc_speed(positions[i], positions[i + 1],
                                    timestamps[i], timestamps[i + 1])
              for i in range(len(positions) - 1)]
    id_pairs = [(i, i+1) for i, v in enumerate(speeds) if speed - tol <= v <= speed + tol]
    return id_pairs


def filter_pairs_by_angular_speed(poses, timestamps, speed, tol, degrees=False):
    """
    filters pairs in a list of SE(3) poses by the angular speed of the motion in between them
    :param poses: list of SE(3) poses
    :param timestamps: list of timestamps corresponding to the poses
    :param speed: in rad/s
    :param tol: tolerance to accept or reject velocities, in rad/s
    :param degrees: set to True to use deg/s
    :return: list of index tuples of the filtered pairs
    """
    speeds = [trajectory.calc_angular_speed(poses[i], poses[i + 1],
                                            timestamps[i], timestamps[i + 1], degrees)
              for i in range(len(poses) - 1)]
    id_pairs = [(i, i+1) for i, v in enumerate(speeds) if speed - tol <= v <= speed + tol]
    return id_pairs
