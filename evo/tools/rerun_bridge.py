"""
Functions for easier sending of evo data to Rerun.
"""

from dataclasses import dataclass
from packaging import version
from typing import Sequence

import rerun as rr
from rerun.datatypes import Float64ArrayLike, Float32ArrayLike, Rgba32ArrayLike

import numpy as np
import matplotlib.cm
from matplotlib.colors import Normalize, rgb2hex

from evo.core.trajectory import PosePath3D, PoseTrajectory3D
from evo.tools.plot import color_cycle, PlotMode
from evo.tools.settings import SETTINGS

TIMELINE = "time"
INDEX_TIMELINE = "index"


def _check_rerun_version(min_version: str) -> None:
    """
    Raises ImportError if the installed Rerun version is less than min_version.
    """
    if version.parse(rr.__version__) < version.parse(min_version):
        raise ImportError(
            f"rerun-sdk >= {min_version} is required, installed version: {rr.__version__}"
        )


# Ensure that Rerun is at least version 0.28.0,
# which has TransformAxes3D.
_check_rerun_version("0.28.0")


@dataclass
class Color:
    """
    Helper for specifying either a static color, sequential colors, or none.
    Note that sequential colors must have the same length as other data columns when sent.
    """

    static: Rgba32ArrayLike | None = None
    # <Archetype>.columns(..., colors= ) only works with int32 colors,
    # not RGBA tuples that e.g. from_fields supports (otherwise: Arrow error).
    # TODO: https://github.com/rerun-io/rerun/issues/10170
    sequential: Sequence[int] | None = None  # [0xffaabbcc, ...]

    def __post_init__(self):
        if self.sequential is not None and self.static is not None:
            raise ValueError(
                "can't use sequential and static colors simultaneously"
            )


def _to_time_column(timestamps: np.ndarray) -> rr.TimeColumn:
    return rr.TimeColumn(TIMELINE, timestamp=timestamps)


def _to_index_column(num_indices: int) -> rr.TimeColumn:
    return rr.TimeColumn(INDEX_TIMELINE, sequence=np.arange(num_indices))


def _to_timeline_column(traj: PosePath3D) -> rr.TimeColumn:
    if isinstance(traj, PoseTrajectory3D):
        return _to_time_column(traj.timestamps)
    return _to_index_column(traj.num_poses)


def ui_points_radii(value: Float32ArrayLike) -> Float32ArrayLike:
    """
    Rerun interprets negative radii as points in screen space.
    """
    return -np.abs(value)  # type: ignore


def mapped_colors(cmap_name: str, values: np.ndarray) -> Sequence[int]:
    """
    Creates a color sequence from scalar values using a matplotlib colormap.
    """
    # Rerun SDK has no colormap implementation? mpl to the rescue...
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
        )
        for v in values
    ]


def send_transforms(
    entity_path: str, traj: PosePath3D, axis_length: float
) -> None:
    """
    Sends the trajectory poses as Transform3D to Rerun.
    """
    quaternions_xyzw = np.roll(traj.orientations_quat_wxyz, -1)
    rr.send_columns(
        entity_path,
        indexes=[_to_timeline_column(traj)],
        columns=rr.Transform3D.columns(
            translation=traj.positions_xyz, quaternion=quaternions_xyzw
        ),
    )
    rr.log(
        entity_path,
        rr.TransformAxes3D.from_fields(axis_length=axis_length),
        static=True,
    )


def send_line_strips(
    entity_path: str,
    traj: PosePath3D,
    radii: Float32ArrayLike,
    color: Color,
) -> None:
    """
    Sends connections between trajectory poses as LineStrips3D to Rerun.
    """
    strips = [
        [a, b] for a, b in zip(traj.positions_xyz, traj.positions_xyz[1:])
    ]

    if isinstance(traj, PoseTrajectory3D):
        strip_timestamps = traj.timestamps[1:]
        index = _to_time_column(strip_timestamps)
    else:
        index = _to_index_column(traj.num_poses - 1)

    rr.send_columns(
        entity_path,
        indexes=[index],
        columns=[
            *rr.LineStrips3D.columns(strips=strips, colors=color.sequential)
        ],
    )
    rr.log(
        entity_path,
        rr.LineStrips3D.from_fields(colors=color.static, radii=radii),
        static=True,
    )


def send_points(
    entity_path: str,
    traj: PosePath3D,
    radii: Float32ArrayLike,
    color: Color,
) -> None:
    """
    Sends the trajectory positions as Points3D to Rerun.
    """
    rr.send_columns(
        entity_path,
        indexes=[_to_timeline_column(traj)],
        columns=[
            *rr.Points3D.columns(
                positions=traj.positions_xyz, colors=color.sequential
            )
        ],
    )
    rr.log(
        entity_path,
        rr.Points3D.from_fields(colors=color.static, radii=radii),
        static=True,
    )


def send_scalars(
    entity_path: str,
    scalars: Float64ArrayLike,
    color: Color,
    timestamps: np.ndarray | None = None,
    labelname: str | None = None,
) -> None:
    """
    Sends a batch of scalars to Rerun, e.g. for plotting.
    If timestamps are provided, uses the time timeline;
    otherwise uses the index timeline.
    """
    if timestamps is not None:
        index = _to_time_column(timestamps)
    else:
        index = _to_index_column(len(np.asarray(scalars)))

    rr.send_columns(
        entity_path,
        indexes=[index],
        columns=rr.Scalars.columns(scalars=scalars),
    )
    rr.log(
        entity_path,
        rr.SeriesLines(colors=color.static, names=labelname),
        static=True,
    )


def send_correspondence_strips(
    entity_path: str,
    traj_1: PosePath3D,
    traj_2: PosePath3D,
    radii: Float32ArrayLike,
    color: Color,
):
    """
    Sends LineStrips3D connecting corresponding poses of two synced trajectories to Rerun.
    """
    if not traj_1.num_poses == traj_2.num_poses:
        raise ValueError("trajectories must be synced")

    correspondences = [
        [p1, p2] for p1, p2 in zip(traj_1.positions_xyz, traj_2.positions_xyz)
    ]

    if isinstance(traj_1, PoseTrajectory3D):
        index = _to_time_column(traj_1.timestamps)
    else:
        index = _to_index_column(traj_1.num_poses)

    rr.send_columns(
        entity_path,
        indexes=[index],
        columns=[
            *rr.LineStrips3D.columns(
                strips=correspondences, colors=color.sequential
            )
        ],
    )
    rr.log(
        entity_path,
        rr.LineStrips3D.from_fields(colors=color.static, radii=radii),
        static=True,
    )


def send_trajectory(entity_path: str, traj: PosePath3D, color: Color) -> None:
    """
    Convenience function to send transforms, points, and lines to Rerun.
    """
    # Note: in contrast to plot.py, we always send transform axes here.
    # If the scale is 0., you can still make it visible in the Rerun
    # viewer by changing the length in the entity settings after sending.
    send_transforms(
        entity_path=f"{entity_path}/transforms",
        traj=traj,
        axis_length=SETTINGS.plot_axis_marker_scale,
    )
    send_points(
        entity_path=f"{entity_path}/points",
        traj=traj,
        radii=ui_points_radii(SETTINGS.plot_linewidth * 1.25),
        color=color,
    )
    send_line_strips(
        entity_path=f"{entity_path}/lines",
        traj=traj,
        radii=ui_points_radii(SETTINGS.plot_linewidth),
        color=(
            Color(sequential=color.sequential[1:])
            if color.sequential
            else color
        ),
    )


def send_statistics_bar_chart(
    entity_path: str,
    stats: dict,
) -> None:
    """
    Sends a static bar chart of result statistics (mean, std, etc.) to Rerun.
    Each statistic is sent as a separate single-bar BarChart entity so that
    the entity path name serves as the label in the BarChartView.
    Colors follow the evo color cycle (seaborn palette from SETTINGS).
    Only statistics listed in SETTINGS.plot_statistics are included.
    """
    colors = color_cycle()
    included = [s for s in SETTINGS.plot_statistics if s in stats]

    for i, name in enumerate(included):
        value = stats[name]
        color = colors[i % len(colors)]
        rr.log(
            f"{entity_path}/{name}",
            rr.BarChart(
                values=np.array([value]),
                abscissa=np.array([i]),
                color=color,
            ),
            static=True,
        )


def send_view_coordinates(plot_mode: PlotMode):
    """
    Derive and send view coordinates (scene up) from a PlotMode value,
    for consistency with matplotlib plots.

    Should be called _after_ sending a blueprint.
    """
    if plot_mode.value in ("xy", "xyz"):
        view_coordinates = rr.ViewCoordinates.RIGHT_HAND_Z_UP
    elif plot_mode.value == "xz":
        view_coordinates = rr.ViewCoordinates.RIGHT_HAND_Y_DOWN
    elif plot_mode.value == "yz":
        view_coordinates = rr.ViewCoordinates.RIGHT_HAND_X_UP
    elif plot_mode.value == "yx":
        view_coordinates = rr.ViewCoordinates.RIGHT_HAND_Z_DOWN
    elif plot_mode.value == "zx":
        view_coordinates = rr.ViewCoordinates.RIGHT_HAND_Y_UP
    elif plot_mode.value == "zy":
        view_coordinates = rr.ViewCoordinates.RIGHT_HAND_X_DOWN

    rr.log("/", view_coordinates, static=True)
