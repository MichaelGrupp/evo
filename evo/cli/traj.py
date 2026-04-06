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
import logging
import pprint
import sys
from pathlib import Path

from natsort import natsorted

import evo.core.lie_algebra as lie
from evo.core import trajectory
from evo.core.trajectory import Plane
from evo.core.trajectory_bundle import TrajectoryBundle
from evo.tools import file_interface, log
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80


def die(msg):
    logger.error(msg)
    sys.exit(1)


def load_trajectories(args) -> TrajectoryBundle:
    """
    Load trajectories from files or bags based on the subcommand.
    :return: a TrajectoryBundle with all loaded trajectories and reference
    """
    bundle = TrajectoryBundle()
    if args.subcommand == "tum":
        for traj_file in args.traj_files:
            if traj_file == args.ref:
                continue
            bundle.add(
                traj_file,
                file_interface.read_tum_trajectory_file(traj_file),
            )
        if args.ref:
            bundle.add_reference(
                file_interface.read_tum_trajectory_file(args.ref)
            )
    elif args.subcommand == "kitti":
        for pose_file in args.pose_files:
            if pose_file == args.ref:
                continue
            bundle.add(
                pose_file,
                file_interface.read_kitti_poses_file(pose_file),
            )
        if args.ref:
            bundle.add_reference(
                file_interface.read_kitti_poses_file(args.ref)
            )
    elif args.subcommand == "euroc":
        for csv_file in args.state_gt_csv:
            if csv_file == args.ref:
                continue
            bundle.add(
                csv_file,
                file_interface.read_euroc_csv_trajectory(csv_file),
            )
        if args.ref:
            bundle.add_reference(
                file_interface.read_euroc_csv_trajectory(args.ref)
            )
    elif args.subcommand in ("bag", "bag2", "mcap"):
        if not (args.topics or args.all_topics):
            die("No topics used - specify topics or set --all_topics.")
        if not Path(args.bag).exists():
            raise file_interface.FileInterfaceException(
                f"File doesn't exist: {args.bag}"
            )
        logger.debug("Opening bag file " + args.bag)
        if args.subcommand in ("bag2", "mcap"):
            from rosbags.rosbag2 import Reader as Rosbag2Reader

            bag: Rosbag1Reader | Rosbag2Reader = Rosbag2Reader(args.bag)
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
                    topics_str = "\n- ".join(file_interface.SUPPORTED_ROS_MSGS)
                    die(
                        f"Found no topics of supported types:\n\n- {topics_str}"
                        f"\n\nIf you want to load TF trajectories, "
                        f"specify them like: /tf:map.base_link"
                    )
            else:
                topics = args.topics
            for topic in topics:
                if topic == args.ref:
                    continue
                bundle.add(
                    topic,
                    file_interface.read_bag_trajectory(
                        bag, topic, cache_tf_tree=True
                    ),
                )
            if args.ref:
                bundle.add_reference(
                    file_interface.read_bag_trajectory(
                        bag, args.ref, cache_tf_tree=True
                    )
                )
        finally:
            bag.close()
    return bundle


# TODO refactor
def print_traj_info(name, traj, verbose=False, full_check=False):
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
                        stat_str += "\n\t" + stat + "\t" + f"{value:.6f}"
                    else:
                        stat_str += value
            except trajectory.TrajectoryException as e:
                stat_str += "\n\terror - " + str(e)
            logger.info("stats:" + stat_str)
    else:
        logger.info("infos:\t" + str(traj))


def to_filestem(name: str, args: argparse.Namespace) -> str:
    if args.subcommand in ("bag", "bag2", "mcap"):
        if name.startswith("/"):
            name = name[1:]
        name = name.replace(":", "/")  # TF ID
        return name.replace("/", "_")
    return Path(name).stem


def to_topic_name(name: str, args: argparse.Namespace) -> str:
    if args.subcommand in ("bag", "bag2", "mcap"):
        return name.replace(":", "/")
    return "/" + Path(name).stem.replace(" ", "_")


def to_compact_name(
    name: str, args: argparse.Namespace, latex_friendly=False
) -> str:
    if not args.show_full_names and args.subcommand not in (
        "bag",
        "bag2",
        "mcap",
    ):
        # /some/super/long/path/that/nobody/cares/about/traj.txt  ->  traj
        name = Path(name).stem
    if latex_friendly:
        name = name.replace("_", "\\_")
    return name


def print_infos(bundle, args):
    """Log trajectory info for all trajectories and reference."""
    for name, traj in bundle.trajectories.items():
        print_traj_info(
            to_compact_name(name, args), traj, args.verbose, args.full_check
        )
    if args.ref:
        print_traj_info(
            to_compact_name(args.ref, args),
            bundle.ref_traj,
            args.verbose,
            args.full_check,
        )


def export(bundle, args):
    """Export trajectories to TUM, KITTI, bag or table format."""
    if args.save_as_tum:
        logger.info(SEP)
        for name, traj in bundle.trajectories.items():
            dest = to_filestem(name, args) + ".tum"
            file_interface.write_tum_trajectory_file(
                dest, traj, confirm_overwrite=not args.no_warnings
            )
        if args.ref:
            dest = to_filestem(args.ref, args) + ".tum"
            file_interface.write_tum_trajectory_file(
                dest,
                bundle.ref_traj,
                confirm_overwrite=not args.no_warnings,
            )
    if args.save_as_kitti:
        logger.info(SEP)
        for name, traj in bundle.trajectories.items():
            dest = to_filestem(name, args) + ".kitti"
            file_interface.write_kitti_poses_file(
                dest, traj, confirm_overwrite=not args.no_warnings
            )
        if args.ref:
            dest = to_filestem(args.ref, args) + ".kitti"
            file_interface.write_kitti_poses_file(
                dest,
                bundle.ref_traj,
                confirm_overwrite=not args.no_warnings,
            )
    if args.save_as_bag or args.save_as_bag2:
        from rosbags.rosbag1 import Writer as Rosbag1Writer
        from rosbags.rosbag2 import Writer as Rosbag2Writer

        writers = []
        if args.save_as_bag:
            dest_bag_path = (
                str(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
                + ".bag"
            )
            writers.append(Rosbag1Writer(dest_bag_path))
        if args.save_as_bag2:
            dest_bag_path = str(
                datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            )
            writers.append(
                Rosbag2Writer(
                    dest_bag_path,
                    version=SETTINGS.ros2_bag_format_version,
                    storage_plugin=file_interface.ros2_bag_storage_plugin(
                        SETTINGS.ros2_bag_storage_plugin
                    ),
                )
            )
        for writer in writers:
            logger.info(SEP)
            logger.info("Saving trajectories to " + str(writer.path) + "...")
            try:
                writer.open()
                for name, traj in bundle.trajectories.items():
                    dest_topic = to_topic_name(name, args)
                    frame_id = (
                        traj.meta["frame_id"]
                        if "frame_id" in traj.meta
                        else SETTINGS.ros_fallback_frame_id
                    )
                    file_interface.write_bag_trajectory(
                        writer, traj, dest_topic, frame_id
                    )
                if args.ref:
                    dest_topic = to_topic_name(args.ref, args)
                    frame_id = (
                        bundle.ref_traj.meta["frame_id"]
                        if "frame_id" in bundle.ref_traj.meta
                        else SETTINGS.ros_fallback_frame_id
                    )
                    file_interface.write_bag_trajectory(
                        writer, bundle.ref_traj, dest_topic, frame_id
                    )
            finally:
                writer.close()

    if args.save_table:
        from evo.tools import pandas_bridge

        logger.debug(SEP)
        df = pandas_bridge.trajectories_stats_to_df(bundle.trajectories)
        pandas_bridge.save_df_as_table(
            df, args.save_table, confirm_overwrite=not args.no_warnings
        )


def run(args):
    """
    Main entry point for evo_traj.
    """
    log.configure_logging(
        verbose=args.verbose,
        silent=args.silent,
        debug=args.debug,
        local_logfile=args.logfile,
    )
    if args.debug:
        logger.debug(
            "main_parser config:\n"
            + pprint.pformat({arg: getattr(args, arg) for arg in vars(args)})
            + "\n"
        )
    logger.debug(SEP)

    bundle = load_trajectories(args)

    if args.downsample:
        logger.debug(SEP)
        logger.info(
            "Downsampling trajectories to max %s poses.", args.downsample
        )
        bundle.downsample(args.downsample)

    if args.motion_filter:
        logger.debug(SEP)
        distance_threshold = args.motion_filter[0]
        angle_threshold = args.motion_filter[1]
        logger.info(
            "Filtering trajectories with motion filter thresholds:"
            " %f m, %f deg",
            distance_threshold,
            angle_threshold,
        )
        bundle.motion_filter(distance_threshold, angle_threshold)

    if args.merge:
        if args.subcommand == "kitti":
            die("Can't merge KITTI files.")
        bundle.merge()

    if args.t_offset:
        logger.debug(SEP)
        for name in bundle.trajectories:
            logger.info(f"Adding time offset to {name}: {args.t_offset} (s)")
        bundle.apply_time_offset(args.t_offset)

    if args.n_to_align != -1 and not (args.align or args.correct_scale):
        die("--n_to_align is useless without --align or/and --correct_scale")

    needs_sync = (args.subcommand == "kitti" and bundle.ref_traj) or any(
        (args.sync, args.align, args.correct_scale, args.align_origin)
    )
    if needs_sync:
        if not args.ref:
            die("Can't align or sync without a reference! (--ref)  *grunt*")
        if args.subcommand == "kitti":
            bundle.mark_synced()
        else:
            logger.debug(SEP)
            bundle.sync(max_diff=args.t_max_diff)
        if args.align or args.correct_scale:
            logger.debug(SEP)
            bundle.align(
                correct_scale=args.correct_scale,
                correct_only_scale=args.correct_scale and not args.align,
                n=args.n_to_align,
            )
        if args.align_origin:
            logger.debug(SEP)
            bundle.align_origin()

    if args.transform_left or args.transform_right:
        tf_type = "left" if args.transform_left else "right"
        tf_path = args.transform_left or args.transform_right
        transform = file_interface.load_transform(tf_path)
        if args.invert_transform:
            transform = lie.se3_inverse(transform)
        logger.debug(SEP)
        logger.debug(
            f"Applying a {tf_type}-multiplicative transformation:"
            f"\n{transform}"
        )
        bundle.apply_transform(
            transform,
            right_mul=bool(args.transform_right),
            propagate=args.propagate_transform,
        )

    if args.project_to_plane:
        plane = Plane(args.project_to_plane)
        logger.debug(SEP)
        logger.debug(f"Projecting trajectories to {plane.value} plane.")
        bundle.project(plane)

    print_infos(bundle, args)

    if args.rerun:
        from evo.cli.traj_rerun import send_bundle_to_rerun

        send_bundle_to_rerun(bundle, args, to_compact_name)
    if args.plot or args.save_plot:
        from evo.cli.traj_plot import plot_trajectories

        plot_trajectories(bundle, args, to_compact_name)

    export(bundle, args)
