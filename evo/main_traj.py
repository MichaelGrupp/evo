#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
main executable for trajectory analysis
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
import datetime
import itertools
import logging
from pathlib import Path

from natsort import natsorted

from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80


def die(msg):
    import sys
    logger.error(msg)
    sys.exit(1)


def load_trajectories(args):
    from collections import OrderedDict
    from evo.tools import file_interface
    trajectories = OrderedDict()
    ref_traj = None
    if args.subcommand == "tum":
        for traj_file in args.traj_files:
            if traj_file == args.ref:
                continue
            trajectories[traj_file] = file_interface.read_tum_trajectory_file(
                traj_file)
        if args.ref:
            ref_traj = file_interface.read_tum_trajectory_file(args.ref)
    elif args.subcommand == "kitti":
        for pose_file in args.pose_files:
            if pose_file == args.ref:
                continue
            trajectories[pose_file] = file_interface.read_kitti_poses_file(
                pose_file)
        if args.ref:
            ref_traj = file_interface.read_kitti_poses_file(args.ref)
    elif args.subcommand == "euroc":
        for csv_file in args.state_gt_csv:
            if csv_file == args.ref:
                continue
            else:
                trajectories[
                    csv_file] = file_interface.read_euroc_csv_trajectory(
                        csv_file)
        if args.ref:
            ref_traj = file_interface.read_euroc_csv_trajectory(args.ref)
    elif args.subcommand in ("bag", "bag2"):
        if not (args.topics or args.all_topics):
            die("No topics used - specify topics or set --all_topics.")
        if not Path(args.bag).exists():
            raise file_interface.FileInterfaceException(
                "File doesn't exist: {}".format(args.bag))
        logger.debug("Opening bag file " + args.bag)
        if args.subcommand == "bag2":
            from rosbags.rosbag2 import Reader as Rosbag2Reader
            bag = Rosbag2Reader(args.bag)
        else:
            from rosbags.rosbag1 import Reader as Rosbag1Reader
            bag = Rosbag1Reader(args.bag)
        bag.open()
        try:
            if args.all_topics:
                # Note: args.topics can have TF stuff here, so we add it too.
                topics = args.topics
                topics += natsorted(file_interface.get_supported_topics(bag))
                if args.ref in topics:
                    topics.remove(args.ref)
                if len(topics) == 0:
                    die("No topics of supported types: {}".format(" ".join(
                        file_interface.SUPPORTED_ROS_MSGS)))
            else:
                topics = args.topics
            for topic in topics:
                if topic == args.ref:
                    continue
                trajectories[topic] = file_interface.read_bag_trajectory(
                    bag, topic, cache_tf_tree=True)
            if args.ref:
                ref_traj = file_interface.read_bag_trajectory(
                    bag, args.ref, cache_tf_tree=True)
        finally:
            bag.close()
    return trajectories, ref_traj


# TODO refactor
def print_traj_info(name, traj, verbose=False, full_check=False):
    from evo.core import trajectory

    logger.info(SEP)
    logger.info("name:\t" + name)

    if verbose or full_check:

        def print_dict(name: str, data: dict):
            string = ""
            for key, value in sorted(data.items()):
                string += "\n\t" + key + "\t" + str(value)
            logger.info(name + ":" + string)

        print_dict("infos", traj.get_infos())
        if traj.meta:
            print_dict("meta", traj.meta)
        if full_check:
            print_dict("checks", traj.check()[1])
            stat_str = ""
            try:
                stats = traj.get_statistics()
                for stat, value in sorted(stats.items()):
                    if isinstance(value, float):
                        stat_str += "\n\t" + stat + "\t" + "{0:.6f}".format(
                            value)
                    else:
                        stat_str += value
            except trajectory.TrajectoryException as e:
                stat_str += "\n\terror - " + str(e)
            logger.info("stats:" + stat_str)
    else:
        logger.info("infos:\t" + str(traj))


def to_filestem(name: str, args: argparse.Namespace) -> str:
    if args.subcommand in ("bag", "bag2"):
        if name.startswith('/'):
            name = name[1:]
        name = name.replace(':', '/')  # TF ID
        return name.replace('/', '_')
    return Path(name).stem


def to_topic_name(name: str, args: argparse.Namespace) -> str:
    if args.subcommand in ("bag", "bag2"):
        return name.replace(':', '/')
    return '/' + Path(name).stem.replace(' ', '_')


def to_compact_name(name: str, args: argparse.Namespace,
                    latex_friendly=False) -> str:
    if not args.show_full_names and args.subcommand not in ("bag", "bag2"):
        # /some/super/long/path/that/nobody/cares/about/traj.txt  ->  traj
        name = Path(name).stem
    if latex_friendly:
        name = name.replace("_", "\\_")
    return name


def run(args):
    import numpy as np

    import evo.core.lie_algebra as lie
    from evo.core import trajectory
    from evo.core.metrics import Unit
    from evo.tools import file_interface, log

    log.configure_logging(verbose=args.verbose, silent=args.silent,
                          debug=args.debug, local_logfile=args.logfile)
    if args.debug:
        import pprint
        logger.debug(
            "main_parser config:\n" +
            pprint.pformat({arg: getattr(args, arg)
                            for arg in vars(args)}) + "\n")
    logger.debug(SEP)

    trajectories, ref_traj = load_trajectories(args)

    if args.downsample:
        logger.debug(SEP)
        logger.info("Downsampling trajectories to max %s poses.",
                    args.downsample)
        for traj in trajectories.values():
            traj.downsample(args.downsample)
        if ref_traj:
            ref_traj.downsample(args.downsample)

    if args.motion_filter:
        logger.debug(SEP)
        distance_threshold = args.motion_filter[0]
        angle_threshold = args.motion_filter[1]
        logger.info(
            "Filtering trajectories with motion filter "
            "thresholds: %f m, %f deg", distance_threshold, angle_threshold)
        for traj in trajectories.values():
            traj.motion_filter(distance_threshold, angle_threshold, True)
        if ref_traj:
            ref_traj.motion_filter(distance_threshold, angle_threshold, True)

    if args.merge:
        if args.subcommand == "kitti":
            die("Can't merge KITTI files.")
        if len(trajectories) == 0:
            die("No trajectories to merge (excluding --ref).")
        trajectories = {
            "merged_trajectory": trajectory.merge(trajectories.values())
        }

    if args.t_offset:
        logger.debug(SEP)
        for name, traj in trajectories.items():
            if type(traj) is trajectory.PosePath3D:
                die("{} doesn't have timestamps - can't add time offset.".
                    format(name))
            logger.info("Adding time offset to {}: {} (s)".format(
                name, args.t_offset))
            traj.timestamps += args.t_offset

    if args.n_to_align != -1 and not (args.align or args.correct_scale):
        die("--n_to_align is useless without --align or/and --correct_scale")

    # TODO: this is fugly, but is a quick solution for remembering each synced
    # reference when plotting pose correspondences later...
    synced = (args.subcommand == "kitti" and ref_traj) or any(
        (args.sync, args.align, args.correct_scale, args.align_origin))
    synced_refs = {}
    if synced:
        from evo.core import sync
        if not args.ref:
            logger.debug(SEP)
            die("Can't align or sync without a reference! (--ref)  *grunt*")
        for name, traj in trajectories.items():
            if args.subcommand == "kitti":
                ref_traj_tmp = ref_traj
            else:
                logger.debug(SEP)
                ref_traj_tmp, trajectories[name] = sync.associate_trajectories(
                    ref_traj, traj, max_diff=args.t_max_diff,
                    first_name="reference", snd_name=name)
            if args.align or args.correct_scale:
                logger.debug(SEP)
                logger.debug("Aligning {} to reference.".format(name))
                trajectories[name].align(
                    ref_traj_tmp, correct_scale=args.correct_scale,
                    correct_only_scale=args.correct_scale and not args.align,
                    n=args.n_to_align)
            if args.align_origin:
                logger.debug(SEP)
                logger.debug("Aligning {}'s origin to reference.".format(name))
                trajectories[name].align_origin(ref_traj_tmp)
            if SETTINGS.plot_pose_correspondences:
                synced_refs[name] = ref_traj_tmp

    if args.transform_left or args.transform_right:
        tf_type = "left" if args.transform_left else "right"
        tf_path = args.transform_left \
                if args.transform_left else args.transform_right
        transform = file_interface.load_transform(tf_path)
        if args.invert_transform:
            transform = lie.se3_inverse(transform)
        logger.debug(SEP)
        logger.debug("Applying a {}-multiplicative transformation:\n{}".format(
            tf_type, transform))
        for traj in trajectories.values():
            traj.transform(transform, right_mul=args.transform_right,
                           propagate=args.propagate_transform)

    # Note: projection is done after potential alignment & transformation steps.
    if args.project_to_plane:
        plane = trajectory.Plane(args.project_to_plane)
        logger.debug(SEP)
        logger.debug("Projecting trajectories to %s plane.", plane.value)
        for traj in trajectories.values():
            traj.project(plane)
        if ref_traj:
            ref_traj.project(plane)

    for name, traj in trajectories.items():
        print_traj_info(to_compact_name(name, args), traj, args.verbose,
                        args.full_check)
    if args.ref:
        print_traj_info(to_compact_name(args.ref, args), ref_traj,
                        args.verbose, args.full_check)

    if args.plot or args.save_plot or args.serialize_plot:
        import numpy as np
        from evo.tools import plot
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        import seaborn as sns

        plot_collection = plot.PlotCollection("evo_traj - trajectory plot")
        fig_xyz, axarr_xyz = plt.subplots(3, sharex="col",
                                          figsize=tuple(SETTINGS.plot_figsize))
        fig_rpy, axarr_rpy = plt.subplots(3, sharex="col",
                                          figsize=tuple(SETTINGS.plot_figsize))
        fig_traj = plt.figure(figsize=tuple(SETTINGS.plot_figsize))
        fig_speed = plt.figure()

        plot_mode = plot.PlotMode[args.plot_mode]
        length_unit = Unit(SETTINGS.plot_trajectory_length_unit)
        ax_traj = plot.prepare_axis(fig_traj, plot_mode,
                                    length_unit=length_unit)

        # for x-axis alignment starting from 0 with --plot_relative_time
        start_time = None

        if args.ref:
            if isinstance(ref_traj, trajectory.PoseTrajectory3D) \
                    and args.plot_relative_time:
                start_time = ref_traj.timestamps[0]

            short_traj_name = to_compact_name(args.ref, args,
                                              SETTINGS.plot_usetex)
            plot.traj(ax_traj, plot_mode, ref_traj,
                      style=SETTINGS.plot_reference_linestyle,
                      color=SETTINGS.plot_reference_color,
                      label=short_traj_name,
                      alpha=SETTINGS.plot_reference_alpha,
                      plot_start_end_markers=SETTINGS.plot_start_end_markers)
            plot.draw_coordinate_axes(
                ax_traj, ref_traj, plot_mode,
                SETTINGS.plot_reference_axis_marker_scale)
            plot.traj_xyz(axarr_xyz, ref_traj,
                          style=SETTINGS.plot_reference_linestyle,
                          color=SETTINGS.plot_reference_color,
                          label=short_traj_name,
                          alpha=SETTINGS.plot_reference_alpha,
                          start_timestamp=start_time, length_unit=length_unit)
            plot.traj_rpy(axarr_rpy, ref_traj,
                          style=SETTINGS.plot_reference_linestyle,
                          color=SETTINGS.plot_reference_color,
                          label=short_traj_name,
                          alpha=SETTINGS.plot_reference_alpha,
                          start_timestamp=start_time)
            if isinstance(ref_traj, trajectory.PoseTrajectory3D):
                plot.speeds(fig_speed.gca(), ref_traj,
                            style=SETTINGS.plot_reference_linestyle,
                            color=SETTINGS.plot_reference_color,
                            alpha=SETTINGS.plot_reference_alpha,
                            label=short_traj_name)
        elif args.plot_relative_time:
            # Use lower bound timestamp as the 0 time if there's no reference.
            if len(trajectories) > 1:
                logger.warning("--plot_relative_time is set for multiple "
                               "trajectories without --ref. "
                               "Using the lowest timestamp as zero time.")
            start_time = min(traj.timestamps[0]
                             for _, traj in trajectories.items())

        cmap_colors = None
        if SETTINGS.plot_multi_cmap.lower() != "none":
            cmap = getattr(cm, SETTINGS.plot_multi_cmap)
            cmap_colors = iter(cmap(np.linspace(0, 1, len(trajectories))))
        color_palette = itertools.cycle(sns.color_palette())

        for name, traj in trajectories.items():
            if cmap_colors is None:
                color = next(color_palette)
            else:
                color = next(cmap_colors)

            short_traj_name = to_compact_name(name, args, SETTINGS.plot_usetex)
            plot.traj(ax_traj, plot_mode, traj,
                      SETTINGS.plot_trajectory_linestyle, color,
                      short_traj_name, alpha=SETTINGS.plot_trajectory_alpha,
                      plot_start_end_markers=SETTINGS.plot_start_end_markers)
            plot.draw_coordinate_axes(ax_traj, traj, plot_mode,
                                      SETTINGS.plot_axis_marker_scale)
            if ref_traj and synced and SETTINGS.plot_pose_correspondences:
                plot.draw_correspondence_edges(
                    ax_traj, traj, synced_refs[name], plot_mode, color=color,
                    style=SETTINGS.plot_pose_correspondences_linestyle,
                    alpha=SETTINGS.plot_trajectory_alpha)
            plot.traj_xyz(axarr_xyz, traj, SETTINGS.plot_trajectory_linestyle,
                          color, short_traj_name,
                          alpha=SETTINGS.plot_trajectory_alpha,
                          start_timestamp=start_time, length_unit=length_unit)
            plot.traj_rpy(axarr_rpy, traj, SETTINGS.plot_trajectory_linestyle,
                          color, short_traj_name,
                          alpha=SETTINGS.plot_trajectory_alpha,
                          start_timestamp=start_time)
            if isinstance(traj, trajectory.PoseTrajectory3D):
                plot.speeds(fig_speed.gca(), traj,
                            style=SETTINGS.plot_trajectory_linestyle,
                            color=color, alpha=SETTINGS.plot_trajectory_alpha,
                            label=short_traj_name)
            if not SETTINGS.plot_usetex:
                fig_rpy.text(
                    0., 0.005, "euler_angle_sequence: {}".format(
                        SETTINGS.euler_angle_sequence), fontsize=6)

        if args.ros_map_yaml:
            plot.ros_map(ax_traj, args.ros_map_yaml, plot_mode)

        plot_collection.add_figure("trajectories", fig_traj)
        plot_collection.add_figure("xyz", fig_xyz)
        plot_collection.add_figure("rpy", fig_rpy)
        plot_collection.add_figure("speeds", fig_speed)
        if args.plot:
            plot_collection.show()
        if args.save_plot:
            logger.info(SEP)
            plot_collection.export(args.save_plot,
                                   confirm_overwrite=not args.no_warnings)
        if args.serialize_plot:
            logger.info(SEP)
            plot_collection.serialize(args.serialize_plot,
                                      confirm_overwrite=not args.no_warnings)

    if args.save_as_tum:
        logger.info(SEP)
        for name, traj in trajectories.items():
            dest = to_filestem(name, args) + ".tum"
            file_interface.write_tum_trajectory_file(
                dest, traj, confirm_overwrite=not args.no_warnings)
        if args.ref:
            dest = to_filestem(args.ref, args) + ".tum"
            file_interface.write_tum_trajectory_file(
                dest, ref_traj, confirm_overwrite=not args.no_warnings)
    if args.save_as_kitti:
        logger.info(SEP)
        for name, traj in trajectories.items():
            dest = to_filestem(name, args) + ".kitti"
            file_interface.write_kitti_poses_file(
                dest, traj, confirm_overwrite=not args.no_warnings)
        if args.ref:
            dest = to_filestem(args.ref, args) + ".kitti"
            file_interface.write_kitti_poses_file(
                dest, ref_traj, confirm_overwrite=not args.no_warnings)
    if args.save_as_bag or args.save_as_bag2:
        from rosbags.rosbag1 import Writer as Rosbag1Writer
        from rosbags.rosbag2 import Writer as Rosbag2Writer
        writers = []
        if args.save_as_bag:
            dest_bag_path = str(
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")) + ".bag"
            writers.append(Rosbag1Writer(dest_bag_path))
        if args.save_as_bag2:
            dest_bag_path = str(
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
            writers.append(Rosbag2Writer(dest_bag_path))
        for writer in writers:
            logger.info(SEP)
            logger.info("Saving trajectories to " + str(writer.path) + "...")
            try:
                writer.open()
                for name, traj in trajectories.items():
                    dest_topic = to_topic_name(name, args)
                    frame_id = traj.meta[
                        "frame_id"] if "frame_id" in traj.meta else ""
                    file_interface.write_bag_trajectory(
                        writer, traj, dest_topic, frame_id)
                if args.ref:
                    dest_topic = to_topic_name(args.ref, args)
                    frame_id = ref_traj.meta[
                        "frame_id"] if "frame_id" in ref_traj.meta else ""
                    file_interface.write_bag_trajectory(
                        writer, ref_traj, dest_topic, frame_id)
            finally:
                writer.close()

    if args.save_table:
        from evo.tools import pandas_bridge
        logger.debug(SEP)
        df = pandas_bridge.trajectories_stats_to_df(trajectories)
        pandas_bridge.save_df_as_table(df, args.save_table,
                                       confirm_overwrite=not args.no_warnings)


if __name__ == '__main__':
    from evo import entry_points
    entry_points.traj()
