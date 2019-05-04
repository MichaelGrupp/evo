# -*- coding: UTF8 -*-
"""
Low- and high-level read/write functions for different file formats.
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

import binascii
import csv
import io
import json
import logging
import os
import zipfile

import numpy as np

from evo import EvoException
import evo.core.lie_algebra as lie
import evo.core.transformations as tr
from evo.core import result
from evo.core.trajectory import PosePath3D, PoseTrajectory3D
from evo.tools import user

logger = logging.getLogger(__name__)

SUPPORTED_ROS_MSGS = {
    "geometry_msgs/PoseStamped", "geometry_msgs/PoseWithCovarianceStamped",
    "geometry_msgs/TransformStamped", "nav_msgs/Odometry"
}


class FileInterfaceException(EvoException):
    pass


def has_utf8_bom(file_path):
    """
    Checks if the given file starts with a UTF8 BOM
    wikipedia.org/wiki/Byte_order_mark
    """
    size_bytes = os.path.getsize(file_path)
    if size_bytes < 3:
        return False
    with open(file_path, 'rb') as f:
        return not int(binascii.hexlify(f.read(3)), 16) ^ 0xEFBBBF


def csv_read_matrix(file_path, delim=',', comment_str="#"):
    """
    directly parse a csv-like file into a matrix
    :param file_path: path of csv file (or file handle)
    :param delim: delimiter character
    :param comment_str: string indicating a comment line to ignore
    :return: 2D list with raw data (string)
    """
    if hasattr(file_path, 'read'):  # if file handle
        generator = (line for line in file_path
                     if not line.startswith(comment_str))
        reader = csv.reader(generator, delimiter=delim)
        mat = [row for row in reader]
    else:
        if not os.path.isfile(file_path):
            raise FileInterfaceException("csv file " + str(file_path) +
                                         " does not exist")
        skip_3_bytes = has_utf8_bom(file_path)
        with open(file_path) as f:
            if skip_3_bytes:
                f.seek(3)
            generator = (line for line in f
                         if not line.startswith(comment_str))
            reader = csv.reader(generator, delimiter=delim)
            mat = [row for row in reader]
    return mat


def read_tum_trajectory_file(file_path):
    """
    parses trajectory file in TUM format (timestamp tx ty tz qx qy qz qw)
    :param file_path: the trajectory file path (or file handle)
    :return: trajectory.PoseTrajectory3D object
    """
    raw_mat = csv_read_matrix(file_path, delim=" ", comment_str="#")
    error_msg = ("TUM trajectory files must have 8 entries per row "
                 "and no trailing delimiter at the end of the rows (space)")
    if len(raw_mat) > 0 and len(raw_mat[0]) != 8:
        raise FileInterfaceException(error_msg)
    try:
        mat = np.array(raw_mat).astype(float)
    except ValueError:
        raise FileInterfaceException(error_msg)
    stamps = mat[:, 0]  # n x 1
    xyz = mat[:, 1:4]  # n x 3
    quat = mat[:, 4:]  # n x 4
    quat = np.roll(quat, 1, axis=1)  # shift 1 column -> w in front column
    if not hasattr(file_path, 'read'):  # if not file handle
        logger.debug("Loaded {} stamps and poses from: {}".format(
            len(stamps), file_path))
    return PoseTrajectory3D(xyz, quat, stamps)


def write_tum_trajectory_file(file_path, traj, confirm_overwrite=False):
    """
    :param file_path: desired text file for trajectory (string or handle)
    :param traj: trajectory.PoseTrajectory3D
    :param confirm_overwrite: whether to require user interaction
           to overwrite existing files
    """
    if isinstance(file_path, str) and confirm_overwrite:
        if not user.check_and_confirm_overwrite(file_path):
            return
    if not isinstance(traj, PoseTrajectory3D):
        raise FileInterfaceException(
            "trajectory must be a PoseTrajectory3D object")
    stamps = traj.timestamps
    xyz = traj.positions_xyz
    # shift -1 column -> w in back column
    quat = np.roll(traj.orientations_quat_wxyz, -1, axis=1)
    mat = np.column_stack((stamps, xyz, quat))
    np.savetxt(file_path, mat, delimiter=" ")
    if isinstance(file_path, str):
        logger.info("Trajectory saved to: " + file_path)


def read_kitti_poses_file(file_path):
    """
    parses pose file in KITTI format (first 3 rows of SE(3) matrix per line)
    :param file_path: the trajectory file path (or file handle)
    :return: trajectory.PosePath3D
    """
    raw_mat = csv_read_matrix(file_path, delim=" ", comment_str="#")
    error_msg = ("KITTI pose files must have 12 entries per row "
                 "and no trailing delimiter at the end of the rows (space)")
    if len(raw_mat) > 0 and len(raw_mat[0]) != 12:
        raise FileInterfaceException(error_msg)
    try:
        mat = np.array(raw_mat).astype(float)
    except ValueError:
        raise FileInterfaceException(error_msg)
    # yapf: disable
    poses = [np.array([[r[0], r[1], r[2], r[3]],
                       [r[4], r[5], r[6], r[7]],
                       [r[8], r[9], r[10], r[11]],
                       [0, 0, 0, 1]]) for r in mat]
    # yapf: enable
    if not hasattr(file_path, 'read'):  # if not file handle
        logger.debug("Loaded {} poses from: {}".format(len(poses), file_path))
    return PosePath3D(poses_se3=poses)


def write_kitti_poses_file(file_path, traj, confirm_overwrite=False):
    """
    :param file_path: desired text file for trajectory (string or handle)
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D
    :param confirm_overwrite: whether to require user interaction
           to overwrite existing files
    """
    if isinstance(file_path, str) and confirm_overwrite:
        if not user.check_and_confirm_overwrite(file_path):
            return
    # first 3 rows  of SE(3) matrix flattened
    poses_flat = [p.flatten()[:-4] for p in traj.poses_se3]
    np.savetxt(file_path, poses_flat, delimiter=' ')
    if isinstance(file_path, str):
        logger.info("Poses saved to: " + file_path)


def read_euroc_csv_trajectory(file_path):
    """
    parses ground truth trajectory from EuRoC MAV state estimate .csv
    :param file_path: <sequence>/mav0/state_groundtruth_estimate0/data.csv
    :return: trajectory.PoseTrajectory3D object
    """
    raw_mat = csv_read_matrix(file_path, delim=",", comment_str="#")
    error_msg = ("EuRoC MAV state ground truth must have 17 entries per row "
                 "and no trailing delimiter at the end of the rows (comma)")
    if len(raw_mat) > 0 and len(raw_mat[0]) != 17:
        raise FileInterfaceException(error_msg)
    try:
        mat = np.array(raw_mat).astype(float)
    except ValueError:
        raise FileInterfaceException(error_msg)
    stamps = np.divide(mat[:, 0], 1e9)  # n x 1  -  nanoseconds to seconds
    xyz = mat[:, 1:4]  # n x 3
    quat = mat[:, 4:8]  # n x 4
    logger.debug("Loaded {} stamps and poses from: {}".format(
        len(stamps), file_path))
    return PoseTrajectory3D(xyz, quat, stamps)


def _get_xyz_quat_from_transform_stamped(msg):
    xyz = [
        msg.transform.translation.x, msg.transform.translation.y,
        msg.transform.translation.z
    ]
    quat = [
        msg.transform.rotation.w, msg.transform.rotation.x,
        msg.transform.rotation.y, msg.transform.rotation.z
    ]
    return xyz, quat


def _get_xyz_quat_from_pose_or_odometry_msg(msg):
    # Make nav_msgs/Odometry behave like geometry_msgs/PoseStamped.
    while not hasattr(msg.pose, 'position') and not hasattr(
            msg.pose, 'orientation'):
        msg = msg.pose
    xyz = [msg.pose.position.x, msg.pose.position.y, msg.pose.position.z]
    quat = [
        msg.pose.orientation.w, msg.pose.orientation.x, msg.pose.orientation.y,
        msg.pose.orientation.z
    ]
    return xyz, quat


def read_bag_trajectory(bag_handle, topic):
    """
    :param bag_handle: opened bag handle, from rosbag.Bag(...)
    :param topic: trajectory topic of supported message type
    :return: trajectory.PoseTrajectory3D
    """
    if not bag_handle.get_message_count(topic) > 0:
        raise FileInterfaceException("no messages for topic '" + topic +
                                     "' in bag")
    msg_type = bag_handle.get_type_and_topic_info().topics[topic].msg_type
    if msg_type not in SUPPORTED_ROS_MSGS:
        raise FileInterfaceException(
            "unsupported message type: {}".format(msg_type))

    # Choose appropriate message conversion.
    if msg_type == "geometry_msgs/TransformStamped":
        get_xyz_quat = _get_xyz_quat_from_transform_stamped
    else:
        get_xyz_quat = _get_xyz_quat_from_pose_or_odometry_msg

    stamps, xyz, quat = [], [], []
    for topic, msg, _ in bag_handle.read_messages(topic):
        # Use the header timestamps (converted to seconds).
        t = msg.header.stamp
        stamps.append(t.secs + (t.nsecs * 1e-9))
        xyz_t, quat_t = get_xyz_quat(msg)
        xyz.append(xyz_t)
        quat.append(quat_t)
    logger.debug("Loaded {} {} messages of topic: {}".format(
        len(stamps), msg_type, topic))
    generator = bag_handle.read_messages(topic)
    _, first_msg, _ = next(generator)
    frame_id = first_msg.header.frame_id
    return PoseTrajectory3D(xyz, quat, stamps, meta={"frame_id": frame_id})


def write_bag_trajectory(bag_handle, traj, topic_name, frame_id=""):
    """
    :param bag_handle: opened bag handle, from rosbag.Bag(...)
    :param traj: trajectory.PoseTrajectory3D
    :param topic_name: the desired topic name for the trajectory
    :param frame_id: optional ROS frame_id
    """
    import rospy
    from geometry_msgs.msg import PoseStamped
    if not isinstance(traj, PoseTrajectory3D):
        raise FileInterfaceException(
            "trajectory must be a PoseTrajectory3D object")
    for stamp, xyz, quat in zip(traj.timestamps, traj.positions_xyz,
                                traj.orientations_quat_wxyz):
        p = PoseStamped()
        p.header.stamp = rospy.Time.from_sec(stamp)
        p.header.frame_id = frame_id
        p.pose.position.x = xyz[0]
        p.pose.position.y = xyz[1]
        p.pose.position.z = xyz[2]
        p.pose.orientation.w = quat[0]
        p.pose.orientation.x = quat[1]
        p.pose.orientation.y = quat[2]
        p.pose.orientation.z = quat[3]
        bag_handle.write(topic_name, p, t=p.header.stamp)
    logger.info("Saved geometry_msgs/PoseStamped topic: " + topic_name)


def save_res_file(zip_path, result_obj, confirm_overwrite=False):
    """
    save results of a pose error metric (pe_metric) to a zip file
    :param zip_path: path to zip file
    :param result_obj: evo.core.result.Result instance
    :param confirm_overwrite: whether to require user interaction
           to overwrite existing files
    """
    from tempfile import TemporaryFile
    logger.debug("Saving results to " + zip_path + "...")
    if confirm_overwrite and not user.check_and_confirm_overwrite(zip_path):
        return
    with zipfile.ZipFile(zip_path, 'w') as archive:
        archive.writestr("info.json", json.dumps(result_obj.info))
        archive.writestr("stats.json", json.dumps(result_obj.stats))
        for name, array in result_obj.np_arrays.items():
            tmp_file = TemporaryFile()
            np.save(tmp_file, array)
            tmp_file.seek(0)
            archive.writestr("{}.npz".format(name), tmp_file.read())
            tmp_file.close()
        for name, traj in result_obj.trajectories.items():
            tmp_file = TemporaryFile()
            if type(traj) is PosePath3D:
                fmt_suffix = ".kitti"
                write_kitti_poses_file(tmp_file, traj)
            elif type(traj) is PoseTrajectory3D:
                fmt_suffix = ".tum"
                write_tum_trajectory_file(tmp_file, traj)
            else:
                raise FileInterfaceException(
                    "unknown format of trajectory {}".format(name))
            tmp_file.seek(0)
            archive.writestr("{}{}".format(name, fmt_suffix), tmp_file.read())
            tmp_file.close()


def load_res_file(zip_path, load_trajectories=False):
    """
    load contents of a result .zip file saved with save_res_file(...)
    :param zip_path: path to zip file
    :param load_trajectories: set to True to load also the (backup) trajectories
    :return: evo.core.result.Result instance
    """
    logger.debug("Loading result from {} ...".format(zip_path))
    result_obj = result.Result()
    with zipfile.ZipFile(zip_path, mode='r') as archive:
        file_list = archive.namelist()
        if not {"error_array.npz", "info.json", "stats.json"
                } <= set(file_list):
            logger.warning("{} not suitable for evo_res".format(zip_path))
        npz_files = [n for n in archive.namelist() if n.endswith(".npz")]
        for filename in npz_files:
            with io.BytesIO(archive.read(filename)) as f:
                array = np.load(f)
                name = os.path.splitext(os.path.basename(filename))[0]
                result_obj.add_np_array(name, array)
        if load_trajectories:
            tum_files = [n for n in archive.namelist() if n.endswith(".tum")]
            for filename in tum_files:
                with io.TextIOWrapper(archive.open(filename, mode='r')) as f:
                    traj = read_tum_trajectory_file(f)
                    name = os.path.splitext(os.path.basename(filename))[0]
                    result_obj.add_trajectory(name, traj)
            kitti_files = [
                n for n in archive.namelist() if n.endswith(".kitti")
            ]
            for filename in kitti_files:
                with io.TextIOWrapper(archive.open(filename, mode='r')) as f:
                    traj = read_kitti_poses_file(f)
                    name = os.path.splitext(os.path.basename(filename))[0]
                    result_obj.add_trajectory(name, traj)
        result_obj.info = json.loads(archive.read("info.json").decode("utf-8"))
        result_obj.stats = json.loads(
            archive.read("stats.json").decode("utf-8"))
    return result_obj


def load_transform_json(json_path):
    """
    load a transformation stored in xyz + quaternion format in a .json file
    :param json_path: path to the .json file
    :return: t (SE(3) matrix)
    """
    with open(json_path, 'r') as tf_file:
        data = json.load(tf_file)
        keys = ("x", "y", "z", "qx", "qy", "qz", "qw")
        if not all(key in data for key in keys):
            raise FileInterfaceException(
                "invalid transform file - expected keys " + str(keys))
        xyz = np.array([data["x"], data["y"], data["z"]])
        quat = np.array([data["qw"], data["qx"], data["qy"], data["qz"]])
        t = lie.se3(lie.so3_from_se3(tr.quaternion_matrix(quat)), xyz)
        return t
