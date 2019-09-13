# -*- coding: UTF8 -*-
"""
translate between evo and Pandas types
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

import os

import numpy as np
import pandas as pd

from evo.core import trajectory, result


def trajectory_to_df(traj):
    if not isinstance(traj, trajectory.PosePath3D):
        raise TypeError("trajectory.PosePath3D or derived required")
    poses_dict = {
        "x": traj.positions_xyz[:, 0],
        "y": traj.positions_xyz[:, 1],
        "z": traj.positions_xyz[:, 2],
        "qw": traj.orientations_quat_wxyz[:, 0],
        "qx": traj.orientations_quat_wxyz[:, 1],
        "qy": traj.orientations_quat_wxyz[:, 2],
        "qz": traj.orientations_quat_wxyz[:, 3],
    }
    if type(traj) is trajectory.PoseTrajectory3D:
        index = traj.timestamps
    else:
        index = np.arange(0, traj.num_poses)
    return pd.DataFrame(data=poses_dict, index=index)


def df_to_trajectory(df):
    if not isinstance(df, pd.DataFrame):
        raise TypeError("pandas.DataFrame or derived required")
    positions_xyz = df.loc[:,['x','y','z']].to_numpy()
    quaternions_wxyz = df.loc[:,['qw','qx','qy','qz']].to_numpy()
    # NOTE: df must have timestamps as index
    stamps = np.divide(df.index, 1e9)  # n x 1 - nanoseconds to seconds
    return trajectory.PoseTrajectory3D(positions_xyz, quaternions_wxyz, stamps)


def result_to_df(result_obj, label=None):
    if not isinstance(result_obj, result.Result):
        raise TypeError("result.Result or derived required")
    data = {
        "info": result_obj.info,
        "stats": result_obj.stats,
        "np_arrays": {},
        "trajectories": {}
    }
    for name, array in result_obj.np_arrays.items():
        data["np_arrays"][name] = array
    if label is None and "est_name" in data["info"]:
        label = os.path.splitext(os.path.basename(data["info"]["est_name"]))[0]
    elif label is None:
        label = "unnamed_result"
    return pd.DataFrame(data=data).T.stack().to_frame(name=label)
