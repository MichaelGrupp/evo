#!/usr/bin/env python
# -*- coding: utf-8 -*-

from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
import numpy as np

DESC = "Combine KITTI poses and timestamps files to a TUM trajectory file"


def kitti_poses_and_timestamps_to_trajectory(poses_file, timestamp_file):
    pose_path = file_interface.read_kitti_poses_file(poses_file)
    raw_timestamps_mat = file_interface.csv_read_matrix(timestamp_file)
    error_msg = ("timestamp file must have same row with KITTI poses file")
    if len(raw_timestamps_mat) > 0 and len(raw_timestamps_mat[0]) != 1 and len(timestamps) != pose_path.num_poses:
        raise file_interface.FileInterfaceException(error_msg)
    try:
        timestamps_mat = np.array(raw_timestamps_mat).astype(float)
    except ValueError:
        raise file_interface.FileInterfaceException(error_msg)
    return PoseTrajectory3D(poses_se3=pose_path.poses_se3, timestamps=timestamps_mat)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=DESC)
    parser.add_argument("poses_file", help="pose path file in KITTI format")
    parser.add_argument(
        "timestamp_file", help="KITTI timestamp file of the poses")
    parser.add_argument(
        "trajectory_out", help="output file path for trajectory in TUM format")
    args = parser.parse_args()
    trajectory = kitti_poses_and_timestamps_to_trajectory(
        args.poses_file, args.timestamp_file)
    file_interface.write_tum_trajectory_file(args.trajectory_out, trajectory)
