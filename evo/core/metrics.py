# -*- coding: UTF8 -*-
"""
this module provides metrics for the evaluation of SLAM algorithms
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

from __future__ import print_function  # Python 2.7 backwards compatibility

import abc
import logging
import math
import sys
from enum import Enum  # requires enum34 in Python 2.7

import numpy as np

from evo.core import filters
from evo.core import transformations as tr
from evo.core import lie_algebra as lie

if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
    ABC = abc.ABC
else:
    ABC = abc.ABCMeta('ABC', (), {})


class MetricsException(Exception):
    pass


class StatisticsType(Enum):
    rmse = "rmse"
    mean = "mean"
    median = "median"
    std = "std"
    min = "min"
    max = "max"
    sse = "sse"


class PoseRelation(Enum):
    full_transformation = "full transformation"
    translation_part = "translation part"
    rotation_part = "rotation part"
    rotation_angle_rad = "rotation angle in radians"
    rotation_angle_deg = "rotation angle in degrees"


class Unit(Enum):
    meters = "m"
    seconds = "s"
    degrees = "deg"
    radians = "rad"
    frames = "frames"


class VelUnit(Enum):
    meters_per_sec = "m/s"
    rad_per_sec = "rad/s"
    degrees_per_sec = "deg/s"


class StateModel(Enum):
    """
    conventions for state vectors
    """
    xyz = 1,  # translation only
    xyz_rpy = 2,  # translation + roll, pitch, yaw
    xyz_quat_xyzw = 3,  # translation + xyzw quaternion
    xyz_quat_wxyz = 4,  # translation + wxyz quaternion


class Metric(ABC):
    @abc.abstractmethod
    def reset_parameters(self, parameters):
        return

    @abc.abstractmethod
    def process_data(self, data):
        return

    @abc.abstractmethod
    def get_statistic(self):
        return

    @abc.abstractmethod
    def get_all_statistics(self):
        return


class Hausdorff(Metric):
    def __init__(self, metric=lambda a, b: a - b, backward=True, two_way=False):
        self.metric = metric
        self.backward = backward
        self.two_way = two_way

    def reset_parameters(self, metric=lambda a, b: a - b, backward=True, two_way=False):
        self.__init__(metric, backward, two_way)

    def hausdorff_base(self, A, B):
        h = 0.0
        i = 0
        u = 0
        for a_i in A:
            print("\r" + str(i), end="")
            min_d = min([self.metric(a_i, b_i) for b_i in B])
            if min_d > h:
                h = min_d
                u = i
            i += 1
        print(" winner: " + str(u))
        return h

    def process_data(self, data):
        A, B = data
        if self.backward:
            return self.hausdorff_base(B, A)
        elif self.two_way:
            return max(self.hausdorff_base(A, B), self.hausdorff_base(B, A))
        else:
            return self.hausdorff_base(A, B)

    def get_statistic(self):
        pass

    def get_all_statistics(self):
        pass


class NEES(Metric):
    """
    NEES: normalized estimation error squared
    metric for determining the consistency of a state estimator w.r.t. a reference model
    """

    def __init__(self, threshold=0, state_model=StateModel.xyz_quat_wxyz):
        self.threshold = threshold
        self.state_model = state_model
        self.nees = []
        self.num_outliers = 0

    def reset_parameters(self, threshold, state_model=StateModel.xyz_quat_wxyz):
        """
        resets the current parameters and results
        :param threshold: values above will be counted as outliers
        :param state_model: StateModel value describing how the state vectors are formed
        """
        self.threshold = threshold
        self.state_model = state_model
        self.nees = []
        self.num_outliers = 0

    @staticmethod
    def nees_base(r, cov, threshold):
        """
        calculates the normalized estimation error squared (NEES) given a residual state vector
        :param r: residual state vector (estimate minus reference)
        :param cov: covariance matrix (inverse information matrix)
        :param threshold: values above will be marked as outliers
        :return: epsilon (NEES value), outlier (True or False)
        """
        n = np.dot(r.T, np.dot(np.linalg.inv(cov), r)),  # NEES value
        if np.abs(n)[0] > threshold:
            return n, True  # mark as outlier
        else:
            return n, False

    # TODO quaternion version not yet tested
    def calculate_residuals(self, states_ref, states_est):
        """
        calculate residual states ("inverse motion operator")
        :param states_ref: list of reference state vectors
        :param states_est: list of estimated state vectors
        """
        if self.state_model in {StateModel.xyz, StateModel.xyz_rpy}:
            residuals = states_ref - states_est
        elif self.state_model in {StateModel.xyz_quat_wxyz, StateModel.xyz_quat_xyzw}:
            if self.state_model == StateModel.xyz_quat_xyzw:
                # change quaternion order to wxyz for transformations.py
                states_ref[:, 3:] = np.roll(states_ref[:, 3:], -1, axis=1)
                states_est[:, 3:] = np.roll(states_est[:, 3:], -1, axis=1)
            residuals_xyz = states_ref[:, :3] - states_est[:, :3]
            residuals_quat = np.array(
                [tr.quaternion_multiply(q_1, tr.quaternion_inverse(q_2))  # quaternion division
                 for q_1, q_2 in zip(states_ref[:, 3:], states_est[:, 3:])])
            residuals = np.hstack((residuals_xyz, residuals_quat))
        else:
            raise MetricsException("unsupported state model")
        return residuals

    # TODO quaternion version not yet tested
    def process_data(self, data):
        """
        calculate the normalized estimation error squared (NEES)
        for a batch of state vectors and covariances
        :param data: tuple (states_ref, states_est, covariances) with:
        states_ref: list of reference state vectors
        states_est: list of estimated state vectors
        covariances: list of covariance matrices
        """
        if len(data) != 3:
            raise MetricsException(
                "please provide data tuple as: (states_ref, states_est, covariances)")
        states_ref, states_est, covariances = data
        if len(states_est) != len(states_ref) != len(covariances):
            raise MetricsException("data lists must have same length")
        # calculate NEES
        residuals = self.calculate_residuals(states_ref, states_est)
        for r, cov in zip(residuals, covariances):
            try:
                epsilon, is_outlier = self.nees_base(r, cov, self.threshold)
                self.nees.append(epsilon)
                if is_outlier:
                    self.num_outliers += 1
            except np.linalg.LinAlgError as e:
                logging.warning(str(e) + ", ignoring value for NEES calculation")

    def get_statistic(self, statistics_type=StatisticsType.mean):
        if statistics_type == StatisticsType.rmse:
            return np.sqrt(np.mean(np.power(self.nees, 2)))
        elif statistics_type == StatisticsType.mean:
            return np.mean(self.nees)
        elif statistics_type == StatisticsType.median:
            return np.median(self.nees)
        elif statistics_type == StatisticsType.std:
            return np.std(self.nees)
        elif statistics_type == StatisticsType.min:
            return np.min(np.absolute(self.nees))
        elif statistics_type == StatisticsType.max:
            return np.max(np.absolute(self.nees))
        else:
            raise MetricsException("unsupported statistics_type")

    def get_all_statistics(self):
        """
        shortcut for calling get_statistics with all supported StatisticTypes
        :return: a dictionary {StatisticsType_string : float}
        """
        statistics = {}
        for s in StatisticsType:
            try:
                statistics[s.value] = self.get_statistic(s)
            except MetricsException as e:
                if "unsupported statistics_type" not in str(e):  # ignore unsupported statistics
                    raise
        return statistics


class RPE(Metric):
    """
    RPE: relative pose error
    metric for investigating the odometry drift
    """

    def __init__(self, pose_relation=PoseRelation.translation_part, delta=1.0,
                 delta_unit=Unit.frames,
                 rel_delta_tol=0.1, all_pairs=False):
        if delta < 0:
            raise MetricsException("delta must be a positive number")
        if delta_unit == Unit.frames and not isinstance(delta, int) and not delta.is_integer():
            raise MetricsException(
                "delta must be integer (no decimals) for delta unit " + str(delta_unit))
        self.delta = int(delta) if delta_unit == Unit.frames else delta
        self.delta_unit = delta_unit
        self.rel_delta_tol = rel_delta_tol
        self.pose_relation = pose_relation
        self.all_pairs = all_pairs
        self.E = []
        self.error = []
        self.delta_ids = []
        if pose_relation == PoseRelation.translation_part:
            self.unit = Unit.meters
        elif pose_relation == PoseRelation.rotation_angle_deg:
            self.unit = Unit.degrees
        elif pose_relation == PoseRelation.rotation_angle_rad:
            self.unit = Unit.radians
        else:
            self.unit = None  # dimension-less

    def __str__(self):
        title = "RPE w.r.t. "
        title += (str(self.pose_relation.value) + " "
                  + ("(" + self.unit.value + ")" if self.unit else ""))
        title += "\nfor delta = " + str(self.delta) + " (" + str(self.delta_unit.value) + ")"
        if not self.all_pairs:
            title += " using consecutive pairs"
        else:
            title += " using all possible pairs"
        return title

    def reset_parameters(self, pose_relation=PoseRelation.translation_part, delta=1.0,
                         delta_unit=Unit.frames,
                         all_pairs=False):
        """
        resets the current parameters and results
        :param delta: the interval step for indices (default: 1)
        :param delta_unit: unit of delta (Unit enum member)
        :param pose_relation: MotionType value defining how the RPE should be calculated
        :param all_pairs: use all possible pairs instead of consecutive pairs
        """
        self.__init__(pose_relation, delta, delta_unit, all_pairs)

    @staticmethod
    def rpe_base(Q_i, Q_i_delta, P_i, P_i_delta):
        """
        relative SE(3) error pose for a single pose pair
        following the notation of the TUM RGB-D paper
        :param Q_i: reference SE(3) pose at i
        :param Q_i_delta: reference SE(3) pose at i+delta
        :param P_i: estimated SE(3) pose at i
        :param P_i_delta: estimated SE(3) pose at i+delta
        :return: the RPE matrix E_i in SE(3)
        """
        Q_rel = lie.relative_se3(Q_i, Q_i_delta)
        P_rel = lie.relative_se3(P_i, P_i_delta)
        E_i = lie.relative_se3(Q_rel, P_rel)
        return E_i

    def process_data(self, data, id_pairs=None):
        """
        calculate relative poses on a batch of SE(3) poses
        :param data: tuple (traj_ref, traj_est) with:
        traj_ref: reference evo.trajectory.PosePath or derived
        traj_est: estimated evo.trajectory.PosePath or derived
        :param id_pairs: pre-computed pair indices if you know what you're doing (ignores delta)
        """
        if len(data) != 2:
            raise MetricsException("please provide data tuple as: (traj_ref, traj_est)")
        traj_ref, traj_est = data
        if traj_ref.num_poses != traj_est.num_poses:
            raise MetricsException("trajectories must have same number of poses")

        if id_pairs is None:
            id_pairs = id_pairs_from_delta(traj_est.poses_se3, self.delta, self.delta_unit,
                                           self.rel_delta_tol, all_pairs=self.all_pairs)
        if not self.all_pairs:
            self.delta_ids = [j for i, j in id_pairs]  # store flat id list e.g. for plotting
        self.E = [self.rpe_base(traj_ref.poses_se3[i], traj_ref.poses_se3[j],
                                traj_est.poses_se3[i], traj_est.poses_se3[j])
                  for i, j in id_pairs]
        logging.debug("compared " + str(len(self.E)) + " relative pose pairs, delta = "
                      + str(self.delta) + " (" + str(self.delta_unit.value) + ") "
                      + ("with all possible pairs" if self.all_pairs else "with consecutive pairs"))

        logging.debug("calculating RPE for " + str(self.pose_relation.value) + " pose relation...")
        if self.pose_relation == PoseRelation.translation_part:
            self.error = [np.linalg.norm(E_i[:3, 3]) for E_i in self.E]
        elif self.pose_relation == PoseRelation.rotation_part:
            # ideal: rot(E_i) = 3x3 identity
            self.error = np.array(
                [np.linalg.norm(lie.so3_from_se3(E_i) - np.eye(3)) for E_i in self.E])
        elif self.pose_relation == PoseRelation.full_transformation:
            # ideal: E_i = 4x4 identity
            self.error = np.array([np.linalg.norm(E_i - np.eye(4)) for E_i in self.E])
        elif self.pose_relation == PoseRelation.rotation_angle_rad:
            self.error = np.array([abs(lie.so3_log(E_i[:3, :3])) for E_i in self.E])
        elif self.pose_relation == PoseRelation.rotation_angle_deg:
            self.error = np.array([abs(lie.so3_log(E_i[:3, :3])) * 180 / np.pi for E_i in self.E])
        else:
            raise MetricsException("unsupported pose_relation: ", self.pose_relation)

    def get_statistic(self, statistics_type=StatisticsType.rmse):
        """
        here, the statistics are the actual RPE value
        :param statistics_type: StatisticsType value indicating the type of averaging
        :return: a float RPE value
        """
        if statistics_type == StatisticsType.rmse:
            squared_errors = np.power(self.error, 2)
            return math.sqrt(np.mean(squared_errors))
        elif statistics_type == StatisticsType.sse:
            squared_errors = np.power(self.error, 2)
            return np.sum(squared_errors)
        elif statistics_type == StatisticsType.mean:
            return np.mean(self.error)
        elif statistics_type == StatisticsType.median:
            return np.median(self.error)
        elif statistics_type == StatisticsType.max:
            return np.max(self.error)
        elif statistics_type == StatisticsType.min:
            return np.min(self.error)
        elif statistics_type == StatisticsType.std:
            return np.std(self.error)
        else:
            raise MetricsException("unsupported statistics_type")

    def get_all_statistics(self):
        """
        shortcut for calling get_statistics with all supported StatisticTypes
        :return: a dictionary {StatisticsType_string : float}
        """
        statistics = {}
        for s in StatisticsType:
            try:
                statistics[s.value] = self.get_statistic(s)
            except MetricsException as e:
                if "unsupported statistics_type" not in str(e):  # ignore unsupported statistics
                    raise
        return statistics


class APE(Metric):
    """
    APE: absolute pose error
    metric for investigating the global consistency of a SLAM trajectory
    """

    def __init__(self, pose_relation=PoseRelation.translation_part):
        self.pose_relation = pose_relation
        self.E = []
        self.error = []
        if pose_relation == PoseRelation.translation_part:
            self.unit = Unit.meters
        elif pose_relation == PoseRelation.rotation_angle_deg:
            self.unit = Unit.degrees
        elif pose_relation == PoseRelation.rotation_angle_rad:
            self.unit = Unit.radians
        else:
            self.unit = None  # dimension-less

    def __str__(self):
        title = "APE w.r.t. "
        title += (str(self.pose_relation.value) + " "
                  + ("(" + self.unit.value + ")" if self.unit else ""))
        return title

    def reset_parameters(self, pose_relation=PoseRelation.translation_part):
        """
        resets the current parameters and results
        :param pose_relation: PoseRelation value defining how the RPE should be calculated
        """
        self.__init__(pose_relation)

    @staticmethod
    def ape_base(x_t, x_t_star):
        """
        absolute error pose for a single SE(3) pose pair
        following the notation of the Kümmerle paper
        :param x_t: estimated absolute pose at t
        :param x_t_star: reference absolute pose at t
        .:return: the delta pose
        """
        return lie.relative_se3(x_t, x_t_star)

    def process_data(self, data):
        """
        calculate APE metric on a batch of poses
        :param data: tuple (traj_ref, traj_est) with:
        traj_ref: reference evo.trajectory.PosePath or derived
        traj_est: estimated evo.trajectory.PosePath or derived
        """
        if len(data) != 2:
            raise MetricsException("please provide data tuple as: (traj_ref, traj_est)")
        traj_ref, traj_est = data
        if traj_ref.num_poses != traj_est.num_poses:
            raise MetricsException("trajectories must have same number of poses")

        if self.pose_relation == PoseRelation.translation_part:
            # don't require full SE(3) matrices for faster computation
            self.E = traj_est.positions_xyz - traj_ref.positions_xyz
        else:
            self.E = [self.ape_base(x_t, x_t_star) for x_t, x_t_star in zip(traj_est.poses_se3, traj_ref.poses_se3)]
        logging.debug("compared " + str(len(self.E)) + " absolute pose pairs")
        logging.debug("calculating APE for " + str(self.pose_relation.value) + " pose relation...")
        if self.pose_relation == PoseRelation.translation_part:
            # E is an array of position vectors only in this case
            self.error = [np.linalg.norm(E_i) for E_i in self.E]
        elif self.pose_relation == PoseRelation.rotation_part:
            self.error = np.array(
                [np.linalg.norm(lie.so3_from_se3(E_i) - np.eye(3)) for E_i in self.E])
        elif self.pose_relation == PoseRelation.full_transformation:
            self.error = np.array([np.linalg.norm(E_i - np.eye(4)) for E_i in self.E])
        elif self.pose_relation == PoseRelation.rotation_angle_rad:
            self.error = np.array([abs(lie.so3_log(E_i[:3, :3])) for E_i in self.E])
        elif self.pose_relation == PoseRelation.rotation_angle_deg:
            self.error = np.array([abs(lie.so3_log(E_i[:3, :3])) * 180 / np.pi for E_i in self.E])
        else:
            raise MetricsException("unsupported pose_relation")

    def get_statistic(self, statistics_type=StatisticsType.rmse):
        """
        here, the statistics are the actual APE value
        :param statistics_type: StatisticsType value indicating the type of averaging
        :return: a float APE value
        """
        if statistics_type == StatisticsType.rmse:
            squared_errors = np.power(self.error, 2)
            return math.sqrt(np.mean(squared_errors))
        elif statistics_type == StatisticsType.sse:
            squared_errors = np.power(self.error, 2)
            return np.sum(squared_errors)
        elif statistics_type == StatisticsType.mean:
            return np.mean(self.error)
        elif statistics_type == StatisticsType.median:
            return np.median(self.error)
        elif statistics_type == StatisticsType.max:
            return np.max(self.error)
        elif statistics_type == StatisticsType.min:
            return np.min(self.error)
        elif statistics_type == StatisticsType.std:
            return np.std(self.error)
        else:
            raise MetricsException("unsupported statistics_type")

    def get_all_statistics(self):
        """
        shortcut for calling get_statistics with all supported StatisticTypes
        :return: a dictionary {StatisticsType_string : float}
        """
        statistics = {}
        for s in StatisticsType:
            try:
                statistics[s.value] = self.get_statistic(s)
            except MetricsException as e:
                if "unsupported statistics_type" not in str(e):  # ignore unsupported statistics
                    raise
        return statistics


def id_pairs_from_delta(poses, delta, delta_unit, rel_tol=0.1, all_pairs=False):
    """
    get index tuples of pairs with distance==delta from a pose list
    :param poses: list of SE(3) poses
    :param delta: the interval step for indices
    :param delta_unit: unit of delta (Unit enum member)
    :param rel_tol: relative tolerance to accept or reject deltas
    :param all_pairs: use all possible pairs instead of consecutive pairs
    :return: list of index tuples (pairs)
    """
    if delta_unit == Unit.frames:
        id_pairs = filters.filter_pairs_by_index(poses, delta, all_pairs)
    elif delta_unit == Unit.meters:
        id_pairs = filters.filter_pairs_by_path(poses, delta, delta * rel_tol, all_pairs)
    elif delta_unit in {Unit.degrees, Unit.radians}:
        use_degrees = (delta_unit == Unit.degrees)
        id_pairs = filters.filter_pairs_by_angle(poses, delta, delta * rel_tol, use_degrees,
                                                 all_pairs)
    else:
        raise MetricsException("unsupported delta unit: " + str(delta_unit))

    if len(id_pairs) == 0:
        raise MetricsException("delta = " + str(delta) + " (" + str(delta_unit.value) + ") " +
                               "produced empty index list - try lower values or higher tolerance")
    logging.debug("found " + str(len(id_pairs)) + " pairs with delta " + str(delta)
                  + " (" + str(delta_unit.value) + ") among " + str(len(poses)) + " poses "
                  + ("using consecutive pairs " if not all_pairs else "using all possible pairs"))
    return id_pairs
