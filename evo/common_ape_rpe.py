"""
Common functions for evo_ape and evo_rpe, internal only.
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
import logging
from pathlib import Path

import numpy as np

from evo.core.filters import FilterException
from evo.core.metrics import PoseRelation, Unit
from evo.core.result import Result
from evo.core.trajectory import PosePath3D, PoseTrajectory3D
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80  # separator line


def load_trajectories(
    args: argparse.Namespace,
) -> tuple[PosePath3D, PosePath3D, str, str]:
    from evo.tools import file_interface

    traj_ref: PosePath3D | PoseTrajectory3D
    traj_est: PosePath3D | PoseTrajectory3D

    if args.subcommand == "tum":
        traj_ref = file_interface.read_tum_trajectory_file(args.ref_file)
        traj_est = file_interface.read_tum_trajectory_file(args.est_file)
        ref_name, est_name = args.ref_file, args.est_file
    elif args.subcommand == "kitti":
        traj_ref = file_interface.read_kitti_poses_file(args.ref_file)
        traj_est = file_interface.read_kitti_poses_file(args.est_file)
        ref_name, est_name = args.ref_file, args.est_file
    elif args.subcommand == "euroc":
        traj_ref = file_interface.read_euroc_csv_trajectory(args.state_gt_csv)
        traj_est = file_interface.read_tum_trajectory_file(args.est_file)
        ref_name, est_name = args.state_gt_csv, args.est_file
    elif args.subcommand in ("bag", "bag2"):
        logger.debug("Opening bag file " + args.bag)
        if not Path(args.bag).exists():
            raise file_interface.FileInterfaceException(
                "File doesn't exist: {}".format(args.bag)
            )
        if args.subcommand == "bag2":
            from rosbags.rosbag2 import Reader as Rosbag2Reader

            bag = Rosbag2Reader(args.bag)  # type: ignore
        else:
            from rosbags.rosbag1 import Reader as Rosbag1Reader

            bag = Rosbag1Reader(args.bag)  # type: ignore
        try:
            bag.open()
            traj_ref = file_interface.read_bag_trajectory(
                bag, args.ref_topic, cache_tf_tree=True
            )
            traj_est = file_interface.read_bag_trajectory(
                bag, args.est_topic, cache_tf_tree=True
            )
            ref_name, est_name = args.ref_topic, args.est_topic
        finally:
            bag.close()
    else:
        raise KeyError("unknown sub-command: {}".format(args.subcommand))

    return traj_ref, traj_est, ref_name, est_name


def get_pose_relation(args: argparse.Namespace) -> PoseRelation:
    if args.pose_relation == "full":
        pose_relation = PoseRelation.full_transformation
    elif args.pose_relation == "rot_part":
        pose_relation = PoseRelation.rotation_part
    elif args.pose_relation == "trans_part":
        pose_relation = PoseRelation.translation_part
    elif args.pose_relation == "angle_deg":
        pose_relation = PoseRelation.rotation_angle_deg
    elif args.pose_relation == "angle_rad":
        pose_relation = PoseRelation.rotation_angle_rad
    elif args.pose_relation == "point_distance":
        pose_relation = PoseRelation.point_distance
    elif args.pose_relation == "point_distance_error_ratio":
        pose_relation = PoseRelation.point_distance_error_ratio
    return pose_relation


def get_delta_unit(args: argparse.Namespace) -> Unit:
    delta_unit = Unit.none
    if args.delta_unit == "f":
        delta_unit = Unit.frames
    elif args.delta_unit == "d":
        delta_unit = Unit.degrees
    elif args.delta_unit == "r":
        delta_unit = Unit.radians
    elif args.delta_unit == "m":
        delta_unit = Unit.meters
    return delta_unit


def downsample_or_filter(
    args: argparse.Namespace, traj_ref: PosePath3D, traj_est: PosePath3D
) -> None:
    if not (args.downsample or args.motion_filter):
        return

    logger.debug(SEP)
    old_num_poses_ref = traj_ref.num_poses
    old_num_poses_est = traj_est.num_poses
    if args.downsample:
        logger.debug(
            "Downsampling trajectories to max %d poses.", args.downsample
        )
        traj_ref.downsample(args.downsample)
        traj_est.downsample(args.downsample)
    if args.motion_filter:
        if not all(
            isinstance(t, PoseTrajectory3D) for t in (traj_ref, traj_est)
        ):
            raise FilterException(
                "trajectories without timestamps can't be "
                "motion filtered in metrics because it "
                "could break the required synchronization"
            )
        distance_threshold = args.motion_filter[0]
        angle_threshold = args.motion_filter[1]
        logger.debug(
            "Filtering trajectories with motion filter "
            "thresholds: %f m, %f deg",
            distance_threshold,
            angle_threshold,
        )
        traj_ref.motion_filter(distance_threshold, angle_threshold, True)
        traj_est.motion_filter(distance_threshold, angle_threshold, True)
    logger.debug(
        "Number of poses in reference was reduced from %d to %d.",
        old_num_poses_ref,
        traj_ref.num_poses,
    )
    logger.debug(
        "Number of poses in estimate was reduced from %d to %d.",
        old_num_poses_est,
        traj_est.num_poses,
    )


def plot_result(
    args: argparse.Namespace,
    result: Result,
    traj_ref: PosePath3D,
    traj_est: PosePath3D,
    traj_ref_full: PosePath3D | None = None,
) -> None:
    from evo.tools import plot
    from evo.tools.settings import SETTINGS

    import matplotlib.pyplot as plt
    import numpy as np

    logger.debug(SEP)
    logger.debug("Plotting results... ")
    plot_mode = plot.PlotMode(args.plot_mode)

    # Plot the raw metric values.
    fig1 = plt.figure(figsize=SETTINGS.plot_figsize)
    if (
        args.plot_x_dimension == "distances"
        and "distances_from_start" in result.np_arrays
    ):
        x_array = result.np_arrays["distances_from_start"]
        x_label = "$d$ (m)"
    elif (
        args.plot_x_dimension == "seconds"
        and "seconds_from_start" in result.np_arrays
    ):
        x_array = result.np_arrays["seconds_from_start"]
        x_label = "$t$ (s)"
    else:
        x_array = None
        x_label = "index"

    plot.error_array(
        fig1.gca(),
        result.np_arrays["error_array"],
        x_array=x_array,
        statistics={
            s: result.stats[s]
            for s in SETTINGS.plot_statistics
            if s not in ("min", "max")
        },
        name=result.info["label"],
        title=result.info["title"],
        xlabel=x_label,
    )

    # Plot the values color-mapped onto the trajectory.
    fig2 = plt.figure(figsize=SETTINGS.plot_figsize)
    ax = plot.prepare_axis(
        fig2, plot_mode, length_unit=Unit(SETTINGS.plot_trajectory_length_unit)
    )

    plot.traj(
        ax,
        plot_mode,
        traj_ref_full if traj_ref_full else traj_ref,
        style=SETTINGS.plot_reference_linestyle,
        color=SETTINGS.plot_reference_color,
        label="reference",
        alpha=SETTINGS.plot_reference_alpha,
        plot_start_end_markers=SETTINGS.plot_start_end_markers,
    )
    plot.draw_coordinate_axes(
        ax, traj_ref, plot_mode, SETTINGS.plot_reference_axis_marker_scale
    )

    if args.plot_colormap_min is None:
        args.plot_colormap_min = result.stats["min"]
    if args.plot_colormap_max is None:
        args.plot_colormap_max = result.stats["max"]
    if args.plot_colormap_max_percentile is not None:
        args.plot_colormap_max = np.percentile(
            result.np_arrays["error_array"], args.plot_colormap_max_percentile
        )

    plot.traj_colormap(
        ax,
        traj_est,
        result.np_arrays["error_array"],
        plot_mode,
        min_map=args.plot_colormap_min,
        max_map=args.plot_colormap_max,
        title=result.info["title"],
        plot_start_end_markers=SETTINGS.plot_start_end_markers,
    )
    plot.draw_coordinate_axes(
        ax, traj_est, plot_mode, SETTINGS.plot_axis_marker_scale
    )
    if args.map_tile:
        plot.map_tile(ax, crs=args.map_tile)
    if args.ros_map_yaml:
        plot.ros_map(ax, args.ros_map_yaml, plot_mode)
    if SETTINGS.plot_pose_correspondences:
        plot.draw_correspondence_edges(
            ax,
            traj_est,
            traj_ref,
            plot_mode,
            style=SETTINGS.plot_pose_correspondences_linestyle,
            color=SETTINGS.plot_reference_color,
            alpha=SETTINGS.plot_reference_alpha,
        )
    fig2.axes.append(ax)

    plot_collection = plot.PlotCollection(result.info["title"])
    plot_collection.add_figure("raw", fig1)
    plot_collection.add_figure("map", fig2)
    if args.plot:
        plot_collection.show()
    if args.save_plot:
        plot_collection.export(
            args.save_plot, confirm_overwrite=not args.no_warnings
        )
    plot_collection.close()


def log_result_to_rerun(
    app_id: str,
    result: Result,
    traj_ref: PoseTrajectory3D,
    traj_est: PoseTrajectory3D,
) -> None:
    import rerun as rr
    import rerun.blueprint as rrb
    from matplotlib.colors import to_rgba

    from evo.tools import rerun_bridge as revo
    from evo.tools.rerun_bridge import mapped_colors

    logger.debug(SEP)
    logger.debug("Logging data to rerun.")
    rr.init(app_id, spawn=SETTINGS.rerun_spawn)

    time_range = rrb.VisibleTimeRange(
        timeline=revo.TIMELINE,
        start=rrb.TimeRangeBoundary.infinite(),
        end=rrb.TimeRangeBoundary.cursor_relative(seconds=0.0),
    )

    # Configure the blueprint (3D view, plot, etc.).
    rr.send_blueprint(
        rrb.Blueprint(
            rrb.Tabs(
                contents=[
                    rrb.Grid(
                        name="Visualization",
                        contents=[
                            rrb.Spatial3DView(
                                name="Trajectories", time_ranges=time_range
                            ),
                            rrb.TimeSeriesView(
                                name="Error",
                                time_ranges=time_range,
                                plot_legend=rrb.Corner2D.RightTop,
                            ),
                        ],
                        column_shares=None,
                        row_shares=[2.5, 1.0],
                        grid_columns=1,
                    ),
                    rrb.DataframeView(
                        name="Raw Data",
                        origin=f"/{app_id}",
                        contents=[
                            "$origin/reference/transforms",
                            "$origin/estimate/transforms",
                            "$origin/error/scalars",
                        ],
                    ),
                ]
            ),
            # Expand/collapse the selection and detailed time panels by default?
            rrb.SelectionPanel(expanded=False),
            rrb.TimePanel(expanded=False),
        )
    )

    error_array = result.np_arrays["error_array"]
    if app_id == "evo_rpe":
        # Pad RPE with 0. at the start to match the length of APE error arrays.
        error_array = np.insert(error_array, 0, 0.0)
    error_colors = mapped_colors(SETTINGS.plot_trajectory_cmap, error_array)

    revo.log_trajectory(
        entity_path=f"{app_id}/estimate",
        traj=traj_est,
        color=revo.Color(sequential=error_colors),
    )
    revo.log_trajectory(
        entity_path=f"{app_id}/reference",
        traj=traj_ref,
        color=revo.Color(
            static=to_rgba(
                SETTINGS.plot_reference_color,
                alpha=SETTINGS.plot_reference_alpha,
            )
        ),
    )

    # Log the correspondence edges.
    # In contrast to the matplotlib plot, we always do this here independent of
    # SETTINGS.plot_pose_correspondences.
    # It can be toggled in the rerun viewer and the logging is lightweight.
    revo.log_correspondence_strips(
        entity_path=f"{app_id}/error/correspondences",
        traj_1=traj_est,
        traj_2=traj_ref,
        color=revo.Color(
            static=to_rgba(
                SETTINGS.plot_reference_color,
                alpha=SETTINGS.plot_reference_alpha,
            )
        ),
        radii=revo.ui_points_radii(SETTINGS.plot_linewidth / 2.0),
    )

    # Log the error scalars.
    revo.log_scalars(
        entity_path=f"{app_id}/error/scalars",
        scalars=error_array,
        timestamps=traj_est.timestamps,
        color=revo.Color(static=to_rgba("red")),
        labelname=str(result.info["title"]),
    )
