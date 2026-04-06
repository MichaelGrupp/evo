"""
Helper for calculating the relative pose error (RPE) metric, as used by evo_rpe.
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


def rpe(
    traj_ref: PosePath3D,
    traj_est: PosePath3D,
    pose_relation: metrics.PoseRelation,
    delta: float,
    delta_unit: metrics.Unit,
    rel_delta_tol: float = 0.1,
    all_pairs: bool = False,
    pairs_from_reference: bool = False,
    align: bool = False,
    correct_scale: bool = False,
    n_to_align: int = -1,
    align_origin: bool = False,
    ref_name: str = "reference",
    est_name: str = "estimate",
    support_loop: bool = False,
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

    # Calculate RPE.
    logger.debug(SEP)
    data = (traj_ref, traj_est)
    rpe_metric = metrics.RPE(
        pose_relation,
        delta,
        delta_unit,
        rel_delta_tol,
        all_pairs,
        pairs_from_reference,
    )
    rpe_metric.process_data(data)

    if change_unit:
        rpe_metric.change_unit(change_unit)

    title = str(rpe_metric)
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

    rpe_result = rpe_metric.get_result(ref_name, est_name)
    rpe_result.info["title"] = title
    logger.debug(SEP)
    logger.info(rpe_result.pretty_str())

    # Restrict trajectories to delta ids for further processing steps.
    if support_loop:
        # Avoid overwriting if called repeatedly e.g. in Jupyter notebook.
        import copy

        traj_ref = copy.deepcopy(traj_ref)
        traj_est = copy.deepcopy(traj_est)
    # Note: the pose at index 0 is added for plotting purposes, although it has
    # no RPE value assigned to it since it has no previous pose.
    # (for each pair (i, j), the 'delta_ids' represent only j)
    delta_ids_with_first_pose = [0] + rpe_metric.delta_ids
    traj_ref.reduce_to_ids(delta_ids_with_first_pose)
    traj_est.reduce_to_ids(delta_ids_with_first_pose)
    rpe_result.add_trajectory(ref_name, traj_ref)
    rpe_result.add_trajectory(est_name, traj_est)

    if isinstance(traj_est, PoseTrajectory3D):
        seconds_from_start = np.array(
            [t - traj_est.timestamps[0] for t in traj_est.timestamps]
        )
        # Save times/distances of each calculated value.
        # Note: here the first index needs that was added before needs to be
        # ignored again as it's not relevant for the values (see above).
        rpe_result.add_np_array("seconds_from_start", seconds_from_start[1:])
        rpe_result.add_np_array("timestamps", traj_est.timestamps[1:])
        rpe_result.add_np_array("distances_from_start", traj_ref.distances[1:])
        rpe_result.add_np_array("distances", traj_est.distances[1:])

    if alignment_transformation is not None:
        rpe_result.add_np_array(
            "alignment_transformation_sim3", alignment_transformation
        )

    return rpe_result
