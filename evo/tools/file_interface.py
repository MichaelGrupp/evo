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
import typing
import zipfile

import numpy as np
from rosbags.rosbag1 import (Reader as Rosbag1Reader, Writer as Rosbag1Writer)
from rosbags.rosbag2 import (Reader as Rosbag2Reader, Writer as Rosbag2Writer)
from rosbags.serde import deserialize_cdr, ros1_to_cdr, serialize_cdr
from rosbags.serde.serdes import cdr_to_ros1

from evo import EvoException
import evo.core.lie_algebra as lie
import evo.core.transformations as tr
from evo.core import result
from evo.core.trajectory import PosePath3D, PoseTrajectory3D
from evo.tools import user, tf_id

logger = logging.getLogger(__name__)

# TODO: ensure that this works for both ROS1 and ROS2.
SUPPORTED_ROS_MSGS = {
    "geometry_msgs/msg/PoseStamped",
    "geometry_msgs/msg/PoseWithCovarianceStamped",
    "geometry_msgs/msg/TransformStamped", "nav_msgs/msg/Odometry"
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


def read_tum_trajectory_file(file_path) -> PoseTrajectory3D:
    """
    parses trajectory file in TUM format (timestamp tx ty tz qx qy qz qw)
    :param file_path: the trajectory file path (or file handle)
    :return: trajectory.PoseTrajectory3D object
    """
    raw_mat = csv_read_matrix(file_path, delim=" ", comment_str="#")
    error_msg = ("TUM trajectory files must have 8 entries per row "
                 "and no trailing delimiter at the end of the rows (space)")
    if not raw_mat or (len(raw_mat) > 0 and len(raw_mat[0]) != 8):
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


def write_tum_trajectory_file(file_path, traj: PoseTrajectory3D,
                              confirm_overwrite: bool = False) -> None:
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


def read_kitti_poses_file(file_path) -> PosePath3D:
    """
    parses pose file in KITTI format (first 3 rows of SE(3) matrix per line)
    :param file_path: the trajectory file path (or file handle)
    :return: trajectory.PosePath3D
    """
    raw_mat = csv_read_matrix(file_path, delim=" ", comment_str="#")
    error_msg = ("KITTI pose files must have 12 entries per row "
                 "and no trailing delimiter at the end of the rows (space)")
    if not raw_mat or (len(raw_mat) > 0 and len(raw_mat[0]) != 12):
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


def write_kitti_poses_file(file_path, traj: PosePath3D,
                           confirm_overwrite: bool = False) -> None:
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


def read_euroc_csv_trajectory(file_path) -> PoseTrajectory3D:
    """
    parses ground truth trajectory from EuRoC MAV state estimate .csv
    :param file_path: <sequence>/mav0/state_groundtruth_estimate0/data.csv
    :return: trajectory.PoseTrajectory3D object
    """
    raw_mat = csv_read_matrix(file_path, delim=",", comment_str="#")
    error_msg = (
        "EuRoC format ground truth must have at least 8 entries per row "
        "and no trailing delimiter at the end of the rows (comma)")
    if not raw_mat or (len(raw_mat) > 0 and len(raw_mat[0]) < 8):
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


def _get_xyz_quat_from_transform_stamped(msg) -> typing.Tuple[list, list]:
    xyz = [
        msg.transform.translation.x, msg.transform.translation.y,
        msg.transform.translation.z
    ]
    quat = [
        msg.transform.rotation.w, msg.transform.rotation.x,
        msg.transform.rotation.y, msg.transform.rotation.z
    ]
    return xyz, quat


def _get_xyz_quat_from_pose_or_odometry_msg(msg) -> typing.Tuple[list, list]:
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


def get_supported_topics(
        reader: typing.Union[Rosbag1Reader, Rosbag2Reader]) -> list:
    """
    :param bag_handle: opened bag handle, from rosbag.Bag(...)
    :return: list of ROS topics that are supported by this module
    """
    return sorted([
        c.topic for c in reader.connections.values()
        if c.msgtype in SUPPORTED_ROS_MSGS
    ])


def read_bag_trajectory(reader: typing.Union[Rosbag1Reader, Rosbag2Reader],
                        topic: str) -> PoseTrajectory3D:
    """
    :param reader: opened bag reader (rosbags.rosbag2 or rosbags.rosbag1)
    :param topic: trajectory topic of supported message type,
                  or a TF trajectory ID (e.g.: '/tf:map.base_link' )
    :return: trajectory.PoseTrajectory3D
    """
    if not isinstance(reader, (Rosbag1Reader, Rosbag2Reader)):
        raise FileInterfaceException(
            "reader must be a rosbags.rosbags1.reader.Reader "
            "or rosbags.rosbags2.reader.Reader - "
            "rosbag.Bag() is not supported by evo anymore")

    # TODO: Support TF also with ROS2 bags.
    if isinstance(reader, Rosbag1Reader):
        # Use TfCache instead if it's a TF transform ID.
        if tf_id.check_id(topic):
            from evo.tools import tf_cache
            return tf_cache.instance().get_trajectory(reader, identifier=topic)

    if not reader.message_count > 0:
        raise FileInterfaceException("no messages for topic '" + topic +
                                     "' in bag")

    msg_type = reader.topics[topic].msgtype
    if msg_type not in SUPPORTED_ROS_MSGS:
        raise FileInterfaceException(
            "unsupported message type: {}".format(msg_type))

    # Choose appropriate message conversion.
    # TODO: ensure that this works for both ROS1 and ROS2.
    if msg_type == "geometry_msgs/TransformStamped":
        get_xyz_quat = _get_xyz_quat_from_transform_stamped
    else:
        get_xyz_quat = _get_xyz_quat_from_pose_or_odometry_msg

    stamps, xyz, quat = [], [], []

    connections = [c for c in reader.connections.values() if c.topic == topic]
    for connection, _, rawdata in reader.messages(
            connections=connections):  # type: ignore
        if isinstance(reader, Rosbag1Reader):
            msg = deserialize_cdr(ros1_to_cdr(rawdata, connection.msgtype),
                                  connection.msgtype)
        else:
            msg = deserialize_cdr(rawdata, connection.msgtype)
        # Use the header timestamps (converted to seconds).
        # Note: msg/stamp is a rosbags type here, not native ROS.
        t = msg.header.stamp
        stamps.append(t.sec + (t.nanosec * 1e-9))
        xyz_t, quat_t = get_xyz_quat(msg)
        xyz.append(xyz_t)
        quat.append(quat_t)

    logger.debug("Loaded {} {} messages of topic: {}".format(
        len(stamps), msg_type, topic))

    (connection, _, rawdata) = list(
        reader.messages(connections=connections))[0]  # type: ignore
    if isinstance(reader, Rosbag1Reader):
        first_msg = deserialize_cdr(ros1_to_cdr(rawdata, connection.msgtype),
                                    connection.msgtype)
    else:
        first_msg = deserialize_cdr(rawdata, connection.msgtype)
    frame_id = first_msg.header.frame_id
    return PoseTrajectory3D(np.array(xyz), np.array(quat), np.array(stamps),
                            meta={"frame_id": frame_id})


def write_bag_trajectory(writer, traj: PoseTrajectory3D, topic_name: str,
                         frame_id: str = "") -> None:
    """
    :param writer: opened bag writer (rosbags.rosbag2 or rosbags.rosbag1)
    :param traj: trajectory.PoseTrajectory3D
    :param topic_name: the desired topic name for the trajectory
    :param frame_id: optional ROS frame_id
    """
    from rosbags.typesys.types import (
        geometry_msgs__msg__PoseStamped as PoseStamped, std_msgs__msg__Header
        as Header, geometry_msgs__msg__Pose as Pose, geometry_msgs__msg__Point
        as Position, geometry_msgs__msg__Quaternion as Quaternion,
        builtin_interfaces__msg__Time as Time)
    if not isinstance(traj, PoseTrajectory3D):
        raise FileInterfaceException(
            "trajectory must be a PoseTrajectory3D object")
    if not isinstance(writer, (Rosbag1Writer, Rosbag2Writer)):
        raise FileInterfaceException(
            "writer must be a rosbags.rosbags1.writer.Writer "
            "or rosbags.rosbags2.writer.Writer - "
            "rosbag.Bag() is not supported by evo anymore")

    msgtype = PoseStamped.__msgtype__
    connection = writer.add_connection(topic_name, msgtype)
    for stamp, xyz, quat in zip(traj.timestamps, traj.positions_xyz,
                                traj.orientations_quat_wxyz):
        sec = int(stamp // 1)
        nanosec = int((stamp - sec) * 1e9)
        time = Time(sec, nanosec)
        header = Header(time, frame_id)
        position = Position(x=xyz[0], y=xyz[1], z=xyz[2])
        quaternion = Quaternion(w=quat[0], x=quat[1], y=quat[2], z=quat[3])
        pose = Pose(position, quaternion)
        p = PoseStamped(header, pose)
        serialized_msg = serialize_cdr(p, msgtype)
        if isinstance(writer, Rosbag1Writer):
            serialized_msg = cdr_to_ros1(serialized_msg, msgtype)
        writer.write(connection, int(stamp * 1e9), serialized_msg)
    logger.info("Saved geometry_msgs/PoseStamped topic: " + topic_name)


def save_res_file(zip_path, result_obj: result.Result,
                  confirm_overwrite: bool = False) -> None:
    """
    save results to a zip file that can be deserialized with load_res_file()
    :param zip_path: path to zip file (or file handle)
    :param result_obj: evo.core.result.Result instance
    :param confirm_overwrite: whether to require user interaction
           to overwrite existing files
    """
    if isinstance(zip_path, str):
        logger.debug("Saving results to " + zip_path + "...")
    if confirm_overwrite and not user.check_and_confirm_overwrite(zip_path):
        return
    with zipfile.ZipFile(zip_path, 'w') as archive:
        archive.writestr("info.json", json.dumps(result_obj.info))
        archive.writestr("stats.json", json.dumps(result_obj.stats))
        for name, array in result_obj.np_arrays.items():
            array_buffer = io.BytesIO()
            np.save(array_buffer, array)
            array_buffer.seek(0)
            archive.writestr("{}.npy".format(name), array_buffer.read())
            array_buffer.close()
        for name, traj in result_obj.trajectories.items():
            traj_buffer = io.StringIO()
            if isinstance(traj, PoseTrajectory3D):
                fmt_suffix = ".tum"
                write_tum_trajectory_file(traj_buffer, traj)
            elif isinstance(traj, PosePath3D):
                fmt_suffix = ".kitti"
                write_kitti_poses_file(traj_buffer, traj)
            else:
                raise FileInterfaceException(
                    "unknown format of trajectory {}".format(name))
            traj_buffer.seek(0)
            archive.writestr("{}{}".format(name, fmt_suffix),
                             traj_buffer.read().encode("utf-8"))
            traj_buffer.close()


def load_res_file(zip_path, load_trajectories: bool = False) -> result.Result:
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
        if not {"info.json", "stats.json"} <= set(file_list):
            raise FileInterfaceException(
                "{} is not a valid result file".format(zip_path))
        result_obj.info = json.loads(archive.read("info.json").decode("utf-8"))
        result_obj.stats = json.loads(
            archive.read("stats.json").decode("utf-8"))

        # Compatibility: previous evo versions wrote .npz, although it was .npy
        # In any case, np.load() supports both file formats.
        np_files = [f for f in file_list if f.endswith((".npy", ".npz"))]
        for filename in np_files:
            with io.BytesIO(archive.read(filename)) as array_buffer:
                array = np.load(array_buffer)
                name = os.path.splitext(os.path.basename(filename))[0]
                result_obj.add_np_array(name, array)
        if load_trajectories:
            tum_files = [f for f in file_list if f.endswith(".tum")]
            for filename in tum_files:
                with io.TextIOWrapper(archive.open(filename,
                                                   mode='r')) as traj_buffer:
                    traj = read_tum_trajectory_file(traj_buffer)
                    name = os.path.splitext(os.path.basename(filename))[0]
                    result_obj.add_trajectory(name, traj)
            kitti_files = [f for f in file_list if f.endswith(".kitti")]
            for filename in kitti_files:
                with io.TextIOWrapper(archive.open(filename,
                                                   mode='r')) as path_buffer:
                    path = read_kitti_poses_file(path_buffer)
                    name = os.path.splitext(os.path.basename(filename))[0]
                    result_obj.add_trajectory(name, path)
    return result_obj


def load_transform_json(json_path) -> np.ndarray:
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
