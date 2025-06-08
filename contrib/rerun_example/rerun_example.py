#!/usr/bin/env python3
"""
Playground for feeding evo data into rerun,
with sample data from the EuRoC MAV dataset.

While evo is geared towards batch-processing, we can use rerun's column API
to replay and visualize that data over time.

- pip install rerun-sdk
- https://github.com/rerun-io/rerun
"""

from typing import Tuple
from pathlib import Path

import rerun as rr
import rerun.blueprint as rrb

from matplotlib.colors import to_rgba

from evo.core.trajectory import PoseTrajectory3D
from evo.core import metrics, sync
from evo.tools import file_interface

import rerun_bridge as revo

# The script assumes that it sits in the contrib/rerun_example directory of the evo repo.
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test/data"
GROUNDTRUTH_FILE = TEST_DATA_DIR / "V102_groundtruth.csv"
ESTIMATE_FILE = TEST_DATA_DIR / "V102.txt"

VISIBLE_TIME_WINDOW = 10.0
POINT_RADIUS = 0.01
LINE_STRIP_RADIUS = POINT_RADIUS / 4
CORRESPONDENCE_STRIP_RADIUS = POINT_RADIUS / 2
AXIS_LENGTH = 0.1


def example_data() -> Tuple[PoseTrajectory3D, PoseTrajectory3D, metrics.APE]:
    """
    Load some example trajectories and compute a metric.
    """
    groundtruth, estimate = sync.associate_trajectories(
        file_interface.read_euroc_csv_trajectory(GROUNDTRUTH_FILE),
        file_interface.read_tum_trajectory_file(ESTIMATE_FILE),
    )
    estimate.align(groundtruth)

    ape = metrics.APE(metrics.PoseRelation.translation_part)
    ape.process_data((groundtruth, estimate))

    return groundtruth, estimate, ape


def configure_blueprint() -> rr.BlueprintLike:
    # Adapt the blueprint's visible time range to include a sliding window
    # instead of "latest" for better visibility. Can be changed also in the viewer.
    time_range = rrb.VisibleTimeRange(
        timeline=revo.TIMELINE,
        start=rrb.TimeRangeBoundary.cursor_relative(
            seconds=-VISIBLE_TIME_WINDOW),
        end=rrb.TimeRangeBoundary.cursor_relative(seconds=0.0),
    )

    # Show a 3D view and a plot.
    return rrb.Blueprint(
        rrb.Grid(
            contents=[
                rrb.Spatial3DView(time_ranges=time_range),
                rrb.TimeSeriesView(time_ranges=time_range),
            ],
            column_shares=[2, 1],
        ),
        # TODO: hide the selection panel by default?
        rrb.SelectionPanel(expanded=True),
    )


def run_demo() -> None:
    print("Loading data and computing metrics.")
    groundtruth, estimate, ape = example_data()

    rr.init("evo_rerun_example", spawn=True)
    rr.send_blueprint(configure_blueprint())

    print("Logging scalars for the error plot.")
    ape.change_unit(metrics.Unit.centimeters)
    revo.log_scalars(
        "/error/scalars",
        ape.error,
        estimate.timestamps,
        color=revo.Color(static=to_rgba("red")),
        labelname=str(ape),
    )

    print("Logging 3D trajectory visualization data.")
    revo.log_transforms("/groundtruth/transforms", groundtruth, AXIS_LENGTH)
    revo.log_transforms("/estimate/transforms", estimate, AXIS_LENGTH)

    revo.log_points(
        "/groundtruth/points",
        groundtruth,
        POINT_RADIUS,
        revo.Color(static=to_rgba("grey")),
    )
    revo.log_points("/estimate/points", estimate, POINT_RADIUS,
                    revo.Color(static=to_rgba("orange")))

    revo.log_line_strips(
        "/groundtruth/lines",
        groundtruth,
        LINE_STRIP_RADIUS,
        revo.Color(static=to_rgba("grey")),
    )
    revo.log_line_strips(
        "/estimate/lines",
        estimate,
        LINE_STRIP_RADIUS,
        revo.Color(static=to_rgba("orange")),
    )

    print(
        "Logging pose correspondence lines colormapped by the error magnitude."
    )
    revo.log_correspondence_strips(
        "/error/correspondences",
        estimate,
        groundtruth,
        CORRESPONDENCE_STRIP_RADIUS,
        color=revo.Color(sequential=revo.mapped_colors("jet", ape.error)),
    )

    print("Done, use the rerun viewer window to view and replay the data.")


if __name__ == "__main__":
    run_demo()
