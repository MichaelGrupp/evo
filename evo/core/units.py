from enum import Enum


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


LENGTH_UNITS = (Unit.millimeters, Unit.centimeters, Unit.meters,
                Unit.kilometers)
ANGLE_UNITS = (Unit.degrees, Unit.radians)

# Factors to apply to a value a to convert it to meters.
METER_SCALE_FACTORS = {
    Unit.millimeters: 1e-3,
    Unit.centimeters: 1e-2,
    Unit.meters: 1,
    Unit.kilometers: 1e3
}
