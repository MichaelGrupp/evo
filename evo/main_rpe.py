#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
main executable for calculating the relative pose error (RPE) metric
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

SEP = "-" * 80  # separator line


def parser():
    import argparse
    basic_desc = "relative pose error (RPE) metric app"
    lic = "(c) michael.grupp@tum.de"
    shared_parser = argparse.ArgumentParser(add_help=False)
    algo_opts = shared_parser.add_argument_group("algorithm options")
    output_opts = shared_parser.add_argument_group("output options")
    usability_opts = shared_parser.add_argument_group("usability options")
    algo_opts.add_argument("-r", "--pose_relation",
                           help="pose relation on which the RPE is based", default="trans_part",
                           choices=["full", "trans_part", "rot_part", "angle_deg", "angle_rad"])
    algo_opts.add_argument("-d", "--delta", help="delta between relative poses",
                           default=1, type=float)
    algo_opts.add_argument("-t", "--delta_tol", help="relative delta tolerance for all_pairs mode",
                           default=0.1, type=float)
    algo_opts.add_argument("-u", "--delta_unit",
                           help="unit of delta - `f` (frames), `d` (deg), `r` (rad), `m`(meters)",
                           default="f", choices=['f', 'd', 'r', 'm'])
    algo_opts.add_argument("--all_pairs", help="use all possible pairs (incompatible with plot)",
                           action="store_true")
    algo_opts.add_argument("-a", "--align", help="alignment with Umeyama's method (no scale) - "
                                                 "only useful for plotting with RPE",
                           action="store_true")
    algo_opts.add_argument("-s", "--correct_scale", help="correct scale with Umeyama's method",
                           action="store_true")
    output_opts.add_argument("-p", "--plot", help="show plot window", action="store_true")
    output_opts.add_argument("--plot_mode", help="the axes for  plot projection",
                             default=None, choices=["xy", "yx", "xz", "zx", "yz", "xyz"])
    output_opts.add_argument("--save_plot", help="path to save plot", default=None)
    output_opts.add_argument("--serialize_plot", help="path to serialize plot (experimental)",
                             default=None)
    output_opts.add_argument("--save_results", help=".zip file path to store results")
    usability_opts.add_argument("--no_warnings", help="no warnings requiring user confirmation",
                                action="store_true")
    usability_opts.add_argument("-v", "--verbose", help="verbose output", action="store_true")
    usability_opts.add_argument("--silent", help="don't print any output", action="store_true")
    usability_opts.add_argument("--debug", help="verbose output with additional debug info",
                                action="store_true")
    usability_opts.add_argument("-c", "--config",
                                help=".json file with parameters (priority over command line args)")

    main_parser = argparse.ArgumentParser(description="%s %s" % (basic_desc, lic))
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True
    kitti_parser = sub_parsers.add_parser("kitti", description="%s for KITTI pose files - %s"
                                                               % (basic_desc, lic),
                                          parents=[shared_parser])
    kitti_parser.add_argument("ref_file", help="reference pose file (ground truth)")
    kitti_parser.add_argument("est_file", help="estimated pose file")

    tum_parser = sub_parsers.add_parser("tum", description="%s for TUM trajectory files - %s"
                                                           % (basic_desc, lic),
                                        parents=[shared_parser])
    tum_parser.add_argument("ref_file", help="reference trajectory file")
    tum_parser.add_argument("est_file", help="estimated trajectory file")
    tum_parser.add_argument("--t_max_diff",
                            help="maximum timestamp difference for data association",
                            default=0.01, type=float)
    tum_parser.add_argument("--t_offset", help="constant timestamp offset for data association",
                            default=0.0, type=float)

    euroc_parser = sub_parsers.add_parser("euroc", description="%s for EuRoC MAV .csv's - %s"
                                                               % (basic_desc, lic),
                                          parents=[shared_parser])
    euroc_parser.add_argument("state_gt_csv",
                              help="ground truth: <seq>/mav0/state_groundtruth_estimate0/data.csv")
    euroc_parser.add_argument("est_file", help="estimated trajectory file in TUM format")
    euroc_parser.add_argument("--t_max_diff",
                              help="maximum timestamp difference for data association",
                              default=0.01, type=float)
    euroc_parser.add_argument("--t_offset", help="constant timestamp offset for data association",
                              default=0.0, type=float)

    bag_parser = sub_parsers.add_parser("bag", description="%s for ROS bag files - %s"
                                                           % (basic_desc, lic),
                                        parents=[shared_parser])
    bag_parser.add_argument("bag", help="ROS bag file")
    bag_parser.add_argument("ref_topic", help="reference geometry_msgs/PoseStamped topic")
    bag_parser.add_argument("est_topic", help="estimated geometry_msgs/PoseStamped topic")
    bag_parser.add_argument("--t_max_diff",
                            help="maximum timestamp difference for data association",
                            default=0.01, type=float)
    bag_parser.add_argument("--t_offset", help="constant timestamp offset for data association",
                            default=0.0, type=float)
    return main_parser


def main_rpe(traj_ref, traj_est, pose_relation, delta, delta_unit,
             rel_delta_tol=0.1, all_pairs=False, align=False, correct_scale=False,
             ref_name="", est_name="", show_plot=False, save_plot=None,
             plot_mode=None, save_results=None, no_warnings=False, support_loop=False,
             serialize_plot=None):

    from evo.core import metrics, result
    from evo.core import trajectory
    from evo.tools import file_interface
    from evo.tools.settings import SETTINGS

    if (show_plot or save_plot or serialize_plot) and all_pairs:
        raise metrics.MetricsException("all_pairs mode cannot be used with plotting functions")

    only_scale = correct_scale and not align
    if align or correct_scale:
        logging.debug(SEP)
        if only_scale:
            logging.debug("correcting scale...")
        else:
            logging.debug("aligning using Umeyama's method..."
                          + (" (with scale correction)" if correct_scale else ""))
        traj_est = trajectory.align_trajectory(traj_est, traj_ref, correct_scale, only_scale)
    logging.debug(SEP)

    # calculate RPE
    data = (traj_ref, traj_est)
    rpe_metric = metrics.RPE(pose_relation, delta, delta_unit, rel_delta_tol, all_pairs)
    rpe_metric.process_data(data)
    rpe_statistics = rpe_metric.get_all_statistics()

    title = str(rpe_metric)
    if align and not correct_scale:
        title += "\n(with SE(3) Umeyama alignment)"
    elif align and correct_scale:
        title += "\n(with Sim(3) Umeyama alignment)"
    elif only_scale:
        title += "\n(scale corrected)"
    else:
        title += "\n(not aligned)"

    rpe_result = result.from_metric(rpe_metric, title, ref_name, est_name)
    logging.debug(SEP)
    logging.info(rpe_result.pretty_str())

    # restrict trajectories to delta ids
    if support_loop:
        # avoid overwriting if called repeatedly e.g. in Jupyter notebook
        import copy
        traj_ref = copy.deepcopy(traj_ref)
        traj_est = copy.deepcopy(traj_est)
    traj_ref.reduce_to_ids(rpe_metric.delta_ids)
    traj_est.reduce_to_ids(rpe_metric.delta_ids)
    if isinstance(traj_est, trajectory.PoseTrajectory3D) and not all_pairs:
        seconds_from_start = [t - traj_est.timestamps[0] for t in traj_est.timestamps]
        rpe_result.add_np_array("seconds_from_start", seconds_from_start)
    else:
        seconds_from_start = None

    if show_plot or save_plot or serialize_plot and not all_pairs:
        from evo.tools import plot
        import matplotlib.pyplot as plt
        logging.debug(SEP)
        logging.debug("plotting results... ")
        fig1 = plt.figure(figsize=(SETTINGS.plot_figsize[0], SETTINGS.plot_figsize[1]))
        # metric values
        plot.error_array(fig1, rpe_metric.error, x_array=seconds_from_start,
                            statistics=rpe_statistics,
                            name="RPE" + (
                            " (" + rpe_metric.unit.value + ")") if rpe_metric.unit else "",
                            title=title, xlabel="$t$ (s)" if seconds_from_start else "index")
        # info text
        if SETTINGS.plot_info_text and est_name and ref_name:
            ax = fig1.gca()
            ax.text(0, -0.12, "estimate:  " + est_name + "\nreference: " + ref_name,
                    transform=ax.transAxes, fontsize=8, color="gray")
        # trajectory colormapped
        fig2 = plt.figure(figsize=(SETTINGS.plot_figsize[0], SETTINGS.plot_figsize[1]))
        plot_mode = plot_mode if plot_mode is not None else plot.PlotMode.xyz
        ax = plot.prepare_axis(fig2, plot_mode)
        plot.traj(ax, plot_mode, traj_ref, '--', 'gray', 'reference',
                    alpha=0 if SETTINGS.plot_hideref else 1)
        plot.traj_colormap(ax, traj_est, rpe_metric.error, plot_mode,
                            min_map=rpe_statistics["min"], max_map=rpe_statistics["max"],
                            title="RPE mapped onto trajectory")
        fig2.axes.append(ax)
        plot_collection = plot.PlotCollection(title)
        plot_collection.add_figure("raw", fig1)
        plot_collection.add_figure("map", fig2)
        if show_plot:
            plot_collection.show()
        if save_plot:
            plot_collection.export(save_plot, confirm_overwrite=not no_warnings)
        if serialize_plot:
            logging.debug(SEP)
            plot_collection.serialize(serialize_plot, confirm_overwrite=not no_warnings)

    if save_results:
        logging.debug(SEP)
        if SETTINGS.save_traj_in_zip:
            rpe_result.add_trajectory("traj_ref", traj_ref)
            rpe_result.add_trajectory("traj_est", traj_est)
        file_interface.save_res_file(save_results, rpe_result, confirm_overwrite=not no_warnings)

    return rpe_result


def run(args):
    from evo.core import metrics
    from evo.tools import file_interface, settings

    settings.configure_logging(args.verbose, args.silent, args.debug)
    if args.debug:
        import pprint
        logging.debug("main_parser config:\n"
                      + pprint.pformat({arg: getattr(args, arg) for arg in vars(args)}) + "\n")
    logging.debug(SEP)

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

    delta_unit = None
    if args.delta_unit == "f":
        delta_unit = metrics.Unit.frames
    elif args.delta_unit == "d":
        delta_unit = metrics.Unit.degrees
    elif args.delta_unit == "r":
        delta_unit = metrics.Unit.radians
    elif args.delta_unit == "m":
        delta_unit = metrics.Unit.meters

    traj_ref, traj_est, stamps_est = None, None, None
    ref_name, est_name = "", ""
    plot_mode = None  # no plot imports unless really needed (slow)
    if args.subcommand == "tum":
        traj_ref, traj_est = file_interface.load_assoc_tum_trajectories(
            args.ref_file,
            args.est_file,
            args.t_max_diff,
            args.t_offset,
        )
        ref_name, est_name = args.ref_file, args.est_file
        if args.plot or args.save_plot:
            from evo.tools.plot import PlotMode
            plot_mode = PlotMode.xyz if not args.plot_mode else PlotMode[args.plot_mode]
    elif args.subcommand == "kitti":
        traj_ref = file_interface.read_kitti_poses_file(args.ref_file)
        traj_est = file_interface.read_kitti_poses_file(args.est_file)
        ref_name, est_name = args.ref_file, args.est_file
        if args.plot or args.save_plot:
            from evo.tools.plot import PlotMode
            plot_mode = PlotMode.xz if not args.plot_mode else PlotMode[args.plot_mode]
    elif args.subcommand == "euroc":
        args.align = True
        logging.info("forcing trajectory alignment implicitly (EuRoC ground truth is in IMU frame)")
        logging.debug(SEP)
        traj_ref, traj_est = file_interface.load_assoc_euroc_trajectories(
            args.state_gt_csv,
            args.est_file,
            args.t_max_diff,
            args.t_offset,
        )
        ref_name, est_name = args.state_gt_csv, args.est_file
        if args.plot or args.save_plot:
            from evo.tools.plot import PlotMode
            plot_mode = PlotMode.xyz if not args.plot_mode else PlotMode[args.plot_mode]
    elif args.subcommand == "bag":
        import rosbag
        logging.debug("opening bag file " + args.bag)
        bag = rosbag.Bag(args.bag, 'r')
        try:
            traj_ref, traj_est = file_interface.load_assoc_bag_trajectories(
                bag,
                args.ref_topic,
                args.est_topic,
                args.t_max_diff,
                args.t_offset,
            )
        finally:
            bag.close()
        ref_name, est_name = args.ref_topic, args.est_topic
        if args.plot or args.save_plot:
            from evo.tools.plot import PlotMode
            plot_mode = PlotMode.xy if not args.plot_mode else PlotMode[args.plot_mode]

    main_rpe(traj_ref, traj_est, pose_relation, args.delta, delta_unit, args.delta_tol,
             args.all_pairs, args.align, args.correct_scale,
             ref_name, est_name, args.plot, args.save_plot, plot_mode,
             args.save_results, args.no_warnings, serialize_plot=args.serialize_plot)


if __name__ == '__main__':
    from evo import entry_points
    entry_points.rpe()
