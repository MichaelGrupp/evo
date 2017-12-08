#!/usr/bin/env python
"""
test & demo for metrics.APE
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

from __future__ import print_function  # Python 2.7 backwards compatibility

import logging
import pprint
import sys
import time
from timeit import timeit

import matplotlib.pyplot as plt

from evo.core import metrics, trajectory
from evo.tools import plot, file_interface

pretty_printer = pprint.PrettyPrinter(indent=4)
logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.DEBUG)

show_plots = False
align = True  # comparison to TUM script only valid for xyz_diff with alignment!

# load trajectories (examples from TUM benchmark)
ref_file = "data/freiburg1_xyz-groundtruth.txt"
est_file = "data/freiburg1_xyz-rgbdslam_drift.txt"
max_diff = 0.01
offset = 0.0
start = time.clock()
traj_ref, traj_est = file_interface.load_assoc_tum_trajectories(
    est_file,
    ref_file,
    max_diff,
    offset,
)
# align trajectories
print("\naligning trajectories...")
traj_est = trajectory.align_trajectory(traj_est, traj_ref)

stop = time.clock()
load_time = stop - start
print("elapsed time for trajectory loading (seconds): \t", "{0:.6f}".format(load_time))

"""
test absolute pose error algorithms
for different types of pose relations
"""
for pose_relation in metrics.PoseRelation:
    print("\n------------------------------------------------------------------\n")
    data = (traj_ref, traj_est)
    start = time.clock()

    ape_metric = metrics.APE(pose_relation)
    ape_metric.process_data(data)
    ape_stats = ape_metric.get_all_statistics()

    stop = time.clock()
    ape_time = stop-start
    print("APE statistics w.r.t. " + ape_metric.pose_relation.value + ": ")
    pretty_printer.pprint(ape_stats)
    print("\nelapsed time for running the APE algorithm (seconds):\t", "{0:.6f}".format(ape_time))
    print("elapsed time for trajectory loading and APE (seconds):\t", "{0:.6f}".format(load_time+ape_time))

    if show_plots:
        plot.error_array(ape_metric.error, statistics=ape_stats, name="APE w.r.t. " + ape_metric.pose_relation.value)

if show_plots:
    plt.show()

print("\n------------------------------------------------------------------")
print("------------------------------------------------------------------\n")
print("calling offical TUM ATE script for comparison...")
cmd = ["tum_benchmark_tools/evaluate_ate.py", ref_file, est_file, "--max_difference", str(max_diff), "--verbose"]
time_cmd = timeit(stmt="sp.call("+str(cmd)+")", setup="import subprocess as sp", number=1)

print("\nelapsed time for full TUM ATE script (seconds):\t", "{0:.6f}".format(time_cmd))

