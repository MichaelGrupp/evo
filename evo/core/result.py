# -*- coding: UTF8 -*-
"""
container class for results
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

from __future__ import print_function

import numpy as np


class Result(object):
    def __init__(self):
        self.info = {}
        self.stats = {}
        self.np_arrays = {}
        self.trajectories = {}

    def __str__(self):
        return self.pretty_str(stats=False).replace("\n", " ")

    def __eq__(self, other):
        if not isinstance(other, Result):
            return False
        equal = (self.info == other.info)
        equal &= (self.stats == other.stats)
        equal &= (self.trajectories == other.trajectories)
        for k in self.np_arrays:
            if k not in other.np_arrays:
                equal &= False
                break
            if not equal:
                break
            equal &= all([np.array_equal(self.np_arrays[k], other.np_arrays[k])])
        return equal

    def __ne__(self, other):
        return not self == other

    def pretty_str(self, title=True, stats=True, info=False):
        p_str = ""
        p_str += "{}\n\n".format(self.info["title"]) if title else ""
        if stats:
            for name, val in sorted(self.stats.items()):
                p_str += "{:>10}\t{:.6f}\n".format(name, val)
        if info:
            for name, val in sorted(self.info.items()):
                p_str += "{:>10}\t{}\n".format(name, val)
        return p_str

    def add_np_array(self, name, array):
        self.np_arrays[name] = array

    def add_info(self, info_dict):
        self.info.update(info_dict)

    def add_stats(self, stats_dict):
        self.stats.update(stats_dict)

    def add_trajectory(self, name, traj):
        self.trajectories[name] = traj


def from_metric(metric, title, ref_name, est_name):
    result = Result()
    metric_name = metric.__class__.__name__
    if hasattr(metric, "unit"):
        unit_name = metric.unit.value if metric.unit is not None else ""
    result.add_info({
        "title": title,
        "ref_name": ref_name,
        "est_name": est_name,
        "label": "{} {}".format(metric_name, "({})".format(unit_name))
    })
    result.add_stats(metric.get_all_statistics())
    if hasattr(metric, "error"):
        result.add_np_array("error_array", metric.error)
    return result
