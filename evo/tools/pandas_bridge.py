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

import logging
import os
import typing

import numpy as np
import pandas as pd

from evo.core import result
from evo.core.trajectory import PosePath3D, PoseTrajectory3D
from evo.tools import file_interface, user
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

PathOrTrajectory = PosePath3D | PoseTrajectory3D
PathOrTrajectoryType = type[PathOrTrajectory]


def trajectory_to_df(traj: PosePath3D) -> pd.DataFrame:
    if not isinstance(traj, PosePath3D):
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
    if isinstance(traj, PoseTrajectory3D):
        index = traj.timestamps
    else:
        index = np.arange(0, traj.num_poses)
    return pd.DataFrame(data=poses_dict, index=index)


def df_to_trajectory(
    df: pd.DataFrame, as_type: PathOrTrajectoryType | None = None
) -> PathOrTrajectory:
    """
    :param df: DataFrame created with trajectory_to_df()
    :param as_type: Explicit output type, otherwise derived from the data.
                    Either PosePath3D or PoseTrajectory3D.
    """
    quat_wxyz = df[["qw", "qx", "qy", "qz"]].to_numpy()
    positions_xyz = df[["x", "y", "z"]].to_numpy()
    if as_type is PosePath3D or df.index.dtype == np.int_:
        return PosePath3D(positions_xyz, quat_wxyz)
    timestamps = df.index.to_numpy()
    return PoseTrajectory3D(positions_xyz, quat_wxyz, timestamps)


def trajectory_stats_to_df(
    traj: PosePath3D, name: str | None = None
) -> pd.DataFrame:
    if not isinstance(traj, PosePath3D):
        raise TypeError("PosePath3D or derived required")
    data_dict = {k: v for k, v in traj.get_infos().items() if np.isscalar(v)}
    data_dict.update(traj.get_statistics())
    index = [name] if name else ["0"]
    return pd.DataFrame(data=data_dict, index=index)


def trajectories_stats_to_df(
    trajectories: dict[str, PosePath3D],
) -> pd.DataFrame:
    df = pd.DataFrame()
    for name, traj in trajectories.items():
        df = pd.concat((df, trajectory_stats_to_df(traj, name)))
    return df


def result_to_df(
    result_obj: result.Result, label: str | None = None
) -> pd.DataFrame:
    if not isinstance(result_obj, result.Result):
        raise TypeError("result.Result or derived required")
    data = {
        "info": result_obj.info,
        "stats": result_obj.stats,
        "np_arrays": {},
        "trajectories": {},
    }
    for name, array in result_obj.np_arrays.items():
        data["np_arrays"][name] = array
    if label is None and "est_name" in data["info"]:
        label = os.path.basename(data["info"]["est_name"])
    elif label is None:
        label = "unnamed_result"
    df = pd.DataFrame(data=data)
    if df.empty:
        raise ValueError("cannot create a dataframe from an empty result")
    stacked_series: pd.Series = df.T.stack()  # type: ignore
    return stacked_series.to_frame(name=label)


def save_df_as_table(
    df: pd.DataFrame,
    path: str,
    format_str: str = SETTINGS.table_export_format,
    transpose: str = SETTINGS.table_export_transpose,
    confirm_overwrite: bool = False,
) -> None:
    if confirm_overwrite and not user.check_and_confirm_overwrite(path):
        return
    if transpose:
        df = df.T
    if format_str == "excel":
        # requires xlwt and/or openpyxl to be installed
        with pd.ExcelWriter(path) as writer:
            df.to_excel(writer)
    else:
        getattr(df, "to_" + format_str)(path)
    logger.debug("{} table saved to: {}".format(format_str, path))


def load_results_as_dataframe(
    result_files: typing.Iterable[str],
    use_filenames: bool = False,
    merge: bool = False,
) -> pd.DataFrame:
    """
    Load multiple result files into a MultiIndex dataframe.
    :param result_files: result files to load
    :param use_filenames: use the result filename as label instead of
                          the 'est_name' label from the result's info
    :param merge: merge all results into an average result
    """
    if merge:
        results = [file_interface.load_res_file(f) for f in result_files]
        return result_to_df(result.merge_results(results))

    df = pd.DataFrame()
    for result_file in result_files:
        result_obj = file_interface.load_res_file(result_file)
        name = result_file if use_filenames else None
        df = pd.concat([df, result_to_df(result_obj, name)], axis="columns")
    return df
