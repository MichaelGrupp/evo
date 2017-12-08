#!/usr/bin/env python
"""
test & demo for metrics.RPE
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

from evo.core import metrics
from evo.tools import file_interface

pretty_printer = pprint.PrettyPrinter(indent=4)
logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.DEBUG)

# load trajectories (examples from TUM benchmark)
ref_file = "data/freiburg1_xyz-groundtruth.txt"
est_file = "data/freiburg1_xyz-rgbdslam.txt"
max_diff = 0.01
offset = 0.0
start = time.clock()
traj_ref, traj_est = file_interface.load_assoc_tum_trajectories(
    est_file,
    ref_file,
    max_diff,
    offset,
)

stop = time.clock()
load_time = stop - start
print("elapsed time for trajectory loading (seconds): \t", "{0:.6f}".format(load_time))

"""
test relative pose error algorithms
for different types of pose relations
"""
delta = 1
delta_unit = metrics.Unit.frames

for pose_relation in metrics.PoseRelation:

    data = (traj_ref, traj_est)
    print("\n------------------------------------------------------------------\n")
    start = time.clock()

    rpe_metric = metrics.RPE(pose_relation, delta, delta_unit)
    rpe_metric.process_data(data)
    rpe_statistics = rpe_metric.get_all_statistics()

    stop = time.clock()
    rpe_time = stop-start
    print("RPE statistics w.r.t. " + rpe_metric.pose_relation.value + ": ")
    pretty_printer.pprint(rpe_statistics)
    print("\nelapsed time for running the RPE algorithm (seconds):\t", "{0:.6f}".format(rpe_time))
    print("elapsed time for trajectory loading and RPE (seconds):\t", "{0:.6f}".format(load_time+rpe_time))


print("\n------------------------------------------------------------------")
print("------------------------------------------------------------------\n")
print("calling offical TUM RPE script for comparison...")
cmd = ["tum_benchmark_tools/evaluate_rpe.py", ref_file, est_file,
       "--delta", str(delta), "--delta_unit", 'f', "--verbose", '--fixed_delta']
time_cmd = timeit(stmt="sp.call("+str(cmd)+")", setup="import subprocess as sp", number=1)

print("\nelapsed time for full TUM RPE script (seconds):\t", "{0:.6f}".format(time_cmd))
