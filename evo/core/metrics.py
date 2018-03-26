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
from evo.core.result import Result
from evo.core import lie_algebra as lie

if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
    ABC = abc.ABC
else:
    ABC = abc.ABCMeta('ABC', (), {})

logger = logging.getLogger(__name__)


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


class Metric(ABC):
    @abc.abstractmethod
    def reset_parameters(self, parameters):
        return

    @abc.abstractmethod
    def process_data(self, data):
        return

    @abc.abstractmethod
    def get_statistic(self, statistics_type):
        return

    @abc.abstractmethod
    def get_all_statistics(self):
        return

    @abc.abstractmethod
    def get_result(self):
        return


class PE(Metric):
    """
    Abstract base class of pose error metrics.
    """

    def __str__(self):
        return "PE metric base class"

    @abc.abstractmethod
    def reset_parameters(self, parameters):
        return

    @abc.abstractmethod
    def process_data(self, data):
        return

    def get_statistic(self, statistics_type):
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
        :return: a dictionary {StatisticsType.value : float}
        """
        statistics = {}
        for s in StatisticsType:
            try:
                statistics[s.value] = self.get_statistic(s)
            except MetricsException as e:
                if "unsupported statistics_type" not in str(e):  # ignore unsupported statistics
                    raise
        return statistics

    def get_result(self, ref_name="reference", est_name="estimate"):
        """
        Wrap the result in Result object
        :param ref_name: optional, label of the reference data
        :param est_name: optional, label of the estimated data
        :return:
        """
        result = Result()
        metric_name = self.__class__.__name__
        unit_name = self.unit.value if self.unit is not None else ""
        result.add_info({
            "title": str(self),
            "ref_name": ref_name,
            "est_name": est_name,
            "label": "{} {}".format(metric_name, "({})".format(unit_name))
        })
        result.add_stats(self.get_all_statistics())
        if hasattr(self, "error"):
            result.add_np_array("error_array", self.error)
        return result


class RPE(PE):
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
            id_pairs = filters.id_pairs_from_delta(traj_est.poses_se3, self.delta, self.delta_unit,
                                                   self.rel_delta_tol, all_pairs=self.all_pairs)
        if not self.all_pairs:
            self.delta_ids = [j for i, j in id_pairs]  # store flat id list e.g. for plotting
        self.E = [self.rpe_base(traj_ref.poses_se3[i], traj_ref.poses_se3[j],
                                traj_est.poses_se3[i], traj_est.poses_se3[j])
                  for i, j in id_pairs]
        logger.debug("compared " + str(len(self.E)) + " relative pose pairs, delta = "
                     + str(self.delta) + " (" + str(self.delta_unit.value) + ") "
                     + ("with all possible pairs" if self.all_pairs else "with consecutive pairs"))

        logger.debug("calculating RPE for " + str(self.pose_relation.value) + " pose relation...")

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


class APE(PE):
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
            self.E = [self.ape_base(x_t, x_t_star) for x_t, x_t_star in
                      zip(traj_est.poses_se3, traj_ref.poses_se3)]
        logger.debug("compared " + str(len(self.E)) + " absolute pose pairs")
        logger.debug("calculating APE for " + str(self.pose_relation.value) + " pose relation...")

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
