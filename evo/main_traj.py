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

from __future__ import print_function

import logging

logger = logging.getLogger(__name__)

SEP = "-" * 80


def parser():
    import argparse
    basic_desc = "trajectory analysis and manipulation tool"
    lic = "(c) evo authors"
    shared_parser = argparse.ArgumentParser(add_help=False)
    algo_opts = shared_parser.add_argument_group("algorithm options")
    output_opts = shared_parser.add_argument_group("output options")
    usability_opts = shared_parser.add_argument_group("usability options")
    shared_parser.add_argument("-f", "--full_check",
                               help="run all checks and print all stats",
                               action="store_true")
    algo_opts.add_argument(
        "-a", "--align", help="alignment with Umeyama's method (no scale)"
        " - requires --ref", action="store_true")
    algo_opts.add_argument(
        "-s", "--correct_scale", help="scale correction with Umeyama's method"
        " - requires --ref", action="store_true")
    algo_opts.add_argument(
        "--n_to_align",
        help="the number of poses to use for Umeyama alignment, "
        "counted from the start (default: all)", default=-1, type=int)
    algo_opts.add_argument(
        "--align_origin",
        help="align the trajectory origin to the origin of the reference "
        "trajectory", action="store_true")
    algo_opts.add_argument(
        "--sync",
        help="associate trajectories via matching timestamps - requires --ref",
        action="store_true")
    algo_opts.add_argument(
        "--transform_left", help="path to a .json file with a transformation"
        " to apply to the trajectories (left multiplicative)")
    algo_opts.add_argument(
        "--transform_right", help="path to a .json file with a transformation"
        " to apply to the trajectories (right_multiplicative)")
    algo_opts.add_argument(
        "--propagate_transform", help="with --transform_right: transform each "
        "pose and propagate resulting drift to the next.", action="store_true")
    algo_opts.add_argument("--invert_transform",
                           help="invert the transformation of the .json file",
                           action="store_true")
    algo_opts.add_argument(
        "--ref", help="trajectory that will be marked/used as the reference")
    algo_opts.add_argument(
        "--t_offset",
        help="add a constant timestamp offset (not adding to --ref trajectory)",
        default=0.0, type=float)
    algo_opts.add_argument(
        "--t_max_diff",
        help="maximum timestamp difference for data association", default=0.01,
        type=float)
    algo_opts.add_argument(
        "--merge", help="merge the trajectories in a single trajectory",
        action="store_true")
    output_opts.add_argument("-p", "--plot", help="show plot window",
                             action="store_true")
    output_opts.add_argument(
        "--plot_mode", help="the axes for  plot projection", default=None,
        choices=["xy", "xz", "yx", "yz", "zx", "zy", "xyz"])
    output_opts.add_argument("--save_plot", help="path to save plot",
                             default=None)
    output_opts.add_argument("--serialize_plot",
                             help="path to serialize plot (experimental)",
                             default=None)
    output_opts.add_argument("--save_as_tum",
                             help="save trajectories in TUM format (as *.tum)",
                             action="store_true")
    output_opts.add_argument("--save_as_kitti",
                             help="save poses in KITTI format (as *.kitti)",
                             action="store_true")
    output_opts.add_argument("--save_as_bag",
                             help="save trajectories in ROS bag as <date>.bag",
                             action="store_true")
    output_opts.add_argument("--logfile", help="Local logfile path.",
                             default=None)
    usability_opts.add_argument("--no_warnings",
                                help="no warnings requiring user confirmation",
                                action="store_true")
    usability_opts.add_argument("-v", "--verbose", help="verbose output",
                                action="store_true")
    usability_opts.add_argument("--silent", help="don't print any output",
                                action="store_true")
    usability_opts.add_argument(
        "--debug", help="verbose output with additional debug info",
        action="store_true")
    usability_opts.add_argument(
        "-c", "--config",
        help=".json file with parameters (priority over command line args)")

    main_parser = argparse.ArgumentParser(
        description="%s %s" % (basic_desc, lic))
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True
    kitti_parser = sub_parsers.add_parser(
        "kitti",
        description="%s for KITTI pose files - %s" % (basic_desc, lic),
        parents=[shared_parser])
    kitti_parser.add_argument("pose_files", help="one or multiple pose files",
                              nargs='+')

    tum_parser = sub_parsers.add_parser(
        "tum",
        description="%s for TUM trajectory files - %s" % (basic_desc, lic),
        parents=[shared_parser])
    tum_parser.add_argument("traj_files",
                            help="one or multiple trajectory files", nargs='+')

    euroc_parser = sub_parsers.add_parser(
        "euroc",
        description="%s for EuRoC MAV .csv's - %s" % (basic_desc, lic),
        parents=[shared_parser])
    euroc_parser.add_argument(
        "state_gt_csv",
        help="<sequence>/mav0/state_groundtruth_estimate0/data.csv", nargs='+')

    bag_parser = sub_parsers.add_parser(
        "bag", description="%s for ROS bag files - %s" % (basic_desc, lic),
        parents=[shared_parser])
    bag_parser.add_argument("bag", help="ROS bag file")
    bag_parser.add_argument("topics", help="multiple trajectory topics",
                            nargs='*')
    bag_parser.add_argument("--all_topics",
                            help="use all compatible topics in the bag",
                            action="store_true")
    return main_parser


def die(msg):
    import sys
    logger.error(msg)
    sys.exit(1)


def load_trajectories(args):
    from evo.tools import file_interface
    trajectories = {}
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
    elif args.subcommand == "bag":
        if not (args.topics or args.all_topics):
            die("No topics used - specify topics or set --all_topics.")
        import rosbag
        bag = rosbag.Bag(args.bag)
        try:
            if args.all_topics:
                topic_info = bag.get_type_and_topic_info()
                topics = sorted([
                    t for t in topic_info[1].keys()
                    if topic_info[1][t][0] in file_interface.SUPPORTED_ROS_MSGS
                    and t != args.ref
                ])
                if len(topics) == 0:
                    die("No topics of supported types: {}".format(" ".join(
                        file_interface.SUPPORTED_ROS_MSGS)))
            else:
                topics = args.topics
            for topic in topics:
                trajectories[topic] = file_interface.read_bag_trajectory(
                    bag, topic)
            if args.ref:
                ref_traj = file_interface.read_bag_trajectory(bag, args.ref)
        finally:
            bag.close()
    return trajectories, ref_traj


# TODO refactor
def print_traj_info(name, traj, verbose=False, full_check=False):
    import os
    from evo.core import trajectory

    logger.info(SEP)
    logger.info("name:\t" + os.path.splitext(os.path.basename(name))[0])

    if verbose or full_check:
        infos = traj.get_infos()
        info_str = ""
        for info, value in sorted(infos.items()):
            info_str += "\n\t" + info + "\t" + str(value)
        logger.info("infos:" + info_str)
        if full_check:
            passed, details = traj.check()
            check_str = ""
            for test, result in sorted(details.items()):
                check_str += "\n\t" + test + "\t" + result
            logger.info("checks:" + check_str)
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


def run(args):
    import os
    import sys

    import numpy as np

    import evo.core.lie_algebra as lie
    from evo.core import trajectory
    from evo.core.trajectory import PoseTrajectory3D
    from evo.tools import file_interface, log
    from evo.tools.settings import SETTINGS

    log.configure_logging(verbose=args.verbose, silent=args.silent,
                          debug=args.debug, local_logfile=args.logfile)
    if args.debug:
        import pprint
        logger.debug("main_parser config:\n" + pprint.pformat(
            {arg: getattr(args, arg)
             for arg in vars(args)}) + "\n")
    logger.debug(SEP)

    trajectories, ref_traj = load_trajectories(args)

    if args.merge:
        if args.subcommand == "kitti":
            die("Can't merge KITTI files.")
        if len(trajectories) == 0:
            die("No trajectories to merge (excluding --ref).")
        trajectories = {
            "merged_trajectory": trajectory.merge(trajectories.values())
        }

    if args.transform_left or args.transform_right:
        tf_type = "left" if args.transform_left else "right"
        tf_path = args.transform_left \
                if args.transform_left else args.transform_right
        transform = file_interface.load_transform_json(tf_path)
        logger.debug(SEP)
        if not lie.is_se3(transform):
            logger.warning("Not a valid SE(3) transformation!")
        if args.invert_transform:
            transform = lie.se3_inverse(transform)
        logger.debug("Applying a {}-multiplicative transformation:\n{}".format(
            tf_type, transform))
        for traj in trajectories.values():
            traj.transform(transform, right_mul=args.transform_right,
                           propagate=args.propagate_transform)

    if args.t_offset:
        logger.debug(SEP)
        for name, traj in trajectories.items():
            if type(traj) is trajectory.PosePath3D:
                die("{} doesn't have timestamps - can't add time offset.".
                    format(name))
            logger.info("Adding time offset to {}: {} (s)".format(
                name, args.t_offset))
            traj.timestamps += args.t_offset

    if args.sync or args.align or args.correct_scale or args.align_origin:
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
                trajectories[name] = trajectory.align_trajectory(
                    trajectories[name], ref_traj_tmp,
                    correct_scale=args.correct_scale,
                    correct_only_scale=args.correct_scale and not args.align,
                    n=args.n_to_align)
            elif args.align_origin:
                logger.debug(SEP)
                logger.debug("Aligning {}'s origin to reference.".format(name))
                trajectories[name] = trajectory.align_trajectory_origin(
                    trajectories[name], ref_traj_tmp)

    for name, traj in trajectories.items():
        print_traj_info(name, traj, args.verbose, args.full_check)
    if args.ref:
        print_traj_info(args.ref, ref_traj, args.verbose, args.full_check)

    if args.plot or args.save_plot or args.serialize_plot:
        from evo.tools.plot import PlotMode
        plot_mode = PlotMode.xyz if not args.plot_mode else PlotMode[args.
                                                                     plot_mode]
        import numpy as np
        from evo.tools import plot
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm

        plot_collection = plot.PlotCollection("evo_traj - trajectory plot")
        fig_xyz, axarr_xyz = plt.subplots(3, sharex="col",
                                          figsize=tuple(SETTINGS.plot_figsize))
        fig_rpy, axarr_rpy = plt.subplots(3, sharex="col",
                                          figsize=tuple(SETTINGS.plot_figsize))
        fig_traj = plt.figure(figsize=tuple(SETTINGS.plot_figsize))
        ax_traj = plot.prepare_axis(fig_traj, plot_mode)

        if args.ref:
            short_traj_name = os.path.splitext(os.path.basename(args.ref))[0]
            if SETTINGS.plot_usetex:
                short_traj_name = short_traj_name.replace("_", "\\_")
            plot.traj(ax_traj, plot_mode, ref_traj,
                      style=SETTINGS.plot_reference_linestyle,
                      color=SETTINGS.plot_reference_color,
                      label=short_traj_name,
                      alpha=SETTINGS.plot_reference_alpha)
            plot.traj_xyz(
                axarr_xyz, ref_traj, style=SETTINGS.plot_reference_linestyle,
                color=SETTINGS.plot_reference_color, label=short_traj_name,
                alpha=SETTINGS.plot_reference_alpha)
            plot.traj_rpy(
                axarr_rpy, ref_traj, style=SETTINGS.plot_reference_linestyle,
                color=SETTINGS.plot_reference_color, label=short_traj_name,
                alpha=SETTINGS.plot_reference_alpha)

        cmap_colors = None
        if SETTINGS.plot_multi_cmap.lower() != "none":
            cmap = getattr(cm, SETTINGS.plot_multi_cmap)
            cmap_colors = iter(cmap(np.linspace(0, 1, len(trajectories))))

        for name, traj in trajectories.items():
            if cmap_colors is None:
                color = next(ax_traj._get_lines.prop_cycler)['color']
            else:
                color = next(cmap_colors)
            short_traj_name = os.path.splitext(os.path.basename(name))[0]
            if SETTINGS.plot_usetex:
                short_traj_name = short_traj_name.replace("_", "\\_")
            plot.traj(ax_traj, plot_mode, traj, '-', color, short_traj_name,
                      alpha=SETTINGS.plot_trajectory_alpha)
            if args.ref and isinstance(ref_traj, trajectory.PoseTrajectory3D):
                start_time = ref_traj.timestamps[0]
            else:
                start_time = None
            plot.traj_xyz(axarr_xyz, traj, '-', color, short_traj_name,
                          alpha=SETTINGS.plot_trajectory_alpha,
                          start_timestamp=start_time)
            plot.traj_rpy(axarr_rpy, traj, '-', color, short_traj_name,
                          alpha=SETTINGS.plot_trajectory_alpha,
                          start_timestamp=start_time)

        plot_collection.add_figure("trajectories", fig_traj)
        plot_collection.add_figure("xyz_view", fig_xyz)
        plot_collection.add_figure("rpy_view", fig_rpy)
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
            dest = os.path.splitext(os.path.basename(name))[0] + ".tum"
            file_interface.write_tum_trajectory_file(
                dest, traj, confirm_overwrite=not args.no_warnings)
        if args.ref:
            dest = os.path.splitext(os.path.basename(args.ref))[0] + ".tum"
            file_interface.write_tum_trajectory_file(
                dest, ref_traj, confirm_overwrite=not args.no_warnings)
    if args.save_as_kitti:
        logger.info(SEP)
        for name, traj in trajectories.items():
            dest = os.path.splitext(os.path.basename(name))[0] + ".kitti"
            file_interface.write_kitti_poses_file(
                dest, traj, confirm_overwrite=not args.no_warnings)
        if args.ref:
            dest = os.path.splitext(os.path.basename(args.ref))[0] + ".kitti"
            file_interface.write_kitti_poses_file(
                dest, ref_traj, confirm_overwrite=not args.no_warnings)
    if args.save_as_bag:
        import datetime
        import rosbag
        dest_bag_path = str(
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")) + ".bag"
        logger.info(SEP)
        logger.info("Saving trajectories to " + dest_bag_path + "...")
        bag = rosbag.Bag(dest_bag_path, 'w')
        try:
            for name, traj in trajectories.items():
                dest_topic = os.path.splitext(os.path.basename(name))[0]
                frame_id = traj.meta[
                    "frame_id"] if "frame_id" in traj.meta else ""
                file_interface.write_bag_trajectory(bag, traj, dest_topic,
                                                    frame_id)
            if args.ref:
                dest_topic = os.path.splitext(os.path.basename(args.ref))[0]
                frame_id = ref_traj.meta[
                    "frame_id"] if "frame_id" in ref_traj.meta else ""
                file_interface.write_bag_trajectory(bag, ref_traj, dest_topic,
                                                    frame_id)
        finally:
            bag.close()


if __name__ == '__main__':
    from evo import entry_points
    entry_points.traj()
