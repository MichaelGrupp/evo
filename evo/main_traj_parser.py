import argparse

from evo.tools.settings import SETTINGS


def parser() -> argparse.ArgumentParser:
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
        "--transform_left", help="path to a file with a transformation"
        " to apply to the trajectories (left multiplicative)")
    algo_opts.add_argument(
        "--transform_right", help="path to a file with a transformation"
        " to apply to the trajectories (right_multiplicative)")
    algo_opts.add_argument(
        "--propagate_transform", help="with --transform_right: transform each "
        "pose and propagate resulting drift to the next.", action="store_true")
    algo_opts.add_argument("--invert_transform",
                           help="invert the transformation of the file",
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
    algo_opts.add_argument(
        "--project_to_plane", type=str, choices=["xy", "xz", "yz"],
        help="Projects the trajectories to 2D in the desired plane. "
        "This is done after potential 3D alignment & transformation steps.")
    algo_opts.add_argument("--downsample", type=int,
                           help="Downsample trajectories to max N poses.")
    algo_opts.add_argument(
        "--motion_filter", type=float, nargs=2,
        metavar=("DISTANCE", "ANGLE_DEGREES"),
        help="Filters out poses if the distance or angle to the previous one "
        " is below the threshold distance or angle. "
        "Angle is expected in degrees.")
    output_opts.add_argument("-p", "--plot", help="show plot window",
                             action="store_true")
    output_opts.add_argument(
        "--plot_relative_time", action="store_true",
        help="show timestamps relative to the start of the reference")
    output_opts.add_argument(
        "--plot_mode", help="the axes for  plot projection",
        default=SETTINGS.plot_mode_default,
        choices=["xy", "xz", "yx", "yz", "zx", "zy", "xyz"])
    output_opts.add_argument(
        "--ros_map_yaml", help="yaml file of an ROS 2D map image (.pgm/.png)"
        " that will be drawn into the plot", default=None)
    output_opts.add_argument("--save_plot", help="path to save plot",
                             default=None)
    output_opts.add_argument("--save_table",
                             help="path to save table with statistics",
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
    output_opts.add_argument("--save_as_bag2",
                             help="save trajectories in ROS2 bag as <date>",
                             action="store_true")
    output_opts.add_argument("--logfile", help="Local logfile path.",
                             default=None)
    usability_opts.add_argument("--no_warnings",
                                help="no warnings requiring user confirmation",
                                action="store_true")
    usability_opts.add_argument("-v", "--verbose", help="verbose output",
                                action="store_true")
    usability_opts.add_argument(
        "--show_full_names", help="don't shorten input file paths when "
        "displaying trajectory names", action="store_true")
    usability_opts.add_argument("--silent", help="don't print any output",
                                action="store_true")
    usability_opts.add_argument(
        "--debug", help="verbose output with additional debug info",
        action="store_true")
    usability_opts.add_argument(
        "-c", "--config",
        help=".json file with parameters (priority over command line args)")

    main_parser = argparse.ArgumentParser(description="%s %s" %
                                          (basic_desc, lic))
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

    bag2_parser = sub_parsers.add_parser(
        "bag2", description="%s for ROS2 bag files - %s" % (basic_desc, lic),
        parents=[shared_parser])
    bag2_parser.add_argument("bag", help="ROS2 bag file")
    bag2_parser.add_argument("topics", help="multiple trajectory topics",
                             nargs='*')
    bag2_parser.add_argument("--all_topics",
                             help="use all compatible topics in the bag",
                             action="store_true")
    return main_parser
