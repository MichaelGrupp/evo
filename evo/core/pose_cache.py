"""
Internal caching storage for trajectory poses and derived data.
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

import typing
from functools import cached_property

import numpy as np

from evo import EvoException
import evo.core.transformations as tr
import evo.core.geometry as geometry
from evo.core import lie_algebra as lie


class PoseCacheException(EvoException):
    pass


class PoseCache:
    """
    Stores pose data in different representations, lazily handles conversions
    between representations and acts as cache (memoizer).

    Derived values like distances or path length are also cached.
    """

    # self.__dict__ keys of caches of derived values.
    _DERIVED_CACHES: tuple[str, ...] = ()

    def __init__(
        self,
        *,
        positions_xyz: np.ndarray | None = None,
        orientations_quat_wxyz: np.ndarray | None = None,
        poses_se3: typing.Sequence[np.ndarray] | None = None,
    ):
        if (
            positions_xyz is None or orientations_quat_wxyz is None
        ) and poses_se3 is None:
            raise PoseCacheException(
                "must provide at least positions_xyz "
                "& orientations_quat_wxyz, or poses_se3"
            )
        # Note: assignments pre-populate `cached_property`s here.
        if positions_xyz is not None:
            self.positions_xyz = np.array(positions_xyz)
        if orientations_quat_wxyz is not None:
            self.orientations_quat_wxyz = np.array(orientations_quat_wxyz)
        if poses_se3 is not None:
            self.poses_se3 = list(poses_se3)

    @cached_property
    def positions_xyz(self) -> np.ndarray:
        return np.array([p[:3, 3] for p in self.poses_se3])

    @cached_property
    def orientations_quat_wxyz(self) -> np.ndarray:
        return np.array([tr.quaternion_from_matrix(p) for p in self.poses_se3])

    @cached_property
    def poses_se3(self) -> list[np.ndarray]:
        return [
            lie.se3(lie.so3_from_se3(tr.quaternion_matrix(q)), p)
            for q, p in zip(self.orientations_quat_wxyz, self.positions_xyz)
        ]

    @cached_property
    def distances(self) -> np.ndarray:
        self._register_derived("distances")
        return geometry.accumulated_distances(self.positions_xyz)

    @cached_property
    def path_length(self) -> float:
        self._register_derived("path_length")
        return float(geometry.arc_len(self.positions_xyz))

    @property
    def num_poses(self) -> int:
        if self.has_poses_se3():
            return len(self.poses_se3)
        if self.has_positions_xyz():
            return self.positions_xyz.shape[0]
        return 0

    def has_positions_xyz(self) -> bool:
        return "positions_xyz" in self.__dict__

    def has_orientations_quat_wxyz(self) -> bool:
        return "orientations_quat_wxyz" in self.__dict__

    def has_poses_se3(self) -> bool:
        return "poses_se3" in self.__dict__

    def _drop(self, *names: str) -> None:
        for name in names:
            self.__dict__.pop(name, None)

    def _register_derived(self, name: str) -> None:
        cls = type(self)
        if name not in cls._DERIVED_CACHES:
            cls._DERIVED_CACHES = (*cls._DERIVED_CACHES, name)

    def _drop_derived(self) -> None:
        self._drop(*self._DERIVED_CACHES)

    def replace_poses_se3(self, poses: list[np.ndarray]) -> None:
        """
        Replace SE(3) pose representation values. Resets the cache.
        :param poses: new pose matrices
        """
        self._drop("positions_xyz", "orientations_quat_wxyz")
        self.poses_se3 = poses
        self._drop_derived()

    def invalidate_xyz_quat(self) -> None:
        """
        Reset cache for position and quaternion representations,
        and derived values.
        """
        self._drop("positions_xyz", "orientations_quat_wxyz")
        self._drop_derived()

    def scale_translations(self, s: float) -> None:
        """
        Scale translations by a scaling factor. Resets the cache.
        :param s: scaling factor
        """
        if self.has_poses_se3():
            self.poses_se3 = [
                lie.se3(p[:3, :3], s * p[:3, 3]) for p in self.poses_se3
            ]
        if self.has_positions_xyz():
            self.positions_xyz = s * self.positions_xyz
        self._drop_derived()

    def reduce_to_ids(self, ids: typing.Sequence[int] | np.ndarray) -> None:
        """
        Keep only values at the specified indices. Resets the cache.
        :param ids: indices to keep
        """
        if self.has_positions_xyz():
            self.positions_xyz = self.positions_xyz[ids]
        if self.has_orientations_quat_wxyz():
            self.orientations_quat_wxyz = self.orientations_quat_wxyz[ids]
        if self.has_poses_se3():
            self.poses_se3 = [self.poses_se3[i] for i in ids]
        self._drop_derived()
