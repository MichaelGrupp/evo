import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from evo.core.trajectory import calc_angular_speed, TrajectoryException


@pytest.mark.parametrize("degrees", [False, True])
@pytest.mark.parametrize("angles", [(0, 90), (179, -179), (90, 0)])
def test_angular_speed_is_shortest_relative_angle(angles, degrees):
    poses = [np.eye(4), np.eye(4)]
    for pose, angle in zip(poses, angles):
        pose[:3, :3] = Rotation.from_euler(
            "z", angle, degrees=True
        ).as_matrix()
    expected = (
        Rotation.from_matrix(poses[0][:3, :3]).inv()
        * Rotation.from_matrix(poses[1][:3, :3])
    ).magnitude() / 2
    if degrees:
        expected = np.rad2deg(expected)
    actual = calc_angular_speed(*poses, 1.0, 3.0, degrees=degrees)
    assert isinstance(actual, float)
    assert actual == pytest.approx(expected)


def test_angular_speed_ignores_common_world_rotation():
    first = Rotation.from_euler("xyz", [0.7, -0.4, 1.2])
    relative = Rotation.from_euler("xyz", [-0.2, 0.6, 0.1])
    poses = [np.eye(4), np.eye(4)]
    poses[0][:3, :3] = first.as_matrix()
    poses[1][:3, :3] = (first * relative).as_matrix()
    assert calc_angular_speed(*poses, 0.0, 1.0) == pytest.approx(
        relative.magnitude()
    )


@pytest.mark.parametrize("times", [(1, 1), (2, 1)])
def test_angular_speed_rejects_nonincreasing_time(times):
    with pytest.raises(TrajectoryException):
        calc_angular_speed(np.eye(4), np.eye(4), *times)
