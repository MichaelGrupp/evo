#!/usr/bin/env python
"""
unit test for the metrics module
author: Varun Agrawal

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
import unittest

import numpy as np

import helpers
from evo.core import lie_algebra as lie
from evo.core import metrics
from evo.core.trajectory import StateTrajectory3D
from evo.core.units import Unit


def state_trajectory(poses_se3, velocities_xyz):
    n = len(poses_se3)
    return StateTrajectory3D(
        poses_se3=poses_se3,
        velocities_xyz=np.asarray(velocities_xyz, dtype=float),
        timestamps=helpers.fake_timestamps(n, 0.1),
    )


def paper_ase_errors(traj_ref, traj_est):
    """
    Reference implementation of Eq. 9 & 10 in https://arxiv.org/abs/2401.17463
    using plain matrix inversion: E_i = Q_i^-1 * P_i, error_i = ||E_i - I||_F
    with Q the ground truth and P the (already aligned) estimate.
    """
    errors = []
    for q, v_q, p, v_p in zip(
        traj_ref.poses_se3,
        traj_ref.velocities_xyz,
        traj_est.poses_se3,
        traj_est.velocities_xyz,
    ):
        Q = lie.se23(q[:3, :3], q[:3, 3], v_q)
        P = lie.se23(p[:3, :3], p[:3, 3], v_p)
        E = np.linalg.inv(Q) @ P
        errors.append(np.linalg.norm(E - np.eye(5), ord="fro"))
    return np.array(errors)


class TestASE(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        self.traj_ref = helpers.fake_state_trajectory(50, 0.1)
        self.traj_est = helpers.fake_state_trajectory(50, 0.1)

    def test_identical_trajectories_have_zero_error(self):
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, copy.deepcopy(self.traj_ref)))
        self.assertEqual(len(ase.error), self.traj_ref.num_poses)
        self.assertTrue(np.allclose(ase.error, 0.0))
        for E in ase.E:
            self.assertTrue(np.allclose(E, np.eye(5)))

    def test_matches_paper_definition(self):
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, self.traj_est))
        expected = paper_ase_errors(self.traj_ref, self.traj_est)
        self.assertTrue(np.allclose(ase.error, expected))

    def test_rmse_matches_paper_definition(self):
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, self.traj_est))
        expected = paper_ase_errors(self.traj_ref, self.traj_est)
        expected_rmse = np.sqrt(np.mean(np.square(expected)))
        self.assertAlmostEqual(
            ase.get_statistic(metrics.StatisticsType.rmse), expected_rmse
        )

    def test_position_and_velocity_offset(self):
        # Same rotations, positions and velocities shifted by world-frame
        # offsets: ||E - I||_F = sqrt(|dp|^2 + |dv|^2) for every pose.
        dp = np.array([0.1, -0.2, 0.3])
        dv = np.array([1.0, 0.5, -2.0])
        poses_est = []
        for p in self.traj_ref.poses_se3:
            p_est = p.copy()
            p_est[:3, 3] += dp
            poses_est.append(p_est)
        traj_est = state_trajectory(
            poses_est, self.traj_ref.velocities_xyz + dv
        )
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, traj_est))
        expected = np.sqrt(np.sum(dp**2) + np.sum(dv**2))
        self.assertTrue(np.allclose(ase.error, expected))

    def test_rotation_offset(self):
        # Pure rotation error of angle theta at the origin with zero velocity:
        # ||R - I||_F = 2 * sqrt(2) * |sin(theta / 2)|.
        theta = 0.3
        r = lie.so3_exp(np.array([0.0, 0.0, theta]))
        traj_ref = state_trajectory([np.eye(4)], np.zeros((1, 3)))
        traj_est = state_trajectory([lie.se3(r)], np.zeros((1, 3)))
        ase = metrics.ASE()
        ase.process_data((traj_ref, traj_est))
        expected = 2 * np.sqrt(2) * abs(np.sin(theta / 2))
        self.assertAlmostEqual(ase.error[0], expected)

    def test_velocity_error_is_detected(self):
        # Poses are identical, so APE on the full transformation is zero,
        # but ASE must still see the velocity error.
        traj_est = state_trajectory(
            self.traj_ref.poses_se3, self.traj_ref.velocities_xyz + 1.0
        )
        ape = metrics.APE(metrics.PoseRelation.full_transformation)
        ape.process_data((self.traj_ref, traj_est))
        self.assertTrue(np.allclose(ape.error, 0.0))

        ase = metrics.ASE()
        ase.process_data((self.traj_ref, traj_est))
        self.assertTrue(np.allclose(ase.error, np.sqrt(3.0)))

    def test_reduces_to_ape_without_velocities(self):
        zero_v = np.zeros((self.traj_ref.num_poses, 3))
        traj_ref = state_trajectory(self.traj_ref.poses_se3, zero_v)
        traj_est = state_trajectory(self.traj_est.poses_se3, zero_v)
        ape = metrics.APE(metrics.PoseRelation.full_transformation)
        ape.process_data((traj_ref, traj_est))
        ase = metrics.ASE()
        ase.process_data((traj_ref, traj_est))
        self.assertTrue(np.allclose(ase.error, ape.error))

    def test_invariant_to_common_world_transform(self):
        # The metric is left-invariant: moving both trajectories by the same
        # SE(3) transform (which also rotates the world-frame velocities)
        # must not change the error.
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, self.traj_est))
        error_before = ase.error.copy()

        t = lie.random_se3()
        traj_ref = copy.deepcopy(self.traj_ref)
        traj_est = copy.deepcopy(self.traj_est)
        traj_ref.transform(t)
        traj_est.transform(t)
        ase.process_data((traj_ref, traj_est))
        self.assertTrue(np.allclose(ase.error, error_before))

    def test_zero_error_after_sim3_alignment(self):
        # The estimate is the reference seen through a Sim(3) transform.
        # After Umeyama alignment with scale (as in the paper, Sec. IV-C),
        # the error must vanish, including the velocity part.
        traj_est = copy.deepcopy(self.traj_ref)
        traj_est.scale(0.5)
        traj_est.transform(lie.random_se3())
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, traj_est))
        self.assertGreater(ase.get_statistic(metrics.StatisticsType.max), 0.1)

        traj_est.align(self.traj_ref, correct_scale=True)
        ase.process_data((self.traj_ref, traj_est))
        self.assertTrue(np.allclose(ase.error, 0.0, atol=1e-6))

    def test_result(self):
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, self.traj_est))
        result = ase.get_result("ref", "est")
        self.assertEqual(ase.unit, Unit.none)
        self.assertEqual(result.info["label"], "ASE (unit-less)")
        self.assertEqual(result.info["title"], str(ase))
        self.assertTrue(
            np.array_equal(result.np_arrays["error_array"], ase.error)
        )
        for stat in metrics.StatisticsType:
            self.assertIn(stat.value, result.stats)

    def test_unit_conversion_not_supported(self):
        ase = metrics.ASE()
        ase.process_data((self.traj_ref, self.traj_est))
        with self.assertRaises(metrics.MetricsException):
            ase.change_unit(Unit.meters)

    def test_mismatched_lengths(self):
        traj_est = helpers.fake_state_trajectory(10, 0.1)
        with self.assertRaises(metrics.MetricsException):
            metrics.ASE().process_data((self.traj_ref, traj_est))

    def test_wrong_data_tuple(self):
        with self.assertRaises(metrics.MetricsException):
            metrics.ASE().process_data((self.traj_ref,))

    def test_requires_state_trajectories(self):
        traj = helpers.fake_trajectory(50, 0.1)
        with self.assertRaises(metrics.MetricsException):
            metrics.ASE().process_data((traj, self.traj_est))
        with self.assertRaises(metrics.MetricsException):
            metrics.ASE().process_data((self.traj_ref, traj))


if __name__ == "__main__":
    unittest.main(verbosity=2)
