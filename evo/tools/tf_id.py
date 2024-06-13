"""
TF topic ID string handling
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

import re

from evo import EvoException

ROS_NAME_REGEX = re.compile(r"[\/|a-z|A-Z][\/|_|0-9|a-z|A-Z]+")


class TfIdException(EvoException):
    pass


def split_id(identifier: str) -> tuple:
    tf_topic, _, identifier = identifier.partition(":")
    if ":" in identifier:
        identifier, _, tf_static_topic = identifier.rpartition(":")
    else:
        tf_static_topic = None
    parent_frame_id, _, child_frame_id = identifier.partition(".")

    if ROS_NAME_REGEX.match(tf_topic) is None:
        raise TfIdException(
            f"ID string malformed, {tf_topic} is not a valid topic name, "
            "ID string should look like /tf:map.base_footprint(:/tf_static)")

    if not parent_frame_id:
        raise TfIdException(
            "ID string malformed, parent frame ID is missing, ID string "
            "should look like /tf:map.base_footprint(:/tf_static)")

    if not child_frame_id:
        raise TfIdException(
            "ID string malformed, child frame ID is missing, ID string "
            "should look like /tf:map.base_footprint(:/tf_static)")

    if tf_static_topic:
        if ROS_NAME_REGEX.match(tf_static_topic) is None:
            raise TfIdException(
                f"ID string malformed, {tf_static_topic} is not a valid topic name, "
                "ID string should look like /tf:map.base_footprint(:/tf_static)"
            )

        return (tf_topic, parent_frame_id, child_frame_id, tf_static_topic)

    return (tf_topic, parent_frame_id, child_frame_id)


def check_id(identifier: str) -> bool:
    try:
        split_id(identifier)
    except TfIdException:
        return False
    return True
