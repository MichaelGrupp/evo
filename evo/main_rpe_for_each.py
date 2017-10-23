#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
main executable for calculating the sub-sequence-wise averaged relative pose error (RPE) metric
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
    basic_desc = "sub-sequence-wise averaged relative pose error (RPE) metric app"
    lic = "(c) michael.grupp@tum.de"
    shared_parser = argparse.ArgumentParser(add_help=False)
    algo_opts = shared_parser.add_argument_group("algorithm options")
    output_opts = shared_parser.add_argument_group("output options")
    usability_opts = shared_parser.add_argument_group("usability options")
    algo_opts.add_argument("-r", "--pose_relation",
                           help="pose relation on which the RPE is based", default="trans_part",
                           choices=["trans_part", "angle_deg", "angle_rad"])
    algo_opts.add_argument("-m", "--mode", help="the mode on which sequence averaging is based",
                           default="path", choices=["speed", "path", "angle", "angular_speed"])
    algo_opts.add_argument("-b", "--bins", help="bin values of the sub-sequences",
                           nargs='+', type=float)
    algo_opts.add_argument("-t", "--tols",
                           help="rel. tolerances to include sub-sequences in the bins",
                           nargs='+', type=float)
    algo_opts.add_argument("-a", "--align", help="alignment with Umeyama's method (no scale) - "
                                                 "only useful for plotting with RPE",
                           action="store_true")
    algo_opts.add_argument("-s", "--correct_scale", help="correct scale with Umeyama's method",
                           action="store_true")
    output_opts.add_argument("-p", "--plot", help="show plot window", action="store_true")
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

    bag_parser = sub_parsers.add_parser("bag",
                                        description="%s for ROS bag files - %s" % (basic_desc, lic),
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


def main_rpe_for_each(traj_ref, traj_est, pose_relation, mode, bins, rel_tols,
                      align=False, correct_scale=False, ref_name="", est_name="",
                      show_plot=False, save_plot=None, save_results=None, no_warnings=False,
                      serialize_plot=None):

    from evo.algorithms import metrics
    from evo.algorithms import filters
    from evo.algorithms import trajectory
    from evo.tools import file_interface
    from evo.tools.settings import SETTINGS

    if not bins or not rel_tols:
        raise RuntimeError("bins and tolerances must have more than one element")
    if len(bins) != len(rel_tols):
        raise RuntimeError("bins and tolerances must have the same number of elements")
    if mode in {"speed", "angular_speed"} and traj_est is trajectory.PosePath3D:
        raise RuntimeError("timestamps are required for mode: " + mode)

    bin_unit = None
    if mode == "speed":
        bin_unit = metrics.VelUnit.meters_per_sec
    elif mode == "path":
        bin_unit = metrics.Unit.meters
    elif mode == "angle":
        bin_unit = metrics.Unit.degrees
    elif mode == "angular_speed":
        bin_unit = metrics.VelUnit.degrees_per_sec

    rpe_unit = None
    if pose_relation is metrics.PoseRelation.translation_part:
        rpe_unit = metrics.Unit.meters
    elif pose_relation is metrics.PoseRelation.rotation_angle_deg:
        rpe_unit = metrics.Unit.degrees
    elif pose_relation is metrics.PoseRelation.rotation_angle_rad:
        rpe_unit = metrics.Unit.radians

    correct_only_scale = correct_scale and not align
    if align or correct_scale:
        logging.debug(SEP)
        if correct_only_scale:
            logging.debug("correcting scale...")
        else:
            logging.debug("aligning using Umeyama's method..."
                          + (" (with scale correction)" if correct_scale else ""))
        traj_est = trajectory.align_trajectory(traj_est, traj_ref, correct_scale,
                                               correct_only_scale)

    results = []
    for bin, rel_tol, in zip(bins, rel_tols):
        logging.debug(SEP)
        logging.info(
            "calculating RPE for each sub-sequence of " + str(bin) + " (" + bin_unit.value + ")")

        tol = bin * rel_tol
        id_pairs = []
        if mode == "path":
            id_pairs = filters.filter_pairs_by_path(traj_ref.poses_se3, bin, tol, all_pairs=True)
        elif mode == "angle":
            id_pairs = filters.filter_pairs_by_angle(traj_ref.poses_se3, bin, tol, degrees=True)
        elif mode == "speed":
            id_pairs = filters.filter_pairs_by_speed(traj_ref.poses_se3, traj_ref.timestamps,
                                                     bin, tol)
        elif mode == "angular_speed":
            id_pairs = filters.filter_pairs_by_angular_speed(traj_ref.poses_se3,
                                                             traj_ref.timestamps, bin, tol, True)

        if len(id_pairs) == 0:
            raise RuntimeError("bin " + str(bin) + " (" + str(bin_unit.value) + ") "
                               + "produced empty index list - try other values")

        # calculate RPE with all IDs (delta 1 frames)
        data = (traj_ref, traj_est)
        # the delta here has nothing to do with the bin - 1f delta just to use all poses of the bin
        rpe_metric = metrics.RPE(pose_relation, delta=1, delta_unit=metrics.Unit.frames,
                                 all_pairs=True)
        rpe_metric.process_data(data, id_pairs)
        mean = rpe_metric.get_statistic(metrics.StatisticsType.mean)
        results.append(mean)

    if SETTINGS.plot_usetex:
        mode.replace("_", "\_")
    title = "mean RPE w.r.t. " + pose_relation.value + "\nfor different " + mode + " sub-sequences"
    if align and not correct_scale:
        title += "\n(with SE(3) Umeyama alignment)"
    elif align and correct_scale:
        title += "\n(with Sim(3) Umeyama alignment)"
    elif correct_only_scale:
        title += "\n(scale corrected)"
    else:
        title += "\n(not aligned)"
    logging.debug(SEP)
    logging.info("\n" + title + "\n")
    res_str = ""
    for bin, result in zip(bins, results):
        res_str += "{:>10}".format(str(bin) + "(" + bin_unit.value + ")")
        res_str += "\t" + "{0:.6f}".format(result) + "\n"
    logging.info(res_str)

    if show_plot or save_plot or serialize_plot:
        from evo.tools import plot
        import matplotlib.pyplot as plt
        plot_collection = plot.PlotCollection(title)
        fig = plt.figure(figsize=(SETTINGS.plot_figsize[0], SETTINGS.plot_figsize[1]))
        plot.error_array(fig, results, x_array=bins,
                         name="mean RPE" + (" (" + rpe_unit.value + ")") if rpe_unit else "",
                         marker="o", title=title,
                         xlabel=mode + " sub-sequences " + " (" + bin_unit.value + ")")
        # info text
        if SETTINGS.plot_info_text and est_name and ref_name:
            ax = fig.gca()
            ax.text(0, -0.12, "estimate:  " + est_name + "\nreference: " + ref_name,
                    transform=ax.transAxes, fontsize=8, color="gray")
        plt.title(title)
        plot_collection.add_figure("raw", fig)
        if show_plot:
            plot_collection.show()
        if save_plot:
            plot_collection.export(save_plot, confirm_overwrite=not no_warnings)
        if serialize_plot:
            logging.debug(SEP)
            plot_collection.serialize(serialize_plot, confirm_overwrite=not no_warnings)

    rpe_statistics = {bin: result for bin, result in zip(bins, results)}
    if save_results:
        logging.debug(SEP)

        # utility class to trick save_res_file
        class Metric:
            unit = rpe_unit
            error = results

        file_interface.save_res_file(save_results, Metric, rpe_statistics,
                                     title, ref_name, est_name, bins, traj_ref, traj_est,
                                     xlabel=mode + " sub-sequences " + " (" + bin_unit.value + ")",
                                     confirm_overwrite=not no_warnings)

    return rpe_statistics, results


def run(args):
    import sys
    from evo.algorithms import metrics
    from evo.tools import file_interface, settings

    # manually check bins and tols arguments to allow them to be in config files
    if not args.bins or not args.tols:
        logging.error("the following arguments are required: -b/--bins, -t/--tols")
        sys.exit(1)

    settings.configure_logging(args.verbose, args.silent, args.debug)
    if args.debug:
        import pprint
        logging.debug("main_parser config:\n"
                      + pprint.pformat({arg: getattr(args, arg) for arg in vars(args)}) + "\n")
    logging.debug(SEP)

    pose_relation = None
    if args.pose_relation == "trans_part":
        pose_relation = metrics.PoseRelation.translation_part
    elif args.pose_relation == "angle_deg":
        pose_relation = metrics.PoseRelation.rotation_angle_deg
    elif args.pose_relation == "angle_rad":
        pose_relation = metrics.PoseRelation.rotation_angle_rad

    traj_ref, traj_est, stamps_est = None, None, None
    ref_name, est_name = "", ""
    if args.subcommand == "tum":
        traj_ref, traj_est = file_interface.load_assoc_tum_trajectories(
            args.ref_file,
            args.est_file,
            args.t_max_diff,
            args.t_offset,
        )
        ref_name, est_name = args.ref_file, args.est_file
    elif args.subcommand == "kitti":
        traj_ref = file_interface.read_kitti_poses_file(args.ref_file)
        traj_est = file_interface.read_kitti_poses_file(args.est_file)
        ref_name, est_name = args.ref_file, args.est_file
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

    main_rpe_for_each(traj_ref, traj_est, pose_relation, args.mode, args.bins, args.tols,
                      args.align, args.correct_scale, ref_name, est_name,
                      args.plot, args.save_plot, args.save_results, args.no_warnings,
                      serialize_plot=args.serialize_plot)


if __name__ == '__main__':
    from evo import entry_points
    entry_points.rpe_for_each()
