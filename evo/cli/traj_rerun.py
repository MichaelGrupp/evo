"""
Rerun visualization functions for evo_traj.
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

import argparse
import logging
import sys
from typing import Callable

try:
    import pyarrow as pa
    import rerun as rr
    import rerun.blueprint as rrb
    from rerun.experimental import ViewerClient
except ImportError:
    logging.getLogger(__name__).error(
        "Optional dependency rerun-sdk is not installed. "
        "Install it with: pip install rerun-sdk"
    )
    sys.exit(1)

from matplotlib.colors import to_rgba

from evo.cli.traj_plot import get_color_generator
from evo.core.trajectory import PoseTrajectory3D, TrajectoryException
from evo.core.trajectory_bundle import TrajectoryBundle
from evo.tools import pandas_bridge
from evo.tools import rerun_bridge as revo
from evo.tools.plot import PlotMode
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80


def send_bundle_to_rerun(
    bundle: TrajectoryBundle,
    args: argparse.Namespace,
    to_compact_name: Callable,
) -> None:
    logger.debug(SEP)
    logger.debug("Sending data to Rerun.")
    rr.init("evo_traj", recording_id=args.rerun_rec_id)
    rr.spawn(port=SETTINGS.rerun_viewer_port)
    client = ViewerClient(
        addr=f"rerun+http://127.0.0.1:{SETTINGS.rerun_viewer_port}/proxy"
    )

    # Send statistics table first (dedicated view, not part of visualization blueprint).
    stats_df = pandas_bridge.trajectories_stats_to_df(
        bundle.all_trajectories(
            name_transform=lambda n: to_compact_name(n, args)
        )
    ).reset_index()
    client.send_table(
        "evo_traj stats", pa.Table.from_pandas(stats_df).to_batches()
    )

    has_speed = any(
        isinstance(t, PoseTrajectory3D)
        for t in list(bundle.trajectories.values())
        + ([bundle.ref_traj] if bundle.ref_traj else [])
    )

    send_blueprint(bundle, has_speed, args, to_compact_name)
    revo.send_view_coordinates(PlotMode(args.plot_mode))

    get_color = get_color_generator(len(bundle.trajectories))

    def to_rgba_color(rgb):
        return to_rgba(rgb, alpha=SETTINGS.plot_trajectory_alpha)

    if bundle.ref_traj:
        revo.send_trajectory(
            entity_path="evo_traj/reference",
            traj=bundle.ref_traj,
            color=revo.Color(
                static=to_rgba(
                    SETTINGS.plot_reference_color,
                    alpha=SETTINGS.plot_reference_alpha,
                )
            ),
        )

        revo.send_xyz_position_scalars(
            traj=bundle.ref_traj,
            color=revo.Color(
                static=to_rgba(
                    SETTINGS.plot_reference_color,
                    alpha=SETTINGS.plot_reference_alpha,
                )
            ),
            x_entity="evo_traj/time_series/x/reference",
            y_entity="evo_traj/time_series/y/reference",
            z_entity="evo_traj/time_series/z/reference",
        )
        revo.send_rpy_scalars(
            traj=bundle.ref_traj,
            color=revo.Color(
                static=to_rgba(
                    SETTINGS.plot_reference_color,
                    alpha=SETTINGS.plot_reference_alpha,
                )
            ),
            roll_entity="evo_traj/time_series/roll/reference",
            pitch_entity="evo_traj/time_series/pitch/reference",
            yaw_entity="evo_traj/time_series/yaw/reference",
        )
        if isinstance(bundle.ref_traj, PoseTrajectory3D):
            try:
                revo.send_scalars(
                    entity_path="evo_traj/time_series/speed/reference",
                    scalars=bundle.ref_traj.speeds,
                    color=revo.Color(
                        static=to_rgba(
                            SETTINGS.plot_reference_color,
                            alpha=SETTINGS.plot_reference_alpha,
                        )
                    ),
                    timestamps=bundle.ref_traj.timestamps[1:],
                    labelname="v (m/s)",
                )
            except TrajectoryException as error:
                logger.error(
                    f"Can't send speeds of 'reference' to Rerun: {error}"
                )

    for name, traj in bundle.trajectories.items():
        color = get_color()
        entity_path = f"evo_traj/{to_compact_name(name, args)}"

        revo.send_trajectory(
            entity_path=entity_path,
            traj=traj,
            color=revo.Color(static=to_rgba_color(color)),
        )

        if (
            bundle.ref_traj
            and bundle.synced
            and SETTINGS.plot_pose_correspondences
        ):
            revo.send_correspondence_strips(
                entity_path=f"{entity_path}/correspondences",
                traj_1=traj,
                traj_2=bundle.synced_refs[name],
                color=revo.Color(static=to_rgba_color(color)),
                radii=revo.ui_points_radii(SETTINGS.plot_linewidth / 2.0),
            )

        revo.send_xyz_position_scalars(
            traj=traj,
            color=revo.Color(static=to_rgba_color(color)),
            x_entity=f"evo_traj/time_series/x/{to_compact_name(name, args)}",
            y_entity=f"evo_traj/time_series/y/{to_compact_name(name, args)}",
            z_entity=f"evo_traj/time_series/z/{to_compact_name(name, args)}",
        )
        revo.send_rpy_scalars(
            traj=traj,
            color=revo.Color(static=to_rgba_color(color)),
            roll_entity=f"evo_traj/time_series/roll/{to_compact_name(name, args)}",
            pitch_entity=f"evo_traj/time_series/pitch/{to_compact_name(name, args)}",
            yaw_entity=f"evo_traj/time_series/yaw/{to_compact_name(name, args)}",
        )
        if isinstance(traj, PoseTrajectory3D):
            try:
                revo.send_scalars(
                    entity_path=f"evo_traj/time_series/speed/{to_compact_name(name, args)}",
                    scalars=traj.speeds,
                    color=revo.Color(static=to_rgba_color(color)),
                    timestamps=traj.timestamps[1:],
                    labelname="v (m/s)",
                )
            except TrajectoryException as error:
                logger.error(
                    f"Can't send speeds of '{to_compact_name(name, args)}' to Rerun: {error}"
                )


def send_blueprint(
    bundle: TrajectoryBundle,
    has_speed: bool,
    args: argparse.Namespace,
    to_compact_name: Callable,
) -> None:
    any_timestamped = any(
        isinstance(t, PoseTrajectory3D)
        for t in list(bundle.trajectories.values())
        + ([bundle.ref_traj] if bundle.ref_traj else [])
    )
    timeline = revo.TIMELINE if any_timestamped else revo.INDEX_TIMELINE

    time_range = rrb.VisibleTimeRange(
        timeline=timeline,
        start=rrb.TimeRangeBoundary.infinite(),
        end=rrb.TimeRangeBoundary.cursor_relative(
            seconds=0.0 if any_timestamped else 0
        ),
    )

    xyz_views = []
    for label in ("x", "y", "z"):
        xyz_views.append(
            rrb.TimeSeriesView(
                name=label.upper(),
                time_ranges=time_range,
                plot_legend=rrb.PlotLegend(visible=False),
                contents=[f"/evo_traj/time_series/{label}/**"],
                axis_x=rrb.TimeAxis(link="LinkToGlobal"),
            ),
        )

    rpy_views = []
    for label in ("roll", "pitch", "yaw"):
        rpy_views.append(
            rrb.TimeSeriesView(
                name=label.capitalize(),
                time_ranges=time_range,
                plot_legend=rrb.PlotLegend(visible=False),
                contents=[f"/evo_traj/time_series/{label}/**"],
                axis_x=rrb.TimeAxis(link="LinkToGlobal"),
            ),
        )

    # Stack x/y/z and r/p/y vertically each, with speed next to it.
    plots_contents: list[rrb.Vertical | rrb.TimeSeriesView] = [
        rrb.Vertical(name="Position", contents=xyz_views),
        rrb.Vertical(name="Orientation", contents=rpy_views),
    ]
    if has_speed:
        plots_contents.append(
            rrb.TimeSeriesView(
                name="Speed",
                time_ranges=time_range,
                plot_legend=rrb.Corner2D.RightTop,
                contents=["/evo_traj/time_series/speed/**"],
                axis_x=rrb.TimeAxis(link="LinkToGlobal"),
            ),
        )

    rr.send_blueprint(
        rrb.Blueprint(
            rrb.Tabs(
                contents=[
                    rrb.Grid(
                        name="Visualization",
                        contents=[
                            rrb.Spatial3DView(
                                name="Trajectories",
                                time_ranges=time_range,
                            ),
                            rrb.Grid(
                                name="Plots",
                                contents=plots_contents,
                                column_shares=1,
                            ),
                        ],
                        column_shares=None,
                        row_shares=[2.5, 1.0],
                        grid_columns=1,
                    ),
                    rrb.DataframeView(
                        name="Raw Data",
                        origin="/evo_traj",
                        contents=[
                            "$origin/reference/transforms",
                            *[
                                f"$origin/{to_compact_name(n, args)}/transforms"
                                for n in bundle.trajectories
                            ],
                            "$origin/time_series/x/**",
                            "$origin/time_series/y/**",
                            "$origin/time_series/z/**",
                            "$origin/time_series/roll/**",
                            "$origin/time_series/pitch/**",
                            "$origin/time_series/yaw/**",
                        ],
                    ),
                ]
            ),
            rrb.SelectionPanel(expanded=False),
            rrb.TimePanel(expanded=False),
        )
    )
