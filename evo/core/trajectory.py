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

import logging
import typing
from enum import Enum, unique

import numpy as np

from evo import EvoException
import evo.core.transformations as tr
import evo.core.geometry as geometry
from evo.core import lie_algebra as lie
from evo.core import filters

logger = logging.getLogger(__name__)


class TrajectoryException(EvoException):
    pass


@unique
class Plane(Enum):
    """
    Planes embedded in R3, e.g. for projection purposes.
    """
    XY = "xy"
    XZ = "xz"
    YZ = "yz"


class PosePath3D(object):
    """
    just a path, no temporal information
    also: base class for real trajectory
    """
    def __init__(
        self, positions_xyz: typing.Optional[np.ndarray] = None,
        orientations_quat_wxyz: typing.Optional[np.ndarray] = None,
        poses_se3: typing.Optional[typing.Sequence[np.ndarray]] = None,
        meta: typing.Optional[dict] = None):
        """
        :param positions_xyz: nx3 list of x,y,z positions
        :param orientations_quat_wxyz: nx4 list of quaternions (w,x,y,z format)
        :param poses_se3: list of SE(3) poses
        :param meta: optional metadata
        """
        if (positions_xyz is None
                or orientations_quat_wxyz is None) and poses_se3 is None:
            raise TrajectoryException("must provide at least positions_xyz "
                                      "& orientations_quat_wxyz or poses_se3")
        if positions_xyz is not None:
            self._positions_xyz = np.array(positions_xyz)
        if orientations_quat_wxyz is not None:
            self._orientations_quat_wxyz = np.array(orientations_quat_wxyz)
        if poses_se3 is not None:
            self._poses_se3 = poses_se3
        if self.num_poses == 0:
            raise TrajectoryException("pose data is empty")
        self.meta = {} if meta is None else meta
        self._projected = False

    def __str__(self) -> str:
        return "{} poses, {:.3f}m path length".format(self.num_poses,
                                                      self.path_length)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PosePath3D):
            return False
        if not self.num_poses == other.num_poses:
            return False
        equal = True
        equal &= all([
            np.allclose(p1, p2)
            for p1, p2 in zip(self.poses_se3, other.poses_se3)
        ])
        equal &= (np.allclose(self.orientations_quat_wxyz,
                              other.orientations_quat_wxyz)
                  or np.allclose(self.orientations_quat_wxyz,
                                 -other.orientations_quat_wxyz))
        equal &= np.allclose(self.positions_xyz, other.positions_xyz)
        return equal

    def __ne__(self, other: object) -> bool:
        return not self == other

    @property
    def positions_xyz(self) -> np.ndarray:
        if not hasattr(self, "_positions_xyz"):
            assert hasattr(self, "_poses_se3")
            self._positions_xyz = np.array([p[:3, 3] for p in self._poses_se3])
        return self._positions_xyz

    @property
    def distances(self) -> np.ndarray:
        return geometry.accumulated_distances(self.positions_xyz)

    @property
    def orientations_quat_wxyz(self) -> np.ndarray:
        if not hasattr(self, "_orientations_quat_wxyz"):
            assert hasattr(self, "_poses_se3")
            self._orientations_quat_wxyz \
                = np.array(
                    [tr.quaternion_from_matrix(p)
                     for p in self._poses_se3])
        return self._orientations_quat_wxyz

    def get_orientations_euler(self, axes="sxyz") -> np.ndarray:
        if hasattr(self, "_poses_se3"):
            return np.array(
                [tr.euler_from_matrix(p, axes=axes) for p in self._poses_se3])
        assert hasattr(self, "_orientations_quat_wxyz")
        return np.array([
            tr.euler_from_quaternion(q, axes=axes)
            for q in self._orientations_quat_wxyz
        ])

    @property
    def poses_se3(self) -> typing.Sequence[np.ndarray]:
        if not hasattr(self, "_poses_se3"):
            assert hasattr(self, "_positions_xyz")
            assert hasattr(self, "_orientations_quat_wxyz")
            self._poses_se3 \
                = xyz_quat_wxyz_to_se3_poses(self.positions_xyz,
                                             self.orientations_quat_wxyz)
        return self._poses_se3

    @property
    def num_poses(self) -> int:
        if hasattr(self, "_poses_se3"):
            return len(self._poses_se3)
        else:
            return self.positions_xyz.shape[0]

    @property
    def path_length(self) -> float:
        """
        calculates the path length (arc-length)
        :return: path length in meters
        """
        return float(geometry.arc_len(self.positions_xyz))

    def transform(self, t: np.ndarray, right_mul: bool = False,
                  propagate: bool = False) -> None:
        """
        apply a left or right multiplicative transformation to the whole path
        :param t: a 4x4 transformation matrix (e.g. SE(3) or Sim(3))
        :param right_mul: whether to apply it right-multiplicative or not
        :param propagate: whether to propagate drift with RHS transformations
        """
        if right_mul and not propagate:
            # Transform each pose individually.
            self._poses_se3 = [np.dot(p, t) for p in self.poses_se3]
        elif right_mul and propagate:
            # Transform each pose and propagate resulting drift to the next.
            ids = np.arange(0, self.num_poses, 1, dtype=int)
            rel_poses = [
                lie.relative_se3(self.poses_se3[i], self.poses_se3[j]).dot(t)
                for i, j in zip(ids, ids[1:])
            ]
            self._poses_se3 = [self.poses_se3[0]]
            for i, j in zip(ids[:-1], ids):
                self._poses_se3.append(self._poses_se3[j].dot(rel_poses[i]))
        else:
            self._poses_se3 = [np.dot(t, p) for p in self.poses_se3]
        self._positions_xyz, self._orientations_quat_wxyz \
            = se3_poses_to_xyz_quat_wxyz(self.poses_se3)

    def scale(self, s: float) -> None:
        """
        apply a scaling to the whole path
        :param s: scale factor
        """
        if hasattr(self, "_poses_se3"):
            self._poses_se3 = [
                lie.se3(p[:3, :3], s * p[:3, 3]) for p in self._poses_se3
            ]
        if hasattr(self, "_positions_xyz"):
            self._positions_xyz = s * self._positions_xyz

    def project(self, plane: Plane) -> None:
        """
        Projects the positions and orientations of the path into a plane.
        :param plane: desired plane into which the poses will be projected
        """
        if self._projected:
            raise TrajectoryException("path was already projected once")
        if plane == Plane.XY:
            null_dim = 2  # Z
        elif plane == Plane.XZ:
            null_dim = 1  # Y
        elif plane == Plane.YZ:
            null_dim = 0  # X
        else:
            raise TrajectoryException(f"unknown projection plane {plane}")

        # Project poses and rotations (forcing to angle around normal).
        rotation_axis = np.zeros(3)
        rotation_axis[null_dim] = 1
        for pose in self.poses_se3:
            pose[null_dim, 3] = 0
            angle_axis = rotation_axis * tr.euler_from_matrix(
                pose[:3, :3], "sxyz")[null_dim]
            pose[:3, :3] = lie.so3_exp(angle_axis)

        # Flush cached data that will be regenerated on demand via @property.
        if hasattr(self, "_positions_xyz"):
            del self._positions_xyz
        if hasattr(self, "_orientations_quat_wxyz"):
            del self._orientations_quat_wxyz
        self._projected = True

    def align(self, traj_ref: 'PosePath3D', correct_scale: bool = False,
              correct_only_scale: bool = False,
              n: int = -1) -> geometry.UmeyamaResult:
        """
        align to a reference trajectory using Umeyama alignment
        :param traj_ref: reference trajectory
        :param correct_scale: set to True to adjust also the scale
        :param correct_only_scale: set to True to correct the scale, but not the pose
        :param n: the number of poses to use, counted from the start (default: all)
        :return: the result parameters of the Umeyama algorithm
        """
        with_scale = correct_scale or correct_only_scale
        if correct_only_scale:
            logger.debug("Correcting scale...")
        else:
            logger.debug("Aligning using Umeyama's method..." +
                         (" (with scale correction)" if with_scale else ""))
        if n == -1:
            r_a, t_a, s = geometry.umeyama_alignment(self.positions_xyz.T,
                                                     traj_ref.positions_xyz.T,
                                                     with_scale)
        else:
            r_a, t_a, s = geometry.umeyama_alignment(
                self.positions_xyz[:n, :].T, traj_ref.positions_xyz[:n, :].T,
                with_scale)

        if not correct_only_scale:
            logger.debug("Rotation of alignment:\n{}"
                         "\nTranslation of alignment:\n{}".format(r_a, t_a))
        logger.debug("Scale correction: {}".format(s))

        if correct_only_scale:
            self.scale(s)
        elif correct_scale:
            self.scale(s)
            self.transform(lie.se3(r_a, t_a))
        else:
            self.transform(lie.se3(r_a, t_a))

        return r_a, t_a, s

    def align_origin(self, traj_ref: 'PosePath3D') -> np.ndarray:
        """
        align the origin to the origin of a reference trajectory
        :param traj_ref: reference trajectory
        :return: the used transformation
        """
        if self.num_poses == 0 or traj_ref.num_poses == 0:
            raise TrajectoryException("can't align an empty trajectory...")
        traj_origin = self.poses_se3[0]
        traj_ref_origin = traj_ref.poses_se3[0]
        to_ref_origin = np.dot(traj_ref_origin, lie.se3_inverse(traj_origin))
        logger.debug(
            "Origin alignment transformation:\n{}".format(to_ref_origin))
        self.transform(to_ref_origin)
        return to_ref_origin

    def reduce_to_ids(
            self, ids: typing.Union[typing.Sequence[int], np.ndarray]) -> None:
        """
        reduce the elements to the ones specified in ids
        :param ids: list of integer indices
        """
        if hasattr(self, "_positions_xyz"):
            self._positions_xyz = self._positions_xyz[ids]
        if hasattr(self, "_orientations_quat_wxyz"):
            self._orientations_quat_wxyz = self._orientations_quat_wxyz[ids]
        if hasattr(self, "_poses_se3"):
            self._poses_se3 = [self._poses_se3[idx] for idx in ids]

    def downsample(self, num_poses: int) -> None:
        """
        Downsample the trajectory to the specified number of poses
        with a simple evenly spaced sampling.
        Does nothing if the trajectory already has less or equal poses.
        :param num_poses: number of poses to keep
        """
        if self.num_poses <= num_poses:
            return
        if num_poses < 1:
            raise TrajectoryException("can't downsample to less than one pose")
        ids = np.linspace(0, self.num_poses - 1, num_poses, dtype=int)
        self.reduce_to_ids(ids)

    def motion_filter(self, distance_threshold: float, angle_threshold: float,
                      degrees: bool = False) -> None:
        """
        Filters the trajectory by its motion if either the accumulated distance
        or rotation angle is exceeded.
        :param distance_threshold: the distance threshold in meters
        :param angle_threshold: the angle threshold in radians
                                (or degrees if degrees=True)
        :param degrees: set to True if angle_threshold is in degrees
        """
        filtered_ids = filters.filter_by_motion(self.poses_se3,
                                                distance_threshold,
                                                angle_threshold, degrees)
        self.reduce_to_ids(filtered_ids)

    def _jumps(self, dist: float) -> np.ndarray:
        jumps = np.where(self.distances[1:] - self.distances[:-1] > dist)
        if len(jumps[0]) == 0:
            return np.array([0, self.num_poses])
        return np.concatenate([[0], jumps[0] + 1, [self.num_poses]])

    def split_distance_gaps(self,
                            dist: float) -> typing.Sequence["PosePath3D"]:
        """
        Determines translation gaps in the path and splits it into multiple
        paths at the gaps.
        :param dist: distance threshold for gap detection in meters
        """
        if self.num_poses < 2:
            return [self]
        jumps = self._jumps(dist)
        return [
            PosePath3D(poses_se3=self.poses_se3[jumps[i]:jumps[i + 1]])
            for i in range(len(jumps) - 1)
        ]

    def check(self) -> typing.Tuple[bool, dict]:
        """
        checks if the data is valid
        :return: True/False, dictionary with some detailed infos
        """
        if self.num_poses == 0:
            return True, {}
        same_len = self.positions_xyz.shape[0] \
            == self.orientations_quat_wxyz.shape[0] \
            == len(self.poses_se3)
        se3_valid = all([lie.is_se3(p) for p in self.poses_se3])
        norms = np.linalg.norm(self.orientations_quat_wxyz, axis=1)
        quat_normed = np.allclose(norms, np.ones(norms.shape))
        valid = same_len and se3_valid and quat_normed
        details = {
            "array shapes": "ok"
            if same_len else "invalid (lists must have same length)",
            "SE(3) conform": "yes"
            if se3_valid else "no (poses are not valid SE(3) matrices)",
            "quaternions": "ok"
            if quat_normed else "invalid (must be unit quaternions)"
        }
        return valid, details

    def get_infos(self) -> dict:
        """
        :return: dictionary with some infos about the path
        """
        return {
            "nr. of poses": self.num_poses,
            "path length (m)": self.path_length,
            "pos_start (m)": self.positions_xyz[0],
            "pos_end (m)": self.positions_xyz[-1]
        }

    def get_statistics(self) -> dict:
        if self.num_poses < 2:
            return {}
        return {}  # no idea yet


class PoseTrajectory3D(PosePath3D, object):
    """
    a PosePath with temporal information
    """
    def __init__(
        self, positions_xyz: typing.Optional[np.ndarray] = None,
        orientations_quat_wxyz: typing.Optional[np.ndarray] = None,
        timestamps: typing.Optional[np.ndarray] = None,
        poses_se3: typing.Optional[typing.Sequence[np.ndarray]] = None,
        meta: typing.Optional[dict] = None):
        """
        :param timestamps: optional nx1 list of timestamps
        """
        super(PoseTrajectory3D,
              self).__init__(positions_xyz, orientations_quat_wxyz, poses_se3,
                             meta)
        # this is a bit ugly...
        if timestamps is None:
            raise TrajectoryException("no timestamps provided")
        self.timestamps = np.array(timestamps)

    def __str__(self) -> str:
        s = super(PoseTrajectory3D, self).__str__()
        return s + ", {:.3f}s duration".format(self.timestamps[-1] -
                                               self.timestamps[0])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PoseTrajectory3D):
            return False
        if not self.num_poses == other.num_poses:
            return False
        equal = super(PoseTrajectory3D, self).__eq__(other)
        equal &= np.allclose(self.timestamps, other.timestamps)
        return equal

    def __ne__(self, other: object) -> bool:
        return not self == other

    @property
    def speeds(self) -> np.ndarray:
        """
        :return: array with speed of motion between poses
        """
        if self.num_poses < 2:
            return np.array([])
        return np.array([
            calc_speed(self.positions_xyz[i], self.positions_xyz[i + 1],
                       self.timestamps[i], self.timestamps[i + 1])
            for i in range(len(self.positions_xyz) - 1)
        ])

    def align_on_window(self, traj_ref: 'PoseTrajectory3D', correct_scale: bool = False,
                        correct_only_scale: bool = False, n: int = -1,
                        start_time: typing.Optional[float] = None,
                        end_time: typing.Optional[float] = None) -> geometry.UmeyamaResult:
        """
        align to a reference trajectory using Umeyama alignment
        :param traj_ref: reference trajectory
        :param correct_scale: set to True to adjust also the scale
        :param correct_only_scale: set to True to correct the scale, but not the pose
        :param n: the number of poses to use, counted from the start (default: all)
        :param start_time: the time to start the Umeyama alignment window
                           (default: start of the trajectory)
        :param end_time: the time to end the Umeyama alignment window
                         (default: end of the trajectory)
        :return: the result parameters of the Umeyama algorithm
        """
        if start_time is None and end_time is None:
            return self.align(traj_ref, correct_scale, correct_only_scale, n)

        if n != -1:
            # Cannot have start_time not None or end_time not None, and n != 1
            raise TrajectoryException("start_time or end_time with n is not implemented")

        with_scale = correct_scale or correct_only_scale
        if correct_only_scale:
            logger.debug("Correcting scale...")
        else:
            logger.debug(f"Aligning using Umeyama's method... "
                         f"{'(with scale correction)' if with_scale else ''}")

        relative_timestamps = self.timestamps - np.min(self.timestamps)

        if start_time is None:
            start_index = 0
        elif np.all(relative_timestamps < start_time):
            logger.warning(f"Align start time ({start_time}s) is after end of trajectory"
                           f" ({np.max(relative_timestamps)}s), ignoring start time")
            start_index = 0
        else:
            # Find first value that is less or equal to start_time
            start_index = np.flatnonzero(start_time <= relative_timestamps)[0]
            logger.debug(f"Start of alignment: in reference {traj_ref.timestamps[start_index]}s, "
                         f"in trajectory {self.timestamps[start_index]}s")

        if end_time is None:
            end_index = self.positions_xyz.shape[0]
        elif np.all(relative_timestamps < end_time):
            logger.warning(f"Align end time ({end_time}s) is after end of trajectory "
                           f"({np.max(relative_timestamps)}s), ignoring end time")
            end_index = self.timestamps.shape[0]
        else:
            # Find first value that is greater or equal to end_time
            end_index = np.flatnonzero(end_time <= relative_timestamps)[0]
            logger.debug(f"End of alignment: in reference {traj_ref.timestamps[end_index]}s, "
                         f"in trajectory {self.timestamps[end_index]}s")

        if end_index <= start_index:
            raise TrajectoryException("alignment is empty")

        r_a, t_a, s = geometry.umeyama_alignment(self.positions_xyz[start_index:end_index, :].T,
                                                 traj_ref.positions_xyz[start_index:end_index, :].T,
                                                 with_scale)

        if not correct_only_scale:
            logger.debug(f"Rotation of alignment:\n{r_a}"
                         f"\nTranslation of alignment:\n{t_a}")
        logger.debug(f"Scale correction: {s}")

        if correct_only_scale:
            self.scale(s)
        elif correct_scale:
            self.scale(s)
            self.transform(lie.se3(r_a, t_a))
        else:
            self.transform(lie.se3(r_a, t_a))

        return r_a, t_a, s

    def reduce_to_ids(
            self, ids: typing.Union[typing.Sequence[int], np.ndarray]) -> None:
        super(PoseTrajectory3D, self).reduce_to_ids(ids)
        self.timestamps = self.timestamps[ids]

    def reduce_to_time_range(self,
                             start_timestamp: typing.Optional[float] = None,
                             end_timestamp: typing.Optional[float] = None):
        """
        Removes elements with timestamps outside of the specified time range.
        :param start_timestamp: any data with lower timestamp is removed
                                if None: current start timestamp
        :param end_timestamp: any data with larger timestamp is removed
                              if None: current end timestamp
        """
        if self.num_poses == 0:
            raise TrajectoryException("trajectory is empty")
        if start_timestamp is None:
            start_timestamp = self.timestamps[0]
        if end_timestamp is None:
            end_timestamp = self.timestamps[-1]
        if start_timestamp > end_timestamp:
            raise TrajectoryException(
                "start_timestamp is greater than end_timestamp "
                "({} > {})".format(start_timestamp, end_timestamp))
        ids = np.where(
            np.logical_and(self.timestamps >= start_timestamp,
                           self.timestamps <= end_timestamp))[0]
        self.reduce_to_ids(ids)

    def split_time_gaps(self,
                        dt: float) -> typing.Sequence["PoseTrajectory3D"]:
        """
        Determines time gaps in the trajectory and splits it into multiple
        trajectories at the gaps.
        :param dt: time threshold for gap detection in seconds
        """
        if self.num_poses < 2:
            return [self]
        gaps = np.where(self.timestamps[1:] - self.timestamps[:-1] > dt)[0]
        if len(gaps) == 0:
            return [self]
        gaps = np.concatenate([[0], gaps + 1, [self.num_poses]])
        return [
            PoseTrajectory3D(timestamps=self.timestamps[gaps[i]:gaps[i + 1]],
                             poses_se3=self.poses_se3[gaps[i]:gaps[i + 1]])
            for i in range(len(gaps) - 1)
        ]

    def split_distance_gaps(
            self, dist: float) -> typing.Sequence["PoseTrajectory3D"]:
        """
        Determines translation gaps in the path and splits it into multiple
        trajectories at the gaps.
        :param dist: distance threshold for gap detection in meters
        """
        if self.num_poses < 2:
            return [self]
        jumps = self._jumps(dist)
        return [
            PoseTrajectory3D(timestamps=self.timestamps[jumps[i]:jumps[i + 1]],
                             poses_se3=self.poses_se3[jumps[i]:jumps[i + 1]])
            for i in range(len(jumps) - 1)
        ]

    def split_speed_outliers(
            self, v_max: float) -> typing.Sequence["PoseTrajectory3D"]:
        """
        Splits the trajectory into multiple trajectories at speed outliers.
        Can be used for example to handle jumps due to tracking loss.

        :param v_max: speed threshold for outlier detection in m/s
        """
        if self.num_poses < 2:
            return [self]
        speeds = self.speeds
        outliers = np.where(speeds > v_max)[0]
        if len(outliers) == 0:
            return [self]
        jumps = np.concatenate([[0], outliers + 1, [self.num_poses]])
        return [
            PoseTrajectory3D(timestamps=self.timestamps[jumps[i]:jumps[i + 1]],
                             poses_se3=self.poses_se3[jumps[i]:jumps[i + 1]])
            for i in range(len(jumps) - 1)
        ]

    def check(self) -> typing.Tuple[bool, dict]:
        if self.num_poses == 0:
            return True, {}
        valid, details = super(PoseTrajectory3D, self).check()
        len_stamps_valid = (len(self.timestamps) == len(self.positions_xyz))
        valid &= len_stamps_valid
        details["nr. of stamps"] = "ok" if len_stamps_valid else "wrong"
        stamps_ascending = bool(
            np.all(np.sort(self.timestamps) == self.timestamps))
        stamps_ascending &= np.unique(self.timestamps).size == len(
            self.timestamps)
        valid &= stamps_ascending
        if stamps_ascending:
            details["timestamps"] = "ok"
        else:
            details["timestamps"] = "wrong, not ascending or duplicates"
        return valid, details

    def get_infos(self) -> dict:
        """
        :return: dictionary with some infos about the trajectory
        """
        infos = super(PoseTrajectory3D, self).get_infos()
        infos["duration (s)"] = self.timestamps[-1] - self.timestamps[0]
        infos["t_start (s)"] = self.timestamps[0]
        infos["t_end (s)"] = self.timestamps[-1]
        return infos

    def get_statistics(self) -> dict:
        """
        :return: dictionary with some statistics of the trajectory
        """
        if self.num_poses < 2:
            return {}
        stats = super(PoseTrajectory3D, self).get_statistics()
        speeds = self.speeds
        vmax = speeds.max()
        vmin = speeds.min()
        vmean = speeds.mean()
        delta_ts = self.timestamps[1:] - self.timestamps[:-1]
        stats.update({
            "v_max (m/s)": vmax,
            "v_min (m/s)": vmin,
            "v_avg (m/s)": vmean,
            "v_max (km/h)": vmax * 3.6,
            "v_min (km/h)": vmin * 3.6,
            "v_avg (km/h)": vmean * 3.6,
            "dt_max (s)": delta_ts.max(),
            "dt_min (s)": delta_ts.min(),
            "dt_avg (s)": delta_ts.mean(),
        })
        return stats


class Trajectory(PoseTrajectory3D):
    pass  # TODO compat


def calc_speed(xyz_1: np.ndarray, xyz_2: np.ndarray, t_1: float,
               t_2: float) -> float:
    """
    :param xyz_1: position at timestamp 1
    :param xyz_2: position at timestamp 2
    :param t_1: timestamp 1
    :param t_2: timestamp 2
    :return: speed in m/s
    """
    if (t_2 - t_1) <= 0:
        raise TrajectoryException("bad timestamps: " + str(t_1) + " & " +
                                  str(t_2))
    return float(np.linalg.norm(xyz_2 - xyz_1) / (t_2 - t_1))


def calc_angular_speed(p_1: np.ndarray, p_2: np.ndarray, t_1: float,
                       t_2: float, degrees: bool = False) -> float:
    """
    :param p_1: pose at timestamp 1
    :param p_2: pose at timestamp 2
    :param t_1: timestamp 1
    :param t_2: timestamp 2
    :param degrees: set to True to return deg/s
    :return: speed in rad/s
    """
    if (t_2 - t_1) <= 0:
        raise TrajectoryException("bad timestamps: " + str(t_1) + " & " +
                                  str(t_2))
    angle_1 = lie.so3_log(p_1[:3, :3], degrees)
    angle_2 = lie.so3_log(p_2[:3, :3], degrees)
    return (angle_2 - angle_1) / (t_2 - t_1)


def xyz_quat_wxyz_to_se3_poses(
        xyz: np.ndarray, quat: np.ndarray) -> typing.Sequence[np.ndarray]:
    poses = [
        lie.se3(lie.so3_from_se3(tr.quaternion_matrix(quat)), xyz)
        for quat, xyz in zip(quat, xyz)
    ]
    return poses


def se3_poses_to_xyz_quat_wxyz(
    poses: typing.Sequence[np.ndarray]
) -> typing.Tuple[np.ndarray, np.ndarray]:
    xyz = np.array([pose[:3, 3] for pose in poses])
    quat_wxyz = np.array([tr.quaternion_from_matrix(pose) for pose in poses])
    return xyz, quat_wxyz


def merge(trajectories: typing.Sequence[PoseTrajectory3D]) -> PoseTrajectory3D:
    """
    Merges multiple trajectories into a single, timestamp-sorted one.
    :param trajectories: list of PoseTrajectory3D objects
    :return: merged PoseTrajectory3D
    """
    merged_stamps = np.concatenate([t.timestamps for t in trajectories])
    merged_xyz = np.concatenate([t.positions_xyz for t in trajectories])
    merged_quat = np.concatenate(
        [t.orientations_quat_wxyz for t in trajectories])
    order = merged_stamps.argsort()
    merged_stamps = merged_stamps[order]
    merged_xyz = merged_xyz[order]
    merged_quat = merged_quat[order]
    return PoseTrajectory3D(merged_xyz, merged_quat, merged_stamps)
