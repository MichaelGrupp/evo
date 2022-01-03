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

ROS_NAME_REGEX = re.compile(r"([\/|_|0-9|a-z|A-Z]+)")


class TfIdException(EvoException):
    pass


def split_id(identifier: str) -> tuple:
    match = ROS_NAME_REGEX.findall(identifier)
    # If a fourth component exists, it's interpreted as the static TF name.
    if not len(match) in (3, 4):
        raise TfIdException(
            "ID string malformed, it should look similar to this: "
            "/tf:map.base_footprint")
    return tuple(match)


def check_id(self, identifier: str) -> bool:
    try:
        self.split_id(identifier)
    except TfIdException:
        return False
    return True
