import argparse

from evo.core import units
from evo.tools.settings import SETTINGS


def parser() -> argparse.ArgumentParser:
    basic_desc = "Relative pose error (RPE) metric app"
    lic = "(c) evo authors"

    shared_parser = argparse.ArgumentParser(add_help=False)
    algo_opts = shared_parser.add_argument_group("algorithm options")
    output_opts = shared_parser.add_argument_group("output options")
    usability_opts = shared_parser.add_argument_group("usability options")

    algo_opts.add_argument(
        "-r", "--pose_relation", default="trans_part",
        help="pose relation on which the RPE is based", choices=[
            "full", "trans_part", "rot_part", "angle_deg", "angle_rad",
            "point_distance", "point_distance_error_ratio"
        ])
    algo_opts.add_argument("-s", "--correct_scale", action="store_true",
                           help="correct scale with Umeyama's method")
    algo_opts.add_argument(
        "--n_to_align",
        help="the number of poses to use for Umeyama alignment, "
        "counted from the start (default: all)", default=-1, type=int)
    algo_opts.add_argument("-d", "--delta", type=float, default=1,
                           help="delta between relative poses")
    algo_opts.add_argument("-t", "--delta_tol", type=float, default=0.1,
                           help="relative delta tolerance for all_pairs mode")
    algo_opts.add_argument(
        "-u", "--delta_unit", default="f",
        help="unit of delta - `f` (frames), `d` (deg), `r` (rad), `m`(meters)",
        choices=['f', 'd', 'r', 'm'])
    algo_opts.add_argument(
        "--all_pairs",
        action="store_true",
        help="use all pairs instead of consecutive pairs",
    )
    algo_opts.add_argument(
        "--pairs_from_reference", action="store_true",
        help="determine the pose pairs from the reference trajectory")
    algo_opts.add_argument(
        "--change_unit", default=None,
        choices=[u.value for u in (units.ANGLE_UNITS + units.LENGTH_UNITS)],
        help="Changes the output unit of the metric, if possible.")
    algo_opts.add_argument(
        "--project_to_plane", type=str, choices=["xy", "xz", "yz"],
        help="Projects the trajectories to 2D in the desired plane.")
    algo_opts.add_argument("--downsample", type=int,
                           help="Downsample trajectories to max N poses.")
    algo_opts.add_argument(
        "--motion_filter", type=float, nargs=2,
        metavar=("DISTANCE", "ANGLE_DEGREES"),
        help="Filters out poses if the distance or angle to the previous one "
        " is below the threshold distance or angle. "
        "Angle is expected in degrees.")

    align_opts = algo_opts.add_mutually_exclusive_group()
    align_opts.add_argument("-a", "--align",
                            help="alignment with Umeyama's method (no scale)",
                            action="store_true")
    align_opts.add_argument(
        "--align_origin",
        help="align the trajectory origin to the origin of the reference "
        "trajectory", action="store_true")

    output_opts.add_argument(
        "-p",
        "--plot",
        action="store_true",
        help="show plot window",
    )
    output_opts.add_argument(
        "--plot_mode", default=SETTINGS.plot_mode_default,
        help="the axes for plot projection",
        choices=["xy", "xz", "yx", "yz", "zx", "zy", "xyz"])
    output_opts.add_argument(
        "--plot_x_dimension", choices=["index", "seconds",
                                       "distances"], default="seconds",
        help="dimension that is used on the x-axis of the raw value plot"
        "(default: seconds, or index if no timestamps are present)")
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
        "(in %%, overrides --plot_colormap_max)")
    output_opts.add_argument(
        "--plot_full_ref",
        action="store_true",
        help="plot the full, unsynchronized reference trajectory",
    )
    output_opts.add_argument(
        "--ros_map_yaml", help="yaml file of an ROS 2D map image (.pgm/.png)"
        " that will be drawn into the plot", default=None)
    output_opts.add_argument(
        "--map_tile", help="CRS code of a map tile layer to add to the plot. "
        "Requires geo-referenced poses and the contextily package installed.")
    output_opts.add_argument("--save_plot", default=None,
                             help="path to save plot")
    output_opts.add_argument("--serialize_plot", default=None,
                             help="path to serialize plot (experimental)")
    output_opts.add_argument("--save_results",
                             help=".zip file path to store results")
    output_opts.add_argument("--logfile", help="Local logfile path.",
                             default=None)
    usability_opts.add_argument("--no_warnings", action="store_true",
                                help="no warnings requiring user confirmation")
    usability_opts.add_argument("-v", "--verbose", action="store_true",
                                help="verbose output")
    usability_opts.add_argument("--silent", action="store_true",
                                help="don't print any output")
    usability_opts.add_argument(
        "--debug", action="store_true",
        help="verbose output with additional debug info")
    usability_opts.add_argument(
        "-c", "--config",
        help=".json file with parameters (priority over command line args)")

    main_parser = argparse.ArgumentParser(
        description="{} {}".format(basic_desc, lic))
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True

    kitti_parser = sub_parsers.add_parser(
        "kitti", parents=[shared_parser],
        description="{} for KITTI pose files - {}".format(basic_desc, lic))
    kitti_parser.add_argument("ref_file",
                              help="reference pose file (ground truth)")
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
    euroc_parser.add_argument("est_file",
                              help="estimated trajectory file in TUM format")

    bag_parser = sub_parsers.add_parser(
        "bag", parents=[shared_parser],
        description="{} for ROS bag files - {}".format(basic_desc, lic))
    bag_parser.add_argument("bag", help="ROS bag file")
    bag_parser.add_argument("ref_topic", help="reference trajectory topic")
    bag_parser.add_argument("est_topic", help="estimated trajectory topic")

    bag2_parser = sub_parsers.add_parser(
        "bag2", parents=[shared_parser],
        description="{} for ROS2 bag files - {}".format(basic_desc, lic))
    bag2_parser.add_argument("bag", help="ROS2 bag file")
    bag2_parser.add_argument("ref_topic", help="reference trajectory topic")
    bag2_parser.add_argument("est_topic", help="estimated trajectory topic")

    # Add time-sync options to parser of trajectory formats.
    for trajectory_parser in {
            bag_parser, bag2_parser, euroc_parser, tum_parser
    }:
        trajectory_parser.add_argument(
            "--t_max_diff", type=float, default=0.01,
            help="maximum timestamp difference for data association")
        trajectory_parser.add_argument(
            "--t_offset", type=float, default=0.0,
            help="constant timestamp offset for data association")
        trajectory_parser.add_argument(
            "--t_start", type=float, default=None,
            help="only use data with timestamps "
            "greater or equal this start time")
        trajectory_parser.add_argument(
            "--t_end", type=float, default=None,
            help="only use data with timestamps less or equal this end time")

    return main_parser
