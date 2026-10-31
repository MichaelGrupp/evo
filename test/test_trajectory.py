#!/usr/bin/env python
"""
unit test for trajectory module
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
import copy

import numpy as np

import helpers
from evo.core import sync
from evo.core import trajectory
from evo.core import transformations as tr
from evo.core import lie_algebra as lie
from evo.core.trajectory import (
    PosePath3D,
    PoseTrajectory3D,
    StateTrajectory3D,
)
from evo.core.geometry import GeometryException
from evo.core.pose_cache import PoseCacheException


class TestPosePath3D(unittest.TestCase):
    def test_init_wrong_args(self):
        path = helpers.fake_path(10)
        # no args
        with self.assertRaises(PoseCacheException):
            trajectory.PosePath3D()
        # only quaternion
        with self.assertRaises(PoseCacheException):
            trajectory.PosePath3D(
                orientations_quat_wxyz=path.orientations_quat_wxyz
            )
        # only xyz
        with self.assertRaises(PoseCacheException):
            trajectory.PosePath3D(positions_xyz=path.positions_xyz)

    def test_init_correct(self):
        # only poses_se3
        path = helpers.fake_path(10)
        try:
            trajectory.PosePath3D(poses_se3=path.poses_se3)
        except trajectory.TrajectoryException:
            self.fail("unexpected init failure with only poses_se3")
        # xyz + quaternion
        try:
            trajectory.PosePath3D(
                path.positions_xyz, path.orientations_quat_wxyz
            )
        except trajectory.TrajectoryException:
            self.fail("unexpected init failure with xyz + quaternion")
        # all
        try:
            trajectory.PosePath3D(
                path.positions_xyz, path.orientations_quat_wxyz, path.poses_se3
            )
        except trajectory.TrajectoryException:
            self.fail(
                "unexpected init failure with xyz + quaternion + poses_se3"
            )

    def test_equals(self):
        path_1 = helpers.fake_path(10)
        path_1_copy = copy.deepcopy(path_1)
        path_2 = helpers.fake_path(15)
        self.assertTrue(path_1 == path_1_copy)
        self.assertFalse(path_1 == path_2)
        self.assertTrue(path_1 != path_2)
        self.assertFalse(path_1 != path_1_copy)

    def test_equals_equivalent_quaternion(self):
        """
        Checks that paths with equivalent quaternions (q = -q)
        are treated as equal.
        """
        path_1 = helpers.fake_path(10)
        path_2 = PosePath3D(
            path_1.positions_xyz, path_1.orientations_quat_wxyz * -1
        )
        self.assertFalse(
            np.allclose(
                path_1.orientations_quat_wxyz, path_2.orientations_quat_wxyz
            )
        )
        self.assertEqual(path_1, path_2)

    def test_reduce_to_ids(self):
        path = helpers.fake_path(10)
        path_reduced = copy.deepcopy(path)
        path_reduced.reduce_to_ids([0, 2])
        self.assertEqual(path_reduced.num_poses, 2)
        # direct connection from 0 to 2 in initial should be reduced path length
        len_initial_segment = np.linalg.norm(
            path.positions_xyz[2] - path.positions_xyz[0]
        )
        len_reduced = path_reduced.path_length
        self.assertAlmostEqual(len_initial_segment, len_reduced)

    def test_downsample(self):
        path = helpers.fake_path(100)
        path_downsampled = copy.deepcopy(path)
        path_downsampled.downsample(10)
        self.assertEqual(path_downsampled.num_poses, 10)
        self.assertTrue(
            np.equal(
                path.positions_xyz[0], path_downsampled.positions_xyz[0]
            ).all()
        )
        self.assertTrue(
            np.equal(
                path.positions_xyz[-1], path_downsampled.positions_xyz[-1]
            ).all()
        )

        # Downsampling to 1 should reduce to the start pose.
        path_downsampled.downsample(1)
        self.assertEqual(path_downsampled.num_poses, 1)
        self.assertTrue(
            np.equal(
                path.positions_xyz[0], path_downsampled.positions_xyz[0]
            ).all()
        )

    def test_transform(self):
        path = helpers.fake_path(10)
        path_transformed = copy.deepcopy(path)
        t = lie.random_se3()
        path_transformed.transform(t)
        # traj_transformed.transform(lie.se3_inverse(t))
        self.assertAlmostEqual(path_transformed.path_length, path.path_length)

    def test_transform_sim3(self):
        path = helpers.fake_path(10)
        path_transformed = copy.deepcopy(path)
        t = lie.sim3(r=lie.random_so3(), t=np.ones(3), s=1.234)
        path_transformed.transform(t)
        self.assertAlmostEqual(
            path_transformed.path_length, path.path_length * 1.234
        )

    def test_scale(self):
        path = helpers.fake_path(10)
        path_scaled = copy.deepcopy(path)
        s = 5.234
        path_scaled.scale(s)
        len_initial = path.path_length
        len_scaled = path_scaled.path_length
        self.assertAlmostEqual(len_initial * s, len_scaled)

    def test_check(self):
        self.assertTrue(helpers.fake_path(10).check()[0])
        path_wrong = helpers.fake_path(10)
        path_wrong._cache.orientations_quat_wxyz[1][1] = 666
        self.assertFalse(path_wrong.check()[0])

    def test_get_infos(self):
        helpers.fake_path(10).get_infos()

    def test_get_statistics(self):
        helpers.fake_path(10).get_statistics()

    def test_distances(self):
        path = helpers.fake_path(10)
        self.assertEqual(path.distances[0], 0.0)
        self.assertEqual(path.distances.size, path.num_poses)
        self.assertAlmostEqual(path.distances[-1], path.path_length)

    def test_projection(self):
        """
        Checks that projection into a plane modifies the poses correctly.
        """
        for plane, null_dim in zip(trajectory.Plane, [2, 1, 0]):
            path = helpers.fake_path(length=1)
            axis = np.zeros(3)
            axis[null_dim] = 1
            angle = path.get_orientations_euler("sxyz")[0][null_dim]

            path.project(plane)
            # Position value has to be zero outside of the plane.
            self.assertEqual(path.poses_se3[0][null_dim][3], 0)
            self.assertEqual(path.positions_xyz[0][null_dim], 0)
            # Rotation has to be angle around the nulled dimension's axis.
            self.assertTrue(
                np.allclose(
                    lie.so3_log(lie.so3_from_se3(path.poses_se3[0])),
                    angle * axis,
                )
            )
            # Quaternion has to be zero around the plane's basis vectors.
            quat_wxyz = path.orientations_quat_wxyz[0]
            if plane == trajectory.Plane.XY:
                self.assertAlmostEqual(quat_wxyz[1], 0)  # x
                self.assertAlmostEqual(quat_wxyz[2], 0)  # y
            elif plane == trajectory.Plane.XZ:
                self.assertAlmostEqual(quat_wxyz[1], 0)  # x
                self.assertAlmostEqual(quat_wxyz[3], 0)  # z
            elif plane == trajectory.Plane.YZ:
                self.assertAlmostEqual(quat_wxyz[2], 0)  # y
                self.assertAlmostEqual(quat_wxyz[3], 0)  # z

    def test_split_distance_gaps(self):
        """
        Checks if the path can be split correctly at a distance threshold.
        """
        path = PosePath3D(
            poses_se3=[
                lie.se3(r=np.eye(3), t=np.array([0, 0, 0])),
                lie.se3(r=np.eye(3), t=np.array([0, 0, 1])),
                lie.se3(r=np.eye(3), t=np.array([0, 0, 2])),
                lie.se3(r=np.eye(3), t=np.array([0, 0, 4])),
                lie.se3(r=np.eye(3), t=np.array([0, 0, 7])),
                lie.se3(r=np.eye(3), t=np.array([0, 0, 8])),
            ]
        )
        splits = path.split_distance_gaps(1.5)
        self.assertEqual(len(splits), 3)
        self.assertEqual(splits[0].num_poses, 3)
        self.assertEqual(splits[0].path_length, 2.0)
        self.assertEqual(splits[1].num_poses, 1)
        self.assertEqual(splits[1].path_length, 0.0)
        self.assertEqual(splits[2].num_poses, 2)
        self.assertEqual(splits[2].path_length, 1.0)
        splits = path.split_distance_gaps(999.0)
        self.assertEqual(len(splits), 1)
        self.assertEqual(splits[0].num_poses, path.num_poses)


class TestPoseTrajectory3D(unittest.TestCase):
    def test_equals(self):
        traj_1 = helpers.fake_trajectory(10, 1)
        traj_1_copy = copy.deepcopy(traj_1)
        traj_2 = helpers.fake_trajectory(15, 1)
        self.assertTrue(traj_1 == traj_1_copy)
        self.assertFalse(traj_1 == traj_2)
        self.assertTrue(traj_1 != traj_2)
        self.assertFalse(traj_1 != traj_1_copy)

    def test_reduce_to_ids(self):
        traj = helpers.fake_trajectory(10, 1)
        traj.reduce_to_ids([0, 2])
        self.assertEqual(traj.num_poses, 2)
        self.assertEqual(len(traj.timestamps), 2)

    def test_reduce_to_time_range(self):
        """
        Checks if a valid time-range reduces the trajectory correctly.
        """
        traj = helpers.fake_trajectory(10, 1)
        start = 1.2
        end = 7.8
        traj.reduce_to_time_range(start, end)
        self.assertEqual(traj.num_poses, 6)
        self.assertEqual(len(traj.timestamps), 6)
        self.assertGreaterEqual(traj.timestamps[0], start)
        self.assertLessEqual(traj.timestamps[-1], end)

    def test_reduce_to_empty_time_range(self):
        """
        A time-range that doesn't intersect should produce an empty trajectory.
        """
        traj = helpers.fake_trajectory(10, 1)
        start = 42
        end = 666
        traj.reduce_to_time_range(start, end)
        self.assertEqual(traj.num_poses, 0)
        self.assertEqual(len(traj.timestamps), 0)

    def test_check(self):
        self.assertTrue(helpers.fake_trajectory(10, 1).check()[0])
        wrong_traj = helpers.fake_trajectory(10, 1)
        wrong_traj.timestamps[0] = 666
        self.assertFalse(wrong_traj.check()[0])

    def test_get_infos(self):
        helpers.fake_trajectory(10, 1).get_infos()

    def test_get_statistics(self):
        helpers.fake_trajectory(10, 1).get_statistics()

    def test_split_time_gaps(self):
        """
        Checks if the trajectory can be split correctly with a time threshold.
        """
        traj = helpers.fake_trajectory(5, 1.0)
        traj.timestamps[2:5] += 10.0
        traj.timestamps[4] += 10.0
        splits = traj.split_time_gaps(5.0)
        self.assertEqual(len(splits), 3)
        self.assertEqual(splits[0].num_poses, 2)
        self.assertEqual(splits[1].num_poses, 2)
        self.assertEqual(splits[2].num_poses, 1)

    def test_split_speed_outliers(self):
        """
        Checks if the trajectory can be split correctly with a speed threshold.
        """
        traj = PoseTrajectory3D(
            timestamps=np.array([0, 1, 2]),
            poses_se3=[
                lie.se3(r=np.eye(3), t=np.array([0, 0, 0])),
                lie.se3(r=np.eye(3), t=np.array([0, 0, 1])),
                lie.se3(r=np.eye(3), t=np.array([0, 0, 4])),
            ],
        )
        splits = traj.split_speed_outliers(2.0)
        self.assertEqual(len(splits), 2)
        self.assertEqual(splits[0].num_poses, 2)
        self.assertEqual(splits[1].num_poses, 1)

    def _linear_trajectory(self, length=5):
        """
        Helper: a straight-line trajectory with constant identity
        orientation and unit timestamps, used for interpolation tests.
        """
        timestamps = np.arange(length, dtype=float)
        xyz = np.stack(
            [np.zeros(length), np.zeros(length), timestamps], axis=1
        )
        quat_wxyz = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (length, 1))
        return PoseTrajectory3D(xyz, quat_wxyz, timestamps)

    def test_name_is_preserved(self):
        """
        Checks that trajectories derived from a named one inherit its name.
        """
        traj = self._linear_trajectory(5)
        self.assertIsNone(traj.name)
        traj.name = "test"
        self.assertEqual(traj.interpolate(np.array([0.5])).name, "test")
        self.assertTrue(
            all(s.name == "test" for s in traj.split_time_gaps(0.5))
        )
        self.assertEqual(copy.deepcopy(traj).name, "test")

    def test_interpolate_midpoints(self):
        traj = self._linear_trajectory(5)
        stamps = np.array([0.5, 1.5, 2.5, 3.5])
        interp = traj.interpolate(stamps)
        self.assertEqual(interp.num_poses, 4)
        self.assertTrue(np.allclose(interp.timestamps, stamps))
        # Linear interpolation of z positions.
        self.assertTrue(np.allclose(interp.positions_xyz[:, 2], stamps))

    def test_interpolate_exact_timestamps(self):
        traj = self._linear_trajectory(5)
        stamps = np.array([0.0, 2.0, 4.0])
        interp = traj.interpolate(stamps)
        self.assertTrue(
            np.allclose(interp.positions_xyz, traj.positions_xyz[[0, 2, 4]])
        )
        self.assertTrue(
            np.allclose(
                interp.orientations_quat_wxyz,
                traj.orientations_quat_wxyz[[0, 2, 4]],
            )
        )

    def test_interpolate_clamps_out_of_range(self):
        traj = self._linear_trajectory(5)
        interp = traj.interpolate(np.array([-1.0, 5.0]))
        # Without extrapolation, out-of-range stamps clamp to first/last pose.
        self.assertTrue(
            np.allclose(interp.positions_xyz, traj.positions_xyz[[0, 4]])
        )

    def test_interpolate_extrapolates(self):
        traj = self._linear_trajectory(5)
        interp = traj.interpolate(np.array([5.0]), extrapolate=True)
        # Extrapolated z position follows the line: z = timestamp.
        self.assertAlmostEqual(interp.positions_xyz[0, 2], 5.0)

    def test_interpolate_preserves_unit_quaternions(self):
        timestamps = np.arange(5, dtype=float)
        quat_wxyz = np.array(
            [
                tr.quaternion_from_euler(0.0, 0.0, i * np.pi / 8.0)
                for i in range(5)
            ]
        )
        traj = PoseTrajectory3D(np.zeros((5, 3)), quat_wxyz, timestamps)
        interp = traj.interpolate(np.array([0.5, 2.5]))
        for q in interp.orientations_quat_wxyz:
            self.assertAlmostEqual(np.linalg.norm(q), 1.0, places=9)

    def test_sync_with_interpolation(self):
        """
        Checks the sync.SyncMethod.interpolation option of sync_with().
        """
        sparse = self._linear_trajectory(5)
        stamps = np.arange(0.0, 4.5, 0.5)
        dense = PoseTrajectory3D(
            np.stack(
                [np.zeros(len(stamps)), np.zeros(len(stamps)), stamps], axis=1
            ),
            np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (len(stamps), 1)),
            stamps,
        )
        synced_sparse, synced_dense = sparse.sync_with(
            dense, sync_method=sync.SyncMethod.interpolation
        )
        # The denser trajectory is resampled at the timestamps of the sparser
        # one, which is kept as it is.
        self.assertEqual(synced_sparse.num_poses, sparse.num_poses)
        self.assertEqual(synced_dense.num_poses, sparse.num_poses)
        self.assertTrue(
            np.allclose(synced_dense.timestamps, sparse.timestamps)
        )
        self.assertTrue(
            np.allclose(synced_dense.positions_xyz, sparse.positions_xyz)
        )

    def test_interpolate_single_pose_raises(self):
        traj = self._linear_trajectory(5)
        traj.reduce_to_ids([0])
        with self.assertRaises(trajectory.TrajectoryException):
            traj.interpolate(np.array([0.5]))


class TestStateTrajectory3D(unittest.TestCase):
    def test_init_missing_velocities(self):
        with self.assertRaises(trajectory.TrajectoryException):
            StateTrajectory3D(
                poses_se3=helpers.random_se3_list(3), timestamps=[0, 1, 2]
            )

    def test_init_wrong_velocity_shape(self):
        for bad_shape in [(7, 3), (3, 2), (3,), (3, 3, 1)]:
            with self.subTest(shape=bad_shape):
                with self.assertRaises(trajectory.TrajectoryException):
                    StateTrajectory3D(
                        poses_se3=helpers.random_se3_list(3),
                        velocities_xyz=np.zeros(bad_shape),
                        timestamps=[0, 1, 2],
                    )

    def test_init_positional_args(self):
        """
        Positional order is (positions, orientations, velocities, timestamps).
        """
        base = helpers.fake_trajectory(4, 1)
        velocities = np.ones((4, 3))
        traj = StateTrajectory3D(
            base.positions_xyz,
            base.orientations_quat_wxyz,
            velocities,
            base.timestamps,
        )
        np.testing.assert_array_equal(traj.velocities_xyz, velocities)
        np.testing.assert_array_equal(traj.timestamps, base.timestamps)
        np.testing.assert_allclose(traj.positions_xyz, base.positions_xyz)

    def test_equals(self):
        traj_1 = helpers.fake_state_trajectory(10, 1)
        traj_1_copy = copy.deepcopy(traj_1)
        traj_2 = helpers.fake_state_trajectory(15, 1)
        self.assertTrue(traj_1 == traj_1_copy)
        self.assertFalse(traj_1 != traj_1_copy)
        self.assertFalse(traj_1 == traj_2)
        self.assertTrue(traj_1 != traj_2)

    def test_equals_different_velocities(self):
        traj_1 = helpers.fake_state_trajectory(10, 1)
        traj_2 = copy.deepcopy(traj_1)
        traj_2.velocities_xyz[3] += 1.0
        self.assertFalse(traj_1 == traj_2)
        self.assertTrue(traj_1 != traj_2)

    def test_not_equal_to_pose_trajectory(self):
        """
        A PoseTrajectory3D with the same poses and timestamps has no
        velocities, so it must not compare equal, in either direction.
        """
        traj_state = helpers.fake_state_trajectory(5, 1)
        traj_pose = PoseTrajectory3D(
            poses_se3=traj_state.poses_se3, timestamps=traj_state.timestamps
        )
        self.assertFalse(traj_state == traj_pose)
        self.assertFalse(traj_pose == traj_state)
        self.assertTrue(traj_state != traj_pose)
        self.assertTrue(traj_pose != traj_state)

    def test_check(self):
        traj = helpers.fake_state_trajectory(10, 1)
        valid, details = traj.check()
        self.assertTrue(valid)
        self.assertEqual(details["velocities"], "ok")

    def test_check_wrong_velocities(self):
        """
        The constructor validates the velocities, but they can still be
        replaced afterwards, which check() has to catch.
        """
        for bad_shape in [(7, 3), (10, 2)]:
            with self.subTest(shape=bad_shape):
                traj = helpers.fake_state_trajectory(10, 1)
                traj.velocities_xyz = np.zeros(bad_shape)
                valid, details = traj.check()
                self.assertFalse(valid)
                self.assertNotEqual(details["velocities"], "ok")

    def test_check_still_validates_timestamps(self):
        traj = helpers.fake_state_trajectory(10, 1)
        traj.timestamps[0] = 666
        self.assertFalse(traj.check()[0])

    @staticmethod
    def _constant_velocity_trajectory(num_poses=10, dt=0.5):
        """
        Straight-line motion, so the velocities must always match the
        finite differences of the positions.
        """
        velocity = np.array([1.0, -2.0, 0.5])
        stamps = np.arange(num_poses) * dt
        xyz = np.array([0.3, 0.1, -0.2]) + stamps[:, None] * velocity
        quats = np.tile([1.0, 0.0, 0.0, 0.0], (num_poses, 1))
        return StateTrajectory3D(
            xyz, quats, np.tile(velocity, (num_poses, 1)), stamps
        )

    def assert_velocities_match_positions(self, traj):
        finite_diff = (
            np.diff(traj.positions_xyz, axis=0)
            / np.diff(traj.timestamps)[:, None]
        )
        np.testing.assert_allclose(traj.velocities_xyz[:-1], finite_diff)

    def test_transform_rotates_velocities(self):
        traj = helpers.fake_state_trajectory(5, 1)
        original = copy.deepcopy(traj)
        r = lie.so3_exp(np.array([0.0, 0.0, np.pi / 2]))
        traj.transform(lie.se3(r, np.array([5.0, -3.0, 1.0])))
        # Rotation of 90° around z: (x, y, z) -> (-y, x, z).
        expected = np.column_stack(
            [
                -original.velocities_xyz[:, 1],
                original.velocities_xyz[:, 0],
                original.velocities_xyz[:, 2],
            ]
        )
        np.testing.assert_allclose(traj.velocities_xyz, expected, atol=1e-12)

    def test_transform_sim3_keeps_velocities_consistent(self):
        traj = self._constant_velocity_trajectory()
        traj.transform(lie.sim3(lie.random_so3(), np.array([1, 2, 3]), 2.5))
        self.assert_velocities_match_positions(traj)

    def test_transform_right_mul_keeps_velocities(self):
        traj = helpers.fake_state_trajectory(5, 1)
        original = copy.deepcopy(traj)
        traj.transform(lie.random_se3(), right_mul=True)
        np.testing.assert_array_equal(
            traj.velocities_xyz, original.velocities_xyz
        )

    def test_scale(self):
        traj = self._constant_velocity_trajectory()
        traj.scale(3.0)
        np.testing.assert_allclose(traj.velocities_xyz[0], [3.0, -6.0, 1.5])
        self.assert_velocities_match_positions(traj)

    def test_align_with_scale(self):
        """
        Aligning a rotated, translated and scaled copy back onto the
        reference must also bring the velocities back.
        """
        traj_ref = self._constant_velocity_trajectory()
        # Positions on a straight line are degenerate for Umeyama,
        # so bend the path a little (velocities don't need to match here).
        traj_ref = StateTrajectory3D(
            traj_ref.positions_xyz + np.random.rand(traj_ref.num_poses, 3),
            traj_ref.orientations_quat_wxyz,
            traj_ref.velocities_xyz,
            traj_ref.timestamps,
        )
        sim3 = lie.sim3(lie.random_so3(), np.array([1, 2, 3]), 0.4)
        traj_est = copy.deepcopy(traj_ref)
        traj_est.transform(sim3)
        # Set the expected misaligned velocities by hand, so this test
        # doesn't depend on transform() being correct.
        traj_est.velocities_xyz = traj_ref.velocities_xyz @ sim3[:3, :3].T
        traj_est.align(traj_ref, correct_scale=True)
        np.testing.assert_allclose(
            traj_est.velocities_xyz, traj_ref.velocities_xyz, atol=1e-9
        )

    def test_align_origin(self):
        traj_ref = self._constant_velocity_trajectory()
        se3 = lie.random_se3()
        traj_est = copy.deepcopy(traj_ref)
        traj_est.transform(se3)
        traj_est.velocities_xyz = traj_ref.velocities_xyz @ se3[:3, :3].T
        traj_est.align_origin(traj_ref)
        np.testing.assert_allclose(
            traj_est.velocities_xyz, traj_ref.velocities_xyz, atol=1e-9
        )

    def test_projection(self):
        for plane, null_dim in zip(trajectory.Plane, [2, 1, 0]):
            with self.subTest(plane=plane):
                traj = helpers.fake_state_trajectory(5, 1)
                original = copy.deepcopy(traj)
                traj.project(plane)
                np.testing.assert_array_equal(
                    traj.velocities_xyz[:, null_dim], 0
                )
                kept_dims = [d for d in range(3) if d != null_dim]
                np.testing.assert_array_equal(
                    traj.velocities_xyz[:, kept_dims],
                    original.velocities_xyz[:, kept_dims],
                )

    def test_projection_twice_keeps_velocities(self):
        traj = helpers.fake_state_trajectory(5, 1)
        traj.project(trajectory.Plane.XY)
        projected = traj.velocities_xyz.copy()
        with self.assertRaises(trajectory.TrajectoryException):
            traj.project(trajectory.Plane.XZ)
        np.testing.assert_array_equal(traj.velocities_xyz, projected)

    def test_interpolate(self):
        # fake_state_trajectory velocities are [t, 10t, 100t] at time t.
        traj = helpers.fake_state_trajectory(10, 1)
        interpolated = traj.interpolate([0.0, 2.5, 8.75])
        self.assertIsInstance(interpolated, StateTrajectory3D)
        np.testing.assert_allclose(
            interpolated.velocities_xyz,
            [[0, 0, 0], [2.5, 25, 250], [8.75, 87.5, 875]],
        )
        self.assertEqual(interpolated.name, traj.name)

    def test_interpolate_scalar_timestamp(self):
        traj = helpers.fake_state_trajectory(10, 1)
        interpolated = traj.interpolate(4.5)
        np.testing.assert_allclose(
            interpolated.velocities_xyz, [[4.5, 45, 450]]
        )

    def test_interpolate_clamps_out_of_range(self):
        traj = helpers.fake_state_trajectory(10, 1)
        interpolated = traj.interpolate([-5.0, 20.0])
        np.testing.assert_allclose(
            interpolated.velocities_xyz,
            [traj.velocities_xyz[0], traj.velocities_xyz[-1]],
        )

    def test_interpolate_extrapolates(self):
        traj = helpers.fake_state_trajectory(10, 1)
        interpolated = traj.interpolate([-1.0, 12.0], extrapolate=True)
        np.testing.assert_allclose(
            interpolated.velocities_xyz,
            [[-1, -10, -100], [12, 120, 1200]],
        )

    def test_sync_with_interpolation(self):
        """
        Interpolation sync resamples the longer trajectory, which must
        keep its velocities.
        """
        traj_state = helpers.fake_state_trajectory(10, 1)
        traj_other = helpers.fake_trajectory(4, 2, start_time=0.5)
        _, traj_state_synced = sync.associate_trajectories(
            traj_other,
            traj_state,
            sync_method=sync.SyncMethod.interpolation,
            max_diff=0.6,
        )
        self.assertIsInstance(traj_state_synced, StateTrajectory3D)
        np.testing.assert_allclose(
            traj_state_synced.velocities_xyz[:, 0],
            traj_state_synced.timestamps,
        )

    def assert_segments_keep_velocities(self, segments, original):
        for segment in segments:
            self.assertIsInstance(segment, StateTrajectory3D)
            self.assertTrue(segment.check()[0])
            self.assertEqual(segment.name, original.name)
        np.testing.assert_array_equal(
            np.concatenate([s.velocities_xyz for s in segments]),
            original.velocities_xyz,
        )

    def test_split_time_gaps(self):
        traj = helpers.fake_state_trajectory(5, 1.0)
        traj.timestamps[2:] += 10.0
        segments = traj.split_time_gaps(5.0)
        self.assertEqual([s.num_poses for s in segments], [2, 3])
        self.assert_segments_keep_velocities(segments, traj)

    def test_split_distance_gaps(self):
        traj = self._constant_velocity_trajectory(num_poses=6)
        poses = [p.copy() for p in traj.poses_se3]
        for pose in poses[3:]:
            pose[:3, 3] += 100.0
        traj = StateTrajectory3D(
            velocities_xyz=traj.velocities_xyz,
            timestamps=traj.timestamps,
            poses_se3=poses,
        )
        segments = traj.split_distance_gaps(50.0)
        self.assertEqual([s.num_poses for s in segments], [3, 3])
        self.assert_segments_keep_velocities(segments, traj)

    def test_split_speed_outliers(self):
        traj = self._constant_velocity_trajectory(num_poses=6)
        poses = [p.copy() for p in traj.poses_se3]
        for pose in poses[4:]:
            pose[:3, 3] += 100.0
        traj = StateTrajectory3D(
            velocities_xyz=traj.velocities_xyz,
            timestamps=traj.timestamps,
            poses_se3=poses,
        )
        segments = traj.split_speed_outliers(v_max=50.0)
        self.assertEqual([s.num_poses for s in segments], [4, 2])
        self.assert_segments_keep_velocities(segments, traj)

    def test_merge(self):
        traj_1 = helpers.fake_state_trajectory(5, 2.0)  # t = 0, 2, ..., 8
        traj_2 = helpers.fake_state_trajectory(5, 2.0, start_time=1.0)
        traj_2.velocities_xyz += 1000.0  # tell the two apart
        merged = trajectory.merge([traj_1, traj_2])
        self.assertIsInstance(merged, StateTrajectory3D)
        self.assertEqual(merged.num_poses, 10)
        self.assertTrue(merged.check()[0])
        # Sorted by time, so the rows have to alternate between the inputs.
        np.testing.assert_array_equal(
            merged.velocities_xyz[0::2], traj_1.velocities_xyz
        )
        np.testing.assert_array_equal(
            merged.velocities_xyz[1::2], traj_2.velocities_xyz
        )

    def test_merge_with_pose_trajectory(self):
        """
        Only some inputs have velocities, so the result can't have them.
        """
        merged = trajectory.merge(
            [
                helpers.fake_state_trajectory(5, 2.0),
                helpers.fake_trajectory(5, 2.0, start_time=1.0),
            ]
        )
        self.assertIs(type(merged), PoseTrajectory3D)
        self.assertEqual(merged.num_poses, 10)

    def test_get_infos(self):
        traj = helpers.fake_state_trajectory(10, 1)
        infos = traj.get_infos()
        np.testing.assert_array_equal(
            infos["vel_start (m/s)"], traj.velocities_xyz[0]
        )
        np.testing.assert_array_equal(
            infos["vel_end (m/s)"], traj.velocities_xyz[-1]
        )
        # The PoseTrajectory3D infos are still there.
        self.assertIn("duration (s)", infos)

    def test_get_statistics(self):
        traj = self._constant_velocity_trajectory()
        stats = traj.get_statistics()
        speed = np.linalg.norm([1.0, -2.0, 0.5])
        for key in ("max", "min", "avg"):
            self.assertAlmostEqual(stats[f"vel_norm_{key} (m/s)"], speed)
            # On a straight line, the speed from the positions agrees.
            self.assertAlmostEqual(stats[f"v_{key} (m/s)"], speed)

    def test_get_statistics_single_pose(self):
        traj = helpers.fake_state_trajectory(10, 1)
        traj.reduce_to_ids([0])
        self.assertEqual(traj.get_statistics(), {})

    def test_init_velocities_from_list(self):
        traj = StateTrajectory3D(
            poses_se3=helpers.random_se3_list(2),
            velocities_xyz=[[1, 2, 3], [4, 5, 6]],
            timestamps=[0, 1],
        )
        self.assertEqual(traj.velocities_xyz.shape, (2, 3))
        self.assertEqual(traj.velocities_xyz.dtype, float)

    def test_reduce_to_ids(self):
        traj = helpers.fake_state_trajectory(10, 1)
        original = copy.deepcopy(traj)
        ids = [0, 2, 7]
        traj.reduce_to_ids(ids)
        self.assertIsInstance(traj, StateTrajectory3D)
        self.assertEqual(traj.num_poses, 3)
        self.assertEqual(traj.velocities_xyz.shape, (3, 3))
        np.testing.assert_array_equal(
            traj.velocities_xyz, original.velocities_xyz[ids]
        )
        np.testing.assert_array_equal(
            traj.timestamps, original.timestamps[ids]
        )
        np.testing.assert_allclose(
            traj.positions_xyz, original.positions_xyz[ids]
        )

    def test_reduce_to_ids_numpy_array(self):
        traj = helpers.fake_state_trajectory(10, 1)
        original = copy.deepcopy(traj)
        ids = np.array([1, 3, 5])
        traj.reduce_to_ids(ids)
        np.testing.assert_array_equal(
            traj.velocities_xyz, original.velocities_xyz[ids]
        )

    def test_reduce_to_time_range(self):
        """
        reduce_to_time_range goes through reduce_to_ids, so the velocities
        have to stay aligned with the timestamps.
        """
        traj = helpers.fake_state_trajectory(10, 1)
        traj.reduce_to_time_range(1.2, 7.8)
        self.assertEqual(traj.num_poses, 6)
        self.assertEqual(len(traj.velocities_xyz), 6)
        # Velocity row i of the fake trajectory belongs to timestamp i.
        np.testing.assert_array_equal(
            traj.velocities_xyz[:, 0], traj.timestamps
        )

    def test_reduce_to_empty_time_range(self):
        traj = helpers.fake_state_trajectory(10, 1)
        traj.reduce_to_time_range(42, 666)
        self.assertEqual(traj.num_poses, 0)
        self.assertEqual(traj.velocities_xyz.shape, (0, 3))

    def test_downsample(self):
        traj = helpers.fake_state_trajectory(10, 1)
        traj.downsample(4)
        self.assertEqual(traj.num_poses, 4)
        np.testing.assert_array_equal(
            traj.velocities_xyz[:, 0], traj.timestamps
        )

    def test_sync_keeps_velocities_aligned(self):
        """
        Synchronization makes reduced copies with reduce_to_ids.
        """
        traj_state = helpers.fake_state_trajectory(10, 1)
        traj_other = helpers.fake_trajectory(5, 2)
        traj_state_synced, _ = sync.associate_trajectories(
            traj_state, traj_other
        )
        self.assertIsInstance(traj_state_synced, StateTrajectory3D)
        self.assertEqual(traj_state_synced.num_poses, 5)
        np.testing.assert_array_equal(
            traj_state_synced.velocities_xyz[:, 0],
            traj_state_synced.timestamps,
        )
        # The input trajectory must not be modified.
        self.assertEqual(len(traj_state.velocities_xyz), 10)


class TestTrajectoryAlignment(unittest.TestCase):
    def test_se3_alignment(self):
        traj = helpers.fake_trajectory(1000, 1)
        traj_transformed = copy.deepcopy(traj)
        traj_transformed.transform(lie.random_se3())
        self.assertNotEqual(traj, traj_transformed)
        traj_transformed.align(traj)
        self.assertEqual(traj_transformed, traj)

    def test_sim3_alignment(self):
        traj = helpers.fake_trajectory(1000, 1)
        traj_transformed = copy.deepcopy(traj)
        traj_transformed.transform(lie.random_se3())
        traj_transformed.scale(1.234)
        self.assertNotEqual(traj, traj_transformed)
        traj_transformed.align(traj, correct_scale=True)
        self.assertEqual(traj_transformed, traj)

    def test_scale_correction(self):
        traj = helpers.fake_trajectory(1000, 1)
        traj_transformed = copy.deepcopy(traj)
        traj_transformed.scale(1.234)
        self.assertNotEqual(traj, traj_transformed)
        traj_transformed.align(traj, correct_only_scale=True)
        self.assertEqual(traj_transformed, traj)

    def test_origin_alignment(self):
        traj_1 = helpers.fake_trajectory(1000, 1)
        traj_2 = helpers.fake_trajectory(1000, 1)
        self.assertFalse(np.allclose(traj_1.poses_se3[0], traj_2.poses_se3[0]))
        traj_2.align_origin(traj_1)
        self.assertTrue(np.allclose(traj_1.poses_se3[0], traj_2.poses_se3[0]))

    def test_alignment_degenerate_case(self):
        length = 100
        poses = [lie.random_se3()] * length
        traj_1 = PoseTrajectory3D(
            poses_se3=poses, timestamps=helpers.fake_timestamps(length, 1, 0.0)
        )
        traj_2 = copy.deepcopy(traj_1)
        traj_2.transform(lie.random_se3())
        traj_2.scale(1.234)
        self.assertNotEqual(traj_1, traj_2)

        with self.assertRaises(GeometryException):
            traj_1.align(traj_2)

        with self.assertRaises(GeometryException):
            traj_1.align(traj_2, correct_scale=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
