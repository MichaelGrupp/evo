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

# The CLI test launches only the current interpreter with generated inputs.
import subprocess  # nosec B404
import sys
from pathlib import Path

import numpy as np
import pytest

from evo.core import lie_algebra as lie
from evo.core import transformations as tr
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface


def _write_trajectory(path: Path) -> PoseTrajectory3D:
    """Write three poses with differing rotations and return the trajectory."""
    trajectory = PoseTrajectory3D(
        positions_xyz=np.array([[1, 2, 3], [2, 2, 3], [2, 3, 3]]),
        orientations_quat_wxyz=np.array(
            [
                tr.quaternion_from_euler(0.2 * i, 0.1 * i, 0.3 * i)
                for i in range(3)
            ]
        ),
        timestamps=np.array([0.0, 1.0, 2.0]),
    )
    file_interface.write_tum_trajectory_file(path, trajectory)
    return trajectory


def _write_transform(path: Path, scale: float) -> np.ndarray:
    """Write a scaled, rotated, translated transform in the requested format."""
    quaternion = tr.quaternion_from_euler(0, 0, np.pi / 2)
    rotation = tr.quaternion_matrix(quaternion)[:3, :3]
    translation = np.array([10.0, -4.0, 2.0])
    transform = lie.sim3(rotation, translation, scale)
    if path.suffix == ".json":
        data = dict(zip(("x", "y", "z"), translation.tolist()))
        data.update(zip(("qw", "qx", "qy", "qz"), quaternion.tolist()))
        data["scale"] = scale
        path.write_text(json.dumps(data))
    elif path.suffix == ".txt":
        np.savetxt(path, transform)
    else:
        np.save(path, transform)
    return transform


def _run_traj(
    directory: Path, transform_path: Path, right_mul: bool, invert: bool
) -> None:
    """Run the real CLI with isolated settings and report any process failure."""
    command = [
        sys.executable,
        "-c",
        "from evo.cli.entry_points import traj; traj()",
        "tum",
        str(directory / "trajectory.txt"),
        "--transform_right" if right_mul else "--transform_left",
        str(transform_path),
        "--save_as_tum",
        "--no_warnings",
    ]
    if invert:
        command.append("--invert_transform")
    home = directory / "home"
    home.mkdir()
    try:
        # No shell or external input: arguments are constants and fixture paths.
        subprocess.run(  # nosec B603
            command,
            cwd=directory,
            env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)},
            shell=False,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as error:
        pytest.fail(error.stdout + error.stderr)


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
    """Check exported poses against direct matrix multiplication and inversion."""
    trajectory = _write_trajectory(tmp_path / "trajectory.txt")
    transform_path = tmp_path / f"transform.{file_format}"
    transform = _write_transform(transform_path, scale)
    _run_traj(tmp_path, transform_path, right_mul, invert)
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
    np.testing.assert_equal(valid, True, err_msg=str(details))
