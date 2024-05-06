# -*- coding: UTF8 -*-
"""
TF topic handling
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

import logging
import warnings
from collections import defaultdict
from typing import DefaultDict, List, Optional

import numpy as np
import rospy
import tf2_py
from geometry_msgs.msg import TransformStamped
from rosbags.rosbag1 import Reader as Rosbag1Reader
from rosbags.typesys import get_typestore, get_types_from_msg, Stores
from rosbags.typesys.store import Typestore
from std_msgs.msg import Header

from evo import EvoException
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import tf_id
from evo.tools.file_interface import _get_xyz_quat_from_transform_stamped
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SUPPORTED_TF_MSG = "tf2_msgs/msg/TFMessage"


class TfCacheException(EvoException):
    pass


class TfCache(object):
    """
    For caching TF messages and looking up trajectories of specific transforms.
    """
    def __init__(self):
        self.buffer = tf2_py.BufferCore(
            rospy.Duration.from_sec(SETTINGS.tf_cache_max_time))
        self.topics = []
        self.bags = []

    def clear(self) -> None:
        logger.debug("Clearing TF cache.")
        self.buffer.clear()
        self.topics = []
        self.bags = []

    # tf2_msgs/TFMessage is not included in default rosbags typestore,
    # update the ROS1 typestore with the interface definition from the bag.
    # https://ternaris.gitlab.io/rosbags/examples/register_types.html
    @staticmethod
    def _setup_typestore(reader: Rosbag1Reader) -> Typestore:
        typestore = get_typestore(Stores.ROS1_NOETIC)
        for connection in reader.connections:
            if connection.msgtype == SUPPORTED_TF_MSG:
                typestore.register(
                    get_types_from_msg(connection.msgdef, connection.msgtype))
                break
        return typestore

    # TODO: support also ROS2 bag reader.
    def from_bag(self, reader: Rosbag1Reader, topic: str = "/tf",
                 static_topic: str = "/tf_static") -> None:
        """
        Loads the TF topics from a bagfile into the buffer,
        if it's not already cached.
        :param reader: opened bag reader (rosbags.rosbag1)
        :param topic: TF topic
        """
        tf_topics = [topic]
        if topic not in reader.topics:
            raise TfCacheException(
                "no messages for topic {} in bag".format(topic))
        # Implicitly add static TFs to buffer if present.
        if static_topic in reader.topics:
            tf_topics.append(static_topic)

        typestore = self._setup_typestore(reader)

        # Add TF data to buffer if this bag/topic pair is not already cached.
        for tf_topic in tf_topics:
            if tf_topic in self.topics and reader.path.name in self.bags:
                logger.debug("Using cache for topic {} from {}".format(
                    tf_topic, reader.path.name))
                continue
            logger.debug("Caching TF topic {} from {} ...".format(
                tf_topic, reader.path.name))
            connections = [
                c for c in reader.connections if c.topic == tf_topic
            ]
            for connection, _, rawdata in reader.messages(
                    connections=connections):
                if connection.msgtype != SUPPORTED_TF_MSG:
                    raise TfCacheException(
                        f"Expected {SUPPORTED_TF_MSG} message type for topic "
                        f"{tf_topic}, got: {connection.msgtype}")
                msg = typestore.deserialize_ros1(rawdata, connection.msgtype)
                for tf in msg.transforms:  # type: ignore
                    # Convert from rosbags.typesys.types to native ROS.
                    # Related: https://gitlab.com/ternaris/rosbags/-/issues/13
                    stamp = rospy.Time()
                    stamp.secs = tf.header.stamp.sec
                    stamp.nsecs = tf.header.stamp.nanosec
                    tf = TransformStamped(Header(0, stamp, tf.header.frame_id),
                                          tf.child_frame_id, tf.transform)
                    if tf_topic == static_topic:
                        self.buffer.set_transform_static(tf, __name__)
                    else:
                        self.buffer.set_transform(tf, __name__)
            self.topics.append(tf_topic)
        self.bags.append(reader.path.name)

    def lookup_trajectory(self, parent_frame: str, child_frame: str,
                          timestamps: List[rospy.Time]) -> PoseTrajectory3D:
        """
        Look up the trajectory of a transform chain from the cache's TF buffer.
        :param parent_frame, child_frame: TF transform frame IDs
        :param timestamps: timestamps at which to lookup the trajectory poses.
        :param lookup_frequency: frequency of TF lookups between start and end
                                 time, in Hz.
        """
        stamps, xyz, quat = [], [], []
        # Look up the transforms of the trajectory in reverse order:
        timestamps.sort()
        for timestamp in timestamps:
            try:
                tf = self.buffer.lookup_transform_core(parent_frame,
                                                       child_frame, timestamp)
            except tf2_py.ExtrapolationException:
                continue
            stamps.append(tf.header.stamp.to_sec())
            x, q = _get_xyz_quat_from_transform_stamped(tf)
            xyz.append(x)
            quat.append(q)
        # Flip the data order again for the final trajectory.
        trajectory = PoseTrajectory3D(
            np.array(xyz), np.array(quat), np.array(stamps), meta={
                "frame_id": parent_frame,
                "child_frame_id": child_frame
            })
        return trajectory

    def get_trajectory(
            self, reader: Rosbag1Reader, identifier: str,
            timestamps: Optional[List[rospy.Time]] = None) -> PoseTrajectory3D:
        """
        Get a TF trajectory from a bag file. Updates or uses the cache.
        :param reader: opened bag reader (rosbags.rosbag1)
        :param identifier: trajectory ID <topic>:<parent_frame>.<child_frame>
                           Example: /tf:map.base_link
        """
        split_id = tf_id.split_id(identifier)
        topic, parent, child = split_id[0], split_id[1], split_id[2]
        static_topic = split_id[3] if len(split_id) == 4 else "/tf_static"
        logger.debug(f"Loading trajectory of transform '{parent} to {child}' "
                     f"from topic {topic} (static topic: {static_topic}).")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            self.from_bag(reader, topic, static_topic)
        try:
            latest_time = self.buffer.get_latest_common_time(parent, child)
        except (tf2_py.LookupException, tf2_py.TransformException) as e:
            raise TfCacheException("Could not load trajectory: " + str(e))
        # rosbags Reader start_time is in nanoseconds.
        start_time = rospy.Time.from_sec(reader.start_time * 1e-9)
        if timestamps is None:
            timestamps = []
            # Static TF have zero timestamp in the buffer, which will be lower
            # than the bag start time. Looking up a static TF is a valid request,
            # so this should be possible.
            if latest_time < start_time:
                timestamps.append(latest_time)
            else:
                step = rospy.Duration.from_sec(
                    1. / SETTINGS.tf_cache_lookup_frequency)
                time = start_time
                while time <= latest_time:
                    timestamps.append(time)
                    time = time + step
        return self.lookup_trajectory(parent, child, timestamps)


__instance: DefaultDict[int, TfCache] = defaultdict(lambda: TfCache())


def instance(hash: int) -> TfCache:
    """ Hacky module-level "singleton" of TfCache """
    global __instance
    return __instance[hash]
