"""
Matplotlib plotting functions for evo_traj.
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

import argparse
import itertools
import logging
from typing import Callable, Tuple

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from evo.core import trajectory
from evo.core.metrics import Unit
from evo.core.trajectory import PoseTrajectory3D
from evo.core.trajectory_bundle import TrajectoryBundle
from evo.tools import plot
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80


def get_color_generator(
    num_trajectories: int,
) -> Callable[[], Tuple]:
    """
    Returns a callable that yields colors for trajectories.
    Uses the configured multi_cmap colormap if set, otherwise falls back
    to the seaborn color palette.
    """
    cmap_colors = None
    if SETTINGS.plot_multi_cmap.lower() != "none":
        cmap = getattr(cm, SETTINGS.plot_multi_cmap)
        cmap_colors = iter(cmap(np.linspace(0, 1, num_trajectories)))
    color_palette = itertools.cycle(sns.color_palette())

    def get_color():
        if cmap_colors is None:
            return next(color_palette)
        return tuple(next(cmap_colors))

    return get_color


def plot_trajectories(
    bundle: TrajectoryBundle,
    args: argparse.Namespace,
    to_compact_name: Callable,
) -> None:
    plot_collection = plot.PlotCollection("evo_traj - trajectory plot")
    fig_xyz, axarr_xyz = plt.subplots(
        3, sharex="col", figsize=tuple(SETTINGS.plot_figsize)
    )
    fig_rpy, axarr_rpy = plt.subplots(
        3, sharex="col", figsize=tuple(SETTINGS.plot_figsize)
    )
    fig_traj = plt.figure(figsize=tuple(SETTINGS.plot_figsize))
    fig_speed = None

    plot_mode = plot.PlotMode[args.plot_mode]
    length_unit = Unit(SETTINGS.plot_trajectory_length_unit)
    ax_traj = plot.prepare_axis(fig_traj, plot_mode, length_unit=length_unit)

    # for x-axis alignment starting from 0 with --plot_relative_time
    start_time = None

    if bundle.ref_traj:
        if (
            isinstance(bundle.ref_traj, PoseTrajectory3D)
            and args.plot_relative_time
        ):
            start_time = bundle.ref_traj.timestamps[0]

        short_traj_name = to_compact_name(args.ref, args, SETTINGS.plot_usetex)
        plot.traj(
            ax_traj,
            plot_mode,
            bundle.ref_traj,
            style=SETTINGS.plot_reference_linestyle,
            color=SETTINGS.plot_reference_color,
            label=short_traj_name,
            alpha=SETTINGS.plot_reference_alpha,
            plot_start_end_markers=SETTINGS.plot_start_end_markers,
        )
        plot.draw_coordinate_axes(
            ax_traj,
            bundle.ref_traj,
            plot_mode,
            SETTINGS.plot_reference_axis_marker_scale,
        )
        plot.traj_xyz(
            axarr_xyz,
            bundle.ref_traj,
            style=SETTINGS.plot_reference_linestyle,
            color=SETTINGS.plot_reference_color,
            label=short_traj_name,
            alpha=SETTINGS.plot_reference_alpha,
            start_timestamp=start_time,
            length_unit=length_unit,
        )
        plot.traj_rpy(
            axarr_rpy,
            bundle.ref_traj,
            style=SETTINGS.plot_reference_linestyle,
            color=SETTINGS.plot_reference_color,
            label=short_traj_name,
            alpha=SETTINGS.plot_reference_alpha,
            start_timestamp=start_time,
        )
        if isinstance(bundle.ref_traj, PoseTrajectory3D):
            if fig_speed is None:
                fig_speed = plt.figure()
            try:
                plot.speeds(
                    fig_speed.gca(),
                    bundle.ref_traj,
                    style=SETTINGS.plot_reference_linestyle,
                    color=SETTINGS.plot_reference_color,
                    alpha=SETTINGS.plot_reference_alpha,
                    label=short_traj_name,
                    start_timestamp=start_time,
                )
            except trajectory.TrajectoryException as error:
                logger.error(
                    f"Can't plot speeds of {short_traj_name}: {error}"
                )
    elif args.plot_relative_time:
        # Use lower bound timestamp as the 0 time if there's no reference.
        if len(bundle.trajectories) > 1:
            logger.warning(
                "--plot_relative_time is set for multiple "
                "trajectories without --ref. "
                "Using the lowest timestamp as zero time."
            )
        start_time = min(
            traj.timestamps[0]
            for traj in bundle.trajectories.values()
            if isinstance(traj, PoseTrajectory3D)
        )

    get_color = get_color_generator(len(bundle.trajectories))

    for name, traj in bundle.trajectories.items():
        color = get_color()

        short_traj_name = to_compact_name(name, args, SETTINGS.plot_usetex)
        plot.traj(
            ax_traj,
            plot_mode,
            traj,
            SETTINGS.plot_trajectory_linestyle,
            color,
            short_traj_name,
            alpha=SETTINGS.plot_trajectory_alpha,
            plot_start_end_markers=SETTINGS.plot_start_end_markers,
        )
        plot.draw_coordinate_axes(
            ax_traj, traj, plot_mode, SETTINGS.plot_axis_marker_scale
        )
        if (
            bundle.ref_traj
            and bundle.synced
            and SETTINGS.plot_pose_correspondences
        ):
            plot.draw_correspondence_edges(
                ax_traj,
                traj,
                bundle.synced_refs[name],
                plot_mode,
                color=color,
                style=SETTINGS.plot_pose_correspondences_linestyle,
                alpha=SETTINGS.plot_trajectory_alpha,
            )
        plot.traj_xyz(
            axarr_xyz,
            traj,
            SETTINGS.plot_trajectory_linestyle,
            color,
            short_traj_name,
            alpha=SETTINGS.plot_trajectory_alpha,
            start_timestamp=start_time,
            length_unit=length_unit,
        )
        plot.traj_rpy(
            axarr_rpy,
            traj,
            SETTINGS.plot_trajectory_linestyle,
            color,
            short_traj_name,
            alpha=SETTINGS.plot_trajectory_alpha,
            start_timestamp=start_time,
        )
        if isinstance(traj, trajectory.PoseTrajectory3D):
            if fig_speed is None:
                fig_speed = plt.figure()
            try:
                plot.speeds(
                    fig_speed.gca(),
                    traj,
                    style=SETTINGS.plot_trajectory_linestyle,
                    color=color,
                    alpha=SETTINGS.plot_trajectory_alpha,
                    label=short_traj_name,
                    start_timestamp=start_time,
                )
            except trajectory.TrajectoryException as error:
                logger.error(
                    f"Can't plot speeds of {short_traj_name}: {error}"
                )
        if not SETTINGS.plot_usetex:
            fig_rpy.text(
                0.0,
                0.005,
                f"euler_angle_sequence: {SETTINGS.euler_angle_sequence}",
                fontsize=6,
            )

    if args.map_tile:
        plot.map_tile(ax_traj, crs=args.map_tile)
    if args.ros_map_yaml:
        plot.ros_map(ax_traj, args.ros_map_yaml, plot_mode)

    plot_collection.add_figure("trajectories", fig_traj)
    plot_collection.add_figure("xyz", fig_xyz)
    plot_collection.add_figure("rpy", fig_rpy)
    if fig_speed:
        plot_collection.add_figure("speeds", fig_speed)
    if args.plot:
        plot_collection.show()
    if args.save_plot:
        logger.info(SEP)
        plot_collection.export(
            args.save_plot, confirm_overwrite=not args.no_warnings
        )
