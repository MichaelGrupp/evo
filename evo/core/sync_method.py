# -*- coding: UTF8 -*-
"""
Definitions of time synchronization methods.
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

from enum import Enum, unique


@unique
class SyncMethod(Enum):
    """
    Methods for synchronizing two trajectories in time,
    see evo.core.sync.associate_trajectories().
    """

    # Associate poses with the closest matching timestamps.
    nearest_time = "nearest_time"
    # Resample the denser trajectory at the timestamps of the sparser one.
    interpolation = "interpolation"
