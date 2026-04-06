"""
Helper for calculating the absolute pose error (APE) metric, as used by evo_ape.
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

import logging

import numpy as np

from evo.core import lie_algebra, metrics
from evo.core.result import Result
from evo.core.trajectory import PosePath3D, PoseTrajectory3D, Plane

logger = logging.getLogger(__name__)

SEP = "-" * 80  # separator line


def ape(
    traj_ref: PosePath3D,
    traj_est: PosePath3D,
    pose_relation: metrics.PoseRelation,
    align: bool = False,
    correct_scale: bool = False,
    n_to_align: int = -1,
    align_origin: bool = False,
    ref_name: str = "reference",
    est_name: str = "estimate",
    change_unit: metrics.Unit | None = None,
    project_to_plane: Plane | None = None,
) -> Result:
    if align and align_origin:
        raise ValueError("align and align_origin can't be used simultaneously")

    # Align the trajectories.
    only_scale = correct_scale and not align
    alignment_transformation = None
    if align or correct_scale:
        logger.debug(SEP)
        alignment_transformation = lie_algebra.sim3(
            *traj_est.align(traj_ref, correct_scale, only_scale, n=n_to_align)
        )
    if align_origin:
        logger.debug(SEP)
        alignment_transformation = traj_est.align_origin(traj_ref)

    # Projection is done after potential 3D alignment & transformation steps.
    if project_to_plane:
        logger.debug(SEP)
        logger.debug(
            "Projecting trajectories to %s plane.", project_to_plane.value
        )
        traj_ref.project(project_to_plane)
        traj_est.project(project_to_plane)

    # Calculate APE.
    logger.debug(SEP)
    data = (traj_ref, traj_est)
    ape_metric = metrics.APE(pose_relation)
    ape_metric.process_data(data)

    if change_unit:
        ape_metric.change_unit(change_unit)

    title = str(ape_metric)
    if align and not correct_scale:
        title += "\n(with SE(3) Umeyama alignment)"
    elif align and correct_scale:
        title += "\n(with Sim(3) Umeyama alignment)"
    elif only_scale:
        title += "\n(scale corrected)"
    elif not align_origin:
        title += "\n(not aligned)"
    if (align or correct_scale) and n_to_align != -1:
        title += f" (aligned poses: {n_to_align})"
    if align_origin:
        title += "\n(with origin alignment)"

    if project_to_plane:
        title += f"\n(projected to {project_to_plane.value} plane)"

    ape_result = ape_metric.get_result(ref_name, est_name)
    ape_result.info["title"] = title

    logger.debug(SEP)
    logger.info(ape_result.pretty_str())

    ape_result.add_trajectory(ref_name, traj_ref)
    ape_result.add_trajectory(est_name, traj_est)
    if isinstance(traj_est, PoseTrajectory3D):
        seconds_from_start = np.array(
            [t - traj_est.timestamps[0] for t in traj_est.timestamps]
        )
        ape_result.add_np_array("seconds_from_start", seconds_from_start)
        ape_result.add_np_array("timestamps", traj_est.timestamps)
        ape_result.add_np_array("distances_from_start", traj_ref.distances)
        ape_result.add_np_array("distances", traj_est.distances)

    if alignment_transformation is not None:
        ape_result.add_np_array(
            "alignment_transformation_sim3", alignment_transformation
        )

    return ape_result
