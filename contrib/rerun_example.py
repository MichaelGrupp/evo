#!/usr/bin/env python3
"""
Playground for feeding evo data into rerun,
with sample data from the EuRoC MAV dataset.

While evo is geared towards batch-processing, we can use rerun's column API
to replay and visualize that data over time.

- pip install rerun-sdk
- https://github.com/rerun-io/rerun
"""

from pathlib import Path
from typing import Optional

import rerun as rr
import rerun.blueprint as rrb
from rerun.datatypes import Rgba32ArrayLike, Float64ArrayLike

import numpy as np
import matplotlib.cm
from matplotlib.colors import Normalize, rgb2hex, to_rgba

from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface

# The script assumes that it sits in the contrib/ directory of the evo repo.
TEST_DATA_DIR = Path(__file__).parent.parent / "test/data"

TIMELINE = "time"
VISIBLE_TIME_WINDOW = 10.0
POINT_RADIUS = 0.01
LINE_STRIP_RADIUS = POINT_RADIUS / 4
CORRESPONDENCE_STRIP_RADIUS = POINT_RADIUS / 2
AXIS_LENGTH = 0.1


def to_time_column(timestamps: np.ndarray) -> rr.TimeColumn:
    # TimeColumn interprets any numpy timestamp array as nanoseconds...?
    # Make sure to use a list instead.
    # TODO: check why TimeColumn.__init__() only likes float epoch seconds only
    # from non-numpy iterables.
    return rr.TimeColumn(TIMELINE, timestamp=list(timestamps))


def mapped_colors(cmap_name: str, values: np.ndarray) -> Rgba32ArrayLike:
    # rerun SDK has no colormap implementation? mpl to the rescue...
    norm = Normalize(vmin=values.min(), vmax=values.max(), clip=True)
    mapper = matplotlib.cm.ScalarMappable(norm, cmap_name)
    mapper.set_array(values)
    # <Archetype>.columns(..., colors= ) only works with int colors,
    # not RGBA tuples that e.g. from_fields supports?
    # TODO: this should be clearer checked in rerun?
    return [
        int(f"0x{rgb2hex(mapper.to_rgba(v), keep_alpha=True).strip('#')}", base=16)
        for v in values
    ]


def log_transforms(
    entity_path: str, traj: PoseTrajectory3D, axis_length: float
) -> None:
    """
    Logs the trajectory poses as Transform3D to rerun.
    """
    quaternions_xyzw = np.roll(traj.orientations_quat_wxyz, -1)
    rr.send_columns(
        entity_path,
        indexes=[to_time_column(traj.timestamps)],
        columns=rr.Transform3D.columns(
            translation=traj.positions_xyz, quaternion=quaternions_xyzw
        ),
    )
    rr.log(
        entity_path,
        rr.Transform3D.from_fields(axis_length=axis_length),
        static=True,
    )


def log_line_strips(
    entity_path: str,
    traj: PoseTrajectory3D,
    color: Optional[Rgba32ArrayLike] = None,
    color_sequence: Optional[Rgba32ArrayLike] = None,
) -> None:
    """
    Logs connections between trajectory poses as LineStrips3D to rerun.
    """
    if color and color_sequence:
        raise ValueError("set either color or color_sequence, not both")

    strips = [[a, b] for a, b in zip(traj.positions_xyz, traj.positions_xyz[1:])]
    strip_timestamps = traj.timestamps[1:]

    rr.send_columns(
        entity_path,
        indexes=[to_time_column(strip_timestamps)],
        columns=[*rr.LineStrips3D.columns(strips=strips, colors=color_sequence)],
    )
    rr.log(
        entity_path,
        rr.LineStrips3D.from_fields(colors=color, radii=LINE_STRIP_RADIUS),
        static=True,
    )


def log_points(
    entity_path: str,
    traj: PoseTrajectory3D,
    color: Optional[Rgba32ArrayLike] = None,
    color_sequence: Optional[Rgba32ArrayLike] = None,
) -> None:
    """
    Logs the trajectory positions as Points3D to rerun.
    """
    if color and color_sequence:
        raise ValueError("set either color or color_sequence, not both")

    rr.send_columns(
        entity_path,
        indexes=[to_time_column(traj.timestamps)],
        columns=[
            *rr.Points3D.columns(positions=traj.positions_xyz, colors=color_sequence)
        ],
    )
    rr.log(
        entity_path,
        rr.Points3D.from_fields(colors=color, radii=POINT_RADIUS),
        static=True,
    )


def log_scalars(
    entity_path: str,
    scalars: Float64ArrayLike,
    timestamps: np.ndarray,
    color: Optional[Rgba32ArrayLike] = None,
    labelname: Optional[str] = None,
) -> None:
    """
    Logs a batch of scalars with timestamps to rerun, e.g. for plotting.
    """
    rr.send_columns(
        entity_path,
        indexes=[to_time_column(timestamps)],
        columns=rr.Scalars.columns(scalars=scalars),
    )
    rr.log(entity_path, rr.SeriesLines(colors=color, names=labelname), static=True)


def log_correspondence_strips(
    entity_path: str,
    traj_1: PoseTrajectory3D,
    traj_2: PoseTrajectory3D,
    color: Optional[Rgba32ArrayLike] = None,
    color_sequence: Optional[Rgba32ArrayLike] = None,
):
    """
    Logs LineStrips3D connecting corresponding poses of two synced trajectories to rerun.
    """
    if not traj_1.num_poses == traj_2.num_poses:
        ValueError("trajectories must be synced")

    if color and color_sequence:
        raise ValueError("set either color or color_sequence, not both")

    correspondences = [
        [p1, p2] for p1, p2 in zip(traj_1.positions_xyz, traj_2.positions_xyz)
    ]
    rr.send_columns(
        entity_path,
        indexes=[to_time_column(traj_1.timestamps)],
        columns=[
            *rr.LineStrips3D.columns(strips=correspondences, colors=color_sequence)
        ],
    )
    rr.log(
        entity_path,
        rr.LineStrips3D.from_fields(colors=color, radii=CORRESPONDENCE_STRIP_RADIUS),
        static=True,
    )


if __name__ == "__main__":
    # Load some example trajectories and compute a metric.
    groundtruth, estimate = sync.associate_trajectories(
        file_interface.read_euroc_csv_trajectory(
            TEST_DATA_DIR / "V102_groundtruth.csv"
        ),
        file_interface.read_tum_trajectory_file(TEST_DATA_DIR / "V102.txt"),
    )
    estimate.align(groundtruth)

    ape = metrics.APE(metrics.PoseRelation.translation_part)
    ape.process_data((groundtruth, estimate))

    # Adapt the blueprint's visible time range to include a sliding window
    # instead of "latest" for better visibility. Can be changed also in the viewer.
    time_range = rrb.VisibleTimeRange(
        timeline=TIMELINE,
        start=rrb.TimeRangeBoundary.cursor_relative(seconds=-VISIBLE_TIME_WINDOW),
        end=rrb.TimeRangeBoundary.cursor_relative(seconds=0.0),
    )

    # Show a 3D view and a plot.
    # Hide the selection panel by default.
    blueprint = rrb.Blueprint(
        rrb.Grid(
            contents=[
                rrb.Spatial3DView(time_ranges=time_range),
                rrb.TimeSeriesView(time_ranges=time_range),
            ],
            column_shares=[2, 1],
        ),
        rrb.SelectionPanel(expanded=False),
    )

    rr.init("evo_rerun_example", spawn=True)
    rr.send_blueprint(blueprint)

    # Log the scalars for the error plot:
    ape.change_unit(metrics.Unit.centimeters)
    log_scalars(
        "/error/scalars",
        ape.error,
        estimate.timestamps,
        color=to_rgba("red"),
        labelname=str(ape),
    )

    # Log the 3D trajectory visualization:
    log_transforms("/groundtruth/transforms", groundtruth, AXIS_LENGTH)
    log_transforms("/estimate/transforms", estimate, AXIS_LENGTH)

    log_points("/groundtruth/points", groundtruth, to_rgba("grey"))
    log_points("/estimate/points", estimate, to_rgba("orange"))

    log_line_strips("/groundtruth/lines", groundtruth, to_rgba("grey"))
    log_line_strips("/estimate/lines", estimate, to_rgba("orange"))

    # Log pose correspondence lines colormapped by the error magnitude.
    log_correspondence_strips(
        "/error/correspondences",
        estimate,
        groundtruth,
        color_sequence=mapped_colors("jet", ape.error),
    )
