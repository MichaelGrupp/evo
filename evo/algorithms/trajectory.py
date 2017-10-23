# -*- coding: UTF8 -*-
"""
some functions for trajectories
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

import evo.algorithms.transformations as tr
import evo.algorithms.geometry as geometry
from evo.algorithms import lie_algebra as lie


class TrajectoryException(Exception):
    pass


class PosePath3D(object):
    """
    just a path, no temporal information
    also: base class for real trajectory
    """

    def __init__(self, positions_xyz=None, orientations_quat_wxyz=None, poses_se3=None):
        """
        :param positions_xyz: nx3 list of x,y,z positions
        :param orientations_quat_wxyz: nx4 list of quaternions (w,x,y,z format)
        :param poses_se3: list of SE(3) poses
        """
        if (positions_xyz is None and orientations_quat_wxyz is None) and poses_se3 is None:
            raise TrajectoryException("must provide at least positions_xyz "
                                      "& orientations_quat_wxyz or poses_se3")
        if positions_xyz is not None:
            self._positions_xyz = np.array(positions_xyz)
        if orientations_quat_wxyz is not None:
            self._orientations_quat_wxyz = np.array(orientations_quat_wxyz)
        if poses_se3 is not None:
            self._poses_se3 = poses_se3

    @property
    def positions_xyz(self):
        if not hasattr(self, "_positions_xyz"):
            assert hasattr(self, "_poses_se3")
            self._positions_xyz = np.array([p[:3, 3] for p in self._poses_se3])
        return self._positions_xyz

    @property
    def orientations_quat_wxyz(self):
        if not hasattr(self, "_orientations_quat_wxyz"):
            assert hasattr(self, "_poses_se3")
            self._orientations_quat_wxyz \
                = np.array([tr.quaternion_from_matrix(p) for p in self._poses_se3])
        return self._orientations_quat_wxyz

    @property
    def poses_se3(self):
        if not hasattr(self, "_poses_se3"):
            assert hasattr(self, "_positions_xyz")
            assert hasattr(self, "_orientations_quat_wxyz")
            self._poses_se3 \
                = xyz_quat_wxyz_to_se3_poses(self.positions_xyz, self.orientations_quat_wxyz)
        return self._poses_se3

    @property
    def num_poses(self):
        if hasattr(self, "_poses_se3"):
            return len(self._poses_se3)
        else:
            return self.positions_xyz.shape[0]

    def transform(self, t, right_mul=False):
        """
        apply a left or right multiplicative SE(3) transformation to the whole path
        :param t: a valid SE(3) matrix
        :param right_mul: whether to apply it right-multiplicative or not
        """
        if not lie.is_se3(t):
            raise TrajectoryException("transformation is not a valid SE(3) matrix")
        if right_mul:
            self._poses_se3 = [np.dot(p, t) for p in self.poses_se3]
        else:
            self._poses_se3 = [np.dot(t, p) for p in self.poses_se3]
        self._positions_xyz, self._orientations_quat_wxyz \
            = se3_poses_to_xyz_quat_wxyz(self.poses_se3)
    
    def scale(self, s):
        """
        apply a scaling to the whole path
        :param s: scale factor
        """
        if hasattr(self, "_poses_se3"):
            self._poses_se3 = [lie.se3(p[:3, :3], s*p[:3, 3]) for p in self._poses_se3]
        if hasattr(self, "_positions_xyz"):
            self._positions_xyz = s * self._positions_xyz

    def reduce_to_ids(self, ids):
        if hasattr(self, "_positions_xyz"):
            self._positions_xyz = self._positions_xyz[ids]
        if hasattr(self, "_orientations_quat_wxyz"):
            self._orientations_quat_wxyz = self._orientations_quat_wxyz[ids]
        if hasattr(self, "_poses_se3"):
            self._poses_se3 = [self._poses_se3[idx] for idx in ids]

    def check(self):
        """
        checks if the data is valid
        :return: True/False, dictionary with some detailed infos
        """
        same_len = self.positions_xyz.shape[0] \
            == self.orientations_quat_wxyz.shape[0] \
            == len(self.poses_se3)
        se3_valid = all([lie.is_se3(p) for p in self.poses_se3])
        norms = np.linalg.norm(self.orientations_quat_wxyz, axis=1)
        quat_normed = np.allclose(norms, np.ones(norms.shape))
        valid = same_len and se3_valid and quat_normed
        details = {
            "array shapes": "ok" if same_len else "invalid (lists must have same length)",
            "SE(3) conform": "yes" if se3_valid else "no (poses are not valid SE(3) matrices)",
            "quaternions": "ok" if quat_normed else "invalid (must be unit quaternions)"
        }
        return valid, details

    def get_infos(self):
        """
        :return: dictionary with some infos about the path
        """
        return {
            "nr. of poses": self.num_poses,
            "path length (m)": geometry.arc_len(self.positions_xyz),
            "pos_start (m)": self.positions_xyz[0],
            "pos_end (m)": self.positions_xyz[-1]
        }

    def get_statistics(self):
        return {}  # no idea yet


class PoseTrajectory3D(PosePath3D, object):
    """
    a PosePath with temporal information
    """

    def __init__(self, positions_xyz, orientations_quat_wxyz, timestamps, poses_se3=None):
        """
        :param timestamps: optional nx1 list of timestamps
        """
        super(PoseTrajectory3D, self).__init__(positions_xyz, orientations_quat_wxyz, poses_se3)
        if len(positions_xyz) != len(timestamps):
            raise TrajectoryException("timestamps list must have same length as poses")
        self.timestamps = np.array(timestamps)

    def reduce_to_ids(self, ids):
        super(PoseTrajectory3D, self).reduce_to_ids(ids)
        self.timestamps = self.timestamps[ids]

    def get_infos(self):
        """
        :return: dictionary with some infos about the trajectory
        """
        infos = super(PoseTrajectory3D, self).get_infos()
        infos["duration (s)"] = self.timestamps[-1] - self.timestamps[0]
        infos["t_start (s)"] = self.timestamps[0]
        infos["t_end (s)"] = self.timestamps[-1]
        return infos

    def get_statistics(self):
        """
        :return: dictionary with some statistics of the trajectory
        """
        stats = super(PoseTrajectory3D, self).get_statistics()
        speeds = [calc_speed(self.positions_xyz[i], self.positions_xyz[i + 1],
                             self.timestamps[i], self.timestamps[i + 1])
                  for i in range(len(self.positions_xyz) - 1)]
        vmax = max(speeds)
        vmin = min(speeds)
        vmean = np.mean(speeds)
        stats.update({
            "v_max (m/s)": vmax,
            "v_min (m/s)": vmin,
            "v_avg (m/s)": vmean,
            "v_max (km/h)": vmax * 3.6,
            "v_min (km/h)": vmin * 3.6,
            "v_avg (km/h)": vmean * 3.6
        })
        return stats


class Trajectory(PoseTrajectory3D):
    pass  # TODO compat


def calc_speed(xyz_1, xyz_2, t_1, t_2):
    """
    :param xyz_1: position at timestamp 1
    :param xyz_2: position at timestamp 2
    :param t_1: timestamp 1
    :param t_2: timestamp 2
    :return: speed in m/s
    """
    if (t_2 - t_1) <= 0:
        raise TrajectoryException("bad timestamps: " + str(t_1) + " & " + str(t_2))
    return np.linalg.norm(xyz_2 - xyz_1) / (t_2 - t_1)


def calc_angular_speed(p_1, p_2, t_1, t_2, degrees=False):
    """
    :param p_1: pose at timestamp 1
    :param p_2: pose at timestamp 2
    :param t_1: timestamp 1
    :param t_2: timestamp 2
    :param degrees: set to True to return deg/s
    :return: speed in rad/s
    """
    if (t_2 - t_1) <= 0:
        raise TrajectoryException("bad timestamps: " + str(t_1) + " & " + str(t_2))
    if degrees:
        angle_1 = lie.so3_log(p_1[:3, :3]) * 180 / np.pi
        angle_2 = lie.so3_log(p_2[:3, :3]) * 180 / np.pi
    else:
        angle_1 = lie.so3_log(p_1[:3, :3])
        angle_2 = lie.so3_log(p_2[:3, :3])
    return (angle_2 - angle_1) / (t_2 - t_1)


def xyz_quat_wxyz_to_se3_poses(xyz, quat):
    poses = [lie.se3(lie.so3_from_se3(tr.quaternion_matrix(quat)), xyz)
             for quat, xyz in zip(quat, xyz)]
    return poses


def se3_poses_to_xyz_quat_wxyz(poses):
    xyz = np.array([pose[:3, 3] for pose in poses])
    quat_wxyz = np.array([tr.quaternion_from_matrix(pose) for pose in poses])
    return xyz, quat_wxyz


def align_trajectory(traj, traj_ref, correct_scale=False, correct_only_scale=False, n=-1):
    """
    align a trajectory to a reference using Umeyama alignment
    :param traj: the trajectory to align
    :param traj_ref: reference trajectory
    :param correct_scale: set to True to adjust also the scale
    :param correct_only_scale: set to True to correct the scale, but not the pose
    :param n: the number of poses to use, counted from the start (default: all)
    :return: the aligned trajectory
    """
    traj_aligned = copy.deepcopy(traj)  # otherwise np arrays will be references and mess up stuff
    with_scale = correct_scale or correct_only_scale
    if n == -1:
        r_a, t_a, s = geometry.umeyama_alignment(traj_aligned.positions_xyz.T,
                                                 traj_ref.positions_xyz.T, with_scale)
    else:
        r_a, t_a, s = geometry.umeyama_alignment(traj_aligned.positions_xyz[:n, :].T,
                                                 traj_ref.positions_xyz[:n, :].T, with_scale)
    if not correct_only_scale:
        logging.debug("rotation of alignment:\n" + str(r_a)
                      + "\ntranslation of alignment:\n" + str(t_a))
    logging.debug("scale correction: " + str(s))

    if correct_only_scale:
        traj_aligned.scale(s)
    elif correct_scale:
        traj_aligned.scale(s)
        traj_aligned.transform(lie.se3(r_a, t_a))
    else:
        traj_aligned.transform(lie.se3(r_a, t_a))

    return traj_aligned
