"""
Container utility for bundling and batch processing a set of related trajectories.
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
from typing import Callable, Dict, Optional, Sequence, cast

import numpy as np

from evo import EvoException
from evo.core import sync
from evo.core.trajectory import (
    Plane,
    PosePath3D,
    PoseTrajectory3D,
    merge,
)

logger = logging.getLogger(__name__)


class TrajectoryBundleException(EvoException):
    pass


class TrajectoryBundle:
    """
    A bundle of named trajectories with an optional reference trajectory.
    Provides batch operations that apply to all contained trajectories.
    """

    def __init__(
        self,
        trajectories: Optional[Dict[str, PosePath3D]] = None,
        ref_traj: Optional[PosePath3D] = None,
    ):
        self.trajectories: Dict[str, PosePath3D] = trajectories or {}
        self.ref_traj = ref_traj
        self.synced = False
        self.synced_refs: Dict[str, PosePath3D] = {}

    def all_trajectories(
        self,
        name_transform: Optional[Callable[[str], str]] = None,
    ) -> Dict[str, PosePath3D]:
        """
        :param name_transform: optional function to transform trajectory names
        :return: all trajectories including reference (keyed as "reference")
        """
        result: Dict[str, PosePath3D] = {}
        if self.ref_traj:
            result["reference"] = self.ref_traj
        for name, traj in self.trajectories.items():
            key = name_transform(name) if name_transform else name
            result[key] = traj
        return result

    def add(self, name: str, traj: PosePath3D) -> None:
        self.trajectories[name] = traj

    def add_reference(self, traj: PosePath3D) -> None:
        self.ref_traj = traj

    def mark_synced(self) -> None:
        """
        Marks the bundle as synced without performing sync.
        Use this for index-aligned data (e.g. pure paths without time) where trajectories
        are already matched with the reference by index.
        Sets synced_refs to point to ref_traj for all trajectories.
        """
        if not self.ref_traj:
            raise TrajectoryBundleException(
                "Can't mark as synced without a reference trajectory."
            )
        self.synced = True
        for name in self.trajectories:
            if name not in self.synced_refs:
                self.synced_refs[name] = self.ref_traj

    def downsample(self, max_poses: int) -> None:
        """
        Downsample all trajectories and reference to max_poses.
        """
        for traj in self.trajectories.values():
            traj.downsample(max_poses)
        if self.ref_traj:
            self.ref_traj.downsample(max_poses)

    def motion_filter(
        self, distance_threshold: float, angle_threshold: float
    ) -> None:
        """
        Apply a motion filter to all trajectories and reference.
        :param distance_threshold: minimum distance in meters
        :param angle_threshold: minimum angle in degrees
        """
        for traj in self.trajectories.values():
            traj.motion_filter(distance_threshold, angle_threshold, True)
        if self.ref_traj:
            self.ref_traj.motion_filter(
                distance_threshold, angle_threshold, True
            )

    def merge(self) -> None:
        """
        Merge all trajectories into a single trajectory.
        """
        if len(self.trajectories) == 0:
            raise TrajectoryBundleException("No trajectories to merge.")
        self.trajectories = {
            "merged_trajectory": merge(
                cast(
                    Sequence[PoseTrajectory3D],
                    list(self.trajectories.values()),
                )
            )
        }

    def apply_time_offset(self, offset: float) -> None:
        """
        Add a time offset to all trajectory timestamps.
        :param offset: time offset in seconds
        """
        for name, traj in self.trajectories.items():
            if not isinstance(traj, PoseTrajectory3D):
                raise TrajectoryBundleException(
                    f"{name} doesn't have timestamps"
                    " - can't add time offset."
                )
            traj.timestamps += offset

    def sync(self, max_diff: float = 0.01) -> None:
        """
        Associate trajectories with the reference by timestamps.
        Populates synced_refs with the per-trajectory matched reference.
        :param max_diff: maximum timestamp difference for sync
        """
        if not self.ref_traj:
            raise TrajectoryBundleException(
                "Can't sync without a reference trajectory."
            )
        self.synced = True
        for name, traj in self.trajectories.items():
            if not isinstance(traj, PoseTrajectory3D):
                raise TrajectoryBundleException(
                    f"{name} doesn't have timestamps" " - can't sync."
                )
            if not isinstance(self.ref_traj, PoseTrajectory3D):
                raise TrajectoryBundleException(
                    "Reference doesn't have timestamps" " - can't sync."
                )
            logger.debug(f"Syncing {name} with reference.")
            ref_traj_tmp, self.trajectories[name] = (
                sync.associate_trajectories(
                    self.ref_traj,
                    traj,
                    max_diff=max_diff,
                    first_name="reference",
                    snd_name=name,
                )
            )
            self.synced_refs[name] = ref_traj_tmp

    def align(
        self,
        correct_scale: bool = False,
        correct_only_scale: bool = False,
        n: int = -1,
    ) -> None:
        """
        Align all trajectories to the reference using Umeyama alignment.
        Uses per-trajectory synced references if available (from sync),
        otherwise falls back to ref_traj.
        :param correct_scale: correct the scale
        :param correct_only_scale: correct only scale, not rotation/translation
        :param n: number of poses to use for alignment (-1 = all)
        """
        if not self.ref_traj:
            raise TrajectoryBundleException(
                "Can't align without a reference trajectory."
            )
        self.synced = True
        for name in self.trajectories:
            ref = self.synced_refs.get(name, self.ref_traj)
            logger.debug(f"Aligning {name} to reference.")
            self.trajectories[name].align(
                ref,
                correct_scale=correct_scale,
                correct_only_scale=correct_only_scale,
                n=n,
            )
            if name not in self.synced_refs:
                self.synced_refs[name] = self.ref_traj

    def align_origin(self) -> None:
        """
        Align the origin of all trajectories to the reference.
        Uses per-trajectory synced references if available (from sync),
        otherwise falls back to ref_traj.
        """
        if not self.ref_traj:
            raise TrajectoryBundleException(
                "Can't align origin without a reference trajectory."
            )
        self.synced = True
        for name in self.trajectories:
            ref = self.synced_refs.get(name, self.ref_traj)
            logger.debug(f"Aligning {name}'s origin to reference.")
            self.trajectories[name].align_origin(ref)
            if name not in self.synced_refs:
                self.synced_refs[name] = self.ref_traj

    def apply_transform(
        self,
        transform: np.ndarray,
        right_mul: bool = False,
        propagate: bool = False,
    ) -> None:
        """
        Apply a SE(3) transformation to all trajectories (not the reference).
        :param transform: 4x4 SE(3) transformation matrix
        :param right_mul: if True, apply as right-multiplication
        :param propagate: if True, propagate the transform to child frames
        """
        for traj in self.trajectories.values():
            traj.transform(transform, right_mul=right_mul, propagate=propagate)

    def project(self, plane: Plane) -> None:
        """
        Project all trajectories and reference onto a 2D plane.
        :param plane: the projection plane
        """
        for traj in self.trajectories.values():
            traj.project(plane)
        if self.ref_traj:
            self.ref_traj.project(plane)
