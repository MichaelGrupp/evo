"""
CLI run() for the relative pose error (RPE) metric.
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

import evo.cli.common_ape_rpe as common
from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D, Plane
from evo.main_rpe import rpe
from evo.tools import file_interface, log
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80


def run(args: argparse.Namespace) -> None:
    log.configure_logging(
        args.verbose, args.silent, args.debug, local_logfile=args.logfile
    )
    if args.debug:
        from pprint import pformat

        parser_str = pformat({arg: getattr(args, arg) for arg in vars(args)})
        logger.debug(f"main_parser config:\n{parser_str}")
    logger.debug(SEP)

    traj_ref, traj_est, ref_name, est_name = common.load_trajectories(args)
    pose_relation = common.get_pose_relation(args)
    delta_unit = common.get_delta_unit(args)
    change_unit = metrics.Unit(args.change_unit) if args.change_unit else None
    plane = Plane(args.project_to_plane) if args.project_to_plane else None

    traj_ref_full = None
    if args.plot_full_ref:
        import copy

        traj_ref_full = copy.deepcopy(traj_ref)

    # Downsample or filtering has to be done before synchronization.
    # Otherwise filtering might mess up the sync.
    common.downsample_or_filter(args, traj_ref, traj_est)

    if isinstance(traj_ref, PoseTrajectory3D) and isinstance(
        traj_est, PoseTrajectory3D
    ):
        logger.debug(SEP)
        if args.t_start or args.t_end:
            if args.t_start:
                logger.info(f"Using time range start: {args.t_start}s")
            if args.t_end:
                logger.info(f"Using time range end: {args.t_end}s")
            traj_ref.reduce_to_time_range(args.t_start, args.t_end)
        logger.debug("Synchronizing trajectories...")
        traj_ref, traj_est = sync.associate_trajectories(
            traj_ref,
            traj_est,
            args.t_max_diff,
            args.t_offset,
            first_name=ref_name,
            snd_name=est_name,
        )

    result = rpe(
        traj_ref=traj_ref,
        traj_est=traj_est,
        pose_relation=pose_relation,
        delta=args.delta,
        delta_unit=delta_unit,
        rel_delta_tol=args.delta_tol,
        all_pairs=args.all_pairs,
        pairs_from_reference=args.pairs_from_reference,
        align=args.align,
        correct_scale=args.correct_scale,
        n_to_align=args.n_to_align,
        align_origin=args.align_origin,
        ref_name=ref_name,
        est_name=est_name,
        change_unit=change_unit,
        project_to_plane=plane,
    )

    if args.rerun:
        common.send_result_to_rerun(
            "evo_rpe",
            result,
            traj_ref,
            traj_est,
            args,
        )

    if args.plot or args.save_plot:
        common.plot_result(
            args,
            result,
            traj_ref,
            result.trajectories[est_name],
            traj_ref_full=traj_ref_full,
        )

    if args.save_results:
        logger.debug(SEP)
        if not SETTINGS.save_traj_in_zip:
            del result.trajectories[ref_name]
            del result.trajectories[est_name]
        file_interface.save_res_file(
            args.save_results, result, confirm_overwrite=not args.no_warnings
        )
