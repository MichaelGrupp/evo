# -*- coding: UTF8 -*-
"""
Definitions of unit types.
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
class Unit(Enum):
    none = "unit-less"
    millimeters = "mm"
    centimeters = "cm"
    meters = "m"
    kilometers = "km"
    seconds = "s"
    degrees = "deg"
    radians = "rad"
    frames = "frames"
    percent = "%"  # used like a unit for display purposes


LENGTH_UNITS = (
    Unit.millimeters,
    Unit.centimeters,
    Unit.meters,
    Unit.kilometers,
)
ANGLE_UNITS = (Unit.degrees, Unit.radians)

# Factors to apply to a value a to convert it to meters.
METER_SCALE_FACTORS = {
    Unit.millimeters: 1e-3,
    Unit.centimeters: 1e-2,
    Unit.meters: 1,
    Unit.kilometers: 1e3,
}
