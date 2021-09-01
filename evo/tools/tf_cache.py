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
import re
import warnings

import rospy
import tf2_py

import numpy as np
from evo import EvoException
from evo.core.trajectory import PoseTrajectory3D
from evo.tools.file_interface import _get_xyz_quat_from_transform_stamped
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

ROS_NAME_REGEX = re.compile(r"([\/|_|0-9|a-z|A-Z]+)")


class TfCacheException(EvoException):
    pass


__instance = None


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

    def from_bag(self, bag_handle, topic: str = "/tf",
                 static_topic: str = "/tf_static") -> None:
        """
        Loads the TF topics from a bagfile into the buffer,
        if it's not already cached.
        :param bag_handle: opened bag handle, from rosbag.Bag(...)
        :param topic: TF topic
        """
        tf_topics = [topic]
        if not bag_handle.get_message_count(topic) > 0:
            raise TfCacheException(
                "no messages for topic {} in bag".format(topic))
        # Implicitly add static TFs to buffer if present.
        if bag_handle.get_message_count(static_topic) > 0:
            tf_topics.append(static_topic)

        # Add TF data to buffer if this bag/topic pair is not already cached.
        for tf_topic in tf_topics:
            if tf_topic in self.topics and bag_handle.filename in self.bags:
                logger.debug("Using cache for topic {} from {}".format(
                    tf_topic, bag_handle.filename))
                continue
            logger.debug("Caching TF topic {} from {} ...".format(
                tf_topic, bag_handle.filename))
            for _, msg, _ in bag_handle.read_messages(tf_topic):
                for tf in msg.transforms:
                    if tf_topic == static_topic:
                        self.buffer.set_transform_static(tf, __name__)
                    else:
                        self.buffer.set_transform(tf, __name__)
            self.topics.append(tf_topic)
        self.bags.append(bag_handle.filename)

    @staticmethod
    def split_id(identifier: str) -> tuple:
        match = ROS_NAME_REGEX.findall(identifier)
        # If a fourth component exists, it's interpreted as the static TF name.
        if not len(match) in (3, 4):
            raise TfCacheException(
                "ID string malformed, it should look similar to this: "
                "/tf:map.base_footprint")
        return tuple(match)

    def check_id(self, identifier: str) -> bool:
        try:
            self.split_id(identifier)
        except TfCacheException:
            return False
        return True

    def lookup_trajectory(
        self, parent_frame: str, child_frame: str, start_time: rospy.Time,
        end_time: rospy.Time,
        lookup_frequency: float = SETTINGS.tf_cache_lookup_frequency
    ) -> PoseTrajectory3D:
        """
        Look up the trajectory of a transform chain from the cache's TF buffer.
        :param parent_frame, child_frame: TF transform frame IDs
        :param start_time, end_time: expected start and end time of the
                                     trajectory in the buffer
        :param lookup_frequency: frequency of TF lookups between start and end
                                 time, in Hz.
        """
        stamps, xyz, quat = [], [], []
        step = rospy.Duration.from_sec(1. / lookup_frequency)
        # Static TF have zero timestamp in the buffer, which will be lower
        # than the bag start time. Looking up a static TF is a valid request,
        # so this should be possible.
        attempt_single_static_lookup = end_time.to_sec() == 0.
        # Look up the transforms of the trajectory in reverse order:
        while end_time >= start_time or attempt_single_static_lookup:
            try:
                tf = self.buffer.lookup_transform_core(parent_frame,
                                                       child_frame, end_time)
            except tf2_py.ExtrapolationException:
                break
            stamps.append(tf.header.stamp.to_sec())
            x, q = _get_xyz_quat_from_transform_stamped(tf)
            xyz.append(x)
            quat.append(q)
            if attempt_single_static_lookup:
                break
            end_time = end_time - step
        # Flip the data order again for the final trajectory.
        trajectory = PoseTrajectory3D(np.flipud(xyz), np.flipud(quat),
                                      np.flipud(stamps))
        trajectory.meta = {
            "frame_id": parent_frame,
            "child_frame_id": child_frame
        }
        return trajectory

    def get_trajectory(self, bag_handle, identifier: str) -> PoseTrajectory3D:
        """
        Get a TF trajectory from a bag file. Updates or uses the cache.
        :param bag_handle: opened bag handle, from rosbag.Bag(...)
        :param identifier: trajectory ID <topic>:<parent_frame>.<child_frame>
                           Example: /tf:map.base_link
        """
        split_id = self.split_id(identifier)
        topic, parent, child = split_id[0], split_id[1], split_id[2]
        static_topic = split_id[3] if len(split_id) == 4 else "/tf_static"
        logger.debug(f"Loading trajectory of transform '{parent} to {child}' "
                     f"from topic {topic} (static topic: {static_topic}).")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            self.from_bag(bag_handle, topic, static_topic)
        try:
            latest_time = self.buffer.get_latest_common_time(parent, child)
        except (tf2_py.LookupException, tf2_py.TransformException) as e:
            raise TfCacheException("Could not load trajectory: " + str(e))
        return self.lookup_trajectory(
            parent, child,
            start_time=rospy.Time.from_sec(bag_handle.get_start_time()),
            end_time=latest_time)


def instance() -> TfCache:
    """ Hacky module-level "singleton" of TfCache """
    global __instance
    if __instance is None:
        __instance = TfCache()
    return __instance
