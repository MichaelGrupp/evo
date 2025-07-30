"""
Functions for easier logging of evo data into rerun.
"""

from dataclasses import dataclass
from typing import Optional, Sequence

import rerun as rr
from rerun.datatypes import Float64ArrayLike, Float32ArrayLike, Rgba32ArrayLike

import numpy as np
import matplotlib.cm
from matplotlib.colors import Normalize, rgb2hex

from evo.core.trajectory import PoseTrajectory3D
from evo.tools.settings import SETTINGS

TIMELINE = "time"

# Ensure that rerun is at least version 0.24.0,
# which has the fix for timestamps columns.
# https://github.com/rerun-io/rerun/issues/10167
from packaging import version
if version.parse(rr.__version__) < version.parse("0.24.0"):
    raise ImportError(
        f"rerun >= 0.24.0 is required, installed version: {rr.__version__}")


@dataclass
class Color:
    """
    Helper for specifying either a static color, sequential colors, or none.
    Note that sequential colors must have the same length as other data columns when logged.
    """

    static: Optional[Rgba32ArrayLike] = None
    # <Archetype>.columns(..., colors= ) only works with int32 colors,
    # not RGBA tuples that e.g. from_fields supports (otherwise: Arrow error).
    # TODO: https://github.com/rerun-io/rerun/issues/10170
    sequential: Optional[Sequence[int]] = None  # [0xffaabbcc, ...]

    def __post_init__(self):
        if self.sequential is not None and self.static is not None:
            raise ValueError(
                "can't use sequential and static colors simultaneously")


def _to_time_column(timestamps: np.ndarray) -> rr.TimeColumn:
    return rr.TimeColumn(TIMELINE, timestamp=timestamps)


def ui_points_radii(value: Float32ArrayLike) -> Float32ArrayLike:
    """
    rerun interprets negative radii as points in screen space.
    """
    return -np.abs(value)


def mapped_colors(cmap_name: str, values: np.ndarray) -> Sequence[int]:
    """
    Creates a color sequence from scalar values using a matplotlib colormap.
    """
    # rerun SDK has no colormap implementation? mpl to the rescue...
    norm = Normalize(vmin=values.min(), vmax=values.max(), clip=True)
    mapper = matplotlib.cm.ScalarMappable(norm, cmap_name)
    mapper.set_array(values)
    # <Archetype>.columns(..., colors= ) only works with int colors,
    # not RGBA tuples that e.g. from_fields supports?
    # TODO: https://github.com/rerun-io/rerun/issues/10170
    return [
        int(
            f"0x{rgb2hex(tuple(mapper.to_rgba(v)), keep_alpha=True).strip('#')}",
            base=16,
        ) for v in values
    ]


def log_transforms(entity_path: str, traj: PoseTrajectory3D,
                   axis_length: float) -> None:
    """
    Logs the trajectory poses as Transform3D to rerun.
    """
    quaternions_xyzw = np.roll(traj.orientations_quat_wxyz, -1)
    rr.send_columns(
        entity_path,
        indexes=[_to_time_column(traj.timestamps)],
        columns=rr.Transform3D.columns(translation=traj.positions_xyz,
                                       quaternion=quaternions_xyzw),
    )
    rr.log(
        entity_path,
        rr.Transform3D.from_fields(axis_length=axis_length),
        static=True,
    )


def log_line_strips(
    entity_path: str,
    traj: PoseTrajectory3D,
    radii: Float32ArrayLike,
    color: Color,
) -> None:
    """
    Logs connections between trajectory poses as LineStrips3D to rerun.
    """
    strips = [[a, b]
              for a, b in zip(traj.positions_xyz, traj.positions_xyz[1:])]
    strip_timestamps = traj.timestamps[1:]

    rr.send_columns(
        entity_path,
        indexes=[_to_time_column(strip_timestamps)],
        columns=[
            *rr.LineStrips3D.columns(strips=strips, colors=color.sequential)
        ],
    )
    rr.log(
        entity_path,
        rr.LineStrips3D.from_fields(colors=color.static, radii=radii),
        static=True,
    )


def log_points(
    entity_path: str,
    traj: PoseTrajectory3D,
    radii: Float32ArrayLike,
    color: Color,
) -> None:
    """
    Logs the trajectory positions as Points3D to rerun.
    """
    rr.send_columns(
        entity_path,
        indexes=[_to_time_column(traj.timestamps)],
        columns=[
            *rr.Points3D.columns(positions=traj.positions_xyz,
                                 colors=color.sequential)
        ],
    )
    rr.log(
        entity_path,
        rr.Points3D.from_fields(colors=color.static, radii=radii),
        static=True,
    )


def log_scalars(
    entity_path: str,
    scalars: Float64ArrayLike,
    timestamps: np.ndarray,
    color: Color,
    labelname: Optional[str] = None,
) -> None:
    """
    Logs a batch of scalars with timestamps to rerun, e.g. for plotting.
    """
    rr.send_columns(
        entity_path,
        indexes=[_to_time_column(timestamps)],
        columns=rr.Scalars.columns(scalars=scalars),
    )
    rr.log(entity_path, rr.SeriesLines(colors=color.static, names=labelname),
           static=True)


def log_correspondence_strips(
    entity_path: str,
    traj_1: PoseTrajectory3D,
    traj_2: PoseTrajectory3D,
    radii: float,
    color: Color,
):
    """
    Logs LineStrips3D connecting corresponding poses of two synced trajectories to rerun.
    """
    if not traj_1.num_poses == traj_2.num_poses:
        raise ValueError("trajectories must be synced")

    correspondences = [
        [p1, p2] for p1, p2 in zip(traj_1.positions_xyz, traj_2.positions_xyz)
    ]
    rr.send_columns(
        entity_path,
        indexes=[_to_time_column(traj_1.timestamps)],
        columns=[
            *rr.LineStrips3D.columns(strips=correspondences,
                                     colors=color.sequential)
        ],
    )
    rr.log(
        entity_path,
        rr.LineStrips3D.from_fields(colors=color.static, radii=radii),
        static=True,
    )


def log_trajectory(entity_path: str, traj: PoseTrajectory3D,
                   color: Color) -> None:
    """
    Convenience function to log transforms, points, and lines to rerun.
    """
    # Note: in contrast to plot.py, we always log transform axes here.
    # If the scale is 0., you can still make it visible in the rerun
    # viewer by changing the length in the entity settings after logging.
    log_transforms(entity_path=f"{entity_path}/transforms", traj=traj,
                   axis_length=SETTINGS.plot_axis_marker_scale)
    log_points(
        entity_path=f"{entity_path}/points",
        traj=traj,
        radii=ui_points_radii(SETTINGS.plot_linewidth * 1.25),
        color=color,
    )
    log_line_strips(
        entity_path=f"{entity_path}/lines",
        traj=traj,
        radii=ui_points_radii(SETTINGS.plot_linewidth),
        color=color if color.static is not None else Color(
            sequential=color.sequential[1:]),
    )
