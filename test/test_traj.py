"""
Regression tests for the trajectory CLI.

This file is part of evo (github.com/MichaelGrupp/evo).

evo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

evo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with evo. If not, see <http://www.gnu.org/licenses/>.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from evo.core import lie_algebra as lie
from evo.core import transformations as tr
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface


@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
@pytest.mark.parametrize("file_format", ["json", "txt", "npy"])
@pytest.mark.parametrize("right_mul", [False, True])
@pytest.mark.parametrize("invert", [False, True])
def test_transform(
    tmp_path: Path,
    scale: float,
    file_format: str,
    right_mul: bool,
    invert: bool,
) -> None:
    positions = np.array([[1, 2, 3], [2, 2, 3], [2, 3, 3]])
    quaternions = np.array(
        [tr.quaternion_from_euler(0.2 * i, 0.1 * i, 0.3 * i) for i in range(3)]
    )
    trajectory = PoseTrajectory3D(
        positions_xyz=positions,
        orientations_quat_wxyz=quaternions,
        timestamps=np.array([0.0, 1.0, 2.0]),
    )
    trajectory_path = tmp_path / "trajectory.txt"
    file_interface.write_tum_trajectory_file(trajectory_path, trajectory)

    quaternion = tr.quaternion_from_euler(0, 0, np.pi / 2)
    rotation = tr.quaternion_matrix(quaternion)[:3, :3]
    translation = np.array([10.0, -4.0, 2.0])
    transform = lie.sim3(rotation, translation, scale)
    transform_path = tmp_path / f"transform.{file_format}"
    if file_format == "json":
        data = dict(zip(("x", "y", "z"), translation.tolist()))
        data.update(zip(("qw", "qx", "qy", "qz"), quaternion.tolist()))
        data["scale"] = scale
        transform_path.write_text(json.dumps(data))
    elif file_format == "txt":
        np.savetxt(transform_path, transform)
    else:
        np.save(transform_path, transform)

    command = [
        sys.executable,
        "-c",
        "from evo.cli.entry_points import traj; traj()",
        "tum",
        str(trajectory_path),
        "--transform_right" if right_mul else "--transform_left",
        str(transform_path),
        "--save_as_tum",
        "--no_warnings",
    ]
    if invert:
        command.append("--invert_transform")
    home = tmp_path / "home"
    home.mkdir()
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    result = file_interface.read_tum_trajectory_file(
        tmp_path / "trajectory.tum"
    )
    operation = np.linalg.inv(transform) if invert else transform
    expected = np.array(
        [
            pose @ operation if right_mul else operation @ pose
            for pose in trajectory.poses_se3
        ]
    )
    # TUM stores rotations as unit quaternions, without the Sim(3) scale.
    expected[:, :3, :3] /= 1 / scale if invert else scale
    np.testing.assert_allclose(result.poses_se3, expected, atol=1e-12)
    np.testing.assert_array_equal(result.timestamps, trajectory.timestamps)
    np.testing.assert_allclose(
        np.linalg.norm(result.orientations_quat_wxyz, axis=1), 1.0, atol=1e-12
    )
    valid, details = result.check()
    assert valid, details
