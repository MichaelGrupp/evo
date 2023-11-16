#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
Main executable for calculating the absolute pose error (APE) metric.
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
import typing

import numpy as np

import evo.common_ape_rpe as common
from evo.core import lie_algebra, sync, metrics
from evo.core.result import Result
from evo.core.trajectory import PosePath3D, PoseTrajectory3D, ProjectionPlane
from evo.tools import file_interface, log
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80  # separator line


def ape(traj_ref: PosePath3D, traj_est: PosePath3D,
        pose_relation: metrics.PoseRelation, align: bool = False,
        correct_scale: bool = False, n_to_align: int = -1,
        align_origin: bool = False, ref_name: str = "reference",
        est_name: str = "estimate",
        change_unit: typing.Optional[metrics.Unit] = None,
        project_to_plane: typing.Optional[ProjectionPlane] = None) -> Result:

    # Align the trajectories.
    only_scale = correct_scale and not align
    alignment_transformation = None
    if align or correct_scale:
        logger.debug(SEP)
        alignment_transformation = lie_algebra.sim3(
            *traj_est.align(traj_ref, correct_scale, only_scale, n=n_to_align))
    elif align_origin:
        logger.debug(SEP)
        alignment_transformation = traj_est.align_origin(traj_ref)

    # Projection is done after potential 3D alignment & transformation steps.
    if project_to_plane:
        logger.debug(SEP)
        logger.debug(
            f"Projecting trajectories to {project_to_plane.value} plane.")
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
    elif align_origin:
        title += "\n(with origin alignment)"
    else:
        title += "\n(not aligned)"
    if (align or correct_scale) and n_to_align != -1:
        title += " (aligned poses: {})".format(n_to_align)

    ape_result = ape_metric.get_result(ref_name, est_name)
    ape_result.info["title"] = title

    logger.debug(SEP)
    logger.info(ape_result.pretty_str())

    ape_result.add_trajectory(ref_name, traj_ref)
    ape_result.add_trajectory(est_name, traj_est)
    if isinstance(traj_est, PoseTrajectory3D):
        seconds_from_start = np.array(
            [t - traj_est.timestamps[0] for t in traj_est.timestamps])
        ape_result.add_np_array("seconds_from_start", seconds_from_start)
        ape_result.add_np_array("timestamps", traj_est.timestamps)
        ape_result.add_np_array("distances_from_start", traj_ref.distances)
        ape_result.add_np_array("distances", traj_est.distances)

    if alignment_transformation is not None:
        ape_result.add_np_array("alignment_transformation_sim3",
                                alignment_transformation)

    return ape_result


def run(args: argparse.Namespace) -> None:
    log.configure_logging(args.verbose, args.silent, args.debug,
                          local_logfile=args.logfile)
    if args.debug:
        from pprint import pformat
        parser_str = pformat({arg: getattr(args, arg) for arg in vars(args)})
        logger.debug("main_parser config:\n{}".format(parser_str))
    logger.debug(SEP)

    traj_ref, traj_est, ref_name, est_name = common.load_trajectories(args)

    traj_ref_full = None
    if args.plot_full_ref:
        import copy
        traj_ref_full = copy.deepcopy(traj_ref)

    if isinstance(traj_ref, PoseTrajectory3D) and isinstance(
            traj_est, PoseTrajectory3D):
        logger.debug(SEP)
        if args.t_start or args.t_end:
            if args.t_start:
                logger.info("Using time range start: {}s".format(args.t_start))
            if args.t_end:
                logger.info("Using time range end: {}s".format(args.t_end))
            traj_ref.reduce_to_time_range(args.t_start, args.t_end)
        logger.debug("Synchronizing trajectories...")
        traj_ref, traj_est = sync.associate_trajectories(
            traj_ref, traj_est, args.t_max_diff, args.t_offset,
            first_name=ref_name, snd_name=est_name)

    pose_relation = common.get_pose_relation(args)
    change_unit = metrics.Unit(args.change_unit) if args.change_unit else None
    plane = ProjectionPlane(
        args.project_to_plane) if args.project_to_plane else None

    result = ape(traj_ref=traj_ref, traj_est=traj_est,
                 pose_relation=pose_relation, align=args.align,
                 correct_scale=args.correct_scale, n_to_align=args.n_to_align,
                 align_origin=args.align_origin, ref_name=ref_name,
                 est_name=est_name, change_unit=change_unit,
                 project_to_plane=plane)

    if args.plot or args.save_plot or args.serialize_plot:
        common.plot_result(args, result, traj_ref,
                           result.trajectories[est_name],
                           traj_ref_full=traj_ref_full)

    if args.save_results:
        logger.debug(SEP)
        if not SETTINGS.save_traj_in_zip:
            del result.trajectories[ref_name]
            del result.trajectories[est_name]
        file_interface.save_res_file(args.save_results, result,
                                     confirm_overwrite=not args.no_warnings)


if __name__ == '__main__':
    from evo import entry_points
    entry_points.ape()
