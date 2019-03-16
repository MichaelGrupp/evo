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

import copy
import logging

import numpy as np

from evo import EvoException

logger = logging.getLogger(__name__)


class ResultException(EvoException):
    pass


class Result(object):
    def __init__(self):
        self.info = {}
        self.stats = {}
        self.np_arrays = {}
        self.trajectories = {}

    def __str__(self):
        return self.pretty_str(stats=True)

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
            equal &= all(
                [np.array_equal(self.np_arrays[k], other.np_arrays[k])])
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


def merge_results(results):
    if not results or not all(isinstance(r, Result) for r in results):
        raise ValueError("no results to merge")
    if len(results) == 1:
        return results[0]

    # Check if all results share keys for "stats" and "np_arrays" dicts.
    dict_lists = [[r.np_arrays for r in results], [r.stats for r in results]]
    for dicts in dict_lists:
        if not all(a.keys() == b.keys() for a, b in zip(dicts, dicts[1:])):
            raise ResultException("can't merge results with non-matching keys")

    # Determine merge strategy:
    strategy = "average"
    length_lists = [[a.size for a in r.np_arrays.values()] for r in results]
    if not all(a == b for a, b in zip(length_lists, length_lists[1:])):
        logger.warning("Appending raw value arrays due to different lengths.")
        strategy = "append"
    else:
        logger.info("Averaging raw values of input results in merged result.")

    merged_result = copy.deepcopy(results[0])
    logger.warning("Using info dict of first result.")
    for result in results[1:]:
        merged_result.stats = {
            key: ((merged_result.stats[key] + result.stats[key]) / 2)
            for key in merged_result.stats
        }
        if strategy == "average":
            merged_result.np_arrays = {
                key: np.mean(
                    np.array(
                        [merged_result.np_arrays[key], result.np_arrays[key]]),
                    axis=0)
                for key in result.np_arrays
            }
        elif strategy == "append":
            merged_result.np_arrays = {
                key: np.append(merged_result.np_arrays[key],
                               result.np_arrays[key])
                for key in result.np_arrays
            }

    return merged_result
