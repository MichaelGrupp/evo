#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
Main executable for calculating the absolute pose error (APE) metric.
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

from enum import Enum

logger = logging.getLogger(__name__)

SEP = "-" * 80  # separator line


def parser():
    import argparse
    basic_desc = "absolute pose error (APE) metric app"
    lic = "(c) michael.grupp@tum.de"
    shared_parser = argparse.ArgumentParser(add_help=False)
    algo_opts = shared_parser.add_argument_group("algorithm options")
    output_opts = shared_parser.add_argument_group("output options")
    usability_opts = shared_parser.add_argument_group("usability options")
    algo_opts.add_argument(
        "-r", "--pose_relation", default="trans_part",
        help="pose relation on which the APE is based",
        choices=["full", "trans_part", "rot_part", "angle_deg", "angle_rad"])
    algo_opts.add_argument(
        "-a", "--align",
        help="alignment with Umeyama's method (no scale)",
        action="store_true")
    algo_opts.add_argument(
        "-s", "--correct_scale", action="store_true",
        help="correct scale with Umeyama's method")
    output_opts.add_argument(
        "-p", "--plot", action="store_true",
        help="show plot window",)
    output_opts.add_argument(
        "--plot_mode", default=None,
        help="the axes for plot projection",
        choices=["xy", "yx", "xz", "zx", "yz", "xyz"])
    output_opts.add_argument(
        "--plot_colormap_max", type=float,
        help="the upper bound used for the color map plot "
        "(default: maximum error value)")
    output_opts.add_argument(
        "--plot_colormap_min", type=float,
        help="the lower bound used for the color map plot "
             "(default: minimum error value)")
    output_opts.add_argument(
        "--plot_colormap_max_percentile", type=float,
        help="percentile of the error distribution to be used "
             "as the upper bound of the color map plot "
             "(in %%, overrides --plot_colormap_min)")
    output_opts.add_argument(
        "--save_plot", default=None,
        help="path to save plot")
    output_opts.add_argument(
        "--serialize_plot", default=None,
        help="path to serialize plot (experimental)")
    output_opts.add_argument(
        "--save_results",
        help=".zip file path to store results")
    usability_opts.add_argument(
        "--no_warnings", action="store_true",
        help="no warnings requiring user confirmation")
    usability_opts.add_argument(
        "-v", "--verbose", action="store_true",
        help="verbose output")
    usability_opts.add_argument(
        "--silent", action="store_true",
        help="don't print any output")
    usability_opts.add_argument(
        "--debug", action="store_true",
        help="verbose output with additional debug info")
    usability_opts.add_argument(
        "-c", "--config",
        help=".json file with parameters (priority over command line args)")

    main_parser = argparse.ArgumentParser(
        description="%s %s" % (basic_desc, lic))
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True

    kitti_parser = sub_parsers.add_parser(
        "kitti", parents=[shared_parser],
        description="{} for KITTI pose files - {}".format(basic_desc, lic))
    kitti_parser.add_argument(
        "ref_file", help="reference pose file (ground truth)")
    kitti_parser.add_argument("est_file", help="estimated pose file")

    tum_parser = sub_parsers.add_parser(
        "tum", parents=[shared_parser],
        description="{} for TUM trajectory files - {}".format(basic_desc, lic))
    tum_parser.add_argument("ref_file", help="reference trajectory file")
    tum_parser.add_argument("est_file", help="estimated trajectory file")

    euroc_parser = sub_parsers.add_parser(
        "euroc", parents=[shared_parser],
        description="{} for EuRoC MAV files - {}".format(basic_desc, lic))
    euroc_parser.add_argument(
        "state_gt_csv",
        help="ground truth: <seq>/mav0/state_groundtruth_estimate0/data.csv")
    euroc_parser.add_argument(
        "est_file", help="estimated trajectory file in TUM format")

    bag_parser = sub_parsers.add_parser(
        "bag", parents=[shared_parser],
        description="{} for ROS bag files - {}".format(basic_desc, lic))
    bag_parser.add_argument("bag", help="ROS bag file")
    bag_parser.add_argument(
        "ref_topic", help="reference geometry_msgs/PoseStamped topic")
    bag_parser.add_argument(
        "est_topic", help="estimated geometry_msgs/PoseStamped topic")

    # Add time-sync options to parser of trajectory formats.
    for trajectory_parser in {bag_parser, euroc_parser, tum_parser}:
        trajectory_parser.add_argument(
            "--t_max_diff", type=float, default=0.01,
            help="maximum timestamp difference for data association")
        trajectory_parser.add_argument(
            "--t_offset", type=float, default=0.0,
            help="constant timestamp offset for data association")

    return main_parser


def main_ape(traj_ref, traj_est, pose_relation, align=True,
             correct_scale=False, ref_name="", est_name="",
             show_plot=False, save_plot=None, plot_mode=None,
             save_results=None, no_warnings=False, serialize_plot=None,
             plot_colormap_max=None, plot_colormap_min=None,
             plot_colormap_max_percentile=None):

    from evo.core import metrics
    from evo.core import trajectory
    from evo.tools import file_interface
    from evo.tools.settings import SETTINGS

    import numpy as np

    # Align the trajectories.
    only_scale = correct_scale and not align
    if align or correct_scale:
        logger.debug(SEP)
        traj_est = trajectory.align_trajectory(
            traj_est, traj_ref, correct_scale, only_scale)

    # Calculate APE.
    logger.debug(SEP)
    data = (traj_ref, traj_est)
    ape_metric = metrics.APE(pose_relation)
    ape_metric.process_data(data)
    ape_statistics = ape_metric.get_all_statistics()

    title = str(ape_metric)
    if align and not correct_scale:
        title += "\n(with SE(3) Umeyama alignment)"
    elif align and correct_scale:
        title += "\n(with Sim(3) Umeyama alignment)"
    elif only_scale:
        title += "\n(scale corrected)"
    else:
        title += "\n(not aligned)"

    ape_result = ape_metric.get_result(ref_name, est_name)
    logger.debug(SEP)
    logger.info(ape_result.pretty_str())

    if isinstance(traj_est, trajectory.PoseTrajectory3D):
        seconds_from_start = [t - traj_est.timestamps[0]
                              for t in traj_est.timestamps]
        ape_result.add_np_array("seconds_from_start", seconds_from_start)
        ape_result.add_np_array("timestamps", traj_est.timestamps)
    else:
        seconds_from_start = None

    ape_result.add_trajectory(ref_name, traj_ref)
    ape_result.add_trajectory(est_name, traj_est)

    if show_plot or save_plot or serialize_plot:
        from evo.tools import plot
        import matplotlib.pyplot as plt
        logger.debug(SEP)
        logger.debug("Plotting results... ")

        # Plot the raw metric values.
        fig1 = plt.figure(figsize=SETTINGS.plot_figsize)
        plot.error_array(
            fig1, ape_metric.error,
            x_array=seconds_from_start,
            statistics=ape_statistics,
            name="APE" + (" (" + ape_metric.unit.value
                          + ")") if ape_metric.unit else "",
            title=title,
            xlabel="$t$ (s)" if seconds_from_start else "index")

        # Plot the values color-mapped onto the trajectory.
        fig2 = plt.figure(figsize=SETTINGS.plot_figsize)
        ax = plot.prepare_axis(fig2, plot_mode)
        plot.traj(ax, plot_mode, traj_ref, '--', 'gray', 'reference',
                  alpha=0.0 if SETTINGS.plot_hideref else 1.0)

        if plot_colormap_min is None:
            plot_colormap_min = ape_statistics["min"]
        if plot_colormap_max is None:
            plot_colormap_max = ape_statistics["max"]
        if plot_colormap_max_percentile is not None:
            plot_colormap_max = np.percentile(
                ape_result.np_arrays["error_array"],
                plot_colormap_max_percentile)

        plot.traj_colormap(ax, traj_est, ape_metric.error, plot_mode,
                           min_map=plot_colormap_min,
                           max_map=plot_colormap_max,
                           title="APE mapped onto trajectory")
        fig2.axes.append(ax)

        plot_collection = plot.PlotCollection(title)
        plot_collection.add_figure("raw", fig1)
        plot_collection.add_figure("map", fig2)
        if show_plot:
            plot_collection.show()
        if save_plot:
            plot_collection.export(
                save_plot, confirm_overwrite=not no_warnings)
        if serialize_plot:
            logger.debug(SEP)
            plot_collection.serialize(
                serialize_plot, confirm_overwrite=not no_warnings)



def run(args):
    from evo.core import metrics, sync
    from evo.tools import file_interface, log

    log.configure_logging(args.verbose, args.silent, args.debug)
    if args.debug:
        from pprint import pformat
        parser_str = pformat({arg: getattr(args, arg) for arg in vars(args)})
        logger.debug("main_parser config:\n{}".format(parser_str))
    logger.debug(SEP)

    pose_relation = None
    if args.pose_relation == "full":
        pose_relation = metrics.PoseRelation.full_transformation
    elif args.pose_relation == "rot_part":
        pose_relation = metrics.PoseRelation.rotation_part
    elif args.pose_relation == "trans_part":
        pose_relation = metrics.PoseRelation.translation_part
    elif args.pose_relation == "angle_deg":
        pose_relation = metrics.PoseRelation.rotation_angle_deg
    elif args.pose_relation == "angle_rad":
        pose_relation = metrics.PoseRelation.rotation_angle_rad

    if args.subcommand == "tum":
        traj_ref = file_interface.read_tum_trajectory_file(args.ref_file)
        traj_est = file_interface.read_tum_trajectory_file(args.est_file)
        ref_name, est_name = args.ref_file, args.est_file

    elif args.subcommand == "kitti":
        traj_ref = file_interface.read_kitti_poses_file(args.ref_file)
        traj_est = file_interface.read_kitti_poses_file(args.est_file)
        ref_name, est_name = args.ref_file, args.est_file
    elif args.subcommand == "euroc":
        args.align = True
        logger.info("Forcing trajectory alignment implicitly "
                    "(EuRoC ground truth is in IMU frame).")
        logger.debug(SEP)
        traj_ref = file_interface.read_euroc_csv_trajectory(args.state_gt_csv)
        traj_est = file_interface.read_tum_trajectory_file(args.est_file)
        ref_name, est_name = args.ref_file, args.est_file
    elif args.subcommand == "bag":
        import rosbag
        logger.debug("Opening bag file " + args.bag)
        bag = rosbag.Bag(args.bag, 'r')
        try:
            traj_ref = file_interface.read_bag_trajectory(bag, args.ref_topic)
            traj_est = file_interface.read_bag_trajectory(bag, args.est_topic)
            ref_name, est_name = args.ref_file, args.est_file
        finally:
            bag.close()
    else:
        raise KeyError("unknown sub-command: {}".format(args.subcommand))

    if args.subcommand != "kitti":
        logger.debug("Synchronizing trajectories...")
        traj_ref, traj_est = sync.associate_trajectories(
            traj_ref, traj_est, args.t_max_diff, args.t_offset,
            first_name=ref_name, snd_name=est_name)

    result =

    if args.show_plot or args.save_plot or args.serialize_plot:

    if args.save_results:
        logger.debug(SEP)
        if SETTINGS.save_traj_in_zip:
            result.add_trajectory("traj_ref", traj_ref)
            result.add_trajectory("traj_est", traj_est)
        file_interface.save_res_file(
            args.save_results, result, confirm_overwrite=not args.no_warnings)

    main_ape(
        traj_ref=traj_ref,
        traj_est=traj_est,
        pose_relation=pose_relation,
        align=args.align,
        correct_scale=args.correct_scale,
        ref_name=ref_name,
        est_name=est_name,
        show_plot=args.plot,
        save_plot=args.save_plot,
        plot_mode=args.plot_mode,
        save_results=args.save_results,
        no_warnings=args.no_warnings,
        serialize_plot=args.serialize_plot,
        plot_colormap_max=args.plot_colormap_max,
        plot_colormap_min=args.plot_colormap_min,
        plot_colormap_max_percentile=args.plot_colormap_max_percentile,
    )


if __name__ == '__main__':
    from evo import entry_points
    entry_points.ape()
