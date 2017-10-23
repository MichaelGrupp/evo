# -*- coding: UTF8 -*-
"""
low- and high-level read/write functions for different file formats
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

import io
import zipfile
import csv
import logging
import os
import json

import numpy as np

from evo.algorithms import sync
from evo.algorithms import trajectory
from evo.algorithms.trajectory import PosePath3D, PoseTrajectory3D
from evo.tools import user
from evo.tools.settings import SETTINGS


class FileInterfaceException(Exception):
    pass


def csv_read_matrix(file_path, delim=',', comment_str="#"):
    """
    directly parse a csv-like file into a matrix
    :param file_path: path of csv file (or file handle)
    :param delim: delimiter character
    :param comment_str: string indicating a comment line to ignore
    :return: 2D list with raw data (string)
    """
    if hasattr(file_path, 'read'):  # if file handle
        generator = (line for line in file_path if not line.startswith(comment_str))
        reader = csv.reader(generator, delimiter=delim)
        mat = [row for row in reader]
    else:
        if not os.path.isfile(file_path):
            raise FileInterfaceException("csv file " + str(file_path) + " does not exist")
        with open(file_path) as f:
            generator = (line for line in f if not line.startswith(comment_str))
            reader = csv.reader(generator, delimiter=delim)
            mat = [row for row in reader]
    return mat


def read_tum_trajectory_file(file_path):
    """
    parses trajectory file in TUM format (timestamp tx ty tz qx qy qz qw)
    :param file_path: the trajectory file path (or file handle)
    :return: trajectory.PoseTrajectory3D object
    """
    mat = np.array(csv_read_matrix(file_path, delim=" ", comment_str="#")).astype(float)
    if mat.shape[1] != 8:
        raise FileInterfaceException("TUM trajectory files must have 8 entries per row")
    stamps = mat[:, 0]  # n x 1
    xyz = mat[:, 1:4]  # n x 3
    quat = mat[:, 4:]  # n x 4
    quat = np.roll(quat, 1, axis=1)  # shift 1 column -> w in front column
    if not hasattr(file_path, 'read'):  # if not file handle
        logging.debug("loaded " + str(len(stamps)) + " stamps and poses from: " + file_path)
    return PoseTrajectory3D(xyz, quat, stamps)


def write_tum_trajectory_file(file_path, traj, quat_is_wxyz=True, confirm_overwrite=False):
    """
    :param file_path: desired text file for trajectory (string or handle)
    :param traj: trajectory.PoseTrajectory3D
    :param quat_is_wxyz: set to False if you use xyzw quaternion order
    :param confirm_overwrite: whether to require user interaction to overwrite existing files
    """
    if isinstance(file_path, str) and confirm_overwrite:
        if not user.check_and_confirm_overwrite(file_path):
            return
    if not isinstance(traj, PoseTrajectory3D):
        raise FileInterfaceException("trajectory must be a PoseTrajectory3D object")
    stamps = traj.timestamps
    xyz = traj.positions_xyz
    quat = traj.orientations_quat_wxyz
    if quat_is_wxyz:
        quat = np.roll(quat, -1, axis=1)  # shift -1 column -> w in back column
    mat = np.column_stack((stamps, xyz, quat))
    np.savetxt(file_path, mat, delimiter=" ")
    if isinstance(file_path, str):
        logging.debug("trajectory saved to: " + file_path)


def read_kitti_poses_file(file_path):
    """
    parses pose file in KITTI format (first 3 rows of SE(3) matrix per line)
    :param file_path: the trajectory file path (or file handle)
    :return: trajectory.PosePath3D
    """
    mat = np.array(csv_read_matrix(file_path, delim=" ", comment_str="#")).astype(float)
    if mat.shape[1] != 12:
        raise FileInterfaceException("KITTI pose files must have 12 entries per row")
    poses = [np.array([[r[0], r[1], r[2], r[3]],
                       [r[4], r[5], r[6], r[7]],
                       [r[8], r[9], r[10], r[11]],
                       [0, 0, 0, 1]]) for r in mat]
    if not hasattr(file_path, 'read'):  # if not file handle
        logging.debug("loaded " + str(len(poses)) + " poses from: " + file_path)
    return PosePath3D(poses_se3=poses)


def write_kitti_poses_file(file_path, traj, confirm_overwrite=False):
    """
    :param file_path: desired text file for trajectory (string or handle)
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D
    :param confirm_overwrite: whether to require user interaction to overwrite existing files
    """
    if isinstance(file_path, str) and confirm_overwrite:
        if not user.check_and_confirm_overwrite(file_path):
            return
    poses_flat = [p.flatten()[:-4] for p in traj.poses_se3]  # first 3 rows flattened
    np.savetxt(file_path, poses_flat, delimiter=' ')
    if isinstance(file_path, str):
        logging.debug("poses saved to: " + file_path)


def read_euroc_csv_trajectory(file_path):
    """
    parses ground truth trajectory from EuRoC MAV state estimate .csv
    :param file_path: <sequence>/mav0/state_groundtruth_estimate0/data.csv
    :return: trajectory.PoseTrajectory3D object
    """
    mat = np.array(csv_read_matrix(file_path, delim=",", comment_str="#")).astype(float)
    if mat.shape[1] != 17:
        raise FileInterfaceException("EuRoC MAV state ground truth must have 17 entries per row")
    stamps = np.divide(mat[:, 0], 1e9)  # n x 1  -  nanoseconds to seconds
    xyz = mat[:, 1:4]  # n x 3
    quat = mat[:, 4:]  # n x 4
    logging.debug("loaded " + str(len(stamps)) + " stamps and poses from: " + file_path)
    return PoseTrajectory3D(xyz, quat, stamps)


def read_bag_trajectory(bag_handle, topic):
    """
    :param bag_handle: opened bag handle, from rosbag.Bag(...)
    :param topic: geometry_msgs/PoseStamped topic
    :return: trajectory.PoseTrajectory3D
    """
    if not bag_handle.get_message_count(topic) > 0:
        raise FileInterfaceException("no messages for topic '" + topic + "' in bag")
    stamps, xyz, quat = [], [], []
    for topic, msg, t in bag_handle.read_messages(topic):
        stamps.append(t.secs + (t.nsecs * 1e-9))
        xyz.append([msg.pose.position.x, msg.pose.position.y, msg.pose.position.z])
        quat.append([msg.pose.orientation.x, msg.pose.orientation.y, 
                     msg.pose.orientation.z, msg.pose.orientation.w])
    logging.debug("loaded " + str(len(stamps)) + " geometry_msgs/PoseStamped messages" 
                  + " of topic: " + topic)
    quat = np.roll(quat, 1, axis=1)  # shift 1 column -> w in front column
    return PoseTrajectory3D(xyz, quat, stamps)


def write_bag_trajectory(bag_handle, traj, topic_name):
    """
    :param bag_handle: opened bag handle, from rosbag.Bag(...)
    :param traj: trajectory.PoseTrajectory3D
    :param topic_name: the desired topic name for the trajectory
    """
    import rospy
    from geometry_msgs.msg import PoseStamped
    if not isinstance(traj, PoseTrajectory3D):
        raise FileInterfaceException("trajectory must be a PoseTrajectory3D object")
    for stamp, xyz, quat in zip(traj.timestamps, traj.positions_xyz, traj.orientations_quat_wxyz):
        p = PoseStamped()
        p.header.stamp = rospy.Time.from_sec(stamp)
        p.header.frame_id = topic_name.replace("/", "")
        p.pose.position.x = xyz[0]
        p.pose.position.y = xyz[1]
        p.pose.position.z = xyz[2]
        p.pose.orientation.w = quat[0]
        p.pose.orientation.x = quat[1]
        p.pose.orientation.y = quat[2]
        p.pose.orientation.z = quat[3]
        bag_handle.write(topic_name, p, t=p.header.stamp)
    logging.debug("saved geometry_msgs/PoseStamped topic: " + topic_name)


def load_assoc_tum_trajectories(ref_file, est_file, max_diff=0.01, offset_2=0.0, invert=False):
    """
    parses two trajectory files in TUM format (timestamp tx ty tz qx qy qz qw)
    and returns the data with associated (matching) timestamps according to the time parameters
    :param ref_file: first trajectory file
    :param est_file: second trajectory file
    :param max_diff: max. allowed absolute time difference for associating
    :param offset_2: optional time offset of second timestamp vector
    :param invert: set to True to match from longer list to short (default: short to longer list)
    :return: trajectory.PoseTrajectory3D objects traj_ref and traj_est
    """
    traj_ref = read_tum_trajectory_file(ref_file)
    traj_est = read_tum_trajectory_file(est_file)
    return sync.associate_trajectories(traj_ref, traj_est, max_diff, offset_2,
                                       invert, ref_file, est_file)


def load_assoc_euroc_trajectories(ref_file, est_file, max_diff=0.01, offset_2=0.0, invert=False):
    """
    parses ground truth trajectory from EuRoC MAV state estimate .csv and estimated TUM trajectory
    and returns the data with associated (matching) timestamps according to the time parameters
    :param ref_file: ground truth: <sequence>/mav0/state_groundtruth_estimate0/data.csv
    :param est_file: estimated TUM trajectory file
    :param max_diff: max. allowed absolute time difference for associating
    :param offset_2: optional time offset of second timestamp vector
    :param invert: set to True to match from longer list to short (default: short to longer list)
    :return: trajectory.PoseTrajectory3D objects traj_ref and traj_est
    """
    traj_ref = read_euroc_csv_trajectory(ref_file)
    traj_est = read_tum_trajectory_file(est_file)
    return sync.associate_trajectories(traj_ref, traj_est, max_diff, offset_2, invert,
                                       ref_file, est_file)


def load_assoc_bag_trajectories(bag_handle, ref_topic, est_topic,
                                max_diff=0.01, offset_2=0.0, invert=False):
    """
    reads trajectory data from a ROS bag file with two geometry_msgs/PoseStamped topics
    and returns the data with associated (matching) timestamps according to the time parameters
    :param bag_handle: opened bag handle, from rosbag.Bag(...)
    :param ref_topic: first geometry_msgs/PoseStamped topic
    :param est_topic: second geometry_msgs/PoseStamped topic
    :param max_diff: max. allowed absolute time difference for associating
    :param offset_2: optional time offset of second timestamp vector
    :param invert: set to True to match from longer list to short (default: short to longer list)
    :return: trajectory.PoseTrajectory3D objects traj_ref and traj_est
    """
    traj_ref = read_bag_trajectory(bag_handle, ref_topic)
    traj_est = read_bag_trajectory(bag_handle, est_topic)
    return sync.associate_trajectories(traj_ref, traj_est, max_diff, offset_2, invert,
                                       ref_topic, est_topic)


def save_res_file(zip_path, pe_metric, pe_statistics, title, ref_name, est_name,
                  seconds_from_start=None, traj_ref=None, traj_est=None, xlabel=None,
                  confirm_overwrite=False):
    """
    save results of a pose error metric (pe_metric) to a zip file
    :param zip_path: path to zip file
    :param pe_metric: instance of metrics.APE or metrics.RPE
    :param pe_statistics: dictionary with statistics from pe_metric.get_[all_]statistic[s]
    :param title: the title of the experiment
    :param ref_name: name of the reference (ground_truth)
    :param est_name: name of the estimate
    :param seconds_from_start: optional time array (useful for plotting the time instead of index)
    :param traj_ref: optional - save trajectory that was used as the reference (requires traj_est)
    :param traj_est: optional - save trajectory that was used as the estimate (requires traj_ref)
    :param xlabel: optional custom (plot) xlabel to save
    :param confirm_overwrite: whether to require user interaction to overwrite existing files
    """
    from tempfile import TemporaryFile
    from evo.algorithms.metrics import APE
    logging.debug("saving results to " + zip_path + "...")
    if confirm_overwrite and not user.check_and_confirm_overwrite(zip_path):
        return
    with zipfile.ZipFile(zip_path, 'w') as archive:
        pe_type = "APE" if isinstance(pe_metric, APE) else "RPE"
        info = {"title": title, "ref_name": ref_name, "est_name": est_name,
                "label": pe_type + (" (" + pe_metric.unit.value + ")") if pe_metric.unit else ""}
        if xlabel:
            info["xlabel"] = xlabel
        archive.writestr("info.json", json.dumps(info))
        archive.writestr("stats.json", json.dumps(pe_statistics))
        # save np arrays in .npz format
        tmp_file_err = TemporaryFile()
        np.save(tmp_file_err, pe_metric.error)
        tmp_file_err.seek(0)
        archive.writestr("error_array.npz", tmp_file_err.read())
        tmp_file_err.close()
        if seconds_from_start:
            tmp_file_sec = TemporaryFile()
            if seconds_from_start:
                np.save(tmp_file_sec, seconds_from_start)
            tmp_file_sec.seek(0)
            archive.writestr("sec_from_start.npz", tmp_file_sec.read())
            tmp_file_sec.close()
        if SETTINGS.save_traj_in_zip and traj_ref is not None and traj_est is not None:
            tmp_file_ref = TemporaryFile()
            tmp_file_est = TemporaryFile()
            if type(traj_ref) is PosePath3D or type(traj_est) is PosePath3D:
                traj_type = ".kitti"
                write_kitti_poses_file(tmp_file_ref, traj_ref)
                write_kitti_poses_file(tmp_file_est, traj_est)
            else:
                traj_type = ".tum"
                write_tum_trajectory_file(tmp_file_ref, traj_ref)
                write_tum_trajectory_file(tmp_file_est, traj_est)
            tmp_file_ref.seek(0)
            tmp_file_est.seek(0)
            archive.writestr("traj_ref" + traj_type, tmp_file_ref.read())
            archive.writestr("traj_est" + traj_type, tmp_file_est.read())
            tmp_file_ref.close()
            tmp_file_est.close()


def load_res_file(zip_path, load_trajectories=False):
    """
    load contents of a result .zip file saved with save_res_file(...)
    :param zip_path: path to zip file
    :param load_trajectories: set to True to load also the (backup) trajectories
    :return: info (dictionary), statistics (dictionary),
             error_array (numpy array), seconds_from_start (list or None)
    """
    logging.debug("loading results from " + zip_path + "...")
    with zipfile.ZipFile(zip_path, mode='r') as archive:
        file_list = archive.namelist()
        if not {"error_array.npz", "info.json", "stats.json"} <= set(file_list):
            raise FileInterfaceException("incorrect zip file structure")
        seconds_from_start = None
        if "sec_from_start.npz" in file_list:
            with io.BytesIO(archive.read("sec_from_start.npz")) as f:
                seconds_from_start = np.load(f)
        traj_ref, traj_est = None, None
        if load_trajectories and "traj_ref.tum" and "traj_est.tum" in file_list:
            with io.TextIOWrapper(archive.open("traj_ref.tum", mode='r')) as f:
                traj_ref = read_tum_trajectory_file(f)
            with io.TextIOWrapper(archive.open("traj_est.tum", mode='r')) as f:
                traj_est = read_tum_trajectory_file(f)
        elif load_trajectories and "traj_ref.kitti" and "traj_est.kitti" in file_list:
            with io.TextIOWrapper(archive.open("traj_ref.kitti", mode='r')) as f:
                traj_ref = read_kitti_poses_file(f)
            with io.TextIOWrapper(archive.open("traj_est.kitti", mode='r')) as f:
                traj_est = read_kitti_poses_file(f)
        with io.BytesIO(archive.read("error_array.npz")) as f:
            error_array = np.load(f)
        info = json.loads(archive.read("info.json").decode("utf-8"))
        statistics = json.loads(archive.read("stats.json").decode("utf-8"))
        return info, statistics, error_array, seconds_from_start, traj_ref, traj_est


def load_transform_json(json_path):
    """
    load a transformation stored in xyz + quaternion format in a .json file
    :param json_path: path to the .json file
    :return: t (SE(3) matrix), xyz (position), quat (orientation quaternion)
    """
    import evo.algorithms.lie_algebra as lie
    import evo.algorithms.transformations as tr
    with open(json_path, 'r') as tf_file:
        data = json.load(tf_file)
        keys = ("x", "y", "z", "qx", "qy", "qz", "qw")
        if not all(key in data for key in keys):
            raise FileInterfaceException("invalid transform file - expected keys " + str(keys))
        xyz = np.array([data["x"], data["y"], data["z"]])
        quat = np.array([data["qw"], data["qx"], data["qy"], data["qz"]])
        t = lie.se3(lie.so3_from_se3(tr.quaternion_matrix(quat)), xyz)
        return t, xyz, quat
