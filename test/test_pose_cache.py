#!/usr/bin/env python
"""
unit tests for the PoseCache helper
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

import unittest

import numpy as np

from evo.core.pose_cache import PoseCache


def _make_poses(n=3):
    """n identity-rotation SE(3) poses with translation [i, 0, 0]."""
    poses = []
    for i in range(n):
        p = np.eye(4)
        p[:3, 3] = [i, 0, 0]
        poses.append(p)
    return poses


class TestPoseCacheLazyConversion(unittest.TestCase):
    def test_xyz_derived_from_poses(self):
        cache = PoseCache(poses_se3=_make_poses())
        np.testing.assert_array_equal(
            cache.positions_xyz, [[0, 0, 0], [1, 0, 0], [2, 0, 0]]
        )

    def test_poses_derived_from_xyz_quat(self):
        xyz = np.array([[0.0, 0, 0], [1, 0, 0], [2, 0, 0]])
        quat = np.tile([1.0, 0.0, 0.0, 0.0], (3, 1))
        cache = PoseCache(positions_xyz=xyz, orientations_quat_wxyz=quat)
        derived_xyz = np.array([p[:3, 3] for p in cache.poses_se3])
        np.testing.assert_allclose(derived_xyz, xyz)
        for p in cache.poses_se3:
            np.testing.assert_allclose(p[:3, :3], np.eye(3), atol=1e-12)


class TestPoseCacheHasFlags(unittest.TestCase):
    def test_only_what_was_set(self):
        cache = PoseCache(poses_se3=_make_poses())
        self.assertTrue(cache.has_poses_se3())
        self.assertFalse(cache.has_positions_xyz())
        self.assertFalse(cache.has_orientations_quat_wxyz())

    def test_flips_after_lazy_access(self):
        cache = PoseCache(poses_se3=_make_poses())
        _ = cache.positions_xyz
        self.assertTrue(cache.has_positions_xyz())
        self.assertFalse(cache.has_orientations_quat_wxyz())


class TestPoseCacheMutators(unittest.TestCase):
    def test_replace_poses_drops_xyz_quat(self):
        cache = PoseCache(poses_se3=_make_poses())
        _ = cache.positions_xyz
        _ = cache.orientations_quat_wxyz
        cache.replace_poses_se3(_make_poses(5))
        self.assertEqual(cache.num_poses, 5)
        self.assertFalse(cache.has_positions_xyz())
        self.assertFalse(cache.has_orientations_quat_wxyz())
        # Re-derives correctly from new poses.
        np.testing.assert_array_equal(
            cache.positions_xyz[:, 0], [0, 1, 2, 3, 4]
        )

    def test_invalidate_xyz_quat_idempotent(self):
        cache = PoseCache(poses_se3=_make_poses())
        _ = cache.positions_xyz
        cache.invalidate_xyz_quat()
        cache.invalidate_xyz_quat()  # second call must not raise
        self.assertFalse(cache.has_positions_xyz())

    def test_scale_only_touches_existing_reps(self):
        cache = PoseCache(poses_se3=_make_poses())
        cache.scale_translations(2.0)
        # xyz was not materialized; scaling shouldn't fabricate it.
        self.assertFalse(cache.has_positions_xyz())
        self.assertEqual(cache.poses_se3[1][0, 3], 2.0)

    def test_reduce_to_ids_only_touches_existing_reps(self):
        cache = PoseCache(poses_se3=_make_poses(5))
        _ = cache.positions_xyz  # materialize xyz only
        cache.reduce_to_ids([0, 2, 4])
        self.assertEqual(cache.num_poses, 3)
        np.testing.assert_array_equal(cache.positions_xyz[:, 0], [0, 2, 4])
        self.assertFalse(cache.has_orientations_quat_wxyz())

    def test_derived_cleared_after_mutation(self):
        cache = PoseCache(poses_se3=_make_poses())
        _ = cache.distances
        self.assertIn("distances", cache.__dict__)
        cache.scale_translations(2.0)
        self.assertNotIn("distances", cache.__dict__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
